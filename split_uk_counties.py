#!/usr/bin/env python3
"""Re-split ONLY the UK oversized leaves by the counties the early-stop skipped.
Same shape as split_oversized.py but on the `locations` (county) axis, which is
where England's residue actually divides. Reports reach before/after."""
import csv, json, os, sys
import clay_lib as cl
from clay_geo import GEO

apply = "--apply" in sys.argv
counties = GEO["United Kingdom"]["counties"]
rows, tot_cell, tot_new, tot_old = [], 0, 0, 0

for r in [x for x in csv.DictReader(open("United_Kingdom_nontech_counts.csv"))
          if x["Count"].isdigit() and int(x["Count"]) > 0]:
    ind = r["Industry"]
    pf = "%s/clicklist_%s.json" % (cl.PLAN_DIR, cl.slugify("%s_United Kingdom" % ind))
    if not os.path.exists(pf):
        continue
    plan = json.load(open(pf)); changed = False
    for leaf in list(plan):
        if not leaf.get("oversized"):
            continue
        f = leaf["filters"]
        used = set(f.get("locations_exclude") or [])
        rest = [c for c in counties if c not in used]
        if not rest:
            continue
        live = cl.count(f) or 0
        if not live:
            continue
        subs, hit = [], []
        for c in rest:
            n = cl.count({**f, "locations": [c]}) or 0
            if not n:
                continue
            hit.append(c)
            subs.append({"slug": cl.slugify("%s_cty_%s_%d" % (cl.slugify("%s_United Kingdom" % ind), c, len(subs))),
                         "count": n, "oversized": n > cl.EXPORT_LIMIT,
                         "filters": {**f, "locations": [c]}})
        if not hit:
            continue
        rf = {**f, "locations_exclude": sorted(used | set(hit))}
        rn = cl.count(rf) or 0
        if rn:
            subs.append({"slug": cl.slugify("%s_ctyX%d_rest" % (cl.slugify("%s_United Kingdom" % ind), len(used)+len(hit))),
                         "count": rn, "oversized": rn > cl.EXPORT_LIMIT, "filters": rf})
        new = min(sum(min(s["count"], cl.EXPORT_LIMIT) for s in subs), live)
        old = min(live, cl.EXPORT_LIMIT)
        rows.append({"industry": ind, "cell_size": live, "sub_slices": len(subs), "counties_hit": len(hit),
                     "reach_before": old, "reach_after": new,
                     "pct_before": round(100*old/live, 1), "pct_after": round(100*new/live, 1),
                     "gain": max(0, new-old)})
        tot_cell += live; tot_new += new; tot_old += old
        print("%-34s cell %7s -> %2d subs (%2d counties)  %5.1f%% -> %5.1f%%  +%s" %
              (ind[:32], format(live, ","), len(subs), len(hit), 100*old/live, 100*new/live,
               format(rows[-1]["gain"], ",")), flush=True)
        if apply:
            plan.remove(leaf); plan.extend(subs); changed = True
    if apply and changed:
        json.dump(plan, open(pf, "w"), indent=1)

with open("uk_oversized_split.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print("\n%d cells | %s companies" % (len(rows), format(tot_cell, ",")))
print("reach %s (%.1f%%) -> %s (%.1f%%)   +%s" % (format(tot_old, ","), 100*tot_old/tot_cell,
      format(tot_new, ","), 100*tot_new/tot_cell, format(tot_new-tot_old, ",")))
print("APPLIED" if apply else "dry run -- re-run with --apply")
