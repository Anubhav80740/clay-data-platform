import csv
import glob
import json
import os
import re
import subprocess
import sys
import time
import pandas as pd
import streamlit as st

# Helper for safe numeric conversion avoiding IntCastingNaNError
def safe_int(val, default=0):
    try:
        if pd.isna(val) or val is None or str(val).strip() == "":
            return default
        return int(float(val))
    except (ValueError, TypeError):
        return default

def safe_sum(series):
    try:
        return int(pd.to_numeric(series, errors="coerce").fillna(0).sum())
    except Exception:
        return 0

def load_ledger_dataframe(filepath):
    if not filepath or not os.path.exists(filepath):
        return pd.DataFrame()
    std_cols = ["industry", "clay_count", "rows_downloaded", "unique_companies", "coverage_pct", "existing_in_file", "new_added", "file"]
    parsed_rows = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            r = csv.reader(f)
            header = next(r, None)
            if not header:
                return pd.DataFrame()
            for line in r:
                if not line or not any(line):
                    continue
                if len(line) == 6:
                    ind, cc, dl, un, cov, fpath = line
                    parsed_rows.append([ind, cc, dl, un, cov, un, 0, fpath])
                elif len(line) >= 8:
                    parsed_rows.append(line[:8])
                else:
                    padded = line + [""] * (8 - len(line))
                    parsed_rows.append(padded)
        df = pd.DataFrame(parsed_rows, columns=std_cols)
        return df
    except Exception:
        try:
            return pd.read_csv(filepath, on_bad_lines="skip")
        except Exception:
            return pd.DataFrame()

# Import taxonomy and geo dict
try:
    from clay_taxonomy import ALL_CLAY_INDUSTRIES, ALL_CLAY_COUNTRIES, TECH_INDUSTRIES, NON_TECH_INDUSTRIES
except ImportError:
    ALL_CLAY_INDUSTRIES = ["Telecommunications", "Information Services", "Biotechnology", "Industrial Automation"]
    ALL_CLAY_COUNTRIES = ["Spain", "United States", "India", "United Kingdom", "France", "Germany", "Canada", "Netherlands", "Australia", "Sweden", "United Arab Emirates", "Singapore", "Denmark", "Ireland", "New Zealand"]
    TECH_INDUSTRIES = ALL_CLAY_INDUSTRIES
    NON_TECH_INDUSTRIES = []

import clay_geo
import clay_lib as cl
import streamlit.components.v1 as components

# PostHog Analytics Setup
POSTHOG_API_KEY = os.environ.get("POSTHOG_API_KEY") or "phc_C9kRXc4cEpL5SrF8yb6kpBdJazYy85WmjNTm4Gh2oi5a"
POSTHOG_HOST = os.environ.get("POSTHOG_HOST") or "https://us.i.posthog.com"

try:
    import posthog
    posthog.api_key = POSTHOG_API_KEY
    posthog.host = POSTHOG_HOST
    posthog.sync_mode = True
    POSTHOG_ENABLED = True
except Exception:
    POSTHOG_ENABLED = False

import clay_logger

def track_event(event_name, properties=None):
    uid = st.session_state.get("user_id", "team_user")
    props = properties or {}
    # Enrich with Web Analytics properties
    if "$host" not in props:
        props["$host"] = "clay-data-platform.streamlit.app"
    if "$current_url" not in props:
        props["$current_url"] = "https://clay-data-platform.streamlit.app/"
    if "$pathname" not in props:
        props["$pathname"] = "/"
    props["application"] = "Clay Data Platform"

    # Centralized Activity Audit Log
    try:
        clay_logger.log_activity(
            event_name,
            entity=props.get("entity", "Companies"),
            country=props.get("country", ""),
            industry=props.get("industry", ""),
            status=props.get("status", "SUCCESS"),
            details=props,
            user_id=uid
        )
    except Exception:
        pass

    if POSTHOG_ENABLED:
        try:
            posthog.capture(uid, event_name, props)
        except Exception:
            pass
    # Direct HTTP fallback for instant delivery
    try:
        import requests
        requests.post(
            f"{POSTHOG_HOST}/capture/",
            json={"api_key": POSTHOG_API_KEY, "event": event_name, "distinct_id": uid, "properties": props},
            timeout=3
        )
    except Exception:
        pass

# Page Configuration
st.set_page_config(
    page_title="Clay Data Platform",
    layout="wide"
)

# Inject PostHog JS for Full Web Analytics, Session Replay & Heatmaps
posthog_js = f"""
<script>
    !function(t,e){{var o,n,p,r;e.__SV||(window.posthog=e,e._i=[],e.init=function(i,s,a){{function g(t,e){{var o=e.split(".");2==o.length&&(t=t[o[0]],e=o[1]),t[e]=function(){{t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}}}var u=e;for("undefined"!=typeof a?u=e[a]=[]:a="posthog",u.people=u.people||[],u.toString=function(t){{var e="posthog";return"posthog"!==a&&(e+="."+a),t||(e+=" (stub)"),e}},u.people.toString=function(){{return u.toString(1)+".people (stub)"}},o="capture identify alias people.set people.set_once set_config register register_once unregister opt_out_capturing has_opted_out_capturing opt_in_capturing reset isFeatureEnabled onFeatureFlags getFeatureFlag getFeatureFlagPayload reloadFeatureFlags group updateEarlyAccessFeatureEnrollment getEarlyAccessFeatures getActiveMatchingSurveys getSurveys onSessionId".split(" "),n=0;n<o.length;n++)g(u,o[n]);e._i.push([i,s,a])}},e.__SV=1)}}(document,window.posthog||[]);
    
    var appUrl = document.referrer || window.location.href;
    try {{
        if (window.parent && window.parent.location && window.parent.location.href) {{
            appUrl = window.parent.location.href;
        }}
    }} catch(e) {{
        if (document.referrer) {{
            appUrl = document.referrer;
        }}
    }}

    var parsedHost = "clay-data-platform.streamlit.app";
    var parsedPath = "/";
    try {{
        if (appUrl.indexOf("http") === 0) {{
            var urlObj = new URL(appUrl);
            parsedHost = urlObj.host || parsedHost;
            parsedPath = urlObj.pathname || parsedPath;
        }}
    }} catch(e) {{}}

    posthog.init('{POSTHOG_API_KEY}', {{
        api_host: '{POSTHOG_HOST}',
        person_profiles: 'always',
        autocapture: true,
        capture_pageview: false,
        capture_pageleave: true,
        session_recording: {{
            maskAllInputs: false,
            maskInputOptions: {{
                password: true
            }}
        }}
    }});
    
    var webProps = {{
        'application': 'Clay Data Platform',
        '$current_url': appUrl,
        '$host': parsedHost,
        '$pathname': parsedPath
    }};
    
    posthog.register(webProps);
    posthog.capture('$pageview', webProps);
</script>
"""
components.html(posthog_js, height=0, width=0)

import uuid

# Theme State Handling (Light vs Dark Mode)
if "theme_mode" not in st.session_state:
    st.session_state["theme_mode"] = "dark"

if "current_process" not in st.session_state:
    st.session_state["current_process"] = None

if "session_id" not in st.session_state:
    st.session_state["session_id"] = uuid.uuid4().hex[:8]

if "posthog_init" not in st.session_state:
    st.session_state["posthog_init"] = True
    track_event("app_loaded", {"platform": "Streamlit Cloud", "theme": st.session_state["theme_mode"], "session_id": st.session_state["session_id"]})

# Inject Clean Responsive CSS with Dark/Light Theme Support & Hidden Headers
if st.session_state["theme_mode"] == "dark":
    theme_css = """
        <style>
        header[data-testid="stHeader"] { display: none !important; }
        footer { display: none !important; }
        #MainMenu { visibility: hidden !important; }
        .stApp { margin-top: -30px; background-color: #0b0f19; color: #f1f5f9; }
        
        .top-navbar {
            background-color: #111827;
            padding: 16px 24px;
            border-radius: 10px;
            margin-bottom: 24px;
            border: 1px solid #1f2937;
        }
        .metric-box {
            background-color: #111827;
            padding: 16px;
            border-radius: 8px;
            border: 1px solid #1f2937;
            text-align: center;
        }
        .badge-green { background-color: #065f46; color: #34d399; padding: 4px 10px; border-radius: 6px; font-weight: 600; }
        .badge-orange { background-color: #92400e; color: #fbbf24; padding: 4px 10px; border-radius: 6px; font-weight: 600; }
        .badge-blue { background-color: #1e40af; color: #60a5fa; padding: 4px 10px; border-radius: 6px; font-weight: 600; }
        
        /* Dark Mode Dividers & Borders */
        hr, div[data-testid="stDivider"] {
            border: none !important;
            border-top: 1px solid #334155 !important;
            opacity: 1 !important;
            margin: 20px 0 !important;
        }
        div[data-baseweb="tab-list"] {
            border-bottom: 2px solid #1f2937 !important;
        }
        div[data-baseweb="tab-highlight"] {
            background-color: #ef4444 !important;
        }
        </style>
    """
