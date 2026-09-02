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
import clay_logger
import clay_people as cp
from clay_taxonomy import ALL_CLAY_INDUSTRIES

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 count_people.py <Country> [--industries-file path]")
        sys.exit(1)
        
    country = sys.argv[1]
    user_id = os.environ.get("CLAY_USER_ID", "team")
    if "--user" in sys.argv:
        u_idx = sys.argv.index("--user")
        if u_idx + 1 < len(sys.argv):
            user_id = sys.argv[u_idx + 1]
            os.environ["CLAY_USER_ID"] = user_id
    industries = ALL_CLAY_INDUSTRIES
    
    if "--industries-file" in sys.argv:
        idx = sys.argv.index("--industries-file")
        if idx + 1 < len(sys.argv):
            with open(sys.argv[idx + 1], "r", encoding="utf-8") as f:
                industries = json.load(f)
                
    os.makedirs("data", exist_ok=True)
    out_file = os.path.join("data", f"{cl.slugify(country)}_people_counts.csv")
    print(f"Counting People for {len(industries)} industries in {country} -> {out_file}...")
    clay_logger.log_activity("COUNT_STARTED", "People", country, details={"industries_count": len(industries)})
    
    have_prev = {}
    if os.path.exists(out_file):
        try:
            with open(out_file, encoding="utf-8", errors="replace") as f:
                have_prev = {r["Industry"]: r["Count"] for r in csv.DictReader(f) if "Industry" in r and "Count" in r}
        except Exception:
            pass

    counts = []
    tot = len(industries)
    for i, ind in enumerate(industries, 1):
        prev_val = have_prev.get(ind)
        filters = {
            "location_countries_include": [country],
            "company_industries_include": [ind]
        }
        cnt = cp.count_people(filters)
        val = cnt if cnt is not None else 0
        print(f"[{i}/{tot}] {ind}: {val:,} people (previous: {prev_val if prev_val is not None else 'N/A'})", flush=True)
        counts.append({"Industry": ind, "Count": val})
        
        # Log to permanent time-series count history
        clay_logger.log_count_observation("People", country, ind, new_count=val, previous_count=prev_val, notes="Step 1 People Live Count")
    counts.sort(key=lambda x: -x["Count"])
    with open(out_file, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["Industry", "Count"])
        w.writeheader()
        w.writerows(counts)
        
    tot_people = sum(c['Count'] for c in counts)
    clay_logger.log_activity("COUNT", "People", country, industries=industries, total_rows=tot_people, status="SUCCESS", details=f"{tot_people:,} people across {len(counts)} industries")
    print(f"Count complete! Total People in {country}: {tot_people:,} across {len(counts)} industries.")

if __name__ == "__main__":
    main()


