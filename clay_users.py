"""
clay_users.py -- User Management and Per-User Cookie Isolation for Clay Data Platform.
"""
import os
import json
import hashlib

DATA_DIR = "data"
USERS_FILE = os.path.join(DATA_DIR, "users.json")

os.makedirs(DATA_DIR, exist_ok=True)

def _hash_pw(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def _load_users():
    if not os.path.exists(USERS_FILE):
        default_admin = {
            "team": _hash_pw("clay2026"),
            "anubhav": _hash_pw("clay2026")
        }
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(default_admin, f, indent=2)
        return default_admin
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_users(users_dict):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users_dict, f, indent=2)

def register_user(username, password):
    u = username.strip().lower()
    p = password.strip()
    if not u or len(u) < 2:
        return False, "Username must be at least 2 characters."
    if not p or len(p) < 4:
        return False, "Password must be at least 4 characters."
    
    users = _load_users()
    if u in users:
        return False, f"Username '{u}' is already registered. Please log in."
    
    users[u] = _hash_pw(p)
    _save_users(users)
    return True, f"User '{u}' successfully registered!"

def authenticate_user(username, password):
    u = username.strip().lower()
    p = password.strip()
    users = _load_users()
    if u in users and users[u] == _hash_pw(p):
        return True
    return False

def get_user_cookie_path(username):
    u = (username or "team").strip().lower()
    return os.path.join(DATA_DIR, f".clay_cookie_{u}.txt")

def get_user_data_dir(username):
    u = (username or "team").strip().lower()
    return os.path.join(os.getcwd(), f".clay_user_data_{u}")

import re

def extract_clean_cookie(raw_input):
    """Intelligently extracts the pure cookie string from cURL commands, HTTP headers, or raw tokens."""
    if not raw_input:
        return ""
    s = str(raw_input).strip()
    
    # 1. Look for -b '...' or --cookie '...' in curl commands
    m_b = re.search(r"(?:-b|--cookie)\s+['\"]([^'\"]+)['\"]", s)
    if m_b and "claysession=" in m_b.group(1):
        return m_b.group(1).strip()
        
    # 2. Look for -H 'cookie: ...' or -H 'Cookie: ...' in curl commands
    m_h = re.search(r"-H\s+['\"][Cc]ookie:\s*([^'\"]+)['\"]", s)
    if m_h and "claysession=" in m_h.group(1):
        return m_h.group(1).strip()
        
    # 3. Look for Cookie: header lines
    for line in s.splitlines():
        ls = line.strip()
        if ls.lower().startswith("cookie:"):
            cand = ls[7:].strip().strip("'\"")
            if "claysession=" in cand:
                return cand
                
    # 4. If multiline curl or text containing claysession=
    if "claysession=" in s:
        for line in s.splitlines():
            if "claysession=" in line:
                cand = line.strip().rstrip("\\").strip().strip("'\"")
                if cand.startswith("-b "):
                    cand = cand[3:].strip().strip("'\"")
                elif cand.lower().startswith("-h 'cookie:"):
                    cand = cand[11:].strip().rstrip("'\"")
                elif cand.lower().startswith("cookie:"):
                    cand = cand[7:].strip().strip("'\"")
                if "claysession=" in cand:
                    return cand
                    
    return s

def save_user_cookie(username, cookie_str):
    u = (username or "team").strip().lower()
    clean_cookie = extract_clean_cookie(cookie_str)
    cp = get_user_cookie_path(u)
    with open(cp, "w", encoding="utf-8") as f:
        f.write(clean_cookie.strip())
    fallback_cp = os.path.join(os.getcwd(), ".clay_cookie.txt")
    if not os.path.exists(fallback_cp):
        try:
            with open(fallback_cp, "w", encoding="utf-8") as f:
                f.write(clean_cookie.strip())
        except Exception:
            pass
    return cp

def get_user_cookie(username):
    u = (username or "team").strip().lower()
    cp = get_user_cookie_path(u)
    if os.path.exists(cp):
        try:
            with open(cp, "r", encoding="utf-8", errors="replace") as f:
                val = f.read().strip()
                if val:
                    return val
        except Exception:
            pass

    fallback_cp = os.path.join(os.getcwd(), ".clay_cookie.txt")
    if os.path.exists(fallback_cp):
        try:
            with open(fallback_cp, "r", encoding="utf-8", errors="replace") as f:
                val = f.read().strip()
                if val:
                    return val
        except Exception:
            pass

    return ""