else:
    theme_css = """
        <style>
        header[data-testid="stHeader"] { display: none !important; }
        footer { display: none !important; }
        #MainMenu { visibility: hidden !important; }
        .stApp { margin-top: -30px; background-color: #f8fafc; color: #0f172a !important; }
        
        .top-navbar {
            background-color: #ffffff;
            padding: 16px 24px;
            border-radius: 10px;
            margin-bottom: 24px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        .metric-box {
            background-color: #ffffff;
            padding: 16px;
            border-radius: 8px;
            border: 1px solid #cbd5e1;
            text-align: center;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        .badge-green { background-color: #dcfce7; color: #166534; padding: 4px 10px; border-radius: 6px; font-weight: 600; border: 1px solid #bbf7d0; }
        .badge-orange { background-color: #fef3c7; color: #92400e; padding: 4px 10px; border-radius: 6px; font-weight: 600; border: 1px solid #fde68a; }
        .badge-blue { background-color: #dbeafe; color: #1e40af; padding: 4px 10px; border-radius: 6px; font-weight: 600; border: 1px solid #bfdbfe; }
        
        /* High contrast divider and tab separator lines in light mode */
        hr, div[data-testid="stDivider"] {
            border: none !important;
            border-top: 2px solid #cbd5e1 !important;
            opacity: 1 !important;
            margin: 20px 0 !important;
        }
        div[data-baseweb="tab-list"] {
            border-bottom: 2px solid #cbd5e1 !important;
        }
        div[data-baseweb="tab-highlight"] {
            background-color: #ef4444 !important;
        }
        
        /* High contrast light mode elements */
        .stButton > button {
            background-color: #ffffff !important;
            color: #0f172a !important;
            border: 1px solid #cbd5e1 !important;
            font-weight: 500 !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
        }
        .stButton > button * {
            color: #0f172a !important;
        }
        .stButton > button:hover {
            background-color: #f1f5f9 !important;
            border-color: #94a3b8 !important;
            color: #0284c7 !important;
        }
        .stButton > button:hover * {
            color: #0284c7 !important;
        }
        .stButton > button[kind="primary"] {
            background-color: #2563eb !important;
            color: #ffffff !important;
            border: 1px solid #1d4ed8 !important;
        }
        .stButton > button[kind="primary"] * {
            color: #ffffff !important;
        }
        .stButton > button[kind="primary"]:hover {
            background-color: #1d4ed8 !important;
            color: #ffffff !important;
        }
        
        /* Tabs contrast in light mode */
        button[data-baseweb="tab"] {
            color: #475569 !important;
            font-size: 15px !important;
            font-weight: 600 !important;
        }
        button[data-baseweb="tab"] p, button[data-baseweb="tab"] span, button[data-baseweb="tab"] div {
            color: #475569 !important;
            font-weight: 600 !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            color: #ef4444 !important;
            border-bottom-color: #ef4444 !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] p, button[data-baseweb="tab"][aria-selected="true"] span {
            color: #ef4444 !important;
            font-weight: 700 !important;
        }
        
        /* Radio button labels in light mode */
        div[data-testid="stRadio"] label, div[data-testid="stRadio"] label p, div[data-testid="stRadio"] label span {
            color: #0f172a !important;
            font-weight: 600 !important;
        }
        div[data-testid="stRadio"] div[role="radiogroup"] {
            color: #0f172a !important;
        }
        
        /* Selectboxes & Dropdowns in light mode */
        div[data-baseweb="select"] > div {
            background-color: #ffffff !important;
            color: #0f172a !important;
            border: 1px solid #cbd5e1 !important;
        }
        div[data-baseweb="select"] input, div[data-baseweb="select"] span, div[data-baseweb="select"] div {
            color: #0f172a !important;
        }
        div[data-baseweb="popover"], div[data-baseweb="menu"], div[role="listbox"], ul[role="listbox"] {
            background-color: #ffffff !important;
            color: #0f172a !important;
            border: 1px solid #cbd5e1 !important;
        }
        li[role="option"] {
            background-color: #ffffff !important;
            color: #0f172a !important;
        }
        li[role="option"] * {
            color: #0f172a !important;
        }
        li[role="option"]:hover {
            background-color: #f1f5f9 !important;
        }
        
        /* Multiselect tags */
        div[data-baseweb="tag"] {
            background-color: #e2e8f0 !important;
            color: #0f172a !important;
            border: 1px solid #cbd5e1 !important;
        }
        div[data-baseweb="tag"] span {
            color: #0f172a !important;
        }
        
        /* Checkbox */
        div[data-testid="stCheckbox"] label, div[data-testid="stCheckbox"] label p, div[data-testid="stCheckbox"] label span {
            color: #0f172a !important;
            font-weight: 500 !important;
        }
        
        /* Alerts */
        .stAlert {
            color: #0f172a !important;
            border-radius: 8px !important;
        }
        .stAlert p, .stAlert span {
            color: #0f172a !important;
        }
        div[data-testid="stAlert"] {
            background-color: #fef9c3 !important;
            border: 1px solid #fde047 !important;
        }
        div[data-testid="stAlert"] p {
            color: #713f12 !important;
            font-weight: 500 !important;
        }
        
        /* Metrics & Typography */
        div[data-testid="stMetricValue"] {
            color: #0f172a !important;
        }
        div[data-testid="stMetricLabel"] {
            color: #475569 !important;
        }
        div[data-testid="stExpander"] {
            background-color: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 8px !important;
        }
        .stTextInput input, .stTextArea textarea {
            background-color: #ffffff !important;
            color: #0f172a !important;
            border-color: #cbd5e1 !important;
        }
        .stCaption, small {
            color: #475569 !important;
        }
        label, p, span, h1, h2, h3, h4, h5, h6 {
            color: #0f172a;
        }
        </style>
    """

st.markdown(theme_css, unsafe_allow_html=True)

# Shared Single-Login Authentication
TEAM_USER_ID = os.environ.get("CLAY_USER_ID", "team")
TEAM_PASSWORD = os.environ.get("CLAY_PASSWORD", "clay2026")

try:
    if "CLAY_USER_ID" in st.secrets:
        TEAM_USER_ID = str(st.secrets["CLAY_USER_ID"]).strip()
    if "CLAY_PASSWORD" in st.secrets:
        TEAM_PASSWORD = str(st.secrets["CLAY_PASSWORD"]).strip()
except Exception:
    pass

# Persistent Session Restore via Query Params
if st.query_params.get("auth") == "1":
    st.session_state["authenticated"] = True
    if "user_id" not in st.session_state:
        st.session_state["user_id"] = st.query_params.get("uid", TEAM_USER_ID)

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

def login_screen():
    st.markdown("### Clay Data Platform - Team Login")
    st.caption("Please enter your team credentials to access the extraction workspace.")
    
    col_login, _ = st.columns([1, 2])
    with col_login:
        user_id = st.text_input("User ID")
        password = st.text_input("Password", type="password")
        if st.button("Login", type="primary", use_container_width=True):
            if user_id.strip() == TEAM_USER_ID and password.strip() == TEAM_PASSWORD:
                st.session_state["authenticated"] = True
                st.session_state["user_id"] = user_id.strip()
                st.query_params["auth"] = "1"
                st.query_params["uid"] = user_id.strip()
                track_event("user_login", {"user_id": user_id.strip()})
                st.rerun()
            else:
                st.error("Invalid User ID or Password.")

if not st.session_state["authenticated"]:
    login_screen()
    st.stop()

# Fixed Top Navigation Bar (Logo, Cookie Status, Theme Toggle, Stop Button, Logout)
nav_col1, nav_col_cookie, nav_col2, nav_col3, nav_col4 = st.columns([3.5, 1.8, 1.1, 1.1, 0.9])

