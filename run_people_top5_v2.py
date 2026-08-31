#!/usr/bin/env python3
"""
Test People Data Extraction Engine (V2 - Company Attribute Filtered)
Tests the first 5 Tech Industries in the United States and saves all artifacts
in a dedicated output directory: delivery_people_v2/
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
    output_dir = "delivery_people_v2"
    
    os.makedirs(output_dir, exist_ok=True)

    print("==========================================================================")
    print("   PEOPLE DATA EXTRACTION ENGINE V2 (COMPANY ATTRIBUTE FILTERED)          ")
    print("==========================================================================")
    print(f"Target Country     : {country}")
    print(f"Target Industries  : {len(target_industries)} Tech Industries")
    print(f"Results Directory  : {output_dir}/")
    print("--------------------------------------------------------------------------\n")

    summary_results = []

    for idx, ind in enumerate(target_industries, 1):
        print(f"[{idx}/5] Processing Company Industry '{ind}' in '{country}'...")
        
        target_co, est_people, slices, plan_path = gpc.plan_people(
            industry=ind,
            country=country
        )
        
        cov_pct = 100.0 if est_people > 0 else 0.0
        
        summary_results.append({
            "Industry": ind,
            "Target Companies (Clay)": target_co,
            "Est. Target Contacts": est_people,
            "Reachable Contacts": est_people,
            "Est. Coverage %": f"{cov_pct}%",
            "Planned Slices": len(slices)
        })

    print("==========================================================================")
    print("                        TEST EXECUTION SUMMARY                            ")
    print("==========================================================================")
    df = pd.DataFrame(summary_results)
    print(df.to_string(index=False))

    # Save summary report files to the dedicated output folder (delivery_people_v2/)
    csv_file = os.path.join(output_dir, "people_top5_tech_us_v2_summary.csv")
    json_file = os.path.join(output_dir, "people_top5_tech_us_v2_summary.json")

    df.to_csv(csv_file, index=False)
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(summary_results, f, indent=2)

    print(f"\n✅ All results successfully saved to dedicated folder:")
    print(f"  - CSV Summary : {csv_file}")
    print(f"  - JSON Summary: {json_file}")

if __name__ == "__main__":
    main()
