#!/usr/bin/env python3
"""
Fast Test for Top 5 Tech Industries People Data in United States.
"""
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

import clay_people_lib as cpl
from clay_taxonomy import TECH_INDUSTRIES

def query_industry(ind):
    country = "United States"
    filter_base = {
        "country_names": [country],
        "industries": [ind]
    }
    cnt = cpl.count_people(filter_base)
    
    # Also test partitioning by major seniorities
    seniority_counts = {}
    for sen in ["C-Suite", "VP", "Director", "Manager"]:
        c = cpl.count_people({**filter_base, "management_levels": [sen]})
        if c:
            seniority_counts[sen] = c
            
    return {
        "Industry": ind,
        "Country": country,
        "Total Target People": cnt if cnt is not None else 0,
        "C-Suite": seniority_counts.get("C-Suite", 0),
        "VP": seniority_counts.get("VP", 0),
        "Director": seniority_counts.get("Director", 0),
        "Manager": seniority_counts.get("Manager", 0),
    }

def main():
    target_industries = TECH_INDUSTRIES[:5]
    print("==========================================================================")
    print("  PEOPLE DATA COUNTING & PARTITION TEST (TOP 5 TECH INDUSTRIES IN US)     ")
    print("==========================================================================")
    print("Target Industries:")
    for idx, i in enumerate(target_industries, 1):
        print(f"  {idx}. {i}")
    print("--------------------------------------------------------------------------\n")
    print("Querying Clay People Search API...")

    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(query_industry, target_industries))

    df = pd.DataFrame(results)
    print("\n==========================================================================")
    print("                        PEOPLE EXTRACTION RESULTS                         ")
    print("==========================================================================")
    print(df.to_string(index=False))

    summary_file = "people_top5_tech_us_summary.csv"
    df.to_csv(summary_file, index=False)
    print(f"\nSaved test results summary to: {summary_file}")

    with open("people_top5_tech_us_summary.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    main()
