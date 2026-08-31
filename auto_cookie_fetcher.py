#!/usr/bin/env python3
"""
Automated Clay Cookie Fetcher using Playwright.
Maintains persistent browser session and intercepts live session cookies from api.clay.com/v3/.
Saves verified working cookie to .clay_cookie.txt.
"""

import os
import sys
import time
import argparse
import requests
from playwright.sync_api import sync_playwright

COOKIE_FILE = os.path.join(os.path.dirname(__file__), ".clay_cookie.txt")
USER_DATA_DIR = os.path.join(os.path.dirname(__file__), ".clay_user_data")
WORKSPACE_ID = "744216"
TEST_URL = f"https://api.clay.com/v3/workspaces/{WORKSPACE_ID}/actions/run-cpj-preview-enrichment"

def verify_cookie(cookie_str):
    """Tests cookie against Clay Preview Enrichment API."""
    if not cookie_str or "claysession=" not in cookie_str:
        return False
    headers = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json",
        "cookie": cookie_str,
        "origin": "https://app.clay.com",
        "referer": "https://app.clay.com/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
        "x-clay-frontend-version": "v20260830_143110Z_acbd7caddc"
    }
    payload = {
        "enrichmentType": "find-lists-of-companies-with-mixrank-source-preview",
        "options": {"returnTaskId": True, "returnActionMetadata": True},
        "inputs": {
            "country_names": ["United States"],
            "industries": ["Software Development"],
            "limit": 1,
            "result_count": True
        }
    }
    try:
        resp = requests.post(TEST_URL, json=payload, headers=headers, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            if "result" in data and ("companyCount" in data["result"] or "peopleCount" in data["result"]):
                return True
    except Exception as e:
        print(f"Verification request error: {e}")
    return False

def fetch_cookie(headless=False, timeout_seconds=120):
    """Launches browser, intercepts request headers to api.clay.com, and extracts active cookie."""
    os.makedirs(USER_DATA_DIR, exist_ok=True)
    captured_cookie = None

    print(f"[*] Starting Clay Auto-Cookie Fetcher (headless={headless})...")
    print(f"[*] Persistent profile: {USER_DATA_DIR}")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=headless,
            viewport={"width": 1280, "height": 800},
            args=["--disable-blink-features=AutomationControlled"]
        )

        page = context.new_page()

        def handle_request(request):
            nonlocal captured_cookie
            url = request.url
            if "api.clay.com/v3" in url:
                headers = request.headers
                if "cookie" in headers and "claysession=" in headers["cookie"]:
                    cookie_val = headers["cookie"]
                    if captured_cookie != cookie_val:
                        captured_cookie = cookie_val
                        print("[+] Captured live claysession cookie from outgoing API call!")

        page.on("request", handle_request)

        try:
            print("[*] Navigating to https://app.clay.com ...")
            page.goto("https://app.clay.com", wait_until="networkidle", timeout=60000)
        except Exception as e:
            print(f"[!] Navigation note: {e}")

        # Poll for cookie capture
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            if captured_cookie:
                print("[*] Testing captured cookie against Clay live API...")
                if verify_cookie(captured_cookie):
                    print("[✓] COOKIE VERIFICATION SUCCESSFUL!")
                    with open(COOKIE_FILE, "w", encoding="utf-8") as f:
                        f.write(captured_cookie)
                    print(f"[✓] Saved active cookie to: {COOKIE_FILE}")
                    context.close()
                    return captured_cookie
                else:
                    print("[!] Captured cookie failed verification. Waiting for fresh request...")
                    captured_cookie = None
            time.sleep(2)

        context.close()

    print("[X] Timeout reached without capturing a valid cookie.")
    return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automated Clay Cookie Fetcher")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout in seconds")
    parser.add_argument("--verify-only", action="store_true", help="Only verify existing cookie file")
    args = parser.parse_args()

    if args.verify_only:
        if os.path.exists(COOKIE_FILE):
            with open(COOKIE_FILE, "r", encoding="utf-8") as f:
                c = f.read().strip()
            if verify_cookie(c):
                print("[✓] Current cookie in .clay_cookie.txt is ACTIVE and VALID.")
                sys.exit(0)
            else:
                print("[X] Current cookie in .clay_cookie.txt is EXPIRED or INVALID.")
                sys.exit(1)
        else:
            print("[X] No .clay_cookie.txt file found.")
            sys.exit(1)

    result = fetch_cookie(headless=args.headless, timeout_seconds=args.timeout)
    if result:
        sys.exit(0)
    else:
        sys.exit(1)
