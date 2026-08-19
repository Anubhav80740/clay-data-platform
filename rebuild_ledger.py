#!/usr/bin/env python3
"""Rebuild <Country>_nontech_progress.csv from what's on disk: Clay's count vs
rows actually downloaded vs unique companies. Free -- reads local CSVs only.

Usage: python3 rebuild_ledger.py "Canada"
"""
import csv
import os
import sys

import clay_lib as cl
from run_nontech import delivery_name, tally

country = sys.argv[1]
counts = f"{cl.slugify(country)}_nontech_counts.csv"
if not os.path.exists(counts):                       # Canada's sheet predates count_industries.py
    counts = f"../{country} Non-Tech Industries Counts.csv"
col = "Count" if "nontech_counts" in counts else f"{country}_Count"

with open(counts) as f:
    rows = [r for r in csv.DictReader(f)
            if r.get("Industry") and str(r[col]).isdigit() and int(r[col]) > 0]
rows.sort(key=lambda r: -int(r[col]))

out = f"{cl.slugify(country)}_nontech_progress.csv"
n = te = tr = tu = 0
with open(out, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["industry", "clay_count", "rows_downloaded", "unique_companies",
                "coverage_pct", "file"])
    for r in rows:
        ind, exp = r["Industry"], int(r[col])
        dst = os.path.join("delivery", delivery_name(country, ind))
        if not os.path.exists(dst):
            continue
        dl, uniq = tally(dst)
        n += 1; te += exp; tr += dl; tu += uniq
        w.writerow([ind, exp, dl, uniq, round(100 * uniq / exp, 1) if exp else "", dst])

print(f"{out}: {n} industries | clay {te:,} | downloaded {tr:,} | unique {tu:,} "
      f"| {100*tu/te:.1f}%" if te else out)
