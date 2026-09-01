#!/usr/bin/env python3
"""
count_people.py -- Batch counting script for People data across industries in a country.
Usage: python3 count_people.py <Country> [--industries-file path]
Outputs: <country_slug>_people_counts.csv
"""
import csv
import json
import os
import sys
import time

import clay_lib as cl
import clay_people as cp
from clay_taxonomy import ALL_CLAY_INDUSTRIES

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 count_people.py <Country> [--industries-file path]")
        sys.exit(1)
        
    country = sys.argv[1]
    industries = ALL_CLAY_INDUSTRIES
    
    if "--industries-file" in sys.argv:
        idx = sys.argv.index("--industries-file")
        if idx + 1 < len(sys.argv):
            with open(sys.argv[idx + 1], "r", encoding="utf-8") as f:
                industries = json.load(f)
                
    out_file = f"{cl.slugify(country)}_people_counts.csv"
    print(f"Counting People for {len(industries)} industries in {country} -> {out_file}...")
    
    counts = []
    tot = len(industries)
    for i, ind in enumerate(industries, 1):
        filters = {
            "location_countries_include": [country],
            "company_industries_include": [ind]
        }
        cnt = cp.count_people(filters)
        print(f"[{i}/{tot}] {ind}: {cnt if cnt is not None else 0:,} people", flush=True)
        counts.append({"Industry": ind, "Count": cnt if cnt is not None else 0})
        time.sleep(0.2)
        
    counts.sort(key=lambda x: -x["Count"])
    with open(out_file, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["Industry", "Count"])
        w.writeheader()
        w.writerows(counts)
        
    print(f"Count complete! Total People in {country}: {sum(c['Count'] for c in counts):,} across {len(counts)} industries.")

if __name__ == "__main__":
    main()
