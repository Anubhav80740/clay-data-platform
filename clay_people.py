#!/usr/bin/env python3
"""
clay_people.py -- People-search companion to clay_lib (companies).

Full integration for Clay People Extraction:
- Exact MixRank people counting oracle (free).
- Lossless multi-dimensional partitioning (States, Cities, Company Description, Job Title).
- Table creation (type: 'people', actionPackageId: 'e251a70e-46d7-4f3a-b3ef-a211ad3d8bd2').
- Export & download polling.
- Centralized deduplication on LinkedIn URL and Name@CompanyDomain.
"""
from __future__ import annotations

import csv
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field

import clay_lib as cl

PEOPLE_ENRICHMENT = "find-lists-of-people-with-mixrank-source-preview"

# Full filter object captured verbatim from Clay UI
PEOPLE_TEMPLATE = {
    "name": "", "limit": None, "names": [], "languages": [], "locations": [],
    "school_names": [], "cluster_count": 5, "company_sizes": [],
    "job_functions": [], "about_keywords": [], "follower_count": None,
    "job_title_mode": "smart", "company_table_id": "", "connection_count": None,
    "experience_count": None, "profile_keywords": [],
    "clustering_method": "agglomerative", "company_record_id": [],
    "headline_keywords": [], "locations_exclude": [],
    "start_from_method": "CsvOfCompanies", "company_identifier": [],
    "job_title_keywords": [], "max_follower_count": None,
    "search_raw_location": False, "max_connection_count": None,
    "max_experience_count": None, "role_range_end_month": None,
    "company_table_view_id": None, "exclude_entity_bitmap": None,
    "certification_keywords": [], "company_table_field_id": None,
    "role_range_start_month": None, "company_annual_revenues": [],
    "exclude_entities_bitmap": None, "location_cities_exclude": [],
    "location_cities_include": [], "location_states_exclude": [],
    "location_states_include": [], "include_past_experiences": False,
    "job_description_keywords": [], "location_regions_exclude": [],
    "location_regions_include": [], "previous_entities_bitmap": None,
    "company_industries_exclude": [], "company_industries_include": [],
    "job_title_exclude_keywords": [], "job_title_seniority_levels": [],
    "location_countries_exclude": [], "location_countries_include": [],
    "company_audience_segment_id": None, "company_description_keywords": [],
    "include_company_filter_bitmap": None, "job_title_seniority_levels_v2": [],
    "exclude_entities_configuration": [],
    "job_title_seniority_match_mode": "exact",
    "job_title_seniority_floor_level": None,
    "exclude_people_identifiers_mixed": [],
    "company_description_keywords_exclude": [],
    "include_company_filter_identifier_count": 0,
    "current_role_max_months_since_start_date": None,
    "current_role_min_months_since_start_date": None,
}

PEOPLE_FIELDS = [
    {"name": "Company Name", "dataType": "text", "formulaText": "{{source}}.latest_experience_company"},
    {"name": "Name", "dataType": "text", "formulaText": "{{source}}.name"},
    {"name": "First Name", "dataType": "text", "formulaText": "{{source}}.first_name"},
    {"name": "Last Name", "dataType": "text", "formulaText": "{{source}}.last_name"},
    {"name": "Title", "dataType": "text", "formulaText": "{{source}}.latest_experience_title"},
    {"name": "Company Domain", "dataType": "url", "formulaText": "{{source}}.domain"},
    {"name": "Location", "dataType": "text", "formulaText": "{{source}}.location_name"},
    {"name": "Country ISO", "dataType": "text", "formulaText": "{{source}}.location_country_iso"},
    {"name": "Follower Count", "dataType": "number", "formulaText": "{{source}}.follower_count"},
    {"name": "LinkedIn URL", "dataType": "url", "formulaText": "{{source}}.url", "isDedupeField": True},
]

PEOPLE_DESC_KEYWORDS = [
    "the", "and", "a", "of", "to", "in", "for", "is", "we", "our",
    "company", "services", "solutions", "technology", "business", "software",
    "data", "digital", "platform", "global", "team", "products", "customers",
    "management", "systems", "innovative", "leading", "provider",
    "development", "world", "clients", "help", "enterprise", "cloud",
    "based", "with", "that", "on", "as", "by", "at", "us", "you", "your",
    "more", "quality", "experience", "trusted", "committed", "focused",
    "dedicated",
]

