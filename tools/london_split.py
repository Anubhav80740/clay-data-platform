#!/usr/bin/env python3
"""Add supplementary slices to the London-pinned cells.

They cannot be partitioned (city is already pinned; postcodes/size/type/desc are
empty on this residue), but the parent still delivers EXPORT_LIMIT and we merge
by concatenation -- so any extra slice that fits under the cap adds whatever it
holds. Try boroughs via the free-form `locations` filter, then follower bands.
"""
import csv, hashlib, json, os, sys
import clay_lib as cl

apply = "--apply" in sys.argv
BOROUGHS = ["Camden","Islington","Hackney","Southwark","Lambeth","Wandsworth","Westminster",
 "Kensington","Chelsea","Fulham","Greenwich","Lewisham","Tower Hamlets","Newham","Haringey",
 "Brent","Ealing","Hounslow","Richmond","Kingston","Merton","Sutton","Croydon","Bromley",
 "Bexley","Havering","Redbridge","Barking","Enfield","Barnet","Harrow","Hillingdon","Waltham Forest",
 "Shoreditch","Canary Wharf","Mayfair","Soho","Clerkenwell","Holborn","Paddington","Victoria"]
fh = lambda d: hashlib.md5(json.dumps(d, sort_keys=True).encode()).hexdigest()[:10]

tot_add = tot_rows = 0
for r in [x for x in csv.DictReader(open("United_Kingdom_nontech_counts.csv"))
          if x["Count"].isdigit() and int(x["Count"]) > 0]:
    ind = r["Industry"]
    pf = "%s/clicklist_%s.json" % (cl.PLAN_DIR, cl.slugify("%s_United Kingdom" % ind))
    if not os.path.exists(pf):
        continue
    plan = json.load(open(pf)); changed = False
    for leaf in list(plan):
        if not leaf.get("oversized") or not leaf["filters"].get("location_cities_include"):
            continue
        f = leaf["filters"]; live = cl.count(f) or 0
        if live <= cl.EXPORT_LIMIT:
            continue
        need = live - cl.EXPORT_LIMIT
        adds, got = [], 0
        for b in BOROUGHS:
            if got >= need:
                break
            n = cl.count({**f, "locations": [b]}) or 0
            if n and n <= cl.EXPORT_LIMIT:
                sf = {**f, "locations": [b]}
                adds.append({"slug": cl.slugify("%s_ldn_%s_%s" % (cl.slugify("%s_United Kingdom" % ind), b, fh(sf))),
                             "count": n, "oversized": False, "filters": sf})
                got += n
        for fol in (2, 5, 10):
            if got >= need:
                break
            sf = {**f, "minimum_follower_count": fol}
            n = cl.count(sf) or 0
            if n and n <= cl.EXPORT_LIMIT:
                adds.append({"slug": cl.slugify("%s_fol%d_%s" % (cl.slugify("%s_United Kingdom" % ind), fol, fh(sf))),
                             "count": n, "oversized": False, "filters": sf})
                got += n
        if adds:
            tot_add += len(adds); tot_rows += got
            print("%-32s cell %7s need %6s -> +%2d slices covering %6s (%.0f%%)" %
                  (ind[:30], format(live, ","), format(need, ","), len(adds), format(got, ","),
                   100*min(got, need)/need), flush=True)
            if apply:
                plan.extend(adds); changed = True
    if apply and changed:
        json.dump(plan, open(pf, "w"), indent=1)
print("\n+%d slices, ~%s rows of overflow recovery" % (tot_add, format(tot_rows, ",")))
print("APPLIED" if apply else "dry run")
