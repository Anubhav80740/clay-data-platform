#!/usr/bin/env python3
"""
Automated Clay Cookie Fetcher using Playwright.
Maintains persistent per-user browser sessions and intercepts live session cookies from api.clay.com/v3/.
Saves verified working cookie to data/.clay_cookie_<username>.txt without hardcoding any personal tokens.
"""

import os
import sys
import time
import argparse
import subprocess
import requests

import clay_users

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def verify_cookie(cookie_str=None, username=None):
    """Tests cookie dynamically against Clay Workspaces API."""
    c = cookie_str
    if not c and username:
        c = clay_users.get_user_cookie(username)

    if not c:
        return False

    c = clay_users.extract_clean_cookie(c)

    if not c or "claysession=" not in c:
        return False

    headers = {
        "accept": "application/json, text/plain, */*",
        "cookie": c,
        "origin": "https://app.clay.com",
        "referer": "https://app.clay.com/",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
        "x-clay-frontend-version": "v20260901_204532Z_1f9b744063"
    }
    url = "https://api.clay.com/v3/my-workspaces"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict) and "results" in data:
                return len(data["results"]) > 0 or "id" in data
            if isinstance(data, list) and len(data) > 0:
                return True
            if isinstance(data, dict) and ("id" in data or "name" in data):
                return True
    except Exception:
        pass
    return False

def seed_browser_cookies(username, cookie_str):
    """Injects a valid cookie string into the user's persistent Playwright profile so future Auto-Refreshes work automatically."""
    if not username or not cookie_str:
        return
    from playwright.sync_api import sync_playwright
    u = username.strip().lower()
    if not u:
        return
    user_data_dir = clay_users.get_user_data_dir(u)
    os.makedirs(user_data_dir, exist_ok=True)
    
    cookies_to_add = []
    for item in (cookie_str or "").split(";"):
        item = item.strip()
        if "=" in item:
            name, val = item.split("=", 1)
            name = name.strip()
            val = val.strip()
            if name and val:
                cookies_to_add.append({
                    "name": name,
                    "value": val,
                    "domain": ".clay.com",
                    "path": "/"
                })
                
    if cookies_to_add:
        try:
            with sync_playwright() as p:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-setuid-sandbox"]
                )
                context.add_cookies(cookies_to_add)
                page = context.pages[0] if context.pages else context.new_page()
                try:
                    page.goto("https://app.clay.com", wait_until="domcontentloaded", timeout=10000)
                except Exception:
                    pass
                context.close()
                print(f"[+] Seeded and persisted {len(cookies_to_add)} cookies into profile for '{u}'")
        except Exception as e:
            print(f"[!] Cookie seed note: {e}")

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

def fetch_cookie(username=None, headless=None, timeout_seconds=60):
    """Launches browser for specific user, intercepts request headers and cookie jars from api.clay.com."""
    if not username:
        return None
    u = username.strip().lower()
    if not u:
        return None

    # 1. Fast Check: If the user's saved cookie is ALREADY valid & active, return instantly!
    existing_c = clay_users.get_user_cookie(u)
    if existing_c and verify_cookie(existing_c, username=u):
        print(f"[OK] Current cookie for '{u}' is ALREADY active and verified!")
        return existing_c

    from playwright.sync_api import sync_playwright
    user_data_dir = clay_users.get_user_data_dir(u)
    
    # In cloud Linux (Streamlit Cloud), default to headless. On Windows, default to headed so user can log in once if needed.
    if headless is None:
        headless = sys.platform != "win32" and "DISPLAY" not in os.environ

    os.makedirs(user_data_dir, exist_ok=True)
    captured_cookie = None

    print(f"[*] Starting Clay Auto-Cookie Fetcher for user '{u}' (headless={headless}, dir={user_data_dir})...")
    
    # Auto-download chromium if missing
    ensure_playwright_browsers()

    try:
        with sync_playwright() as p:
            try:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    headless=headless,
                    viewport={"width": 1280, "height": 800},
                    args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-setuid-sandbox"]
                )
            except Exception as e:
                print(f"Launch failed ({e}), installing chromium...")
                subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
                context = p.chromium.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    headless=headless,
                    viewport={"width": 1280, "height": 800},
                    args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-setuid-sandbox"]
                )

            page = context.pages[0] if context.pages else context.new_page()

            def handle_request(request):
                nonlocal captured_cookie
                try:
                    url = request.url
                    if "api.clay.com" in url or "app.clay.com" in url:
                        headers = request.headers
                        if "cookie" in headers and "claysession=" in headers["cookie"]:
                            cookie_val = headers["cookie"]
                            if captured_cookie != cookie_val:
                                captured_cookie = cookie_val
                except Exception:
                    pass

            try:
                page.on("request", handle_request)
            except Exception:
                pass

            try:
                print("[*] Navigating to https://app.clay.com ...")
                page.goto("https://app.clay.com", wait_until="domcontentloaded", timeout=45000)
            except Exception as e:
                print(f"[!] Navigation note: {e}")

            # Poll for cookie capture or direct cookie inspection
            start_time = time.time()
            while time.time() - start_time < timeout_seconds:
                # 1. Direct browser cookie jar extraction
                try:
                    all_cookies = context.cookies(["https://app.clay.com", "https://api.clay.com"])
                    has_session = any(c.get("name") == "claysession" for c in all_cookies)
                    if has_session:
                        jar_cookie = "; ".join([f"{c['name']}={c['value']}" for c in all_cookies if c.get("name") and c.get("value")])
                        if jar_cookie and verify_cookie(jar_cookie, username=u):
                            print(f"[OK] Extracted active cookie directly from browser context for '{u}'!")
                            clay_users.save_user_cookie(u, jar_cookie)
                            try:
                                context.close()
                            except Exception:
                                pass
                            return jar_cookie
                except Exception:
                    # If browser was manually closed, break gracefully
                    break

                # 2. Intercepted request header validation
                if captured_cookie:
                    try:
                        if verify_cookie(captured_cookie, username=u):
                            print(f"[OK] COOKIE VERIFICATION SUCCESSFUL FOR USER '{u}'!")
                            clay_users.save_user_cookie(u, captured_cookie)
                            try:
                                context.close()
                            except Exception:
                                pass
                            return captured_cookie
                        else:
                            captured_cookie = None
                    except Exception:
                        pass

                time.sleep(2)

            try:
                context.close()
            except Exception:
                pass

    except Exception as outer_e:
        print(f"[!] Auto-cookie fetcher note: {outer_e}")

    return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automated Clay Cookie Fetcher")
    parser.add_argument("--user", type=str, default="team", help="Username for user-specific cookie profile")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout in seconds")
    parser.add_argument("--verify-only", action="store_true", help="Only verify existing cookie")
    args = parser.parse_args()

    if args.verify_only:
        if verify_cookie(username=args.user):
            print(f"[OK] Cookie for user '{args.user}' is ACTIVE and VALID.")
            sys.exit(0)
        else:
            print(f"[X] Cookie for user '{args.user}' is EXPIRED or INVALID.")
            sys.exit(1)

    result = fetch_cookie(username=args.user, headless=args.headless, timeout_seconds=args.timeout)
    if result:
        sys.exit(0)
    else:
        sys.exit(1)