PEOPLE_TITLE_KEYWORDS = [
    "senior", "director", "software", "analyst", "lead", "vice", "head",
    "executive", "chief", "officer", "product", "project", "technical",
    "principal", "coordinator", "member", "board", "partner", "regional",
    "national", "junior", "representative", "designer", "scientist", "planner",
    "controller", "auditor", "nurse", "producer", "operator", "fellow",
    "group", "department", "photographer", "pharmacist", "clerk", "pilot",
    "stylist", "psychologist", "chiropractor",
]


def build_people_inputs(filters):
    inputs = dict(PEOPLE_TEMPLATE)
    inputs.update(filters)
    inputs["limit"] = filters.get("limit", 1)
    inputs["result_count"] = True
    return inputs


def count_people_raw(filters):
    body = {
        "workspaceId": cl.WORKSPACE_ID,
        "enrichmentType": PEOPLE_ENRICHMENT,
        "options": {"returnTaskId": True, "returnActionMetadata": True},
        "inputs": build_people_inputs(filters)
    }
    return cl._post(cl.COUNT_URL, body)


_PEOPLE_COUNT_CACHE = {}


def count_people(filters, retries=6):
    """Exact peopleCount (free). None on repeated failure."""
    import random
    key = json.dumps(filters, sort_keys=True)
    if key in _PEOPLE_COUNT_CACHE:
        return _PEOPLE_COUNT_CACHE[key]
    for attempt in range(1, retries + 1):
        raw = count_people_raw({**filters, "limit": 1})
        try:
            if raw:
                parsed = json.loads(raw)
                res = parsed.get("result")
                if res is not None:
                    cnt = res.get("peopleCount")
                    if cnt is not None and isinstance(cnt, int):
                        _PEOPLE_COUNT_CACHE[key] = cnt
                    return cnt
                if parsed.get("type") == "TooManyRequests":
                    time.sleep(2.0 * attempt + random.uniform(1.0, 3.0))
                    continue
        except Exception:
            pass
        time.sleep(min(15, 1.2 ** attempt + random.uniform(0.5, 1.5)))
    return None


def people_preview(filters, retries=5):
    """limit:1 -> (taskId, peopleCount). Needed to seed create_people_table."""
    for attempt in range(1, retries + 1):
        raw = count_people_raw({**filters, "limit": 1})
        try:
            o = json.loads(raw)
            if o.get("taskId"):
                return o.get("taskId"), (o.get("result") or {}).get("peopleCount")
        except json.JSONDecodeError:
            time.sleep(1.5 * attempt)
    return None, None


def create_people_table(filters, name="People Search", limit=5000):
    task_id, cnt = people_preview(filters)
    if not task_id:
        return {"error": "preview_failed_no_task_id"}, cnt
    inputs = build_people_inputs(filters)
    inputs["limit"] = limit
    inputs.pop("result_count", None)
    body = {
        "workspaceId": cl.get_active_workspace_id(),
        "workbookName": name,
        "workbookId": None,
        "conversationId": "",
        "assignedFieldId": "f_people_search",
        "cpjConfig": {
            "type": "people",
            "typeSettings": {
                "name": "Find people",
                "iconType": "Person",
                "actionKey": "find-lists-of-people-with-mixrank-source",
                "actionPackageId": "e251a70e-46d7-4f3a-b3ef-a211ad3d8bd2",
                "previewTextPath": "name",
                "defaultPreviewText": "Profile",
                "recordsPath": "people",
                "idPath": "profile_id",
                "scheduleConfig": {"runSettings": "once"},
                "hasEvaluatedInputs": False,
                "inputs": inputs,
                "previewActionKey": PEOPLE_ENRICHMENT,
            },
            "clientSettings": {"tableType": "people"},
            "basicFields": PEOPLE_FIELDS,
            "previewActionTaskId": task_id,
        },
    }
    raw = cl._post(cl.CREATE_URL, body)
    return json.loads(raw), cnt


def build_people_dims(country):
    from clay_geo import GEO
    geo = GEO.get(country, {})
    dims = []
    if geo.get("states"):
        dims.append(cl.Dimension("state", "location_states_include",
                                 geo["states"],
                                 exclude_key="location_states_exclude"))
    if geo.get("cities"):
        dims.append(cl.Dimension("city", "location_cities_include",
                                 geo["cities"],
                                 exclude_key="location_cities_exclude"))
    dims.append(cl.ChainedDimension("desc", "company_description_keywords",
                                    PEOPLE_DESC_KEYWORDS,
                                    exclude_key="company_description_keywords_exclude"))
    dims.append(cl.ChainedDimension("title", "job_title_keywords",
                                    PEOPLE_TITLE_KEYWORDS,
                                    exclude_key="job_title_exclude_keywords"))
    return dims


