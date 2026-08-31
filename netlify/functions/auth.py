#!/usr/bin/env python3
"""
Netlify Serverless Function: /.netlify/functions/auth
Handles team login authentication for Netlify deployment.
"""
import os
import json

def handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
    except Exception:
        body = {}

    user = str(body.get("user", "")).strip()
    password = str(body.get("pass", "")).strip()

    team_user = os.environ.get("CLAY_USER_ID", "team")
    team_pass = os.environ.get("CLAY_PASSWORD", "clay2026")

    if user == team_user and password == team_pass:
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"status": "success", "user": user})
        }
    else:
        return {
            "statusCode": 401,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"status": "error", "message": "Invalid User ID or Password"})
        }
