#!/usr/bin/env python3
"""
Delete slice CSVs whose pulled rows fall far short of the plan's stated count,
so the next download re-pulls them.

Why this exists: when the Clay workspace hit its 15M-row ceiling, views
materialised PARTIALLY -- a slice stating 5,000 rows would export 1, or 51.
That writes a valid, non-empty CSV, so every guard passes (file exists, not
header-only, industry total above the 10% floor) and the slice is silently
accepted as complete. Only stated-vs-pulled catches it.

Usage: python3 repair_truncated.py "United States" ["Industry|Industry"] [--apply]
"""
import csv
import glob
import json
import os
import shutil
import sys

import clay_lib as cl

MIN_STATED = 100      # ignore tiny slices, where a small delta is just churn
KEEP_RATIO = 0.75     # pulled/stated below this = truncated, not ranked-subset

country = sys.argv[1]
only = None
apply = "--apply" in sys.argv
verify = "--verify" in sys.argv   # live count-check each candidate before re-pulling
for a in sys.argv[2:]:
    if not a.startswith("--"):
        only = set(a.split("|"))

counts = f"{cl.slugify(country)}_nontech_counts.csv"
if not os.path.exists(counts):          # Canada's sheet predates count_industries.py
    counts = f"../{country} Non-Tech Industries Counts.csv"
col = "Count" if "nontech_counts" in counts else f"{country}_Count"
rows = [r for r in csv.DictReader(open(counts))
        if r.get("Industry") and str(r[col]).isdigit() and int(r[col]) > 0]

total_bad = total_rows = 0
for r in rows:
    ind = r["Industry"]
    if only and ind not in only:
        continue
    pre = cl.slugify(f"{ind}_{country}")
    pf = f"{cl.PLAN_DIR}/clicklist_{pre}.json"
    if not os.path.exists(pf):
        continue
    bad = []
    for s in json.load(open(pf)):
        slug = cl.slugify(s["slug"])
        p = os.path.join("downloads", slug, slug + ".csv")
        if not os.path.exists(p) or s["count"] < MIN_STATED:
            continue
        # An oversized leaf legitimately truncates at the export cap -- re-pulling
        # returns the same 5,000 rows. Not damage.
        if s.get("oversized"):
            continue
        with open(p, newline="", encoding="utf-8", errors="replace") as f:
            n = max(0, sum(1 for _ in csv.reader(f)) - 1)
        if n >= s["count"] * KEEP_RATIO:
            continue
        if verify:
            # Clay's own count drifts between planning and now. If it now agrees
            # with what we pulled, the data isn't there to re-fetch -- skip it.
            live = cl.count(s["filters"])
            if live is not None and live <= max(n * 1.25, n + 50):
                print(f"    skip (count drifted {s['count']}->{live}, we have {n}): {slug[:50]}")
                continue
        bad.append((slug, s["count"], n))
    if not bad:
        continue
    print(f"{ind}: {len(bad)} truncated slice(s)")
    for slug, stated, got in sorted(bad, key=lambda b: b[2] - b[1])[:6]:
        print(f"    {stated:>6} -> {got:<6} {slug[:64]}")
        total_rows += stated - got
    total_bad += len(bad)
    if apply:
        for slug, _, _ in bad:
            shutil.rmtree(os.path.join("downloads", slug), ignore_errors=True)

print(f"\n{'DELETED' if apply else 'WOULD DELETE'}: {total_bad} slices, "
      f"~{total_rows:,} rows to re-pull")
if not apply:
    print("re-run with --apply")
