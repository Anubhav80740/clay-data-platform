#!/usr/bin/env python3
"""
generate_people_clicklist.py -- Multi-dimensional partition planner for People search.
Usage: python3 generate_people_clicklist.py <Industry> <Country>
Outputs: plans/clicklist_<industry_country>_people.json and plans/clicklist_<industry_country>_people.csv
"""
import csv
import json
import os
import sys

import clay_lib as cl
import clay_people as cp

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 generate_people_clicklist.py <Industry> <Country>")
        sys.exit(1)
        
    industry = sys.argv[1]
    country = sys.argv[2]
    
    prefix = cl.slugify(f"{industry}_{country}_people")
    os.makedirs(cl.PLAN_DIR, exist_ok=True)
    
    stats, base = cp.run_people(industry, country, merge=True)
    leaves = sorted(stats.leaves, key=lambda l: -l.count)
    
    json_path = f"{cl.PLAN_DIR}/clicklist_{prefix}.json"
    csv_path = f"{cl.PLAN_DIR}/clicklist_{prefix}.csv"
    
    plan_data = []
    for i, l in enumerate(leaves, 1):
        slug = cl.slugify(f"{prefix}_s{i:04d}")
        plan_data.append({
            "slug": slug,
            "count": l.count,
            "oversized": l.oversized,
            "filters": l.filters
        })
        
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(plan_data, f, indent=1)
        
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["slug", "count", "oversized", "filters"])
        for d in plan_data:
            w.writerow([d["slug"], d["count"], d["oversized"], json.dumps(d["filters"])])
            
    print(f"PLAN READY: {len(leaves)} slices for {industry} in {country} (People) -> {json_path}")

if __name__ == "__main__":
    main()
