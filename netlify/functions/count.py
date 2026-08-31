#!/usr/bin/env python3
"""
Netlify Serverless Function: /.netlify/functions/count
Executes Step 1 Count query using clay_lib for Netlify deployment.
"""
import os
import json
import sys

# Ensure parent path is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import clay_lib as cl

def handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
    except Exception:
        body = {}

    country = body.get("country", "United States")
    industries = body.get("industries", [])

    results = []
    for ind in industries:
        filter_co = {
            "country_names": [country],
            "industries": [ind]
        }
        cnt = cl.count(filter_co)
        results.append({
            "Industry": ind,
            "Country": country,
            "Count": cnt if cnt is not None else 0
        })

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps({"status": "success", "results": results})
    }
