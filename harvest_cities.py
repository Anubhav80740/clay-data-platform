#!/usr/bin/env python3
"""Learn city names from the rows we already pulled.

The oversized cells are "state, NOT IN [our city list]" remainders -- so the
Location column of what we DID pull names exactly the cities our GEO list is
missing. Far better than guessing from memory: New York's list had no boroughs,
so Bronx/Queens/Staten Island were all piling into the remainder.
"""
import csv, glob, json, os, re, sys, collections
import clay_lib as cl
from clay_geo import GEO

MIN_HITS = 3          # ignore one-off / malformed location strings
apply = "--apply" in sys.argv
found = collections.defaultdict(collections.Counter)

for r in [x for x in csv.DictReader(open("United_States_nontech_counts.csv"))
          if x["Count"].isdigit() and int(x["Count"]) > 0]:
    pf = "%s/clicklist_%s.json" % (cl.PLAN_DIR, cl.slugify("%s_United States" % r["Industry"]))
    if not os.path.exists(pf):
        continue
    for s in json.load(open(pf)):
        if not s.get("oversized"):
            continue
        st = (s["filters"].get("location_states_include") or [None])[0]
        if not st:
            continue
        slug = cl.slugify(s["slug"]); p = "downloads/%s/%s.csv" % (slug, slug)
        if not os.path.exists(p):
            continue
        have = set(GEO["United States"]["states"].get(st, []))
        with open(p, newline="", encoding="utf-8", errors="replace") as f:
            rd = csv.reader(f); h = next(rd, None)
            if not h or "Location" not in h:
                continue
            li = h.index("Location")
            for row in rd:
                loc = row[li] if li < len(row) else ""
                parts = [x.strip() for x in loc.split(",")]
                # VERIFY the row's own state matches this cell's -- a slug collision
                # once fed New York rows into Ohio's file and taught "Bronx, Ohio".
                if len(parts) < 2 or parts[1] != st:
                    continue
                city = parts[0]
                if city and city not in have and not re.search(r"\d", city) and 2 < len(city) <= 30:
                    found[st][city] += 1

total = 0
for st, c in sorted(found.items()):
    keep = [k for k, v in c.most_common() if v >= MIN_HITS]
    total += len(keep)
    print("%-18s %4d new cities (of %d seen)  e.g. %s" % (st, len(keep), len(c), ", ".join(keep[:6])))

if apply:
    p = __import__("pathlib").Path("clay_geo.py"); s = p.read_text()
    for st, c in found.items():
        keep = [k for k, v in c.most_common() if v >= MIN_HITS]
        if not keep:
            continue
        m = re.search(r'("%s"\s*:\s*\[)' % re.escape(st), s)
        if not m:
            print("  !! %s not found in clay_geo.py" % st); continue
        s = s[:m.end()] + "\n            " + ", ".join('"%s"' % k.replace('"', "")
                                                       for k in keep) + "," + s[m.end():]
    p.write_text(s)
    print("\nAPPLIED: +%d cities to clay_geo.py" % total)
else:
    print("\nwould add %d cities -- re-run with --apply" % total)
