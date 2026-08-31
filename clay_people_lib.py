#!/usr/bin/env python3
"""
clay_people_lib -- shared library for the Clay People/Contact extraction pipeline.

Consolidates auth, company-attribute-aware people counting, table create/populate,
export/download, and deduplication for People Search.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import clay_lib as cl

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

csv.field_size_limit(2147483647)

WORKSPACE_ID = "744216"
COOKIE_FILE = ".clay_cookie.txt"
PLAN_DIR = "plans_people"
RESULTS_DIR = "delivery_people_v2"
FRONTEND_VERSION = "v20260815_170454z_6bd76386ec"

COUNT_URL = "https://api.clay.com/v3/actions/run-cpj-preview-enrichment"
CREATE_URL = "https://api.clay.com/v3/sources/create-cpj-table"
EXPORT_URL = "https://api.clay.com/v3/tables/{t}/views/{v}/export"
POLL_URL = "https://api.clay.com/v3/exports/{id}"

EXPORT_LIMIT = 4800

PEOPLE_BASIC_FIELDS = [
    {"name": "Full Name", "dataType": "text", "formulaText": "{{source}}.name"},
    {"name": "First Name", "dataType": "text", "formulaText": "{{source}}.first_name"},
    {"name": "Last Name", "dataType": "text", "formulaText": "{{source}}.last_name"},
    {"name": "Job Title", "dataType": "text", "formulaText": "{{source}}.title"},
    {"name": "Seniority", "dataType": "text", "formulaText": "{{source}}.seniority"},
    {"name": "Department", "dataType": "text", "formulaText": "{{source}}.department"},
    {"name": "Work Email", "dataType": "email", "formulaText": "{{source}}.email"},
    {"name": "Phone Number", "dataType": "phone", "formulaText": "{{source}}.phone_number"},
    {"name": "Person LinkedIn URL", "dataType": "url", "formulaText": "{{source}}.linkedin_url", "isDedupeField": True},
    {"name": "Company Name", "dataType": "text", "formulaText": "{{source}}.company_name"},
    {"name": "Company Domain", "dataType": "url", "formulaText": "{{source}}.company_domain"},
    {"name": "Company Industry", "dataType": "text", "formulaText": "{{source}}.company_industry"},
    {"name": "Company Size", "dataType": "text", "formulaText": "{{source}}.company_size"},
    {"name": "Location", "dataType": "text", "formulaText": "{{source}}.location"},
    {"name": "Country", "dataType": "text", "formulaText": "{{source}}.country"},
]

def slugify(s):
    slug = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_") or "slice"
    if len(slug) > 90:
        slug = slug[:81].rstrip("_") + "_" + hashlib.md5(s.encode()).hexdigest()[:8]
    return slug

def count_target_companies(industry, country="United States"):
    """
    Company-attribute stage: Query Clay to get the exact count of target companies
    for the specified company industry and country.
    """
    filter_co = {
        "country_names": [country] if isinstance(country, str) else country,
        "industries": [industry] if isinstance(industry, str) else industry
    }
    return cl.count(filter_co)

def estimate_people_for_company_target(company_count, job_titles=None, seniorities=None):
    """
    Estimates realistic total contact pool based on targeted company count and decision-maker roles.
    Average decision-maker headcount multiplier per target company: ~6-12 contacts.
    """
    if not company_count or company_count <= 0:
        return 0
    multiplier = 8.5
    if seniorities:
        multiplier = len(seniorities) * 1.8
    elif job_titles:
        multiplier = len(job_titles) * 1.5
    return int(company_count * multiplier)

def dedupe_people_file(in_csv, out_csv):
    seen = set()
    deduped_rows = []
    header = None
    
    if os.path.exists(out_csv) and os.path.getsize(out_csv) > 0:
        with open(out_csv, newline="", encoding="utf-8", errors="replace") as f:
            r = csv.reader(f)
            header = next(r, None)
            if header:
                li = header.index("Person LinkedIn URL") if "Person LinkedIn URL" in header else (header.index("LinkedIn URL") if "LinkedIn URL" in header else None)
                ei = header.index("Work Email") if "Work Email" in header else (header.index("Email") if "Email" in header else None)
                for row in r:
                    lnk = row[li].strip().lower() if li is not None and li < len(row) else ""
                    eml = row[ei].strip().lower() if ei is not None and ei < len(row) else ""
                    key = lnk or ("eml:" + eml)
                    if key and key not in seen:
                        seen.add(key)
                        deduped_rows.append(row)

    initial_count = len(deduped_rows)
    with open(in_csv, newline="", encoding="utf-8", errors="replace") as f:
        r = csv.reader(f)
        in_header = next(r, None)
        if in_header:
            if not header:
                header = in_header
            li = in_header.index("Person LinkedIn URL") if "Person LinkedIn URL" in in_header else (in_header.index("LinkedIn URL") if "LinkedIn URL" in in_header else None)
            ei = in_header.index("Work Email") if "Work Email" in in_header else (in_header.index("Email") if "Email" in in_header else None)
            for row in r:
                lnk = row[li].strip().lower() if li is not None and li < len(row) else ""
                eml = row[ei].strip().lower() if ei is not None and ei < len(row) else ""
                key = lnk or ("eml:" + eml)
                if key and key in seen:
                    continue
                if key:
                    seen.add(key)
                deduped_rows.append(row)
                
    new_added = len(deduped_rows) - initial_count
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if header:
            w.writerow(header)
        w.writerows(deduped_rows)
        
    print(f"PEOPLE DEDUPE: Added {new_added} new contacts (Total Unique Contacts: {len(deduped_rows)})", flush=True)
    return len(deduped_rows)
