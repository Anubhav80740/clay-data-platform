#!/usr/bin/env python3
"""
Netlify Serverless Function: /.netlify/functions/cookie_refresh
Monitors and serves the active Clay session cookie state on Netlify.
"""
import os
import json

def handler(event, context):
    cookie_file = ".clay_cookie.txt"
    cookie_val = ""
    if os.path.exists(cookie_file):
        with open(cookie_file, "r", encoding="utf-8") as f:
            cookie_val = f.read().strip()

    response_data = {
        "status": "success",
        "provider": "netlify",
        "has_cookie": bool(cookie_val),
        "cookie_length": len(cookie_val)
    }

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(response_data)
    }
