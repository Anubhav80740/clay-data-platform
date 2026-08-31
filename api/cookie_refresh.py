#!/usr/bin/env python3
"""
Vercel Serverless API Route: /api/cookie_refresh
Refreshes and returns active Clay cookie for Vercel deployments.
"""
import os
import json
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        cookie_file = ".clay_cookie.txt"
        cookie_val = ""
        if os.path.exists(cookie_file):
            with open(cookie_file, "r", encoding="utf-8") as f:
                cookie_val = f.read().strip()
                
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        response_data = {
            "status": "success",
            "has_cookie": bool(cookie_val),
            "cookie_length": len(cookie_val)
        }
        self.wfile.write(json.dumps(response_data).encode('utf-8'))
