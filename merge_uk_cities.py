#!/usr/bin/env python3
"""One-off: fold the colleague's flat UK_CITIES into our state-scoped GEO. Our
city dim is scoped (parent_map state->cities), so each city must land under the
right state or it just yields 0 and wastes a count call. Probe, then patch."""
import importlib.util
import pathlib
import re

import clay_lib as cl
import clay_geo

THEIRS = ("/private/tmp/claude-501/-Users-prasad-dev-dts/"
          "e2ece590-34ac-4867-abba-5aa0ee9a2e39/scratchpad/colleague/clay_geo.py")
spec = importlib.util.spec_from_file_location("theirs", THEIRS)
t = importlib.util.module_from_spec(spec); spec.loader.exec_module(t)

states = clay_geo.GEO["United Kingdom"]["states"]
mine = {c for cs in states.values() for c in cs}
missing = [c for c in t.UK_CITIES if c not in mine]
print(f"{len(missing)} cities to place")

base = {"industries": ["Construction"], "country_names": ["United Kingdom"]}
placed = {s: [] for s in states}
for c in missing:
    best, bestn = None, 0
    for st in states:
        n = cl.count({**base, "location_states_include": [st],
                      "location_cities_include": [c]}) or 0
        if n > bestn:
            best, bestn = st, n
    if best:
        placed[best].append(c)
        print(f"  {c:22} -> {best} ({bestn})")
    else:
        print(f"  {c:22} -> (no data, skipped)")

p = pathlib.Path("clay_geo.py"); s = p.read_text()
for st, cities in placed.items():
    if not cities:
        continue
    m = re.search(rf'("{re.escape(st)}"\s*:\s*\[)', s)
    ins = m.end()
    s = s[:ins] + "\n            " + ", ".join(f'"{c}"' for c in cities) + "," + s[ins:]
p.write_text(s)
print("\nadded:", {k: len(v) for k, v in placed.items() if v})
