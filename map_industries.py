#!/usr/bin/env python3
"""
TASK: map. One free count() per industry for a country (~33 calls). Produces
per-industry totals + a rough export-slice estimate, to size the job before
spending any credits. Pure counting -- what Clay's UI does on every filter change.

Usage: python3 map_industries.py ["United States"]
"""
import csv
import math
import sys
import time

import clay_lib as cl

ALL_INDUSTRIES = [
    "Software Development", "IT Services and IT Consulting",
    "Information Technology and Services", "Technology, Information and Internet",
    "Technology, Information and Media", "Computer Hardware",
    "Computer Hardware Manufacturing", "Computer Networking",
    "Computer Networking Products", "Computer and Network Security",
    "Computers and Electronics Manufacturing", "Data Infrastructure and Analytics",
    "Data Security Software Products", "Desktop Computing Software Products",
    "Mobile Computing Software Products", "Embedded Software Products",
    "Business Intelligence Platforms", "Semiconductors",
    "Semiconductor Manufacturing", "Internet Publishing",
    "Internet Marketplace Platforms", "Internet News", "Computer Games",
    "Mobile Gaming Apps", "Blockchain Services", "Social Networking Platforms",
    "IT System Custom Software Development", "IT System Data Services",
    "IT System Design Services", "IT System Installation and Disposal",
    "IT System Operations and Maintenance", "IT System Testing and Evaluation",
    "IT System Training and Support",
]


def main():
    country = sys.argv[1] if len(sys.argv) > 1 else "United States"
    rows, grand = [], 0
    print(f"{'count':>9}  {'~slices':>7}  industry   (country={country})")
    print("-" * 60)
    for ind in ALL_INDUSTRIES:
        c = cl.count({"industries": [ind], "country_names": [country]})
        if c is None:
            print(f"{'ERR':>9}  {'?':>7}  {ind}"); rows.append((ind, "", "")); continue
        slices = math.ceil(c / cl.EXPORT_LIMIT)
        grand += c
        rows.append((ind, c, slices))
        print(f"{c:>9,}  {slices:>7}  {ind}")
        time.sleep(0.5)
    total_slices = sum(r[2] for r in rows if r[2])
    print("-" * 60)
    print(f"{grand:>9,}  {total_slices:>7}  TOTAL ({country}, {len(ALL_INDUSTRIES)} industries)")

    out = f"industry_map_{cl.slugify(country)}.csv"
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["industry", "company_count", "min_slices"])
        w.writerows(rows)
    print(f"\nSaved: {out}  (totals overlap; dedup by domain after export)")


if __name__ == "__main__":
    main()
