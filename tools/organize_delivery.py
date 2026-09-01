#!/usr/bin/env python3
"""Collect the non-tech delivery CSVs into delivery/<Country>/non-tech/.

Membership comes from each country's counts sheet (the authoritative non-tech
list), not from filename guessing -- so the tech industries downloaded earlier
in the project stay out. Files are COPIED, not moved: run_nontech resumes by
checking for delivery/<name>.csv, so moving them would make a future re-run
re-download everything.
"""
import csv, os, shutil, sys
import clay_lib as cl
from run_nontech import delivery_name

apply = "--apply" in sys.argv
JOBS = [("United Kingdom", "UK", "United_Kingdom_nontech_counts.csv", "Count"),
        ("United States", "US", "United_States_nontech_counts.csv", "Count"),
        ("Canada", "Canada", "../Canada Non-Tech Industries Counts.csv", "Canada_Count")]

grand_n = grand_b = 0
for country, short, sheet, col in JOBS:
    if not os.path.exists(sheet):
        print("%-16s counts sheet missing: %s" % (short, sheet)); continue
    inds = [r["Industry"] for r in csv.DictReader(open(sheet))
            if r.get("Industry") and str(r[col]).isdigit() and int(r[col]) > 0]
    dest = os.path.join("delivery", short, "non-tech")
    if apply:
        os.makedirs(dest, exist_ok=True)
    n = b = missing = 0
    for ind in inds:
        src = os.path.join("delivery", delivery_name(country, ind))
        if not os.path.exists(src):
            missing += 1; continue
        b += os.path.getsize(src); n += 1
        if apply:
            shutil.copy2(src, os.path.join(dest, os.path.basename(src)))
    grand_n += n; grand_b += b
    print("%-8s %3d/%3d industries -> %-28s %6.2f GB%s" %
          (short, n, len(inds), dest, b/1e9, "   (%d missing)" % missing if missing else ""))
print("\n%s %d files, %.2f GB" % ("COPIED" if apply else "would copy", grand_n, grand_b/1e9))
if not apply:
    print("re-run with --apply")
