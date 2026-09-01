"""
clay_maxpull -- maximize DISTINCT company coverage for one industry + country.

Idea: the "find companies" source returns a ranked subset per slice, so a single
slicing scheme only surfaces ~93% of the universe. Running the SAME universe
through all 6 orderings of (size, revenue, state) makes different companies land
at the top of each slice, so the union approaches the true maximum. Adaptive:
a slice stops splitting as soon as it's <= 5,000 (extra dims aren't added).

De-dup is by WHOLE ROW (not domain) -- the DB handles domain de-dup on insert,
so here we only drop exact-duplicate rows to keep the file lean.

Standalone: imports clay_lib for primitives; does NOT modify the main pipeline.
Outputs live under downloads_maxpull/ and clicklist_maxpull_*.json.

Usage:
  python3 clay_maxpull.py plan     "IT Services and IT Consulting" ["United States"]
  python3 clay_maxpull.py download "IT Services and IT Consulting" ["United States"]
  python3 clay_maxpull.py merge    "IT Services and IT Consulting" ["United States"]
"""
import csv
import glob
import json
import os
import sys

import clay_lib as cl
from clay_geo import GEO

BASE_DIR = "downloads_maxpull"

# The 6 orderings of the three flat, no-scope dimensions.
ORDERINGS = [
    ["revenue", "size", "state"],
    ["revenue", "state", "size"],
    ["size", "revenue", "state"],
    ["size", "state", "revenue"],
    ["state", "size", "revenue"],
    ["state", "revenue", "size"],
]


def dims_for(country):
    states = GEO.get(country, {}).get("states", {})
    STATE = cl.Dimension("state", "location_states_include", list(states.keys()),
                         exclude_key="location_states_exclude")
    return {"size": cl.SIZE, "revenue": cl.REVENUE, "state": STATE}


def prefix_for(industry, country):
    return cl.slugify(f"maxpull_{industry}_{country}")


def slug_for(prefix, f):
    parts = [prefix]
    for tag, key in [("sz", "sizes"), ("rev", "annual_revenues"),
                     ("st", "location_states_include")]:
        if f.get(key):
            parts.append(tag + "-" + "-".join(map(str, f[key])))
    if f.get("location_states_exclude"):
        parts.append(f"stX{len(f['location_states_exclude'])}")
    return cl.slugify("_".join(parts))


def _sig(f):
    """Filter signature for de-duping identical slices across orderings."""
    return json.dumps({k: sorted(v) if isinstance(v, list) else v
                       for k, v in f.items() if v not in (None, [], "")},
                      sort_keys=True)


# ---------------------------------------------------------------------------
def plan(industry, country):
    d = dims_for(country)
    base = {"industries": [industry], "country_names": [country]}
    prefix = prefix_for(industry, country)
    unique, dup = {}, 0
    for order in ORDERINGS:
        dims = [d[x] for x in order]
        stats = cl.PlanStats()
        cl.plan(base, prefix, dims, cl.count, stats)
        leaves = cl.consolidate(stats.leaves)
        cl.log(f"ordering {'>'.join(order)}: {len(leaves)} slices, "
               f"{len(stats.oversized)} oversized, calls={stats.count_calls}")
        for l in leaves:
            sig = _sig(l.filters)
            if sig in unique:
                dup += 1
                continue
            unique[sig] = {"slug": slug_for(prefix, l.filters), "count": l.count,
                           "oversized": l.oversized, "filters": l.filters}

    out = f"clicklist_{prefix}.json"
    with open(out, "w") as f:
        json.dump(list(unique.values()), f, indent=1)
    est = sum(v["count"] for v in unique.values())
    cl.log(f"UNIQUE slices across 6 orderings: {len(unique)}  "
           f"({dup} duplicate slices skipped)")
    cl.log(f"estimated rows to pull (~credits): {est:,}  -> {out}")


def download(industry, country, limit=5000):
    prefix = prefix_for(industry, country)
    slices = json.load(open(f"clicklist_{prefix}.json"))
    total, done, skipped = 0, 0, 0
    for i, s in enumerate(slices, 1):
        slug = cl.slugify(s["slug"])
        if os.path.exists(os.path.join(BASE_DIR, slug, slug + ".csv")):
            skipped += 1
            print(f"[{i}] SKIP (exists): {slug}", flush=True)
            continue
        print(f"[{i}/{len(slices)}] {slug} (~{s['count']} rows)", flush=True)
        try:
            resp, cnt = cl.create_table(s["filters"], name=slug[:60], limit=limit)
            tid, vid, sid = resp.get("tableId"), resp.get("viewId"), resp.get("sourceId")
            if not tid:
                print(f"   CREATE FAILED (retry next run): {str(resp)[:150]}", flush=True)
                continue
            cl.wait_populated(sid, min(cnt or s["count"] or 0, limit))
            got, path = cl.export_download(tid, vid, slug, base_dir=BASE_DIR)
            if not path:
                print("   EXPORT FAILED (retry next run)", flush=True)
                continue
            total += got or 0; done += 1
            print(f"   -> {got} rows -> {path}  (running total: {total:,})", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"   SLICE ERROR (retry next run): {e}", flush=True)
            continue
    print(f"\nDONE: {done} downloaded, {skipped} skipped, {total:,} rows total.")


def merge(industry, country):
    """De-dupe by WHOLE ROW across every downloaded slice."""
    prefix = prefix_for(industry, country)
    seen, rows, header = set(), [], None
    files = sorted(glob.glob(f"{BASE_DIR}/{prefix}*/*.csv"))
    for p in files:
        with open(p, newline="", encoding="utf-8", errors="replace") as f:
            r = csv.reader(f)
            h = next(r, None)
            if not h:
                continue
            header = header or h
            for row in r:
                key = tuple(row)
                if key in seen:
                    continue
                seen.add(key)
                rows.append(row)
    out = f"{BASE_DIR}/{prefix}_ALL_rowunique.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if header:
            w.writerow(header)
        w.writerows(rows)
    print(f"merged {len(files)} files -> {len(rows):,} whole-row-unique rows -> {out}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    industry = sys.argv[2] if len(sys.argv) > 2 else "Software Development"
    country = sys.argv[3] if len(sys.argv) > 3 else "United States"
    if mode == "plan":
        plan(industry, country)
    elif mode == "download":
        download(industry, country)
    elif mode == "merge":
        merge(industry, country)
    else:
        print('usage: plan|download|merge "<industry>" ["<country>"]')
