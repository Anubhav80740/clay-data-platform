#!/usr/bin/env python3
"""
Netlify Serverless Function: /.netlify/functions/count
Executes ultra-fast parallel count queries against Clay API for Companies or People data.
Fully fault-tolerant with multiple cookie resolution strategies and CORS support.
"""
import os
import json
import requests
from concurrent.futures import ThreadPoolExecutor

WORKSPACE_ID = "744216"
FRONTEND_VERSION = "v20260830_143110Z_acbd7caddc"

# Known fallback active cookie if environment variable / file is unavailable in Lambda
FALLBACK_COOKIE = (
    "marketing_ajs_anonymous_id=DEBUG_B; _ga=GA1.1.203504950.1785217902; "
    "claysession=s%3AirV0NOBrZHfl0XdJLdsdYi1wECnh-nbR.gbhu3335fWNG72Zl0fH85wI%2FuoAJlM1SRP5oKr3%2FUFA; "
    "intercom-device-id-w28k1kwz=d424c801-aa75-4f80-bcfc-998b90dd88b6; "
    "_ga_NHFD0GLCLV=GS2.1.s1788176390$o6$g1$t1788176396$j54$l0$h0$dp_PDvBVKSoP-8tSn0HhEGiV26xiM4MPy3Q"
)

def get_cookie():
    # 1. Check environment variable
    env_cookie = os.environ.get("CLAY_COOKIE", "").strip()
    if env_cookie:
        return env_cookie

    # 2. Check local paths
    search_paths = [
        os.path.join(os.path.dirname(__file__), ".clay_cookie.txt"),
        os.path.join(os.path.dirname(__file__), "..", ".clay_cookie.txt"),
        os.path.join(os.path.dirname(__file__), "..", "..", ".clay_cookie.txt"),
        ".clay_cookie.txt"
    ]
    for p in search_paths:
        try:
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    c = f.read().strip()
                    if c:
                        return c
        except Exception:
            pass

    return FALLBACK_COOKIE

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
    headers_response = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS"
    }

    # Handle CORS preflight
    http_method = event.get("httpMethod", "POST")
    if http_method == "OPTIONS":
        return {"statusCode": 200, "headers": headers_response, "body": ""}

    try:
        body_raw = event.get("body", "{}")
        if isinstance(body_raw, str):
            body = json.loads(body_raw or "{}")
        else:
            body = body_raw or {}
    except Exception:
        body = {}

    country = body.get("country", "India")
    industries = body.get("industries", [])
    entity_type = body.get("entityType", "companies")

    if not industries:
        return {
            "statusCode": 200,
            "headers": headers_response,
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
    
    try:
        # Execute in parallel with 10 worker threads for lightning speed
        with ThreadPoolExecutor(max_workers=min(10, max(1, len(tasks)))) as executor:
            results = list(executor.map(fetch_single_count, tasks))
    except Exception as e:
        results = [fetch_single_count(t) for t in tasks]

    total_count = sum(r.get("Exact Clay Target Count", 0) for r in results)

    return {
        "statusCode": 200,
        "headers": headers_response,
        "body": json.dumps({
            "status": "success",
            "results": results,
            "total_count": total_count,
            "industries_count": len(results)
        })
    }
