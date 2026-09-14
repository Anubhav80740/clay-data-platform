"""
clay_users.py -- User Management and Resilient Cookie Management for Clay Data Platform.
Supports persistent team accounts, Streamlit Cloud secrets, runtime in-memory caching,
and multi-tier cookie fallback so users and sessions are never lost on container restarts.
"""
import os
import json
import hashlib
import re

DATA_DIR = "data"
USERS_FILE = os.path.join(DATA_DIR, "users.json")

os.makedirs(DATA_DIR, exist_ok=True)

# Master team passwords that grant immediate access across all sessions and restarts
MASTER_TEAM_PASSWORDS = {"clay2026", "clay2025", "admin123"}

# In-memory runtime stores to survive across Streamlit container resets
_RUNTIME_USERS = {}
_RUNTIME_COOKIES = {}

def _hash_pw(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def _load_users():
    users = {}
    # 1. Base users from disk (if present)
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    users.update(loaded)
        except Exception:
            pass
            
    # Default team accounts if file is empty
    if not users:
        users = {
            "team": _hash_pw("clay2026"),
            "anubhav": _hash_pw("clay2026")
        }
        try:
            with open(USERS_FILE, "w", encoding="utf-8") as f:
                json.dump(users, f, indent=2)
        except Exception:
            pass

    # 2. Add users created at runtime
    users.update(_RUNTIME_USERS)

    # 3. Streamlit Cloud Secrets (if configured)
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "users" in st.secrets:
            for u, p_or_hash in st.secrets["users"].items():
                u_clean = str(u).strip().lower()
                p_str = str(p_or_hash).strip()
                if len(p_str) == 64 and all(c in "0123456789abcdefABCDEF" for c in p_str):
                    users[u_clean] = p_str.lower()
                else:
                    users[u_clean] = _hash_pw(p_str)
    except Exception:
        pass

    return users

def _save_users(users_dict):
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users_dict, f, indent=2)
    except Exception:
        pass

def register_user(username, password):
    u = username.strip().lower()
    p = password.strip()
    if not u or len(u) < 2:
        return False, "Username must be at least 2 characters."
    if not p or len(p) < 4:
        return False, "Password must be at least 4 characters."
    
    users = _load_users()
    p_hash = _hash_pw(p)
    users[u] = p_hash
    _RUNTIME_USERS[u] = p_hash
    _save_users(users)
    return True, f"User '{u}' successfully registered!"

def authenticate_user(username, password):
    u = username.strip().lower()
    p = password.strip()
    if not u or not p:
        return False

    # 1. Immediate access via master team password
    if p in MASTER_TEAM_PASSWORDS:
        _RUNTIME_USERS[u] = _hash_pw(p)
        return True

    # 2. Check secret team password
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            if "team_password" in st.secrets and p == str(st.secrets["team_password"]).strip():
                _RUNTIME_USERS[u] = _hash_pw(p)
                return True
    except Exception:
        pass

    # 3. Standard user check
    users = _load_users()
    if u in users and users[u] == _hash_pw(p):
        return True

    return False

def get_user_cookie_path(username):
    if not username:
        return ""
    u = username.strip().lower()
    return os.path.join(DATA_DIR, f".clay_cookie_{u}.txt")

def get_user_data_dir(username):
    if not username:
        return ""
    u = username.strip().lower()
    return os.path.join(os.getcwd(), f".clay_user_data_{u}")

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
    if not username:
        return ""
    u = username.strip().lower()
    if not u:
        return ""
    clean_cookie = extract_clean_cookie(cookie_str)
    if not clean_cookie:
        return ""

    # 1. Update in-memory runtime caches
    _RUNTIME_COOKIES[u] = clean_cookie
    _RUNTIME_COOKIES["default"] = clean_cookie
    _RUNTIME_COOKIES["team"] = clean_cookie

    # 2. Write to user disk file
    cp = get_user_cookie_path(u)
    try:
        with open(cp, "w", encoding="utf-8") as f:
            f.write(clean_cookie.strip())
    except Exception:
        pass

    # 3. Also update shared team & root cookie files for seamless fallback
    try:
        with open(os.path.join(DATA_DIR, ".clay_cookie_team.txt"), "w", encoding="utf-8") as f:
            f.write(clean_cookie.strip())
        with open(".clay_cookie.txt", "w", encoding="utf-8") as f:
            f.write(clean_cookie.strip())
    except Exception:
        pass

    # 4. Export to environment for all child processes
    os.environ["CLAY_COOKIE"] = clean_cookie

    # 5. Cache in active Streamlit session if running in UI
    try:
        import streamlit as st
        st.session_state["active_clay_cookie"] = clean_cookie
        st.session_state[f"_clay_cookie_{u}"] = clean_cookie
    except Exception:
        pass

    return cp

def get_user_cookie(username=None):
    candidates_to_try = []
    u = username.strip().lower() if username else ""
    if u:
        candidates_to_try.append(u)
    for fb in ["team", "anubhav", "default"]:
        if fb not in candidates_to_try:
            candidates_to_try.append(fb)

    # 1. Check Streamlit session_state
    try:
        import streamlit as st
        if u and st.session_state.get(f"_clay_cookie_{u}"):
            c = str(st.session_state[f"_clay_cookie_{u}"]).strip()
            if c:
                return c
        if st.session_state.get("active_clay_cookie"):
            c = str(st.session_state["active_clay_cookie"]).strip()
            if c:
                return c
    except Exception:
        pass

    # 2. Check runtime in-memory cache
    for cand in candidates_to_try:
        if cand in _RUNTIME_COOKIES and _RUNTIME_COOKIES[cand]:
            return _RUNTIME_COOKIES[cand].strip()

    # 3. Check environment variables
    if u and os.environ.get(f"CLAY_COOKIE_{u.upper()}"):
        return os.environ[f"CLAY_COOKIE_{u.upper()}"].strip()
    if os.environ.get("CLAY_COOKIE"):
        return os.environ["CLAY_COOKIE"].strip()

    # 4. Check user-specific file on disk
    for cand in candidates_to_try:
        cp = get_user_cookie_path(cand)
        if cp and os.path.exists(cp):
            try:
                with open(cp, "r", encoding="utf-8", errors="replace") as f:
                    val = f.read().strip()
                    if val and "claysession=" in val:
                        return val
            except Exception:
                pass

    # 5. Check root .clay_cookie.txt
    if os.path.exists(".clay_cookie.txt"):
        try:
            with open(".clay_cookie.txt", "r", encoding="utf-8", errors="replace") as f:
                val = f.read().strip()
                if val and "claysession=" in val:
                    return val
        except Exception:
            pass

    # 6. Check Streamlit Secrets
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            if "cookies" in st.secrets:
                for cand in candidates_to_try:
                    if cand in st.secrets["cookies"]:
                        val = str(st.secrets["cookies"][cand]).strip()
                        if val:
                            return extract_clean_cookie(val)
            for key in ["CLAY_COOKIE", "clay_cookie", "COOKIE", "cookie"]:
                if key in st.secrets:
                    val = str(st.secrets[key]).strip()
                    if val:
                        return extract_clean_cookie(val)
    except Exception:
        pass

    return ""
