#!/usr/bin/env python3
"""
Split an oversized cell with the FEWEST slices that clear the cap.

Enumerating every city is wasteful: a cell 129 over the limit needs one city
with >=129 rows, not 1,800 count calls and a compaction pass afterwards. The
rows we already pulled give each city's frequency, so we can PICK a set that
sums to just over the excess, then verify with a handful of live counts.

  cell N -> buckets of <= CAP each, built greedily from the sampled frequencies,
  plus the exclude-remainder. Slices = ceil(N/CAP), which is the minimum possible.

Usage: python3 split_minimal.py "United Kingdom" [--apply]
"""
import csv, hashlib, json, os, re, sys, collections
import clay_lib as cl

country = sys.argv[1]
apply = "--apply" in sys.argv
CAP = cl.EXPORT_LIMIT
TARGET = 4500                      # leave headroom; live counts drift

def fhash(f):
    return hashlib.md5(json.dumps(f, sort_keys=True).encode()).hexdigest()[:10]

rows_out, tot_before, tot_after, tot_slices = [], 0, 0, 0
for r in [x for x in csv.DictReader(open("%s_nontech_counts.csv" % cl.slugify(country)))
          if x["Count"].isdigit() and int(x["Count"]) > 0]:
    ind = r["Industry"]
    pf = "%s/clicklist_%s.json" % (cl.PLAN_DIR, cl.slugify("%s_%s" % (ind, country)))
    if not os.path.exists(pf):
        continue
    plan = json.load(open(pf)); changed = False
    for leaf in list(plan):
        if not leaf.get("oversized") or leaf["filters"].get("location_cities_include"):
            continue
        f = leaf["filters"]
        st = (f.get("location_states_include") or [None])[0]
        slug = cl.slugify(leaf["slug"]); p = "downloads/%s/%s.csv" % (slug, slug)
        if not st or not os.path.exists(p):
            continue
        live = cl.count(f) or 0
        if live <= CAP:
            continue
        # city frequencies from the rows we already have (a CAP-sized sample)
        freq = collections.Counter()
        with open(p, newline="", encoding="utf-8", errors="replace") as fh:
            rd = csv.reader(fh); h = next(rd, None)
            if not h or "Location" not in h:
                continue
            li = h.index("Location")
            for row in rd:
                parts = [x.strip() for x in (row[li] if li < len(row) else "").split(",")]
                if len(parts) >= 2 and parts[1] == st and parts[0] and not re.search(r"\d", parts[0]):
                    freq[parts[0]] += 1
        if not freq:
            continue
        scale = live / max(1, sum(freq.values()))       # sample -> whole cell
        already = set(f.get("location_cities_exclude") or [])
        # greedy bin-pack the biggest cities into buckets of <= TARGET
        buckets, cur, cur_n = [], [], 0
        for city, n in freq.most_common():
            if city in already:
                continue
            est = n * scale
            if est > TARGET:                            # a city that big is its own bucket
                buckets.append([city]); continue
            if cur_n + est > TARGET:
                buckets.append(cur); cur, cur_n = [], 0
            cur.append(city); cur_n += est
            # stop once the remainder would fit
            if (live - sum(freq[c] * scale for b in buckets + [cur] for c in b)) <= TARGET:
                break
        if cur:
            buckets.append(cur)
        used = [c for b in buckets for c in b]
        subs = []
        for b in buckets:
            sf = {**f, "location_cities_include": sorted(b)}
            n = cl.count(sf) or 0
            if n:
                subs.append({"slug": cl.slugify("%s_cin%d_%s" % (cl.slugify("%s_%s" % (ind, country)), len(b), fhash(sf))),
                             "count": n, "oversized": n > CAP, "filters": sf})
        # The break above used a SAMPLED estimate, so the remainder can still be
        # over. Verify live and keep packing real cities until it genuinely fits.
        pool = [c for c, _ in freq.most_common() if c not in already and c not in set(used)]
        rf = {**f, "location_cities_exclude": sorted(already | set(used))}
        rn = cl.count(rf) or 0
        while rn > CAP and pool:
            b, est = [], 0
            while pool and est < TARGET:
                c = pool.pop(0); b.append(c); est += freq[c] * scale
            sf = {**f, "location_cities_include": sorted(b)}
            n = cl.count(sf) or 0
            if n:
                subs.append({"slug": cl.slugify("%s_cin%d_%s" % (cl.slugify("%s_%s" % (ind, country)), len(b), fhash(sf))),
                             "count": n, "oversized": n > CAP, "filters": sf})
            used += b
            rf = {**f, "location_cities_exclude": sorted(already | set(used))}
            rn = cl.count(rf) or 0
        if rn:
            subs.append({"slug": cl.slugify("%s_cX_rest_%s" % (cl.slugify("%s_%s" % (ind, country)), fhash(rf))),
                         "count": rn, "oversized": rn > CAP, "filters": rf})
        reach_before, reach_after = min(live, CAP), min(sum(min(s["count"], CAP) for s in subs), live)
        tot_before += reach_before; tot_after += reach_after; tot_slices += len(subs)
        print("%-32s cell %7s -> %2d slices (%3d cities)  %5.1f%% -> %5.1f%%  still over: %d" %
              (ind[:30], format(live, ","), len(subs), len(used),
               100*reach_before/live, 100*reach_after/live,
               sum(1 for s in subs if s["oversized"])), flush=True)
        if apply:
            plan.remove(leaf); plan.extend(subs); changed = True
    if apply and changed:
        json.dump(plan, open(pf, "w"), indent=1)

print("\ntotal new slices: %d | reach %s -> %s" % (tot_slices, format(tot_before, ","), format(tot_after, ",")))
print("APPLIED" if apply else "dry run -- re-run with --apply")