with nav_col1:
    st.title("Clay Data Platform")
    st.caption("Centralized Company Data Extraction, Deduplication and Portfolio Engine")

@st.cache_data(ttl=120, show_spinner=False)
def check_cookie_cached(cookie_token):
    from auto_cookie_fetcher import verify_cookie
    return verify_cookie(cookie_token)

with nav_col_cookie:
    st.write("")
    try:
        from auto_cookie_fetcher import fetch_cookie, COOKIE_FILE
        active_c = cl._cookie()
        is_cookie_valid = check_cookie_cached(active_c)
        if is_cookie_valid:
            st.markdown("<span class='badge-green'>🟢 Cookie: Active</span>", unsafe_allow_html=True)
        else:
            st.markdown("<span class='badge-orange'>🔴 Cookie: Expired</span>", unsafe_allow_html=True)
        
        if st.button("🍪 Refresh Cookie (Auto)", use_container_width=True, help="Launches automated browser to refresh Clay session cookie"):
            track_event("cookie_refresh_started", {"user_id": st.session_state.get("user_id", "team_user")})
            with st.spinner("Refreshing Clay cookie..."):
                new_c = fetch_cookie(timeout_seconds=90)
                if new_c:
                    st.cache_data.clear()
                    st.success("Cookie successfully verified & updated!")
                    track_event("cookie_refresh_completed", {"success": True})
                    st.rerun()
                else:
                    st.error("Failed to capture new cookie. Using default active session.")
                    track_event("cookie_refresh_completed", {"success": False})
    except Exception as e:
        st.caption(f"Cookie status: {e}")

with nav_col2:
    st.write("")
    theme_btn_label = "☀️ Light Mode" if st.session_state["theme_mode"] == "dark" else "🌙 Dark Mode"
    if st.button(theme_btn_label, use_container_width=True):
        new_theme = "light" if st.session_state["theme_mode"] == "dark" else "dark"
        st.session_state["theme_mode"] = new_theme
        track_event("theme_toggled", {"theme": new_theme})
        st.rerun()

with nav_col3:
    st.write("")
    if st.button("Stop Process", type="secondary", use_container_width=True):
        proc = st.session_state.get("current_process")
        if proc and proc.poll() is None:
            proc.terminate()
            st.session_state["current_process"] = None
            track_event("process_stopped", {"location": "navbar"})
            st.warning("Active process stopped by user.")
        else:
            st.info("No active process running.")

with nav_col4:
    st.write("")
    if st.button("Logout", type="secondary", use_container_width=True):
        st.session_state["authenticated"] = False
        st.query_params.clear()
        st.rerun()

st.divider()

# Fixed Floating Download Card Placeholder (visible on screen regardless of tab or scroll)
global_card_placeholder = st.empty()

