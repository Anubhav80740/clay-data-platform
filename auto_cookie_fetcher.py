#!/usr/bin/env python3
"""
Automated Clay Cookie Fetcher using Playwright.
Maintains persistent browser session and intercepts live session cookies from api.clay.com/v3/.
Saves verified working cookie to .clay_cookie.txt and supports automatic Chromium binary installation.
"""

import os
import sys
import time
import argparse
import subprocess
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

COOKIE_FILE = os.path.join(os.path.dirname(__file__), ".clay_cookie.txt")
USER_DATA_DIR = os.path.join(os.path.dirname(__file__), ".clay_user_data")
WORKSPACE_ID = "744216"
TEST_URL = f"https://api.clay.com/v3/workspaces/{WORKSPACE_ID}/actions/run-cpj-preview-enrichment"

DEFAULT_VERIFIED_COOKIE = "marketing_ajs_anonymous_id=DEBUG_B; _ga=GA1.1.203504950.1785217902; claysession=s%3AirV0NOBrZHfl0XdJLdsdYi1wECnh-nbR.gbhu3335fWNG72Zl0fH85wI%2FuoAJlM1SRP5oKr3%2FUFA; intercom-device-id-w28k1kwz=d424c801-aa75-4f80-bcfc-998b90dd88b6; _ga_NHFD0GLCLV=GS2.1.s1788176390$o6$g1$t1788176396$j54$l0$h0$dp_PDvBVKSoP-8tSn0HhEGiV26xiM4MPy3Q"

def verify_cookie(cookie_str=None):
    """Tests cookie against Clay Preview Enrichment API."""
    c = cookie_str
    if not c:
        if os.path.exists(COOKIE_FILE):
            try:
                with open(COOKIE_FILE, "r", encoding="utf-8") as f:
                    c = f.read().strip()
            except Exception:
                pass
    if not c:
        c = DEFAULT_VERIFIED_COOKIE

    if not c or "claysession=" not in c:
        return False

    headers = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json",
        "cookie": c,
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
        resp = requests.post(TEST_URL, json=payload, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if "result" in data and ("companyCount" in data["result"] or "peopleCount" in data["result"]):
                return True
    except Exception as e:
        print(f"Verification request error: {e}")
    return False

def ensure_playwright_browsers():
    """Auto-installs Chromium binaries if running in cloud Linux environment."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
                browser.close()
                return True
            except Exception as e:
                print(f"Playwright browser check: {e}. Attempting automated install...")
                subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
                return True
    except Exception as e:
        print(f"Error during browser install: {e}")
        return False

def fetch_cookie(headless=None, timeout_seconds=120):
    """Launches browser, intercepts request headers to api.clay.com, and extracts active cookie."""
    from playwright.sync_api import sync_playwright
    
    # In cloud Linux (Streamlit Cloud), default to headless
    if headless is None:
        headless = sys.platform != "win32" and "DISPLAY" not in os.environ

    os.makedirs(USER_DATA_DIR, exist_ok=True)
    captured_cookie = None

    print(f"[*] Starting Clay Auto-Cookie Fetcher (headless={headless})...")
    
    # Auto-download chromium if missing
    ensure_playwright_browsers()

    with sync_playwright() as p:
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR,
                headless=headless,
                viewport={"width": 1280, "height": 800},
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-setuid-sandbox"]
            )
        except Exception as e:
            print(f"Launch failed ({e}), installing chromium...")
            subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
            context = p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR,
                headless=headless,
                viewport={"width": 1280, "height": 800},
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-setuid-sandbox"]
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
            page.goto("https://app.clay.com", wait_until="networkidle", timeout=45000)
        except Exception as e:
            print(f"[!] Navigation note: {e}")

        # Poll for cookie capture
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            if captured_cookie:
                print("[*] Testing captured cookie against Clay live API...")
                if verify_cookie(captured_cookie):
                    print("[OK] COOKIE VERIFICATION SUCCESSFUL!")
                    with open(COOKIE_FILE, "w", encoding="utf-8") as f:
                        f.write(captured_cookie)
                    context.close()
                    return captured_cookie
                else:
                    captured_cookie = None
            time.sleep(2)

        context.close()

    # Fallback to verified default if available
    if verify_cookie(DEFAULT_VERIFIED_COOKIE):
        with open(COOKIE_FILE, "w", encoding="utf-8") as f:
            f.write(DEFAULT_VERIFIED_COOKIE)
        return DEFAULT_VERIFIED_COOKIE

    return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automated Clay Cookie Fetcher")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout in seconds")
    parser.add_argument("--verify-only", action="store_true", help="Only verify existing cookie")
    args = parser.parse_args()

    if args.verify_only:
        if verify_cookie():
            print("[OK] Current cookie is ACTIVE and VALID.")
            sys.exit(0)
        else:
            print("[X] Current cookie is EXPIRED or INVALID.")
            sys.exit(1)

    result = fetch_cookie(headless=args.headless, timeout_seconds=args.timeout)
    if result:
        sys.exit(0)
    else:
        sys.exit(1)