PEOPLE_DIM_INCLUDE_KEYS = [
    "location_states_include", "location_cities_include",
    "company_description_keywords", "job_title_keywords"
]


def run_people(industry, country, merge=True):
    base = {
        "location_countries_include": [country],
        "company_industries_include": [industry]
    }
    label = cl.slugify(f"{industry}_{country}_people")
    dims = build_people_dims(country)
    stats = cl.PlanStats()

    def wrapped(f):
        r = count_people(f)
        if stats.count_calls % 250 == 0:
            cl.log(f"  ...{stats.count_calls} counts | {len(stats.leaves)} leaves "
                   f"| {len(stats.uncovered)} uncovered")
        return r

    cl.log(f"PLAN start: {industry} + {country} (people) | dims={[d.name for d in dims]}")
    cl.plan(base, label, dims, wrapped, stats)
    cl.log(f"PLAN raw done: {len(stats.leaves)} leaves, {len(stats.oversized)} oversized, "
           f"{len(stats.uncovered)} uncovered, calls={stats.count_calls}")
    if merge:
        stats.merged_from = len(stats.leaves)
        saved = cl.DIM_INCLUDE_KEYS
        cl.DIM_INCLUDE_KEYS = PEOPLE_DIM_INCLUDE_KEYS
        try:
            stats.leaves = cl.consolidate(stats.leaves)
        finally:
            cl.DIM_INCLUDE_KEYS = saved
        cl.log(f"PLAN merged: {stats.merged_from} -> {len(stats.leaves)} slices")
    return stats, base


def dedupe_people_file(in_csv, out_csv):
    """
    Centralized Incremental Merge for People Master Datasets:
    1. Reads existing master file in delivery_people/<Country>/...
    2. Registers existing keys (LinkedIn URL and Name@CompanyDomain).
    3. Appends ONLY newly discovered unique people.
    4. Returns (total_unique, existing_count, new_added).
    """
    seen = set()
    deduped_rows = []
    header = None
    
    if os.path.exists(out_csv) and os.path.getsize(out_csv) > 0:
        with open(out_csv, newline="", encoding="utf-8", errors="replace") as f:
            r = csv.reader(f)
            header = next(r, None)
            if header:
                li = header.index("LinkedIn URL") if "LinkedIn URL" in header else None
                nm = header.index("Name") if "Name" in header else None
                di = header.index("Company Domain") if "Company Domain" in header else (header.index("Domain") if "Domain" in header else None)
                for row in r:
                    lnk = row[li].strip().lower() if li is not None and li < len(row) else ""
                    name = row[nm].strip().lower() if nm is not None and nm < len(row) else ""
                    dom = row[di].strip().lower() if di is not None and di < len(row) else ""
                    key = lnk or (f"{name}@{dom}" if name and dom else None)
                    if key and key not in seen:
                        seen.add(key)
                        deduped_rows.append(row)
                    elif not key:
                        deduped_rows.append(row)

    initial_count = len(deduped_rows)
    if os.path.exists(in_csv) and os.path.getsize(in_csv) > 0:
        with open(in_csv, newline="", encoding="utf-8", errors="replace") as f:
            r = csv.reader(f)
            in_header = next(r, None)
            if in_header:
                if not header:
                    header = in_header
                li = in_header.index("LinkedIn URL") if "LinkedIn URL" in in_header else None
                nm = in_header.index("Name") if "Name" in in_header else None
                di = in_header.index("Company Domain") if "Company Domain" in in_header else (in_header.index("Domain") if "Domain" in in_header else None)
                for row in r:
                    lnk = row[li].strip().lower() if li is not None and li < len(row) else ""
                    name = row[nm].strip().lower() if nm is not None and nm < len(row) else ""
                    dom = row[di].strip().lower() if di is not None and di < len(row) else ""
                    key = lnk or (f"{name}@{dom}" if name and dom else None)
                    if key and key in seen:
                        continue
                    if key:
                        seen.add(key)
                    deduped_rows.append(row)
                    
    new_added = len(deduped_rows) - initial_count
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if header:
            w.writerow(header)
        w.writerows(deduped_rows)
        
    print(f"[CENTRALIZED PEOPLE MERGE] Existing in Master: {initial_count:,} | Newly Added: +{new_added:,} | Total Master Unique: {len(deduped_rows):,}", flush=True)
    return len(deduped_rows), initial_count, new_added
