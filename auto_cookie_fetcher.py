#!/usr/bin/env python3
"""
auto_cookie_fetcher.py -- Automated Clay Session Cookie Refresh Engine.

Launches Playwright, navigates to app.clay.com, intercepts network requests sent to api.clay.com/v3/,
extracts the active live 'cookie' header (containing claysession=...), and saves it to .clay_cookie.txt.
"""

import os
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

COOKIE_FILE = ".clay_cookie.txt"
STORAGE_STATE_FILE = ".clay_auth_state.json"

captured_cookie = None

def on_request(request):
    global captured_cookie
    url = request.url
    if "api.clay.com/v3" in url:
        headers = request.headers
        cookie_hdr = headers.get("cookie") or headers.get("Cookie")
        if cookie_hdr and "claysession" in cookie_hdr:
            captured_cookie = cookie_hdr

def fetch_clay_cookie(headless=False, timeout_sec=45):
    """
    Launches browser, navigates to app.clay.com, and captures the active API session cookie.
    """
    global captured_cookie
    if not HAS_PLAYWRIGHT:
        print("ERROR: Playwright is not installed. Please install with: pip install playwright && playwright install chromium")
        return None

    print("==========================================================================")
    print("      AUTOMATED CLAY SESSION COOKIE REFRESH ENGINE (PLAYWRIGHT)           ")
    print("==========================================================================")
    print(f"Target URL         : https://app.clay.com/")
    print(f"Cookie Output File : {COOKIE_FILE}")
    print("--------------------------------------------------------------------------\n")

    captured_cookie = None

    with sync_playwright() as p:
        browser_args = ["--disable-blink-features=AutomationControlled"]
        
        # Check if saved auth state exists
        if os.path.exists(STORAGE_STATE_FILE):
            print("Found saved auth state. Loading session...")
            context = p.chromium.launch_persistent_context(
                user_data_dir=".clay_user_data",
                headless=headless,
                args=browser_args
            )
        else:
            browser = p.chromium.launch(headless=headless, args=browser_args)
            context = browser.new_context()

        page = context.new_page()
        page.on("request", on_request)

        print("Navigating to https://app.clay.com/...")
        try:
            page.goto("https://app.clay.com/", wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            print(f"Navigation note: {e}")

        print("Listening for v3 API requests to capture live session cookie...")
        start_time = time.time()
        
        while time.time() - start_time < timeout_sec:
            if captured_cookie:
                break
            # Scroll or click slightly to trigger background API calls
            try:
                page.mouse.move(100, 100)
            except Exception:
                pass
            time.sleep(1.0)

        context.close()

    if captured_cookie:
        print("\nSUCCESS: Fresh Clay Session Cookie captured!")
        print(f"Cookie Length: {len(captured_cookie)} characters")
        
        with open(COOKIE_FILE, "w", encoding="utf-8") as f:
            f.write(captured_cookie)
            
        print(f"Saved fresh cookie to: {COOKIE_FILE}")
        return captured_cookie
    else:
        print("\nNOTE: No active session cookie captured within timeout.")
        print("If logged out, run with headless=False to log into app.clay.com in the browser window.")
        return None

if __name__ == "__main__":
    headless_mode = "--interactive" not in sys.argv
    fetch_clay_cookie(headless=headless_mode)
