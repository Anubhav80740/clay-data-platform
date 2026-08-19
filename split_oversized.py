#!/usr/bin/env python3
"""
Re-split ONLY the oversized leaves of a country's plans, using the (expanded)
city lists. Each oversized cell becomes: one sub-slice per city that has data,
plus a city-exclude remainder. Everything else in the plan is untouched, so
already-downloaded slices keep their slugs and are skipped on the next run.

Reports, per cell, how much of it the sub-slices actually reach.

Usage: python3 split_oversized.py "United States" [--apply]
"""
import csv
import json
import os
import sys

import hashlib

import clay_lib as cl


def _fhash(f):
    """Slugs must encode the WHOLE filter set: two cells differing only by
    state produced identical slugs, and the second silently inherited the
    first's CSV (New York rows delivered as Ohio)."""
    return hashlib.md5(json.dumps(f, sort_keys=True).encode()).hexdigest()[:10]
from clay_geo import GEO

country = sys.argv[1]
apply = "--apply" in sys.argv
counts = "%s_nontech_counts.csv" % cl.slugify(country)
states = GEO[country]["states"]

rows, tot_cell, tot_reach_new, tot_reach_old = [], 0, 0, 0
for r in [x for x in csv.DictReader(open(counts)) if x["Count"].isdigit() and int(x["Count"]) > 0]:
    ind = r["Industry"]
    pf = "%s/clicklist_%s.json" % (cl.PLAN_DIR, cl.slugify("%s_%s" % (ind, country)))
    if not os.path.exists(pf):
        continue
    plan = json.load(open(pf))
    changed = False
    for leaf in list(plan):
        if not leaf.get("oversized"):
            continue
        f = leaf["filters"]
        st = (f.get("location_states_include") or [None])[0]
        if not st or st not in states:
            continue
        # A cell already pinned to a city (e.g. city=London) cannot be split this
        # way: setting location_cities_include would REPLACE London and silently
        # change what the slice means. Leave those to a different axis.
        if f.get("location_cities_include"):
            continue
        already = set(f.get("location_cities_exclude") or [])
        cand = [c for c in states[st] if c not in already]
        if not cand:
            continue
        live = cl.count(f) or 0
        subs, hit = [], []
        for c in cand:
            n = cl.count({**f, "location_cities_include": [c]}) or 0
            if not n:
                continue
            hit.append(c)
            sf = {**f, "location_cities_include": [c]}
            subs.append({"slug": cl.slugify("%s_city_%s_%s" % (cl.slugify("%s_%s" % (ind, country)), c, _fhash(sf))),
                         "count": n, "oversized": n > cl.EXPORT_LIMIT, "filters": sf})
        if not hit:
            continue
        # remainder: everything not in the newly-used cities (nor the old excludes)
        rf = {**f, "location_cities_exclude": sorted(already | set(hit))}
        rn = cl.count(rf) or 0
        if rn:
            subs.append({"slug": cl.slugify("%s_cityX_rest_%s" % (cl.slugify("%s_%s" % (ind, country)), _fhash(rf))),
                         "count": rn, "oversized": rn > cl.EXPORT_LIMIT, "filters": rf})
        reach_new = sum(min(s["count"], cl.EXPORT_LIMIT) for s in subs)
        reach_old = min(live, cl.EXPORT_LIMIT)
        rows.append({"industry": ind, "state": st, "cell_size": live,
                     "sub_slices": len(subs), "cities_hit": len(hit),
                     "reach_before": reach_old, "reach_after": min(reach_new, live),
                     "reach_pct_before": round(100 * reach_old / live, 1) if live else 0,
                     "reach_pct_after": round(100 * min(reach_new, live) / live, 1) if live else 0,
                     "gain": max(0, min(reach_new, live) - reach_old)})
        tot_cell += live; tot_reach_new += min(reach_new, live); tot_reach_old += reach_old
        print("%-30s %-14s cell %7s -> %2d subs (%2d cities)  reach %5.1f%% -> %5.1f%%  +%s" %
              (ind[:28], st, format(live, ","), len(subs), len(hit),
               100*reach_old/live, 100*min(reach_new, live)/live, format(rows[-1]["gain"], ",")), flush=True)
        if apply:
            plan.remove(leaf); plan.extend(subs); changed = True
    if apply and changed:
        json.dump(plan, open(pf, "w"), indent=1)

with open("oversized_split_plan.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print("\n%d oversized cells | %s companies" % (len(rows), format(tot_cell, ",")))
print("reach: %s (%.1f%%) -> %s (%.1f%%)   +%s companies" %
      (format(tot_reach_old, ","), 100*tot_reach_old/tot_cell,
       format(tot_reach_new, ","), 100*tot_reach_new/tot_cell,
       format(tot_reach_new - tot_reach_old, ",")))
print("%s" % ("APPLIED to plans" if apply else "dry run -- re-run with --apply"))
