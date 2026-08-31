#!/usr/bin/env python3
"""
Netlify Serverless Function: /.netlify/functions/count
Executes ultra-fast parallel count queries against Clay API for Companies or People data.
"""
import os
import json
import requests
from concurrent.futures import ThreadPoolExecutor

WORKSPACE_ID = "744216"
FRONTEND_VERSION = "v20260830_143110Z_acbd7caddc"

def get_cookie():
    cookie_file = os.path.join(os.path.dirname(__file__), "..", "..", ".clay_cookie.txt")
    if os.path.exists(cookie_file):
        with open(cookie_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    return os.environ.get("CLAY_COOKIE", "")

def fetch_single_count(args):
    ind, country, entity_type, headers, url = args
    count_val = 0
    try:
        if entity_type == "people":
            payload = {
                "enrichmentType": "find-lists-of-people-with-mixrank-source-preview",
                "options": {"returnTaskId": True, "returnActionMetadata": True},
                "inputs": {
                    "company_industries_include": [ind],
                    "location_countries_include": [country],
                    "limit": 1,
                    "result_count": True
                }
            }
        else:
            payload = {
                "enrichmentType": "find-lists-of-companies-with-mixrank-source-preview",
                "options": {"returnTaskId": True, "returnActionMetadata": True},
                "inputs": {
                    "country_names": [country],
                    "industries": [ind],
                    "limit": 1,
                    "result_count": True
                }
            }
        resp = requests.post(url, headers=headers, json=payload, timeout=8)
        if resp.status_code == 200:
            data = resp.json().get("result", {})
            count_val = data.get("peopleCount" if entity_type == "people" else "companyCount", 0)
    except Exception:
        count_val = 0

    return {
        "Industry": ind,
        "Target Country": country,
        "Entity Type": "People" if entity_type == "people" else "Companies",
        "Exact Clay Target Count": count_val if count_val is not None else 0
    }

def handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
    except Exception:
        body = {}

    country = body.get("country", "India")
    industries = body.get("industries", [])
    entity_type = body.get("entityType", "companies")

    if not industries:
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"status": "success", "results": [], "total_count": 0})
        }

    cookie = get_cookie()
    headers = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json",
        "cookie": cookie,
        "origin": "https://app.clay.com",
        "referer": "https://app.clay.com/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
        "x-clay-frontend-version": FRONTEND_VERSION
    }
    url = f"https://api.clay.com/v3/workspaces/{WORKSPACE_ID}/actions/run-cpj-preview-enrichment"

    tasks = [(ind, country, entity_type, headers, url) for ind in industries]
    
    # Execute in parallel with 10 worker threads for lightning speed
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(fetch_single_count, tasks))

    total_count = sum(r.get("Exact Clay Target Count", 0) for r in results)

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps({
            "status": "success",
            "results": results,
            "total_count": total_count,
            "industries_count": len(results)
        })
    }
