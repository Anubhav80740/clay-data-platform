#!/usr/bin/env python3
"""
clay_people_lib -- Shared library for Clay People/Contact Search API.

Consolidates exact API payloads, counting, table creation, export, and deduplication
using exact Clay UI parameters (company_industries_include & location_countries_include).
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys
import time
import requests

csv.field_size_limit(2147483647)

WORKSPACE_ID = "744216"
COOKIE_FILE = ".clay_cookie.txt"
PLAN_DIR = "plans_people"
RESULTS_DIR = "delivery_people_v4"
FRONTEND_VERSION = "v20260830_143110Z_acbd7caddc"

COUNT_URL = f"https://api.clay.com/v3/workspaces/{WORKSPACE_ID}/actions/run-cpj-preview-enrichment"

def get_cookie():
    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

def get_headers():
    return {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json",
        "cookie": get_cookie(),
        "origin": "https://app.clay.com",
        "referer": "https://app.clay.com/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
        "x-clay-frontend-version": FRONTEND_VERSION
    }

def count_people_exact(company_industry, country="United States", extra_filters=None):
    """
    Executes live exact count query on Clay People Search API using exact frontend keys.
    """
    inputs = {
        "company_industries_include": [company_industry] if isinstance(company_industry, str) else company_industry,
        "location_countries_include": [country] if isinstance(country, str) else country,
        "limit": 1,
        "result_count": True
    }
    if extra_filters:
        inputs.update(extra_filters)

    payload = {
        "enrichmentType": "find-lists-of-people-with-mixrank-source-preview",
        "options": {"returnTaskId": True, "returnActionMetadata": True},
        "inputs": inputs
    }

    try:
        resp = requests.post(COUNT_URL, headers=get_headers(), json=payload, timeout=15)
        if resp.status_code == 200:
            data = resp.json().get("result", {})
            return data.get("peopleCount")
    except Exception as e:
        print(f"Error querying count for '{company_industry}': {e}")
    return 0

def slugify(s):
    slug = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_") or "slice"
    if len(slug) > 90:
        slug = slug[:81].rstrip("_") + "_" + hashlib.md5(s.encode()).hexdigest()[:8]
    return slug
