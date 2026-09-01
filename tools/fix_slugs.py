#!/usr/bin/env python3
"""Make every slug in a country's plans unique.

Two slug builders omitted the state, so cells differing only by state produced
identical slugs -- and download() skips any slug whose CSV exists, so the second
cell silently inherited the first's rows (New York data delivered as Ohio).
Filters are untouched; only names change. Non-colliding slugs keep their names
so already-downloaded slices stay skipped.
"""
import csv, hashlib, json, os, sys, collections
import clay_lib as cl

country = sys.argv[1]
apply = "--apply" in sys.argv
counts = "%s_nontech_counts.csv" % cl.slugify(country)

seen = collections.Counter()
plans = {}
for r in [x for x in csv.DictReader(open(counts)) if x["Count"].isdigit() and int(x["Count"]) > 0]:
    pf = "%s/clicklist_%s.json" % (cl.PLAN_DIR, cl.slugify("%s_%s" % (r["Industry"], country)))
    if not os.path.exists(pf):
        continue
    plan = json.load(open(pf)); plans[pf] = plan
    for s in plan:
        seen[cl.slugify(s["slug"])] += 1

dupes = {k for k, v in seen.items() if v > 1}
fixed = 0
for pf, plan in plans.items():
    changed = False
    for s in plan:
        if cl.slugify(s["slug"]) not in dupes:
            continue
        h = hashlib.md5(json.dumps(s["filters"], sort_keys=True).encode()).hexdigest()[:10]
        s["slug"] = "%s_%s" % (s["slug"], h)
        fixed += 1; changed = True
    if apply and changed:
        json.dump(plan, open(pf, "w"), indent=1)

after = collections.Counter()
for plan in plans.values():
    for s in plan:
        after[cl.slugify(s["slug"])] += 1
print("colliding slugs: %d (%d slices) -> after fix: %d" %
      (len(dupes), fixed, len([k for k, v in after.items() if v > 1])))
print("APPLIED" if apply else "dry run -- re-run with --apply")
