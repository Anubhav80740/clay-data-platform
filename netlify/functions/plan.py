#!/usr/bin/env python3
"""
Netlify Serverless Function: /.netlify/functions/plan
Executes Step 2 Partition Planning for Netlify deployment.
"""
import os
import json
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

import clay_lib as cl

def handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
    except Exception:
        body = {}

    country = body.get("country", "United States")
    industry = body.get("industry", "Biotechnology")

    cnt = cl.count({"country_names": [country], "industries": [industry]}) or 0
    num_slices = max(1, int(cnt / 4800)) if cnt > 0 else 0

    results = [{
        "Industry": industry,
        "Country": country,
        "Clay Target Count": cnt,
        "Estimated Reachable": cnt,
        "Planned Slices": num_slices,
        "Est Coverage %": "100.0%"
    }]

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"status": "success", "results": results})
    }
