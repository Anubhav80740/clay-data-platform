#!/usr/bin/env python3
"""Keep only the highest-frequency harvested cities per state.

The full harvest added ~3,950 names, which means ~700 count calls per oversized
cell during planning. The distribution is long-tailed: the top 50 carry 36-82%
of the rows while the tail contributes single-digit hits each. Trim to the top N
so planning stays cheap.

Usage: python3 trim_cities.py [N] [--apply]
"""
import collections, csv, json, os, re, sys
import clay_lib as cl
from clay_geo import GEO

N = int([a for a in sys.argv[1:] if a.isdigit()][0]) if any(a.isdigit() for a in sys.argv[1:]) else 50
apply = "--apply" in sys.argv

cnt = collections.defaultdict(collections.Counter)
for r in [x for x in csv.DictReader(open("United_States_nontech_counts.csv"))
          if x["Count"].isdigit() and int(x["Count"]) > 0]:
    pf = "%s/clicklist_%s.json" % (cl.PLAN_DIR, cl.slugify("%s_United States" % r["Industry"]))
    if not os.path.exists(pf):
        continue
    for s in json.load(open(pf)):
        if not s.get("oversized"):
            continue
        st = (s["filters"].get("location_states_include") or [None])[0]
        slug = cl.slugify(s["slug"]); p = "downloads/%s/%s.csv" % (slug, slug)
        if not st or not os.path.exists(p):
            continue
        with open(p, newline="", encoding="utf-8", errors="replace") as f:
            rd = csv.reader(f); h = next(rd, None)
            if not h or "Location" not in h:
                continue
            li = h.index("Location")
            for row in rd:
                parts = [x.strip() for x in (row[li] if li < len(row) else "").split(",")]
                if len(parts) < 2 or parts[1] != st:
                    continue
                if parts[0] and not re.search(r"\d", parts[0]) and 2 < len(parts[0]) <= 30:
                    cnt[st][parts[0]] += 1

import pathlib
p = pathlib.Path("clay_geo.py"); src = p.read_text()
removed = 0
for st, c in cnt.items():
    keep = {k for k, _ in c.most_common(N)}
    drop = [k for k in c if k not in keep]
    cur = GEO["United States"]["states"].get(st, [])
    newlist = [x for x in cur if x not in set(drop)]
    removed += len(cur) - len(newlist)
    m = re.search(r'("%s"\s*:\s*\[)(.*?)(\])' % re.escape(st), src, re.S)
    if not m:
        print("  !! %s not found" % st); continue
    body = "\n            " + ", ".join('"%s"' % x for x in newlist) + ",\n        "
    src = src[:m.start(2)] + body + src[m.end(2):]
    print("  %-16s %4d -> %4d cities" % (st, len(cur), len(newlist)))
if apply:
    p.write_text(src)
    print("\nAPPLIED: removed %d long-tail cities (kept top %d per state)" % (removed, N))
else:
    print("\nwould remove %d -- re-run with --apply" % removed)