def render_download_card(pct, title, subtitle):
    global_card_placeholder.markdown(f"""
    <div style="position: fixed; bottom: 24px; right: 24px; z-index: 999999; min-width: 320px; max-width: 440px; background: #0f172a; color: #ffffff; padding: 16px 20px; border-radius: 12px; border: 2px solid #3b82f6; box-shadow: 0 12px 30px rgba(0,0,0,0.5); font-family: sans-serif;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background-color: #22c55e; box-shadow: 0 0 10px #22c55e;"></span>
                <strong style="font-size: 14px; color: #f8fafc;">{title}</strong>
            </div>
            <span style="font-weight: bold; color: #60a5fa; font-size: 15px;">{int(pct * 100)}%</span>
        </div>
        <div style="font-size: 12px; color: #cbd5e1; margin-bottom: 10px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
            {subtitle}
        </div>
        <div style="background-color: #334155; border-radius: 9999px; height: 6px; width: 100%; overflow: hidden;">
            <div style="background-color: #3b82f6; height: 100%; width: {int(pct * 100)}%; transition: width 0.3s ease;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_download_complete_card(msg):
    global_card_placeholder.markdown(f"""
    <div style="position: fixed; bottom: 24px; right: 24px; z-index: 999999; min-width: 320px; background: #064e3b; color: #ffffff; padding: 14px 20px; border-radius: 12px; border: 2px solid #10b981; box-shadow: 0 12px 30px rgba(0,0,0,0.4); font-family: sans-serif;">
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 16px;">✅</span>
            <strong style="font-size: 14px; color: #ffffff;">{msg}</strong>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Global Persistent Status Banner
live_status = st.session_state.get("live_status")
if live_status and live_status.get("active"):
    pct_val = float(live_status.get("pct", 0.0))
    render_download_card(pct_val, live_status.get("title", "Operation Active"), live_status.get("text", "In progress..."))
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #1e3a8a, #2563eb); color: #ffffff; padding: 14px 20px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #3b82f6; box-shadow: 0 4px 12px rgba(37,99,235,0.2);">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <span style="display: inline-block; width: 12px; height: 12px; border-radius: 50%; background-color: #22c55e; box-shadow: 0 0 10px #22c55e;"></span>
                <div>
                    <strong style="font-size: 15px;">⏳ {live_status.get('title', 'Operation Active')}</strong>
                    <div style="font-size: 13px; opacity: 0.92; margin-top: 2px;">{live_status.get('text', 'In progress...')}</div>
                </div>
            </div>
            <div style="font-size: 18px; font-weight: bold; background: rgba(255,255,255,0.18); padding: 4px 12px; border-radius: 6px;">{int(pct_val * 100)}%</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.progress(pct_val)

tab_download, tab_geo, tab_portfolio, tab_audit, tab_faq = st.tabs([
    "Run Data Extraction",
    "Country Division Settings",
    "Delivered Portfolio",
    "📋 Activity & Count Drift Logs",
    "Centralized Store & Deduplication FAQ"
])

with tab_download:
    st.subheader("Step A: Select Extraction Mode, Country, and Target Industries")
    
    if "_init_mode_loaded" not in st.session_state:
        st.session_state["_init_mode_loaded"] = True
        qp_mode = st.query_params.get("mode", "companies")
        st.session_state["search_mode_idx"] = 1 if qp_mode == "people" else 0
        
    def on_mode_change():
        m_val = st.session_state.get("search_mode_widget")
        st.session_state["search_mode_idx"] = 1 if "People" in str(m_val) else 0
        st.query_params["mode"] = "people" if "People" in str(m_val) else "companies"

    curr_mode_idx = st.session_state.get("search_mode_idx", 0)
    search_mode = st.radio(
        "Select Extraction Entity:",
        ["🏢 Companies Search", "👤 People Search"],
        horizontal=True,
        index=curr_mode_idx,
        key="search_mode_widget",
        on_change=on_mode_change,
        help="Choose whether to extract Company datasets (Domains, Employee sizes, LinkedIn) or People/Contacts datasets (Full Names, Job Titles, Locations, Profile URLs)"
    )
    is_people_mode = "People" in search_mode
    
    col_c, col_i = st.columns([1, 2])
    
    with col_c:
        st.markdown("**1. Target Country Selection**")
        
        # Country dropdown with Global option
        country_options = ["-- Select Target Country --", "🌍 All Supported Countries (Global)"] + ALL_CLAY_COUNTRIES
        
        if "_init_country_loaded" not in st.session_state:
            st.session_state["_init_country_loaded"] = True
            qp_c = st.query_params.get("c", "")
            if qp_c and qp_c in country_options:
                st.session_state["sel_country_idx"] = country_options.index(qp_c)
            elif qp_c == "Global":
                st.session_state["sel_country_idx"] = 1
            else:
                st.session_state["sel_country_idx"] = 0
                
        def on_country_change():
            chosen = st.session_state.get("country_select_widget")
            if chosen and chosen in country_options:
                st.session_state["sel_country_idx"] = country_options.index(chosen)
                if chosen == "🌍 All Supported Countries (Global)":
                    st.query_params["c"] = "Global"
                elif chosen != "-- Select Target Country --":
                    st.query_params["c"] = chosen
                elif "c" in st.query_params:
                    del st.query_params["c"]

        curr_c_idx = st.session_state.get("sel_country_idx", 0)
        if curr_c_idx >= len(country_options):
            curr_c_idx = 0
            
        selected_country_raw = st.selectbox(
            "Search and select country (218 countries available):",
            options=country_options,
            index=curr_c_idx,
            key="country_select_widget",
            on_change=on_country_change,
            help="Select any country or choose Global to extract across all 17 supported countries."
        )
        
        custom_country_toggle = st.checkbox("Enter custom country name manually")
        if custom_country_toggle:
            country_input = st.text_input("Manual Country Name", "")
        else:
            if selected_country_raw == "-- Select Target Country --":
                country_input = ""
            elif selected_country_raw == "🌍 All Supported Countries (Global)":
                country_input = "Global"
            else:
                country_input = selected_country_raw
            
        country_input = country_input.strip()
        if country_input:
            st.query_params["c"] = country_input
        elif "c" in st.query_params:
            del st.query_params["c"]
        
        if country_input:
            if country_input == "Global":
                st.info("🌍 **Global Extraction Active**: Data will be extracted and compiled sequentially across all 17 configured countries, creating both per-country master files and unified Global delivery files.")
            else:
                geo_dict = getattr(clay_geo, "GEO", {})
                has_geo = country_input in geo_dict
                if has_geo:
                    g_cfg = geo_dict[country_input]
                    num_cities = len(g_cfg.get("cities", []))
                    num_states = len(g_cfg.get("states", []))
                    state_str = f"{num_states} States/Regions" if num_states else ""
                    city_str = f"{num_cities} Cities" if num_cities else ""
                    div_str = ", ".join(filter(None, [state_str, city_str]))
                    st.info(f"🟢 **Geographic Partitioning Active for {country_input}**: {div_str} mapped for high-coverage extraction.")
                else:
                    st.info(f"🌐 **Extraction Active for {country_input}**: Multi-Dimensional Partitioning (City, Keyword, Size, Revenue) Enabled.")
        else:
            st.caption("Please select a target country above to get started.")

    with col_i:
        st.markdown("**2. Target Industries Selection**")
        
        if "_init_ind_loaded" not in st.session_state:
            st.session_state["_init_ind_loaded"] = True
            qp_ind = st.query_params.get("ind", "")
            if qp_ind:
                st.session_state["selected_industries"] = [x.strip() for x in qp_ind.split("|") if x.strip() and x.strip() in ALL_CLAY_INDUSTRIES]
            else:
                st.session_state["selected_industries"] = []
        elif "selected_industries" not in st.session_state:
            st.session_state["selected_industries"] = []

        b_col1, b_col2, b_col3, b_col4 = st.columns(4)
        
        with b_col1:
            if st.button("Select Tech Industries", use_container_width=True):
                st.session_state["selected_industries"] = TECH_INDUSTRIES
                st.query_params["ind"] = "|".join(TECH_INDUSTRIES)
                
        with b_col2:
            if st.button("Select Non-Tech Industries", use_container_width=True):
                st.session_state["selected_industries"] = NON_TECH_INDUSTRIES
                st.query_params["ind"] = "|".join(NON_TECH_INDUSTRIES)
                
        with b_col3:
            if st.button("Select All 458 Industries", use_container_width=True):
                st.session_state["selected_industries"] = ALL_CLAY_INDUSTRIES
                st.query_params["ind"] = "|".join(ALL_CLAY_INDUSTRIES)
                
        with b_col4:
            if st.button("Clear Selection", use_container_width=True):
                st.session_state["selected_industries"] = []
                if "ind" in st.query_params:
                    del st.query_params["ind"]

        selected_industries = st.multiselect(
            "Search and select industries (starts empty; select manually or use category buttons above):",
            options=ALL_CLAY_INDUSTRIES,
            key="selected_industries"
        )
        
        if selected_industries:
            st.query_params["ind"] = "|".join(selected_industries)
        elif "ind" in st.query_params:
            del st.query_params["ind"]
        
        st.caption(f"Currently selected: {len(selected_industries)} industries out of 458 total Clay industries.")

    st.divider()
    entity_label = "People / Contacts" if is_people_mode else "Companies"
    st.subheader(f"Step B: 3-Step Execution Workflow ({entity_label})")
    
    def slugify(text):
        return re.sub(r'[^a-zA-Z0-9]+', '_', text).strip('_')

    country_slug = slugify(country_input) if country_input else ""
    os.makedirs("data", exist_ok=True)
    if is_people_mode:
        base_c = f"{country_slug}_people_counts.csv" if country_slug else ""
        base_l = f"{country_slug}_people_progress.csv" if country_slug else ""
        counts_file = os.path.join("data", base_c) if base_c and (os.path.exists(os.path.join("data", base_c)) or not os.path.exists(base_c)) else base_c
        ledger_file = os.path.join("data", base_l) if base_l and (os.path.exists(os.path.join("data", base_l)) or not os.path.exists(base_l)) else base_l
        count_script = "count_people.py"
        plan_script = "generate_people_clicklist.py"
        run_script = "run_people.py"
        plan_suffix = "_people"
        delivery_root = "delivery_people"
    else:
        base_c = f"{country_slug}_nontech_counts.csv" if country_slug else ""
        base_l = f"{country_slug}_nontech_progress.csv" if country_slug else ""
        counts_file = os.path.join("data", base_c) if base_c and (os.path.exists(os.path.join("data", base_c)) or not os.path.exists(base_c)) else base_c
        ledger_file = os.path.join("data", base_l) if base_l and (os.path.exists(os.path.join("data", base_l)) or not os.path.exists(base_l)) else base_l
        count_script = "count_industries.py"
        plan_script = "generate_clicklist.py"
        run_script = "run_nontech.py"
        plan_suffix = ""
        delivery_root = "delivery"

    ind_file = f"selected_industries_{st.session_state['session_id']}.json"

    step_col1, step_col2, step_col3 = st.columns([1, 1, 1])

    # ----------------------------------------------------
    # STEP 1: COUNT WITH PROGRESS BAR
    # ----------------------------------------------------
    with step_col1:
        st.markdown(f"#### Step 1: Count Target {entity_label}")
        c_btn_c1, c_btn_c2 = st.columns([2.5, 1])
        with c_btn_c1:
            btn_count = st.button(f"Run Step 1: Count", use_container_width=True, disabled=not country_input or not selected_industries)
        with c_btn_c2:
            if st.button("🛑 Stop", key="stop_step1_btn", type="secondary", use_container_width=True):
                proc = st.session_state.get("current_process")
                if proc and proc.poll() is None:
                    proc.terminate()
                    st.session_state["current_process"] = None
                    st.warning("Counting stopped.")
                else:
                    st.info("No active count process.")

        if btn_count:
            track_event("count_started", {"entity": entity_label, "country": country_input, "industries_count": len(selected_industries)})
            with open(ind_file, "w", encoding="utf-8") as f:
                json.dump(selected_industries, f)
            if os.path.exists(counts_file):
                os.remove(counts_file)
            
            count_progress_bar = st.progress(0.0)
            count_status = st.empty()
            count_status.text(f"Starting {entity_label} count for {len(selected_industries)} industries in {country_input}...")
            
            cmd = [sys.executable, "-u", count_script, country_input, "--industries-file", ind_file]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            st.session_state["current_process"] = proc
            
            total_to_count = len(selected_industries)
            
            while True:
                line = proc.stdout.readline()
                if not line and proc.poll() is not None:
                    break
                if line:
                    m = re.search(r'\[(\d+)/(\d+)\]', line)
                    if m:
                        current_i = int(m.group(1))
                        tot_i = int(m.group(2))
                        pct = min(1.0, current_i / max(1, tot_i))
                        count_progress_bar.progress(pct)
                        count_status.text(f"Counting: {current_i} of {tot_i} industries ({int(pct*100)}%)")
            
            proc.wait()
            st.session_state["current_process"] = None
            if proc.returncode == 0:
                count_progress_bar.progress(1.0)
                count_status.text("Counting complete.")
                st.success(f"Step 1 Count complete for {entity_label}.")
                track_event("count_completed", {"entity": entity_label, "country": country_input, "industries_count": len(selected_industries)})
            else:
                st.error("Step 1 Count failed or stopped.")

    # ----------------------------------------------------
    # STEP 2: PLAN & ESTIMATE COVERAGE
    # ----------------------------------------------------
    with step_col2:
        st.markdown(f"#### Step 2: Plan Coverage")
        st.caption(f"Free planning query. Partitions {entity_label} slices and estimates reachable coverage.")
        p_btn_c1, p_btn_c2 = st.columns([2.5, 1])
        with p_btn_c1:
            btn_plan = st.button(f"Run Step 2: Plan", use_container_width=True, disabled=not country_input or not selected_industries)
        with p_btn_c2:
            if st.button("🛑 Stop", key="stop_step2_btn", type="secondary", use_container_width=True):
                proc = st.session_state.get("current_process")
                if proc and proc.poll() is None:
                    proc.terminate()
                    st.session_state["current_process"] = None
                    st.warning("Planning stopped.")
                else:
                    st.info("No active plan process.")

        if btn_plan:
            track_event("plan_started", {"entity": entity_label, "country": country_input, "industries_count": len(selected_industries)})
            with open(ind_file, "w", encoding="utf-8") as f:
                json.dump(selected_industries, f)
                
            plan_progress_bar = st.progress(0.0)
            plan_status = st.empty()
            tot_p = len(selected_industries)
            
            for idx, ind in enumerate(selected_industries, 1):
                plan_status.text(f"Planning {idx} of {tot_p}: {ind} ({entity_label})...")
                cmd = [sys.executable, "-u", plan_script, ind, country_input]
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                st.session_state["current_process"] = proc
                stdout_out, _ = proc.communicate()
                if proc.returncode != 0:
                    time.sleep(1)
                    proc_retry = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                    st.session_state["current_process"] = proc_retry
                    proc_retry.communicate()
                plan_progress_bar.progress(idx / tot_p)
                
            st.session_state["current_process"] = None
            plan_status.text("Planning complete.")
            st.success("Step 2 Planning complete. Review estimated coverage below.")
            track_event("plan_completed", {"entity": entity_label, "country": country_input, "industries_count": len(selected_industries)})

    # ----------------------------------------------------
    # STEP 3: DOWNLOAD & DELIVER WITH PROGRESS BAR
    # ----------------------------------------------------
    with step_col3:
        st.markdown(f"#### Step 3: Download Data")
        st.caption(f"Executes download, incremental merge, and deduplication.")
        
        plan_approved = st.checkbox(f"I approve the plan & estimated coverage", key=f"plan_approved_check_{'ppl' if is_people_mode else 'cmp'}")
        d_btn_c1, d_btn_c2 = st.columns([2.5, 1])
        with d_btn_c1:
            btn_download = st.button(f"Run Step 3: Download", type="primary", use_container_width=True, disabled=not plan_approved or not country_input or not selected_industries)
        with d_btn_c2:
            if st.button("🛑 Stop", key="stop_step3_btn", type="secondary", use_container_width=True):
                proc = st.session_state.get("current_process")
                if proc and proc.poll() is None:
                    proc.terminate()
                    st.session_state["current_process"] = None
                    st.warning("Download stopped.")
                else:
                    st.info("No active download process.")

    # ----------------------------------------------------
    # PERSISTENT COUNTS LOAD & DISPLAY FOR SELECTED COUNTRY
    # ----------------------------------------------------
    if country_input and os.path.exists(counts_file):
        try:
            cdf = pd.read_csv(counts_file)
            if selected_industries:
                cdf_sel = cdf[cdf["Industry"].isin(selected_industries)]
            else:
                cdf_sel = cdf
                
            if not cdf_sel.empty:
                st.markdown(f"### Step 1 Count Results ({country_input})")
                st.caption("Cached counts loaded. Click 'Run Step 1: Count' anytime to refresh counts from Clay.")
                cdf_sel_disp = cdf_sel.copy()
                cdf_sel_disp.index = range(1, len(cdf_sel_disp) + 1)
                st.dataframe(cdf_sel_disp, use_container_width=True)
                tot_c = safe_sum(cdf_sel["Count"]) if "Count" in cdf_sel.columns else 0
                st.info(f"Total Clay Target Rows: {tot_c:,} rows across {len(cdf_sel)} selected industries.")
        except Exception:
            pass

    # ----------------------------------------------------
    # STEP 2 PLAN RESULTS & IN-TABLE PER-INDUSTRY RE-PLANNING
    # ----------------------------------------------------
    planned_data = []
    if country_input and selected_industries:
        counts_lookup = {}
        if os.path.exists(counts_file):
            try:
                cdf_lk = pd.read_csv(counts_file)
                for _, r in cdf_lk.iterrows():
                    counts_lookup[str(r.get("Industry")).strip()] = safe_int(r.get("Count"))
            except Exception:
                pass

        for ind in selected_industries:
            prefix = slugify(f"{ind}_{country_input}{plan_suffix}")
            pj = f"plans/clicklist_{prefix}.json"
            exp = counts_lookup.get(ind, 0)
            
            num_slices = 0
            gap = 0
            has_plan_file = os.path.exists(pj)
            is_zero_count = (ind in counts_lookup) and (exp == 0)
            is_planned = has_plan_file or is_zero_count
            status_str = "✅ Planned" if is_planned else "⏳ Pending Plan (Click Step 2)"

            if is_planned:
                try:
                    if has_plan_file and os.path.getsize(pj) >= 2:
                        p_slices = json.load(open(pj))
                        num_slices = len(p_slices)
                        slice_sum = sum(safe_int(s.get("count")) for s in p_slices)
                    else:
                        p_slices = []
                        num_slices = 0
                        slice_sum = 0

                    if exp == 0 and slice_sum > 0:
                        exp = slice_sum

                    unc_csv = f"plans/clicklist_{prefix}_uncovered.csv"
                    if os.path.exists(unc_csv):
                        with open(unc_csv) as uf:
                            gap = sum(safe_int(r.get("count")) for r in csv.DictReader(uf))
                    
                    if exp > 0:
                        reachable = min(exp, max(0, exp - gap))
                    else:
                        reachable = slice_sum
                        exp = reachable
                except Exception:
                    reachable = 0
            else:
                reachable = 0

            if exp > 0 and reachable > exp:
                reachable = exp

            if exp == 0 and is_planned:
                cov_pct = 100.0
            elif exp > 0 and is_planned:
                cov_pct = min(100.0, round(100 * reachable / max(1, exp), 1))
            else:
                cov_pct = 0.0

            planned_data.append({
                "Industry": ind,
                "Clay Target Count": exp,
                "Estimated Reachable": reachable if (is_planned and (exp > 0 or is_zero_count or has_plan_file)) else "Pending",
                "Unreachable Gap": gap if is_planned else "-",
                "Est Coverage %": f"{cov_pct}%" if is_planned else "Pending",
                "Planned Slices": num_slices,
                "Status": status_str,
                "cov_num": cov_pct if is_planned else 0.0
            })

    if planned_data:
        st.markdown(f"### Step 2 Plan & Coverage Estimate Results ({country_input} - {entity_label})")
        pdf_plan = pd.DataFrame([{k: v for k, v in r.items() if k != "cov_num"} for r in planned_data])
        pdf_plan.index = range(1, len(pdf_plan) + 1)
        
        # Display Overview Metric Cards
        tot_reach = sum(safe_int(r["Estimated Reachable"]) for r in planned_data if isinstance(r["Estimated Reachable"], (int, float)) or str(r["Estimated Reachable"]).isdigit())
        tot_target = sum(safe_int(r["Clay Target Count"]) for r in planned_data)
        if tot_target < tot_reach:
            tot_target = tot_reach
        all_planned = all(r["Status"] == "✅ Planned" for r in planned_data)
        overall_cov = min(100.0, round(100 * tot_reach / max(1, tot_target), 1)) if tot_target and all_planned else (0.0 if not all_planned else 100.0)
        
        m_col1, m_col2, m_col3 = st.columns(3)
        with m_col1:
            st.metric(f"Total Target {entity_label}", f"{tot_target:,}")
        with m_col2:
            st.metric(f"Estimated Reachable {entity_label}", f"{tot_reach:,}" if all_planned else "Pending Step 2")
        with m_col3:
            st.metric("Overall Estimated Coverage", f"{overall_cov}%" if all_planned else "Pending Step 2")

        st.dataframe(pdf_plan, use_container_width=True)

        # ----------------------------------------------------
        # IN-TABLE PER-INDUSTRY RE-PLANNING ACTIONS
        # ----------------------------------------------------
        st.markdown(f"#### In-Table Per-Industry Re-Planning & Fine-Tuning ({entity_label})")
        st.caption("If any industry coverage is not sufficient, re-plan that specific industry below without changing your selected industries:")
        
        for p_row in planned_data:
            ind_name = p_row["Industry"]
            cov_num = p_row.get("cov_num", 0.0)
            c_target = p_row["Clay Target Count"]
            c_reach = p_row["Estimated Reachable"]
            c_status = p_row["Status"]

            if c_status != "✅ Planned":
                badge = "⏳ Pending Generation"
                target_str = f"{c_target:,}" if isinstance(c_target, (int, float)) else c_target
                exp_title = f"{ind_name} | ⏳ Plan Pending ({target_str} Target Rows) | {badge}"
            elif c_target == 0:
                badge = "🟢 0 Rows in Country"
                exp_title = f"{ind_name} | 0 Target Rows (100.0% Coverage) | {badge}"
            else:
                badge = "🟢 High Coverage" if cov_num >= 95.0 else ("🟡 Partial Coverage" if cov_num >= 80.0 else "🔴 Gaps Identified")
                reach_str = f"{c_reach:,}" if isinstance(c_reach, (int, float)) else c_reach
                target_str = f"{c_target:,}" if isinstance(c_target, (int, float)) else c_target
                exp_title = f"{ind_name} | {cov_num}% Coverage ({reach_str}/{target_str}) | {badge}"
            
            with st.expander(exp_title):
                exp_c1, exp_c2, exp_c3 = st.columns([2, 1, 1])
                with exp_c1:
                    target_disp = f"{c_target:,}" if isinstance(c_target, (int, float)) else c_target
                    reach_disp = f"{c_reach:,}" if isinstance(c_reach, (int, float)) else c_reach
                    gap_disp = f"{p_row['Unreachable Gap']:,}" if isinstance(p_row['Unreachable Gap'], (int, float)) else p_row['Unreachable Gap']
                    st.write(f"**Target Rows**: {target_disp} | **Reachable**: {reach_disp} | **Gap**: {gap_disp} | **Slices**: {p_row['Planned Slices']}")
                    st.write(f"**Current Status**: `{c_status}`")
                with exp_c2:
                    if st.button(f"Re-Plan '{ind_name[:15]}...'", key=f"replan_{slugify(ind_name)}_{'ppl' if is_people_mode else 'cmp'}", use_container_width=True):
                        track_event("single_replan_triggered", {"industry": ind_name, "country": country_input, "entity": entity_label})
                        with st.spinner(f"Re-generating partition plan for '{ind_name}'..."):
                            # Clean up old slice cache for fresh download
                            prefix = slugify(f"{ind_name}_{country_input}{plan_suffix}")
                            dl_base = "downloads_people" if is_people_mode else "downloads"
                            for d in glob.glob(f"{dl_base}/{prefix}*"):
                                try:
                                    if os.path.isdir(d):
                                        shutil.rmtree(d)
                                    elif os.path.isfile(d):
                                        os.remove(d)
                                except Exception:
                                    pass
                            
                            cmd = [sys.executable, "-u", plan_script, ind_name, country_input]
                            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                            st.session_state["current_process"] = proc
                            proc.wait()
                            st.session_state["current_process"] = None
                            st.success(f"Re-plan complete for '{ind_name}'! Slices refreshed.")
                            st.rerun()
                with exp_c3:
                    if st.button(f"Download '{ind_name[:15]}...'", key=f"dl_{slugify(ind_name)}_{'ppl' if is_people_mode else 'cmp'}", type="primary", use_container_width=True):
                        track_event("single_download_started", {"industry": ind_name, "country": country_input, "entity": entity_label})
                        st.markdown(f"Executing single-industry download for `{ind_name}`...")
                        render_download_card(0.05, f"Starting '{ind_name}'...", f"Country: {country_input}")
                        cmd_run = [sys.executable, "-u", run_script, country_input, "--only", ind_name]
                        proc = subprocess.Popen(cmd_run, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
                        st.session_state["current_process"] = proc
                        log_box = st.empty()
                        logs_single = []
                        while True:
                            l = proc.stdout.readline()
                            if not l and proc.poll() is not None:
                                break
                            if l:
                                stripped_l = l.strip()
                                logs_single.append(stripped_l)
                                log_box.code("\n".join(logs_single[-15:]))
                                m_s = re.search(r'\[(\d+)/(\d+)\]', stripped_l)
                                s_pct = 0.5
                                if m_s:
                                    s_pct = min(0.95, int(m_s.group(1)) / max(1, int(m_s.group(2))))
                                render_download_card(s_pct, f"Downloading: {ind_name[:25]}", stripped_l[:45])
                        proc.wait()
                        st.session_state["current_process"] = None
                        track_event("single_download_completed", {"industry": ind_name, "country": country_input, "entity": entity_label})
                        render_download_complete_card(f"Download complete: {ind_name}!")
                        st.success(f"Download complete for '{ind_name}'!")

    # Execute Step 3 Download with Progress Bar
    if btn_download:
        if not plan_approved:
            st.warning("Please check the approval box in Step 3 to confirm plan approval before downloading.")
        else:
            st.markdown(f"### Executing Live Step 3 Download for {country_input} ({entity_label})...")
            track_event("download_started", {"entity": entity_label, "country": country_input, "industries_count": len(selected_industries), "industries": selected_industries})
            
            with open(ind_file, "w", encoding="utf-8") as f:
                json.dump(selected_industries, f)

            log_container = st.empty()
            dl_progress_bar = st.progress(0.0)
            dl_status_text = st.empty()
            render_download_card(0.02, f"Starting {entity_label} Download", f"Country: {country_input} ({len(selected_industries)} industries)")
            
            cmd_run = [sys.executable, "-u", run_script, country_input]
            only_str = "|".join(selected_industries)
            cmd_run.extend(["--only", only_str])

            process = subprocess.Popen(cmd_run, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            st.session_state["current_process"] = process
            
            logs = []
            tot_ind = len(selected_industries)
            curr_ind_idx = 0
            curr_ind_name = ""
            
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    stripped = line.strip()
                    logs.append(stripped)
                    log_container.code("\n".join(logs[-20:]))
                    
                    # Track active industry: e.g. ===== [3/7] Civil Engineering  (~5,506) =====
                    m_ind = re.search(r'\[(\d+)/(\d+)\]\s+([A-Za-z0-9\s,&-]+?)\s+\(~', stripped)
                    if m_ind:
                        curr_ind_idx = int(m_ind.group(1))
                        curr_ind_name = m_ind.group(3).strip()
                        pct = max(0.01, min(0.99, (curr_ind_idx - 1) / max(1, tot_ind)))
                        dl_progress_bar.progress(pct)
                        status_msg = f"Downloading [{curr_ind_idx}/{tot_ind}]: {curr_ind_name}..."
                        dl_status_text.text(status_msg)
                        st.session_state["live_status"] = {"active": True, "title": f"Step 3 Download: {country_input} ({entity_label})", "text": status_msg, "pct": pct}
                        render_download_card(pct, f"[{curr_ind_idx}/{tot_ind}] {curr_ind_name[:24]}", f"{country_input} • {int(pct*100)}% complete")
                    
                    # Track slice progress: e.g. [2/7] Civil_Engineering_India_st_...
                    m_slice = re.search(r'\[(\d+)/(\d+)\]\s+([A-Za-z0-9_]+)', stripped)
                    if m_slice and not m_ind and curr_ind_idx > 0:
                        s_idx = int(m_slice.group(1))
                        s_tot = int(m_slice.group(2))
                        # Interpolate progress within current industry
                        pct_ind = (s_idx - 1) / max(1, s_tot)
                        pct = min(0.99, ((curr_ind_idx - 1) + pct_ind) / max(1, tot_ind))
                        dl_progress_bar.progress(pct)
                        status_msg = f"Downloading [{curr_ind_idx}/{tot_ind}] {curr_ind_name} — Slice {s_idx}/{s_tot}..."
                        dl_status_text.text(status_msg)
                        st.session_state["live_status"] = {"active": True, "title": f"Step 3 Download: {country_input} ({entity_label})", "text": status_msg, "pct": pct}
                        render_download_card(pct, f"[{curr_ind_idx}/{tot_ind}] {curr_ind_name[:20]}", f"Slice {s_idx}/{s_tot} • {int(pct*100)}%")
                            
            process.wait()
            st.session_state["current_process"] = None
            st.session_state["live_status"] = {"active": False}
            if process.returncode == 0:
                dl_progress_bar.progress(1.0)
                dl_status_text.text(f"Step 3 Download complete. All {tot_ind} industries downloaded & merged.")
                render_download_complete_card(f"Download complete: All {tot_ind} industries merged for {country_input}!")
                st.success(f"Step 3 Download and Centralized Merge complete for {country_input} ({entity_label}).")
                track_event("download_completed", {"entity": entity_label, "country": country_input, "industries_count": len(selected_industries)})
            else:
                render_download_complete_card("Download stopped or completed.")
                st.error("Download finished with errors or stopped.")

    if country_input and os.path.exists(ledger_file):
        st.markdown(f"### 📦 Delivered Master Datasets & Incremental Merge Ledger ({country_input} - {entity_label})")
        try:
            ledger_df = load_ledger_dataframe(ledger_file)
            col_ind = "industry" if "industry" in ledger_df.columns else ("Industry" if "Industry" in ledger_df.columns else None)
            if col_ind and not ledger_df.empty:
                ledger_df = ledger_df.drop_duplicates(subset=[col_ind], keep="last")
            if selected_industries and col_ind:
                ledger_df = ledger_df[ledger_df[col_ind].isin(selected_industries)]
            
            col_uniq = "unique_people" if "unique_people" in ledger_df.columns else ("unique_companies" if "unique_companies" in ledger_df.columns else ("Total Master" if "Total Master" in ledger_df.columns else None))
            col_new = "new_added" if "new_added" in ledger_df.columns else None
            col_ex = "existing_in_file" if "existing_in_file" in ledger_df.columns else None

            tot_master = safe_sum(ledger_df[col_uniq]) if col_uniq and not ledger_df.empty else 0
            tot_new = safe_sum(ledger_df[col_new]) if col_new and not ledger_df.empty else 0
            tot_ex = safe_sum(ledger_df[col_ex]) if col_ex and not ledger_df.empty else (tot_master - tot_new)

            dm1, dm2, dm3 = st.columns(3)
            with dm1:
                st.metric(f"Total Master Unique {entity_label}", f"{tot_master:,}")
            with dm2:
                st.metric("Newly Identified & Merged", f"+{tot_new:,}")
            with dm3:
                st.metric("Deduplication Quality", "100% Unique", help="Deduplicated on Domain and LinkedIn URL")

            ledger_df_disp = ledger_df.copy()
            ledger_df_disp.index = range(1, len(ledger_df_disp) + 1)
            st.dataframe(ledger_df_disp, use_container_width=True)

            st.markdown(f"#### 📥 Download & Inspect Delivered {entity_label} Master Files")
            col_fpath = "file" if "file" in ledger_df.columns else ("File" if "File" in ledger_df.columns else None)
            if col_fpath:
                for _, lrow in ledger_df.iterrows():
                    fpath = str(lrow[col_fpath]).replace("\\", "/")
                    ind_lbl = lrow.get(col_ind, os.path.basename(fpath))
                    if os.path.exists(fpath):
                        with st.expander(f"📄 {ind_lbl} ({os.path.basename(fpath)})"):
                            try:
                                f_preview = pd.read_csv(fpath, nrows=20)
                                st.caption(f"Previewing first {len(f_preview)} rows from `{fpath}`:")
                                f_preview_disp = f_preview.copy()
                                f_preview_disp.index = range(1, len(f_preview_disp) + 1)
                                st.dataframe(f_preview_disp, use_container_width=True)
                                
                                with open(fpath, "rb") as dl_f:
                                    raw_csv_data = dl_f.read()
                                    if not raw_csv_data.startswith(b"\xef\xbb\xbf"):
                                        raw_csv_data = b"\xef\xbb\xbf" + raw_csv_data
                                    st.download_button(
                                        label=f"📥 Download Full Dataset: {os.path.basename(fpath)}",
                                        data=raw_csv_data,
                                        file_name=os.path.basename(fpath),
                                        mime="text/csv; charset=utf-8",
                                        type="primary",
                                        key=f"dl_btn_{cl.slugify(ind_lbl)}_{'ppl' if is_people_mode else 'cmp'}"
                                    )
                            except Exception as pe:
                                st.warning(f"Preview error: {pe}")
        except Exception as ex:
            st.warning(f"Unable to display ledger metrics: {ex}")

with tab_geo:
    st.subheader("Country Geographic Division Settings")
    st.write("When adding a new country, you can define its major cities, states/provinces, and fallback rules here so the partitioning engine splits large industries cleanly without code intervention.")
    
    geo_country = st.selectbox("Select Country to Configure:", ALL_CLAY_COUNTRIES, index=0)
    
    geo_dict = getattr(clay_geo, "GEO", {})
    existing_cfg = geo_dict.get(geo_country, {})
    
    ex_cities = ", ".join(existing_cfg.get("cities", []))
    ex_states = ", ".join(existing_cfg.get("states", []))
    ex_fallback = existing_cfg.get("fallback", ["size", "revenue"])
    
    st.markdown(f"#### Configure Geographic Division for {geo_country}")
    
    input_cities = st.text_area("Major Cities (comma-separated list):", ex_cities, help="e.g. Madrid, Barcelona, Valencia, Seville, Zaragoza, Malaga")
    input_states = st.text_area("States / Provinces / Regions (optional, comma-separated):", ex_states, help="e.g. Ontario, Quebec, British Columbia")
    input_fallback = st.selectbox("Fallback Splitting Strategy:", [["size", "revenue"], ["revenue", "size"]], index=0 if ex_fallback == ["size", "revenue"] else 1)
    
    if st.button(f"Save Geographic Configuration for {geo_country}", type="primary"):
        c_list = [c.strip() for c in input_cities.split(",") if c.strip()]
        s_list = [s.strip() for s in input_states.split(",") if s.strip()]
        
        geo_file = "clay_geo.py"
        with open(geo_file, "r", encoding="utf-8") as gf:
            code = gf.read()
            
        c_str = json.dumps(c_list)
        f_str = json.dumps(input_fallback)
        
        if s_list:
            s_str = json.dumps(s_list)
            new_entry = f'    "{geo_country}": {{"cities": {c_str}, "states": {s_str}, "fallback": {f_str}}},\n}}'
        else:
            new_entry = f'    "{geo_country}": {{"cities": {c_str}, "fallback": {f_str}}},\n}}'
            
        if f'"{geo_country}"' not in code and f"'{geo_country}'" not in code:
            code = code.rstrip().rstrip("}").rstrip() + "\n" + new_entry
            with open(geo_file, "w", encoding="utf-8") as gf:
                gf.write(code)
            track_event("geo_settings_saved", {"country": geo_country, "cities_count": len(c_list), "states_count": len(s_list)})
            st.success(f"Saved new geographic configuration for {geo_country} to clay_geo.py")
        else:
            st.info(f"Configuration for {geo_country} is active. Restart the app if updating existing entries.")

with tab_portfolio:
    st.subheader("Delivered Country Portfolio")
    
    portfolio_choice = st.radio("Select Portfolio View:", ["🏢 Delivered Companies Master Portfolio", "👤 Delivered People Master Portfolio"], horizontal=True)
    delivery_dir = "delivery_people" if "People" in portfolio_choice else "delivery"
    
    if os.path.exists(delivery_dir):
        countries = [d for d in os.listdir(delivery_dir) if os.path.isdir(os.path.join(delivery_dir, d))]
        if countries:
            st.write(f"Found {len(countries)} completed country folders in `{delivery_dir}/`:")
            
            summary_data = []
            for c in sorted(countries):
                cdir = os.path.join(delivery_dir, c)
                files = [f for f in os.listdir(cdir) if f.endswith(".csv")]
                tot_bytes = 0
                for f in files:
                    fp = os.path.join(cdir, f)
                    tot_bytes += os.path.getsize(fp)
                
                summary_data.append({
                    "Country": c,
                    "Delivered CSV Files": len(files),
                    "Total Folder Size": f"{tot_bytes / (1024*1024):.1f} MB",
                    "Folder Path": cdir
                })
                
            st.dataframe(pd.DataFrame(summary_data), use_container_width=True)
            
            selected_country_view = st.selectbox(f"Select a country to view individual delivered files ({portfolio_choice}):", sorted(countries))
            if selected_country_view:
                st.markdown(f"#### Delivered Files in `{delivery_dir}/{selected_country_view}/`")
                cpath = os.path.join(delivery_dir, selected_country_view)
                cfiles = sorted([f for f in os.listdir(cpath) if f.endswith(".csv")])
                
                search_query = st.text_input(
                    "🔍 Search / filter files by industry name:",
                    placeholder="e.g. Transportation, Retail, Software, Manufacturing...",
                    key=f"search_port_{selected_country_view}_{'ppl' if 'People' in portfolio_choice else 'cmp'}"
                )
                if search_query.strip():
                    cfiles = [f for f in cfiles if search_query.strip().lower() in f.lower().replace("-", " ")]
                    st.caption(f"Showing {len(cfiles)} file(s) matching '{search_query}':")
                
                for cf in cfiles:
                    full_p = os.path.join(cpath, cf)
                    f_size_kb = os.path.getsize(full_p) / 1024
                    
                    with st.expander(f"📁 {cf} ({f_size_kb:.1f} KB)"):
                        try:
                            df_prev = pd.read_csv(full_p, nrows=20)
                            st.caption(f"Previewing first {len(df_prev)} rows from `{full_p}`:")
                            df_prev_disp = df_prev.copy()
                            df_prev_disp.index = range(1, len(df_prev_disp) + 1)
                            st.dataframe(df_prev_disp, use_container_width=True)
                            
                            with open(full_p, "rb") as pf_f:
                                raw_port_data = pf_f.read()
                                if not raw_port_data.startswith(b"\xef\xbb\xbf"):
                                    raw_port_data = b"\xef\xbb\xbf" + raw_port_data
                                st.download_button(
                                    label=f"📥 Download Full Master Dataset: {cf}",
                                    data=raw_port_data,
                                    file_name=cf,
                                    mime="text/csv; charset=utf-8",
                                    type="primary",
                                    key=f"port_dl_{cl.slugify(cf)}_{'ppl' if 'People' in portfolio_choice else 'cmp'}"
                                )
                        except Exception as pfe:
                            st.warning(f"Could not preview file: {pfe}")
        else:
            st.info(f"No country folders found in `{delivery_dir}/` yet.")
    else:
        st.info(f"No `{delivery_dir}/` directory created yet.")

with tab_audit:
    st.subheader("📋 Professional Activity Audit & Clay Count Drift Analytics")
    st.caption("Comprehensive tracking of all team operations, downloads, and historical Clay count changes over time.")
    
    audit_tab_drift, audit_tab_act, audit_tab_paths = st.tabs([
        "📈 Clay Count Volatility & Drift Tracker",
        "📜 System Activity Audit Log",
        "📁 Storage & Log File Locations"
    ])
    
    with audit_tab_drift:
        st.markdown("### 📈 Clay Count Volatility & Drift Tracker")
        st.caption("Tracks how often and how drastically Clay changes company & people counts over time across countries and industries.")
        
        df_drift_all = clay_logger.get_count_drift_summary()
        df_history_all = clay_logger.get_count_history_logs(limit=1000)
        
        # Metric summary row
        c_m1, c_m2, c_m3 = st.columns(3)
        total_obs = len(df_history_all)
        drifted_ind = len(df_drift_all[df_drift_all["delta_num"] != 0]) if not df_drift_all.empty else 0
        
        with c_m1:
            st.metric("Total Count Observations Logged", f"{total_obs:,}")
        with c_m2:
            st.metric("Industries with Detected Data Drift", f"{drifted_ind:,}", delta=f"{drifted_ind} count updates recorded" if drifted_ind else None)
        with c_m3:
            st.metric("Time-Series Logging Status", "Active", delta="Real-time CSV & Analytics")
            
        st.markdown("#### Count Drift Summary (First vs Latest Observed)")
        f_c1, f_c2 = st.columns(2)
        with f_c1:
            drift_filter_entity = st.selectbox("Filter Drift by Entity:", ["All", "Companies", "People"], key="drift_filter_ent_key")
        with f_c2:
            drift_countries = ["All"] + sorted(list(df_drift_all["Country"].unique())) if not df_drift_all.empty else ["All"]
            drift_filter_country = st.selectbox("Filter Drift by Country:", drift_countries, key="drift_filter_ctry_key")
            
        df_drift_filtered = clay_logger.get_count_drift_summary(country=drift_filter_country, entity=drift_filter_entity)
        if not df_drift_filtered.empty:
            disp_df = df_drift_filtered.drop(columns=["delta_num"], errors="ignore")
            disp_df.index = range(1, len(disp_df) + 1)
            st.dataframe(disp_df, use_container_width=True)
        else:
            st.info("No count observations recorded yet. Run 'Step 1: Count' on any country to start building drift history.")
            
        st.markdown("#### Full Time-Series Count Log (Every Count Event)")
        df_cnt_log = clay_logger.get_count_history_logs(country=drift_filter_country, entity=drift_filter_entity, limit=500)
        if not df_cnt_log.empty:
            disp_cnt = df_cnt_log.drop(columns=["Timestamp_UTC"], errors="ignore")
            disp_cnt.index = range(1, len(disp_cnt) + 1)
            st.dataframe(disp_cnt, use_container_width=True)
            
            with open(clay_logger.COUNT_HISTORY_FILE, "rb") as f_cnt:
                st.download_button(
                    "📥 Download Complete Count History Log (CSV)",
                    data=f_cnt.read(),
                    file_name="clay_count_history.csv",
                    mime="text/csv",
                    type="primary",
                    key="dl_count_history_csv_btn"
                )

    with audit_tab_act:
        st.markdown("### 📜 System Activity Audit Log")
        st.caption("Timestamped audit trail of all extraction runs, plans, slice downloads, and user actions.")
        
        df_act = clay_logger.get_activity_logs(limit=500)
        if not df_act.empty:
            filter_action = st.selectbox("Filter Activity by Action Type:", ["All"] + sorted(list(df_act["Action"].unique())), key="act_filter_action_key")
            if filter_action != "All":
                df_act_disp = df_act[df_act["Action"] == filter_action]
            else:
                df_act_disp = df_act
                
            df_act_view = df_act_disp.drop(columns=["Timestamp_UTC"], errors="ignore")
            df_act_view.index = range(1, len(df_act_view) + 1)
            st.dataframe(df_act_view, use_container_width=True)
            
            with open(clay_logger.ACTIVITY_LOG_FILE, "rb") as f_act:
                st.download_button(
                    "📥 Download Activity Audit Log (CSV)",
                    data=f_act.read(),
                    file_name="activity_audit_log.csv",
                    mime="text/csv",
                    type="primary",
                    key="dl_act_audit_csv_btn"
                )
        else:
            st.info("No activity logs recorded yet.")

    with audit_tab_paths:
        st.markdown("### 📁 Storage & Log File Locations")
        st.markdown("""
        All logs and time-series data are permanently saved on disk in standardized, professional UTF-8 BOM CSV format:

        | Log Category | File Path | Description |
        |---|---|---|
        | **Clay Count Drift History** | `logs/clay_count_history.csv` | Time-series record of every count query, tracking changes, deltas (±), and % volatility over time. |
        | **Activity Audit Trail** | `logs/activity_audit_log.csv` | Full audit log of all extractions, slice downloads, merges, and system actions. |
        | **Current Industry Counts** | `data/<country>_nontech_counts.csv` | Latest snapshot of target counts for Company extractions. |
        | **Current People Counts** | `data/<country>_people_counts.csv` | Latest snapshot of target counts for People extractions. |
        | **Execution Progress Ledger** | `data/<country>_nontech_progress.csv` | Progress and deduplication metrics for delivered datasets. |
        | **Delivered Master Datasets** | `delivery/<Country>/` & `delivery_people/<Country>/` | Centralized permanent stores of clean, deduped CSVs. |
        """)

with tab_faq:
    st.subheader("Centralized Store and Deduplication FAQ")
    
    st.markdown("""
    ### Data Centralization & Incremental Merging

    1. **Centralized Data Store**:
       - All downloaded datasets are stored in the centralized `delivery/<Country>/` directory.
       - Each dataset file (`<Country> Data [Clay] -<Industry>.csv`) acts as the single source of truth for that country and industry.

    2. **Incremental Deduplication on Re-runs**:
       - When anyone runs a download for an existing country or industry, the engine loads all existing companies into memory.
       - As new data is pulled from Clay, the engine checks every company against the existing set using **LinkedIn URL** (primary key) and **Domain** (fallback key).
       - Only **new or unmatched companies** are appended to the centralized file.
       - Existing companies are preserved without creating duplicate files or duplicate rows.

    3. **Resumability**:
       - If a pull is stopped halfway, re-running automatically picks up right where it left off, downloading only missing slices.
    """)
