#!/usr/bin/env python3
"""
generate_people_clicklist.py -- Company-Attribute Aware Partition Planner for People Search.

Usage:
  python3 generate_people_clicklist.py "Biotechnology" "United States"
"""
import csv
import json
import os
import sys

import clay_people_lib as cpl
import clay_lib as cl

# Standard Seniority / Management Level presets
SENIORITIES = ["C-Suite", "VP", "Director", "Manager", "Owner/Founder"]

# Standard Department presets
DEPARTMENTS = [
    "Engineering", "Sales", "Marketing", "Finance", "Human Resources",
    "Operations", "Product", "Information Technology", "Business Development"
]

def plan_people(industry, country="United States", job_titles=None, seniorities=None):
    # Step 1: Query target company count for this company attribute (Industry + Country)
    target_companies = cpl.count_target_companies(industry, country)
    target_companies = target_companies if target_companies is not None else 0
    
    # Step 2: Estimate people contacts based on targeted companies
    est_total_people = cpl.estimate_people_for_company_target(target_companies, job_titles, seniorities)
    
    print(f"People Planning for Company Industry '{industry}' in '{country}':")
    print(f"  -> Target Companies (Clay): {target_companies:,}")
    print(f"  -> Est. Target Contacts   : {est_total_people:,}")

    slices = []
    
    # Partition by Seniority & Department across the target companies
    active_seniorities = seniorities if seniorities else SENIORITIES
    
    for sen in active_seniorities:
        for dept in DEPARTMENTS:
            # Estimate headcount slice for (company_industry + country + seniority + dept)
            slice_est = max(12, int(est_total_people / (len(active_seniorities) * len(DEPARTMENTS))))
            slice_filter = {
                "company_industry": industry,
                "country_names": [country],
                "management_levels": [sen],
                "departments": [dept]
            }
            if job_titles:
                slice_filter["job_titles"] = job_titles
                
            slices.append({
                "label": f"{industry}_sen-{sen}_dept-{dept}",
                "count": slice_est,
                "filters": slice_filter
            })

    os.makedirs(cpl.PLAN_DIR, exist_ok=True)
    prefix = cpl.slugify(f"people_{industry}_{country}")
    json_path = f"{cpl.PLAN_DIR}/clicklist_{prefix}.json"
    csv_path = f"{cpl.PLAN_DIR}/clicklist_{prefix}.csv"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump([{"slug": cpl.slugify(s["label"]), "count": s["count"], "filters": s["filters"]} for s in slices], f, indent=2)

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["label", "est_contacts", "company_industry", "country", "seniority", "department"])
        for s in slices:
            fl = s["filters"]
            w.writerow([
                s["label"], s["count"],
                fl.get("company_industry"),
                ", ".join(fl.get("country_names", [])),
                ", ".join(fl.get("management_levels", [])),
                ", ".join(fl.get("departments", []))
            ])

    tot_reachable = sum(s["count"] for s in slices)
    print(f"Planning Complete: Created {len(slices)} partition slices | Total Reachable Contacts: {tot_reachable:,}")
    print(f"Saved Plan to: {json_path}\n")
    return target_companies, est_total_people, slices, json_path

if __name__ == "__main__":
    industry = sys.argv[1] if len(sys.argv) > 1 else "Biotechnology"
    country = sys.argv[2] if len(sys.argv) > 2 else "United States"
    plan_people(industry, country)
