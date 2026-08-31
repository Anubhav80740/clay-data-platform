#!/usr/bin/env python3
"""
Test People Data Extraction: Query Clay People Counts & Plan Partitions for the Top 5 Tech Industries in the US.
"""
import json
import os
import sys
import pandas as pd

import clay_people_lib as cpl
import generate_people_clicklist as gpc
from clay_taxonomy import TECH_INDUSTRIES

def main():
    target_industries = TECH_INDUSTRIES[:5]
    country = "United States"
    
    print("================================================================")
    print("   PEOPLE DATA EXTRACTION TEST (TOP 5 US TECH INDUSTRIES)       ")
    print("================================================================")
    print(f"Target Country     : {country}")
    print(f"Target Industries  : {len(target_industries)} Tech Industries")
    print("----------------------------------------------------------------\n")

    results = []

    for idx, ind in enumerate(target_industries, 1):
        print(f"[{idx}/5] Querying People Data for: '{ind}' in '{country}'...")
        
        # Step 1: Count target people in this industry & country
        filter_base = {
            "country_names": [country],
            "industries": [ind]
        }
        cnt = cpl.count_people(filter_base)
        print(f"  -> Total Target People on Clay: {cnt:,}" if cnt else "  -> Count: 0")
        
        # Step 2: Generate Partition Plan (Seniorities & Departments)
        slices, plan_path = gpc.plan_people(
            job_titles=None,
            country=country,
            company_industries=ind,
            seniorities=None
        )
        
        tot_reachable = sum(s["count"] for s in slices)
        cov_pct = round(100 * tot_reachable / cnt, 1) if (cnt and cnt > 0) else 100.0
        
        results.append({
            "Industry": ind,
            "Clay Target People": cnt if cnt is not None else 0,
            "Reachable People": tot_reachable,
            "Est. Coverage %": f"{cov_pct}%",
            "Planned Slices": len(slices)
        })
        print(f"  -> Slices: {len(slices)} | Reachable: {tot_reachable:,} ({cov_pct}%)\n")

    print("================================================================")
    print("                    TEST EXECUTION SUMMARY                      ")
    print("================================================================")
    df = pd.DataFrame(results)
    print(df.to_string(index=False))

    # Save summary report to JSON
    with open("test_people_top5_summary.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    main()
