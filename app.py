import csv
import glob
import json
import os
import re
import shutil
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

import zipfile
import io

SHORT_COUNTRY_DELIVERY = {"United States": "USA", "United Arab Emirates": "UAE", "United Kingdom": "UK"}

def get_industry_category(industry_or_filename):
    try:
        from clay_taxonomy import TECH_INDUSTRIES
        name_str = str(industry_or_filename).strip()
        if " [Clay] -" in name_str:
            name_str = name_str.split(" [Clay] -")[-1].replace(".csv", "").replace(" (People)", "")
        clean_slug = cl.slugify(name_str)
        tech_slugs = {cl.slugify(i) for i in TECH_INDUSTRIES}
        if clean_slug in tech_slugs:
            return "Tech"
        for ti in TECH_INDUSTRIES:
            if cl.slugify(ti) == clean_slug or ti.lower() == name_str.lower():
                return "Tech"
        return "Non-Tech"
    except Exception:
        return "Non-Tech"

def get_delivery_path(country, industry, is_people=False):
    label = SHORT_COUNTRY_DELIVERY.get(country, country)
    base_dir = "delivery_people" if is_people else "delivery"
    cat = get_industry_category(industry)
    if is_people:
        fn = f"{label} People [Clay] -{cl.slugify(industry)}.csv"
    else:
        clean_ind = re.sub(r'[^A-Za-z0-9]+', '-', industry).strip('-')
        fn = f"{label} Data [Clay] -{clean_ind}.csv"
    new_p = os.path.join(base_dir, label, cat, fn)
    old_p = os.path.join(base_dir, label, fn)
    if not os.path.exists(new_p) and os.path.exists(old_p):
        try:
            os.makedirs(os.path.dirname(new_p), exist_ok=True)
            shutil.move(old_p, new_p)
        except Exception:
            return old_p
    return new_p

def create_country_zip(country_dir, category_filter=None):
    """Creates an in-memory ZIP archive of files in country_dir.
    category_filter: None (all), 'Tech', or 'Non-Tech'.
    When a category_filter is specified (e.g. 'Tech' or 'Non-Tech'), the files
    are placed directly at the root of the ZIP archive so extraction is flat
    and does not produce an unnecessary redundant nested folder.
    When category_filter is None (Entire Portfolio), Tech/ and Non-Tech/ subfolders
    are preserved so categories remain neatly grouped upon extraction."""
    buf = io.BytesIO()
    file_count = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(country_dir):
            for file in files:
                if not file.endswith(".csv"):
                    continue
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, country_dir)
                norm_rel = rel_path.replace("\\", "/")
                if category_filter:
                    if not (norm_rel.startswith(f"{category_filter}/") or norm_rel == category_filter):
                        continue
                    cat_dir = os.path.join(country_dir, category_filter)
                    arcname = os.path.relpath(full_path, cat_dir)
                else:
                    arcname = rel_path
                zf.write(full_path, arcname=arcname)
                file_count += 1
    buf.seek(0)
    return buf.getvalue(), file_count

def record_ledger_row(ledger_path, row_data, is_people=False):
    if not ledger_path:
        return
    rows = {}
    col_uniq = "unique_people" if is_people else "unique_companies"
    header = ["industry", "clay_count", "rows_downloaded", col_uniq, "coverage_pct", "existing_in_file", "new_added", "file"]
    if os.path.exists(ledger_path):
        try:
            with open(ledger_path, "r", encoding="utf-8-sig", errors="replace") as f:
                r = csv.reader(f)
                h = next(r, None)
                for line in r:
                    if line and len(line) >= 1 and line[0].strip():
                        rows[line[0].strip()] = line
        except Exception:
            pass
    rows[str(row_data[0]).strip()] = [str(x) for x in row_data]
    os.makedirs(os.path.dirname(ledger_path) or ".", exist_ok=True)
    with open(ledger_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        for k, v in rows.items():
            w.writerow(v)

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
        ind_val = props.get("industries", props.get("industry", None))
        clay_logger.log_activity(
            action=event_name,
            entity=props.get("entity", "Companies"),
            country=props.get("country", ""),
            industries=ind_val,
            total_rows=props.get("total_rows", props.get("total_people", props.get("total_unique", 0))),
            status=props.get("status", "SUCCESS"),
            details=props.get("details", ""),
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
    {f"posthog.identify('{st.session_state.get('user_id')}', {{ username: '{st.session_state.get('user_id')}' }});" if st.session_state.get('user_id') else ""}

    // Background Keep-Alive Worker to prevent browser from freezing the tab or closing WebSockets
    try {{
        var workerCode = "setInterval(function() {{ postMessage('keepalive'); }}, 1500);";
        var workerBlob = new Blob([workerCode], {{ type: 'application/javascript' }});
        var bgWorker = new Worker(URL.createObjectURL(workerBlob));
        bgWorker.onmessage = function() {{}};
    }} catch(e) {{}}

    // Request WakeLock to prevent OS/browser sleep during active runs
    if ('wakeLock' in navigator) {{
        try {{
            navigator.wakeLock.request('screen').catch(function() {{}});
        }} catch(e) {{}}
    }}
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

# ----------------------------------------------------------------------
# Lucide icons (lucide.dev, ISC). Stroke paths on a 24x24 grid.
#   ic()    -> inline SVG for markup we control (headers, stepper, chips)
#   _mask() -> data URI used as a CSS mask so Streamlit widget labels, which
#              escape HTML, can still carry a real icon instead of an emoji.
# ----------------------------------------------------------------------
import urllib.parse

LUCIDE = {
    "check":        '<path d="M20 6 9 17l-5-5"/>',
    "sun":          '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32 1.41 1.41M2 12h2m16 0h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>',
    "moon":         '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>',
    "user":         '<circle cx="12" cy="8" r="5"/><path d="M20 21a8 8 0 0 0-16 0"/>',
    "circle-check": '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
    "circle-alert": '<circle cx="12" cy="12" r="10"/><path d="M12 8v4m0 4h.01"/>',
    "refresh":      '<path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M21 21v-5h-5"/>',
    "stop":         '<circle cx="12" cy="12" r="10"/><rect x="9" y="9" width="6" height="6" rx="1"/>',
    "log-out":      '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/>',
    "pencil":       '<path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497Z"/>',
    "eye":          '<path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>',
    "building":     '<path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z"/><path d="M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2"/><path d="M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2"/><path d="M10 6h4M10 10h4M10 14h4M10 18h4"/>',
    "users":        '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "globe":        '<circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/>',
    "layers":       '<path d="M12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/><path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/>',
    "package":      '<path d="m7.5 4.27 9 5.15"/><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/>',
    "download":     '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/>',
    "file-text":    '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8m8 4H8m8 4H8"/>',
    "code":         '<polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>',
    "layout-grid":  '<rect width="7" height="7" x="3" y="3" rx="1"/><rect width="7" height="7" x="14" y="3" rx="1"/><rect width="7" height="7" x="14" y="14" rx="1"/><rect width="7" height="7" x="3" y="14" rx="1"/>',
    "x":            '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
    "scan-search":  '<path d="M3 7V5a2 2 0 0 1 2-2h2m10 0h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"/><circle cx="12" cy="12" r="3"/><path d="m16 16-1.9-1.9"/>',
}


def ic(name, size=16, extra=""):
    """Inline Lucide SVG for markup we render ourselves."""
    return (
        f'<svg class="lu {extra}" width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round" aria-hidden="true">{LUCIDE[name]}</svg>'
    )


def _mask(name):
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="black" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        + LUCIDE[name] + "</svg>"
    )
    return "data:image/svg+xml," + urllib.parse.quote(svg)


def preset_css():
    """Highlight the industry preset that matches the CURRENT selection.

    Derived from `selected_industries` itself rather than a stored "active
    preset" flag, so it can never disagree with what is actually selected and
    it survives Edit, Continue and page refresh along with the selection.
    Editing the chips by hand makes it a custom selection, so the highlight
    clears. The active button also swaps its icon for a check, so the state
    is not conveyed by colour alone.
    """
    sel = set(st.session_state.get("selected_industries") or [])
    active = None
    if sel:
        for key, group in (("preset_tech", TECH_INDUSTRIES),
                           ("preset_nontech", NON_TECH_INDUSTRIES),
                           ("preset_all", ALL_CLAY_INDUSTRIES)):
            if sel == set(group):
                active = key
                break

    icons = {"preset_tech": "code", "preset_nontech": "building",
             "preset_all": "layout-grid", "preset_clear": "x"}
    if active:
        icons[active] = "check"
    css = icon_button_css(icons)

    if active:
        if st.session_state.get("theme_mode") == "light":
            bg, bd, fg = "#eff6ff", "#2563eb", "#1d4ed8"
        else:
            bg, bd, fg = "rgba(59,130,246,0.16)", "#3b82f6", "#bfdbfe"
        css += (
            "<style>"
            f"div.st-key-{active} button, div.st-key-{active} button:hover {{"
            f" background-color:{bg} !important; border:1px solid {bd} !important;"
            f" color:{fg} !important; font-weight:600 !important; }}"
            f"div.st-key-{active} button * {{ color:{fg} !important; }}"
            "</style>"
        )
    return css


def icon_button_css(mapping):
    """CSS that prefixes keyed Streamlit buttons with a Lucide glyph."""
    rules = []
    for key, name in mapping.items():
        rules.append(
            f'.st-key-{key} button::before {{'
            f' content:""; display:inline-block; width:16px; height:16px;'
            f' margin-right:8px; flex:0 0 16px; background-color:currentColor;'
            f' -webkit-mask:url("{_mask(name)}") no-repeat center / contain;'
            f' mask:url("{_mask(name)}") no-repeat center / contain; }}'
        )
    return "<style>" + "".join(rules) + "</style>"


# ----------------------------------------------------------------------
# Guided Workflow Styling (stage stepper, step cards, coverage metrics)
# Layout/emphasis only -- colours follow the active Streamlit theme.
# ----------------------------------------------------------------------
st.markdown("""
    <style>
    /* ---- job summary chip ---- */
    .wf-job {
        display: inline-flex; align-items: center; gap: 10px;
        padding: 7px 16px; border-radius: 999px;
        border: 1px solid rgba(128,145,175,0.35);
        font-size: 13px; font-weight: 600;
        margin: 2px 0 18px 0;
    }
    .wf-job .sep { opacity: 0.35; font-weight: 400; }
    .wf-job .muted { opacity: 0.7; font-weight: 500; }

    /* ---- five stage stepper ---- */
    .wf-steps { display: flex; align-items: flex-start; gap: 0; margin: 4px 0 22px 0; }
    .wf-stage { display: flex; flex-direction: column; align-items: center; flex: 0 0 auto; min-width: 92px; }
    .wf-dot {
        width: 30px; height: 30px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 13px; font-weight: 700; line-height: 1;
        border: 1.5px solid rgba(128,145,175,0.45);
        color: inherit; opacity: .55; background: transparent;
    }
    .wf-dot.done, .wf-dot.active { opacity: 1; }
    .wf-dot.done   { background: #16a34a; border-color: #16a34a; color: #ffffff; }
    .wf-dot.active { background: #2563eb; border-color: #2563eb; color: #ffffff;
                     box-shadow: 0 0 0 4px rgba(37,99,235,0.18); }
    .wf-label { font-size: 11.5px; margin-top: 7px; text-align: center; color: inherit; opacity: .5; font-weight: 600; }
    .wf-label.on { opacity: 1; }
    .wf-line { flex: 1 1 auto; height: 1.5px; background: rgba(128,145,175,0.3); margin-top: 15px; min-width: 18px; }
    .wf-line.done { background: #16a34a; }

    /* ---- step card header ---- */
    .wf-head { display: flex; align-items: center; gap: 10px; }
    .wf-num {
        width: 26px; height: 26px; border-radius: 50%; flex: 0 0 26px;
        display: flex; align-items: center; justify-content: center;
        font-size: 12px; font-weight: 700;
        border: 1.5px solid rgba(128,145,175,0.45); color: inherit; opacity: .55;
    }
    .wf-num.done, .wf-num.active { opacity: 1; }
    .wf-num.done   { background: #16a34a; border-color: #16a34a; color: #fff; }
    .wf-num.active { background: #2563eb; border-color: #2563eb; color: #fff; }
    .wf-title { font-size: 16px; font-weight: 700; }
    .wf-title.muted { opacity: 0.62; font-weight: 600; }
    .wf-sub { font-size: 12.5px; opacity: 0.72; margin: 4px 0 0 36px; }

    /* ---- coverage metrics ---- */
    .wf-metrics { display: flex; flex-wrap: wrap; gap: 12px; margin: 6px 0 14px 0; }
    .wf-metric {
        flex: 1 1 170px; padding: 14px 16px; border-radius: 10px;
        border: 1px solid rgba(128,145,175,0.28);
    }
    .wf-metric .v { font-size: 25px; font-weight: 700; line-height: 1.15; font-variant-numeric: tabular-nums; }
    .wf-metric .l { font-size: 11px; font-weight: 700; letter-spacing: .05em;
                    text-transform: uppercase; opacity: 0.62; margin-top: 4px; }
    .wf-metric .v.ok   { color: #16a34a; }
    .wf-metric .v.warn { color: #d97706; }
    .wf-metric .v.info { color: #2563eb; }

    /* ---- coverage bar ---- */
    .wf-bar-wrap { display: flex; align-items: center; gap: 12px; margin: 2px 0 14px 0; }
    .wf-bar { flex: 1 1 auto; height: 9px; border-radius: 999px;
              background: rgba(128,145,175,0.25); overflow: hidden; }
    .wf-bar > span { display: block; height: 100%; border-radius: 999px; background: #16a34a; }
    .wf-bar > span.warn { background: #d97706; }
    .wf-bar-pct { font-size: 13px; font-weight: 700; font-variant-numeric: tabular-nums; min-width: 52px; text-align: right; }

    /* ---- header controls: one aligned row of equal-height buttons ---- */
    [data-testid="stPopoverButton"], .stButton > button { min-height: 40px; }

    /* ---- lucide glyphs ---- */
    .lu { flex: 0 0 auto; vertical-align: -0.15em; }
    .wf-job .lu { opacity: .7; }
    .wf-dot .lu, .wf-num .lu { stroke-width: 3; }

    /* ---- compact brand ---- */
    .wf-brand { font-size: 25px; font-weight: 800; letter-spacing: -0.02em; line-height: 1.15; }
    .wf-brand-sub { font-size: 12.5px; opacity: 0.62; margin-top: 3px; line-height: 1.35; }

    /* ---- selected-industry chips ---- */
    .wf-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
    .wf-chips span {
        font-size: 12px; padding: 3px 10px; border-radius: 999px;
        border: 1px solid rgba(128,145,175,0.35); opacity: 0.9;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------------
# Light-mode widget overrides.
#
# Streamlit 1.61 renders inputs with react-aria, not BaseWeb, so every
# `div[data-baseweb="select"]` rule in the theme block above is dead on this
# version -- which is why selects, dropdowns and radios stayed dark (and their
# text invisible) in light mode. These rules target the stable data-testid
# hooks plus the react-aria class names instead.
# ----------------------------------------------------------------------
if st.session_state.get("theme_mode") == "light":
    st.markdown("""
        <style>
        /* popover + account triggers (not inside .stButton) */
        button[data-testid="stPopoverButton"] {
            background-color: #ffffff !important;
            color: #0f172a !important;
            border: 1px solid #cbd5e1 !important;
        }
        button[data-testid="stPopoverButton"] * { color: #0f172a !important; }
        button[data-testid="stPopoverButton"]:hover {
            background-color: #f1f5f9 !important;
            border-color: #94a3b8 !important;
        }

        /* widget labels + help text */
        [data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] * ,
        [data-testid="stMarkdownContainer"] p { color: #0f172a !important; }
        [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * { color: #475569 !important; }

        /* selectbox / combobox control */
        [data-testid="stSelectbox"] .react-aria-ComboBox > div,
        [data-testid="stMultiSelect"] .react-aria-ComboBox > div,
        [data-testid="stTextInputRootElement"],
        [data-testid="stTextAreaRootElement"] {
            background-color: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
        }
        [data-testid="stSelectbox"] input,
        [data-testid="stMultiSelect"] input,
        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea,
        [data-testid="stSelectbox"] button,
        [data-testid="stMultiSelect"] button {
            background-color: transparent !important;
            color: #0f172a !important;
        }
        [data-testid="stSelectbox"] input::placeholder,
        [data-testid="stTextInput"] input::placeholder,
        [data-testid="stTextArea"] textarea::placeholder { color: #94a3b8 !important; }
        [data-testid="stSelectbox"] svg,
        [data-testid="stMultiSelect"] svg { fill: #475569 !important; color: #475569 !important; }

        /* dropdown panel + options (portal-rendered, virtualized).
           The panel is [data-testid$="VirtualDropdown"] with no role, which is
           what left country/industry options as white-on-white in light mode. */
        [data-testid$="VirtualDropdown"],
        [data-testid$="VirtualDropdown"] [role="listbox"] {
            background-color: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            box-shadow: 0 8px 24px rgba(15,23,42,0.12) !important;
        }
        [data-testid$="VirtualDropdown"], [data-testid$="VirtualDropdown"] * { color: #0f172a !important; }
        [data-testid$="VirtualDropdown"] [role="option"]:hover,
        [data-testid$="VirtualDropdown"] [role="option"][data-focused],
        [data-testid$="VirtualDropdown"] [role="option"][aria-selected="true"] {
            background-color: #eef2f7 !important;
        }

        .react-aria-Popover, .react-aria-ListBox, [role="listbox"] {
            background-color: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            box-shadow: 0 8px 24px rgba(15,23,42,0.12) !important;
        }
        .react-aria-Option, [role="option"], .react-aria-Option *, [role="option"] * {
            background-color: transparent !important;
            color: #0f172a !important;
        }
        .react-aria-Option[data-focused], .react-aria-Option:hover,
        [role="option"][aria-selected="true"], [role="option"]:hover {
            background-color: #eef2f7 !important;
        }

        /* multiselect chips */
        [data-testid="stMultiSelectTagsContainer"] span,
        [data-testid="stMultiSelectTagsContainer"] div {
            background-color: #e2e8f0 !important;
            color: #0f172a !important;
        }

        /* radio + checkbox text */
        [data-testid="stRadioOption"], [data-testid="stRadioOption"] *,
        [data-testid="stCheckbox"], [data-testid="stCheckbox"] * { color: #0f172a !important; }

        /* expanders (technical details, per-industry rows, delivered files) */
        [data-testid="stExpander"] details,
        [data-testid="stExpander"] summary,
        [data-testid="stExpanderDetails"] {
            background-color: #ffffff !important;
            color: #0f172a !important;
            border-color: #e2e8f0 !important;
        }
        [data-testid="stExpander"] summary * { color: #0f172a !important; }

        /* popover panel body */
        [data-testid="stPopover"] [data-testid="stVerticalBlock"] { color: #0f172a !important; }

        /* bordered workflow cards */
        [data-testid="stVerticalBlockBorderWrapper"] { border-color: #e2e8f0 !important; }
        </style>
    """, unsafe_allow_html=True)


# Multi-User Authentication via clay_users
import clay_users

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# Persistent Session Restore via Query Params
if st.query_params.get("auth") == "1" and st.query_params.get("uid"):
    st.session_state["authenticated"] = True
    st.session_state["user_id"] = st.query_params.get("uid")

def login_screen():
    st.markdown("### Clay Data Platform - Team Access")
    st.caption("Sign in to your team workspace or register your account to start data extraction.")
    
    col_login, _ = st.columns([1.2, 1.8])
    with col_login:
        tab_signin, tab_signup = st.tabs(["🔑 Log In", "✨ Sign Up / Register"])
        
        with tab_signin:
            user_id = st.text_input("Username", key="login_user_input")
            password = st.text_input("Password", type="password", key="login_pw_input")
            if st.button("Log In", type="primary", use_container_width=True):
                if clay_users.authenticate_user(user_id, password):
                    st.session_state["authenticated"] = True
                    st.session_state["user_id"] = user_id.strip().lower()
                    st.query_params["auth"] = "1"
                    st.query_params["uid"] = user_id.strip().lower()
                    st.cache_data.clear()
                    track_event("user_login", {"user_id": user_id.strip().lower()})
                    st.rerun()
                else:
                    st.error("Invalid Username or Password.")
            st.caption("ℹ️ Teammates can sign in directly using their username with password `clay2026`.")
                    
        with tab_signup:
            new_user = st.text_input("Choose Username", key="signup_user_input")
            new_pw = st.text_input("Choose Password", type="password", key="signup_pw_input")
            if st.button("Create Account & Sign In", type="primary", use_container_width=True):
                ok, msg = clay_users.register_user(new_user, new_pw)
                if ok:
                    st.session_state["authenticated"] = True
                    st.session_state["user_id"] = new_user.strip().lower()
                    st.query_params["auth"] = "1"
                    st.query_params["uid"] = new_user.strip().lower()
                    st.cache_data.clear()
                    track_event("user_registered", {"user_id": new_user.strip().lower()})
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

if not st.session_state.get("authenticated") or not st.session_state.get("user_id"):
    login_screen()
    st.stop()

current_user = st.session_state["user_id"].strip().lower()

def is_ignorable_warning(line_str):
    if not line_str:
        return False
    lower = str(line_str).lower()
    if "scriptruncontext" in lower:
        return True
    if "session_state_proxy" in lower or "session state does not function" in lower:
        return True
    if "warning streamlit" in lower or "streamlit.runtime" in lower:
        return True
    return False

def make_env():
    env = os.environ.copy()
    env["CLAY_USER_ID"] = current_user
    env["PYTHONWARNINGS"] = "ignore"
    env["STREAMLIT_LOG_LEVEL"] = "error"
    active_c_env = clay_users.get_user_cookie(current_user)
    if active_c_env:
        env["CLAY_COOKIE"] = active_c_env
    return env

# Application Header (Brand, Clay status + setup, Theme, Account menu)
# Every control from the previous nav bar is preserved; low-frequency
# actions (Auto-Refresh, Paste, Stop Process, Logout) now live behind the
# status pill and the account menu instead of competing with the workflow.
@st.cache_data(ttl=60, show_spinner=False)
def check_cookie_cached(cookie_token, username):
    from auto_cookie_fetcher import verify_cookie
    return verify_cookie(cookie_token, username=username)

active_c = clay_users.get_user_cookie(current_user)
is_cookie_valid = False
if active_c:
    try:
        is_cookie_valid = check_cookie_cached(active_c, current_user)
    except Exception:
        is_cookie_valid = False

st.markdown(
    icon_button_css({
        "clay_session_pop": "circle-check" if is_cookie_valid else "circle-alert",
        "theme_toggle_btn": "sun" if st.session_state["theme_mode"] == "dark" else "moon",
        "account_pop": "user",
        "btn_auto_refresh": "refresh",
        "btn_stop_process": "stop",
        "btn_logout": "log-out",
        "stop_step1_btn": "stop",
        "stop_step2_btn": "stop",
        "stop_step3_btn": "stop",
        "wf_edit_1": "pencil",
        "wf_edit_2": "pencil",
        "wf_edit_3": "eye",
    }),
    unsafe_allow_html=True,
)

hdr_brand, hdr_status, hdr_theme, hdr_acct = st.columns([4.2, 1.9, 1.3, 1.1])

with hdr_brand:
    st.markdown(
        "<div class='wf-brand'>Clay Data Platform</div>"
        "<div class='wf-brand-sub'>Centralized Company Data Extraction, Deduplication and Portfolio Engine</div>",
        unsafe_allow_html=True,
    )

with hdr_status:
    st.write("")
    _clay_label = "Clay connected" if is_cookie_valid else "Clay setup required"
    _clay_wrap = st.container(key="clay_session_pop")
    with _clay_wrap, st.popover(_clay_label, use_container_width=True):
        st.markdown(f"**Clay session for `{current_user}`**")
        if is_cookie_valid:
            st.success("Cookie active and verified.")
        else:
            st.warning("No active Clay cookie. Counting and downloading will fail until this is set up.")

        if st.button("Auto-Refresh", key="btn_auto_refresh", use_container_width=True, help=f"Launches browser for '{current_user}' profile"):
            track_event("cookie_refresh_started", {"user_id": current_user})
            with st.spinner(f"Opening browser for '{current_user}'... (If prompted, log into Clay in the browser window)"):
                try:
                    from auto_cookie_fetcher import fetch_cookie
                    new_c = fetch_cookie(username=current_user, timeout_seconds=90)
                    if new_c:
                        st.cache_data.clear()
                        st.success("Cookie verified & saved!")
                        track_event("cookie_refresh_completed", {"success": True})
                        st.rerun()
                    else:
                        st.warning("Auto-capture timed out. Tip: paste your cookie below instead.")
                        track_event("cookie_refresh_completed", {"success": False})
                except Exception as e:
                    st.error(f"Auto-refresh error: {e}")

        st.caption("Or paste your `claysession=...` cookie header from your normal browser:")
        manual_cookie = st.text_area("Cookie Header:", value=active_c or "", placeholder="claysession=...", height=100)
        if st.button("Save & Verify Cookie", type="primary", use_container_width=True):
            if manual_cookie.strip():
                from auto_cookie_fetcher import verify_cookie, seed_browser_cookies
                is_valid = verify_cookie(manual_cookie.strip(), username=current_user)
                clay_users.save_user_cookie(current_user, manual_cookie.strip())
                seed_browser_cookies(current_user, manual_cookie.strip())
                st.cache_data.clear()
                if is_valid:
                    st.success(f"Cookie verified, profile seeded & saved for '{current_user}'!")
                    st.rerun()
                else:
                    st.warning("Cookie saved, but verification returned inactive. Please ensure it contains a valid claysession token.")
                    st.rerun()

def _toggle_theme():
    new_theme = "light" if st.session_state["theme_mode"] == "dark" else "dark"
    st.session_state["theme_mode"] = new_theme
    track_event("theme_toggled", {"theme": new_theme})

with hdr_theme:
    st.write("")
    theme_btn_label = "Light Mode" if st.session_state["theme_mode"] == "dark" else "Dark Mode"
    st.button(theme_btn_label, use_container_width=True, key="theme_toggle_btn", on_click=_toggle_theme)

with hdr_acct:
    st.write("")
    _acct_wrap = st.container(key="account_pop")
    with _acct_wrap, st.popover(current_user, use_container_width=True):
        st.markdown(f"**Signed in as `{current_user}`**")
        st.caption("Stop Process halts whichever count, plan or download is currently running.")
        if st.button("Stop Process", key="btn_stop_process", type="secondary", use_container_width=True):
            proc = st.session_state.get("current_process")
            if proc and proc.poll() is None:
                proc.terminate()
                st.session_state["current_process"] = None
                track_event("process_stopped", {"location": "navbar"})
                st.warning("Active process stopped by user.")
            else:
                st.info("No active process running.")
        if st.button("Logout", key="btn_logout", type="secondary", use_container_width=True):
            st.session_state["authenticated"] = False
            st.session_state.pop("user_id", None)
            st.session_state.pop("current_process", None)
            st.query_params.clear()
            st.cache_data.clear()
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
            {ic("circle-check", 16)}
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
                    <strong style="font-size: 15px;">{live_status.get('title', 'Operation Active')}</strong>
                    <div style="font-size: 13px; opacity: 0.92; margin-top: 2px;">{live_status.get('text', 'In progress...')}</div>
                </div>
            </div>
            <div style="font-size: 18px; font-weight: bold; background: rgba(255,255,255,0.18); padding: 4px 12px; border-radius: 6px;">{int(pct_val * 100)}%</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.progress(pct_val)

tab_download, tab_geo, tab_portfolio, tab_faq = st.tabs([
    "Run Data Extraction",
    "Country Division Settings",
    "Delivered Portfolio",
    "Centralized Store & Deduplication FAQ"
])

with tab_download:
    # ==================================================================
    # GUIDED EXTRACTION WORKFLOW
    #   Setup -> Industries -> Coverage -> Review -> Download
    #
    # The active stage is DERIVED from real state (widget values plus the
    # count / plan / ledger files on disk). `wf_open` is a purely visual
    # override recording which card the operator re-opened via Edit -- it
    # never drives execution, so it cannot drift from backend state.
    #
    # Every step's inputs are always rendered (so Streamlit keeps their
    # widget state); collapsed steps are hidden with CSS rather than
    # skipped, which is what keeps selections alive across reruns.
    # ==================================================================
    ph_job = st.empty()
    ph_steps = st.empty()

    if "wf_open" not in st.session_state:
        st.session_state["wf_open"] = 0  # 0 = follow the derived stage

    def wf_head(num, title, state, summary=""):
        cls = "done" if state == "done" else ("active" if state == "active" else "")
        tmuted = "" if state != "todo" else " muted"
        mark = ic("check", 15) if state == "done" else str(num)
        html = (
            f"<div class='wf-head'><div class='wf-num {cls}'>{mark}</div>"
            f"<div class='wf-title{tmuted}'>{title}</div></div>"
        )
        if summary:
            html += f"<div class='wf-sub'>{summary}</div>"
        st.markdown(html, unsafe_allow_html=True)

    def wf_hide(container_key):
        st.markdown(
            f"<style>.st-key-{container_key} {{ display: none !important; }}</style>",
            unsafe_allow_html=True,
        )

    def wf_edit_button(step_num, label="Edit", key=None):
        if st.button(label, key=key or f"wf_edit_{step_num}", use_container_width=True):
            st.session_state["wf_open"] = step_num
            st.rerun()

    if "_init_mode_loaded" not in st.session_state:
        st.session_state["_init_mode_loaded"] = True
        qp_mode = st.query_params.get("mode", "companies")
        st.session_state["search_mode_idx"] = 1 if qp_mode == "people" else 0

    def on_mode_change():
        m_val = st.session_state.get("search_mode_widget")
        st.session_state["search_mode_idx"] = 1 if "People" in str(m_val) else 0
        st.query_params["mode"] = "people" if "People" in str(m_val) else "companies"

    country_options = ["-- Select Target Country --", "\U0001F30D All Supported Countries (Global)"] + ALL_CLAY_COUNTRIES

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
            if chosen == "\U0001F30D All Supported Countries (Global)":
                st.query_params["c"] = "Global"
            elif chosen != "-- Select Target Country --":
                st.query_params["c"] = chosen
            elif "c" in st.query_params:
                del st.query_params["c"]

    if "_init_ind_loaded" not in st.session_state:
        st.session_state["_init_ind_loaded"] = True
        qp_preset = st.query_params.get("preset", "")
        qp_ind = st.query_params.get("ind", "")
        if qp_preset == "tech":
            st.session_state["selected_industries"] = list(TECH_INDUSTRIES)
        elif qp_preset == "nontech":
            st.session_state["selected_industries"] = list(NON_TECH_INDUSTRIES)
        elif qp_preset == "all":
            st.session_state["selected_industries"] = list(ALL_CLAY_INDUSTRIES)
        elif qp_ind:
            parsed_inds = [x.strip() for x in qp_ind.split("|") if x.strip() and x.strip() in ALL_CLAY_INDUSTRIES]
            st.session_state["selected_industries"] = parsed_inds
            if len(parsed_inds) > 3 and "ind" in st.query_params:
                del st.query_params["ind"]
        else:
            st.session_state["selected_industries"] = []
    elif "selected_industries" not in st.session_state:
        st.session_state["selected_industries"] = []

    # A nav button (Edit / Continue) calls st.rerun(), which aborts the run
    # before step 2's multiselect re-renders -- and Streamlit discards widget
    # state for widgets that did not render. `sel_country_idx` already shields
    # the country selectbox the same way; mirror the industry selection into a
    # plain key so Edit cannot silently clear it.
    if not st.session_state.get("selected_industries") and st.session_state.get("wf_inds_backup"):
        st.session_state["selected_industries"] = list(st.session_state["wf_inds_backup"])

    # ---- Current selections, read before any step card renders so the
    # ---- collapsed/expanded decision is correct on a fresh page load too.
    # ---- Widget keys only exist once a widget has rendered, so fall back to
    # ---- the index/state the query-param restore above just populated.
    if "search_mode_widget" in st.session_state:
        _prov_people = "People" in str(st.session_state["search_mode_widget"])
    else:
        _prov_people = st.session_state.get("search_mode_idx", 0) == 1

    if "country_select_widget" in st.session_state:
        _prov_raw_c = st.session_state["country_select_widget"]
    else:
        _ci = st.session_state.get("sel_country_idx", 0)
        _prov_raw_c = country_options[_ci] if 0 <= _ci < len(country_options) else ""

    if st.session_state.get("wf_custom_country", False):
        _prov_country = str(st.session_state.get("wf_manual_country", "")).strip()
    elif _prov_raw_c == "All Supported Countries (Global)":
        _prov_country = "Global"
    elif _prov_raw_c and _prov_raw_c != "-- Select Target Country --":
        _prov_country = str(_prov_raw_c).strip()
    else:
        _prov_country = ""

    _prov_inds = st.session_state.get("selected_industries", []) or []

    forced = st.session_state.get("wf_open", 0)

    # ==================================================================
    # STEP 1 -- SETUP: what to download, and where
    # ==================================================================

    step1_open = (forced == 1) or (not forced and not _prov_country)
    step1_state = "active" if step1_open else ("done" if _prov_country else "todo")

    with st.container(border=True):
        h1a, h1b = st.columns([6, 1])
        with h1a:
            if step1_state == "done":
                _ent_lbl = "People / Contacts" if _prov_people else "Companies"
                wf_head(1, f"{_ent_lbl} &middot; {_prov_country}", "done")
            else:
                wf_head(1, "What do you want to download?", step1_state,
                        "" if step1_open else "Choose an entity type and a target country.")
        with h1b:
            if not step1_open and step1_state == "done":
                wf_edit_button(1)

        with st.container(key="wf_step1"):
            curr_mode_idx = st.session_state.get("search_mode_idx", 0)
            search_mode = st.radio(
                "Select Extraction Entity:",
                ["\U0001F3E2 Companies Search", "\U0001F464 People Search"],
                horizontal=True,
                index=curr_mode_idx,
                key="search_mode_widget",
                on_change=on_mode_change,
                help="Choose whether to extract Company datasets (Domains, Employee sizes, LinkedIn) or People/Contacts datasets (Full Names, Job Titles, Locations, Profile URLs)"
            )
            is_people_mode = "People" in search_mode


            curr_c_idx = st.session_state.get("sel_country_idx", 0)
            if curr_c_idx >= len(country_options):
                curr_c_idx = 0

            col_country, _ = st.columns([1, 1])
            with col_country:
                selected_country_raw = st.selectbox(
                    "Search and select country (218 countries available):",
                    options=country_options,
                    index=curr_c_idx,
                    key="country_select_widget",
                    on_change=on_country_change,
                    help="Select any country or choose Global to extract across all 17 supported countries."
                )

                custom_country_toggle = st.checkbox("Enter custom country name manually", key="wf_custom_country")
                if custom_country_toggle:
                    country_input = st.text_input("Manual Country Name", "", key="wf_manual_country")
                else:
                    if selected_country_raw == "-- Select Target Country --":
                        country_input = ""
                    elif selected_country_raw == "\U0001F30D All Supported Countries (Global)":
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
                    st.info("\U0001F30D **Global Extraction Active**: Data will be extracted and compiled sequentially across all 17 configured countries, creating both per-country master files and unified Global delivery files.")
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
                        st.info(f"\U0001F7E2 **Geographic Partitioning Active for {country_input}**: {div_str} mapped for high-coverage extraction.")
                    else:
                        st.info(f"\U0001F310 **Extraction Active for {country_input}**: Multi-Dimensional Partitioning (City, Keyword, Size, Revenue) Enabled.")
            else:
                st.caption("Please select a target country above to get started.")

            _c1, _c2 = st.columns([3, 1])
            with _c2:
                if st.button("Continue", type="primary", use_container_width=True,
                             disabled=not country_input, key="wf_continue_1"):
                    st.session_state["wf_open"] = 2
                    st.rerun()

        if not step1_open:
            wf_hide("wf_step1")

    entity_label = "People / Contacts" if is_people_mode else "Companies"

    # ==================================================================
    # STEP 2 -- INDUSTRIES
    # ==================================================================

    step2_open = (forced == 2) or (not forced and bool(_prov_country) and not _prov_inds)
    step2_state = "active" if step2_open else ("done" if _prov_inds else "todo")

    with st.container(border=True):
        h2a, h2b = st.columns([6, 1])
        with h2a:
            if step2_state == "done":
                _preview = ", ".join(_prov_inds[:5])
                if len(_prov_inds) > 5:
                    _preview += f" +{len(_prov_inds) - 5} more"
                wf_head(2, f"Industries &middot; {len(_prov_inds)} selected", "done", _preview)
            else:
                wf_head(2, "Choose industries", step2_state,
                        "" if step2_open else f"Pick which industries to pull {entity_label.lower()} from.")
        with h2b:
            if not step2_open and step2_state == "done":
                wf_edit_button(2)

        with st.container(key="wf_step2"):
            st.caption(f"Which industries do you want {entity_label.lower()} from?")
            b_col1, b_col2, b_col3, b_col4 = st.columns(4)

            def _apply_preset(values, preset_name=""):
                vals = list(values)
                st.session_state["selected_industries"] = vals
                st.session_state["wf_inds_backup"] = vals
                if "ind" in st.query_params:
                    del st.query_params["ind"]
                if preset_name:
                    st.query_params["preset"] = preset_name
                elif "preset" in st.query_params:
                    del st.query_params["preset"]

            with b_col1:
                st.button("Select Tech Industries", key="preset_tech", use_container_width=True,
                          on_click=_apply_preset, args=(TECH_INDUSTRIES, "tech"))

            with b_col2:
                st.button("Select Non-Tech Industries", key="preset_nontech", use_container_width=True,
                          on_click=_apply_preset, args=(NON_TECH_INDUSTRIES, "nontech"))

            with b_col3:
                st.button("Select All 458 Industries", key="preset_all", use_container_width=True,
                          on_click=_apply_preset, args=(ALL_CLAY_INDUSTRIES, "all"))

            with b_col4:
                st.button("Clear Selection", key="preset_clear", use_container_width=True,
                          on_click=_apply_preset, args=([], ""))

            selected_industries = st.multiselect(
                "Search and select industries (starts empty; select manually or use category buttons above):",
                options=ALL_CLAY_INDUSTRIES,
                key="selected_industries"
            )

            # Prevent 414 Request-URI Too Large on Nginx:
            # Only store small subsets (<=3) or preset names in URL query params.
            # Large sets are kept in session_state to avoid overflowing Nginx's 8KB URI buffer.
            if len(selected_industries) <= 3 and len(selected_industries) > 0:
                st.query_params["ind"] = "|".join(selected_industries)
                if "preset" in st.query_params:
                    del st.query_params["preset"]
            else:
                if "ind" in st.query_params:
                    del st.query_params["ind"]

            st.session_state["wf_inds_backup"] = list(selected_industries)
            st.caption(f"Currently selected: {len(selected_industries)} industries out of 458 total Clay industries.")

            _i1, _i2 = st.columns([3, 1])
            with _i2:
                if st.button("Continue", type="primary", use_container_width=True,
                             disabled=not selected_industries or not country_input, key="wf_continue_2"):
                    st.session_state["wf_open"] = 3
                    st.rerun()

        if not step2_open:
            wf_hide("wf_step2")

    # ------------------------------------------------------------------
    # Shared derivation -- unchanged from the original implementation
    # ------------------------------------------------------------------
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

    # ---- counts already on disk for this country / entity
    counts_lookup = {}
    counts_present = set()   # industries the count actually returned a value for
    counts_rows = 0
    if country_input and counts_file and os.path.exists(counts_file):
        try:
            cdf_lk = pd.read_csv(counts_file)
            for _, r in cdf_lk.iterrows():
                _ind = str(r.get("Industry")).strip()
                _raw = r.get("Count")
                counts_lookup[_ind] = safe_int(_raw)
                counts_rows += 1
                # A blank Count means the query came back empty (an expired Clay
                # session does this) -- that is NOT the same as a genuine zero.
                if not pd.isna(_raw) and str(_raw).strip() != "":
                    counts_present.add(_ind)
        except Exception:
            pass
    missing_counts = [i for i in selected_industries if i not in counts_present]
    counts_ready = bool(selected_industries) and (len(missing_counts) == 0)
    counts_blank = counts_rows > 0 and not counts_present

    # ---- plan status + coverage, derived exactly as before
    planned_data = []
    if country_input and selected_industries:
        for ind in selected_industries:
            prefix = slugify(f"{ind}_{country_input}{plan_suffix}")
            pj = f"plans/clicklist_{prefix}.json"
            exp = counts_lookup.get(ind, 0)

            num_slices = 0
            gap = 0
            has_plan_file = os.path.exists(pj)
            is_zero_count = (ind in counts_present) and (exp == 0)
            is_planned = has_plan_file or is_zero_count
            status_str = "Planned" if is_planned else "Pending plan"

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

    all_planned = bool(planned_data) and all(r["Status"] == "Planned" for r in planned_data)

    tot_reach = sum(safe_int(r["Estimated Reachable"]) for r in planned_data
                    if isinstance(r["Estimated Reachable"], (int, float)) or str(r["Estimated Reachable"]).isdigit())
    tot_target = sum(safe_int(r["Clay Target Count"]) for r in planned_data)
    if tot_target < tot_reach:
        tot_target = tot_reach
    overall_cov = min(100.0, round(100 * tot_reach / max(1, tot_target), 1)) if tot_target and all_planned else (0.0 if not all_planned else 100.0)
    unreachable = max(0, tot_target - tot_reach) if all_planned else 0

    # ==================================================================
    # HEADER PLACEHOLDERS -- filled before the long-running operations so the
    # job chip and stage indicator stay on screen while a job is running
    # ==================================================================
    _prov_approved = st.session_state.get(
        f"plan_approved_check_{'ppl' if is_people_mode else 'cmp'}", False
    )

    if not country_input:
        active_stage = 1
    elif not selected_industries:
        active_stage = 2
    elif not (counts_ready and all_planned):
        active_stage = 3
    elif not _prov_approved:
        active_stage = 4
    else:
        active_stage = 5

    if country_input and selected_industries:
        _ind_word = "industry" if len(selected_industries) == 1 else "industries"
        with ph_job.container():
            st.markdown(
                f"<div class='wf-job'>{entity_label}"
                f"<span class='sep'>&bull;</span>{country_input}"
                f"<span class='sep'>&bull;</span>"
                f"<span class='muted'>{len(selected_industries)} {_ind_word}</span></div>",
                unsafe_allow_html=True,
            )

    _stage_names = ["Setup", "Industries", "Coverage", "Review", "Download"]
    _parts = []
    for i, nm in enumerate(_stage_names, 1):
        if i < active_stage:
            dot, lab = "done", ic("check", 15)
        elif i == active_stage:
            dot, lab = "active", str(i)
        else:
            dot, lab = "", str(i)
        if i > 1:
            _parts.append(f"<div class='wf-line{' done' if i <= active_stage else ''}'></div>")
        _parts.append(
            f"<div class='wf-stage'><div class='wf-dot {dot}'>{lab}</div>"
            f"<div class='wf-label{' on' if i <= active_stage else ''}'>{nm}</div></div>"
        )
    with ph_steps.container():
        # preset_css() rides along here: this runs after `?ind=` has been
        # restored into session state, so the highlight survives a refresh.
        st.markdown(f"<div class='wf-steps'>{''.join(_parts)}</div>" + preset_css(), unsafe_allow_html=True)


    # ==================================================================
    # STEP 3 -- COVERAGE (Count + Plan presented as one operator stage)
    #
    # Count and Plan remain two separate backend operations, run in the
    # same order and by the same scripts as before. Only the framing is
    # merged: to the operator this is one question -- "how much data is
    # actually available?"
    # ==================================================================
    btn_count = False
    btn_plan = False

    step3_open = (forced == 3) or (not forced and bool(_prov_country) and bool(_prov_inds)
                                   and not (counts_ready and all_planned))
    step3_done = counts_ready and all_planned
    step3_state = "active" if step3_open else ("done" if step3_done else "todo")

    with st.container(border=True):
        h3a, h3b = st.columns([6, 1])
        with h3a:
            if step3_state == "done" and not step3_open and tot_target == 0:
                wf_head(3, "Coverage &middot; no matching records", "done",
                        "The selected industries returned no rows in this country.")
            elif step3_state == "done" and not step3_open:
                wf_head(3, f"Coverage &middot; {overall_cov}% estimated", "done",
                        f"{tot_target:,} matching &middot; ~{tot_reach:,} expected downloadable")
            else:
                wf_head(3, "Check coverage", step3_state,
                        f"We'll count matching {entity_label.lower()} and estimate how much Clay data can be downloaded."
                        if step3_open else "Count matching records and estimate reachable coverage.")
        with h3b:
            if not step3_open and step3_done:
                wf_edit_button(3, "View")

        with st.container(key="wf_step3"):
            if not country_input or not selected_industries:
                st.caption("Complete steps 1 and 2 first.")
            else:
                # ---------- 3a. COUNT ----------
                if not counts_ready:
                    if counts_blank:
                        st.error(
                            "The last count ran but Clay returned no values for these industries. "
                            "This usually means the Clay session has expired — open **Clay session** "
                            "in the header to refresh it, then run the count again."
                        )
                    if len(missing_counts) < len(selected_industries):
                        st.caption(f"Free counting query for {len(missing_counts)} uncounted industries (out of {len(selected_industries)} selected) in {country_input}. No Clay credits are spent.")
                    else:
                        st.caption(f"Free counting query for all {len(selected_industries)} selected industries in {country_input}. No Clay credits are spent.")
                    cc1, cc2 = st.columns([3, 1])
                    with cc1:
                        btn_count = st.button(f"Check matching {entity_label.lower()}", type="primary", use_container_width=True)
                    with cc2:
                        if st.button("Stop", key="stop_step1_btn", type="secondary", use_container_width=True):
                            proc = st.session_state.get("current_process")
                            if proc and proc.poll() is None:
                                proc.terminate()
                                st.session_state["current_process"] = None
                                st.warning("Counting stopped.")
                            else:
                                st.info("No active count process.")
                else:
                    _counted_total = sum(counts_lookup.get(i, 0) for i in selected_industries)
                    st.success(f"Count complete — {_counted_total:,} matching {entity_label.lower()} across {len(selected_industries)} industries.")
                    if country_input and os.path.exists(counts_file):
                        try:
                            cdf_raw = pd.read_csv(counts_file)
                            if selected_industries:
                                cdf_show = cdf_raw[cdf_raw["Industry"].isin(selected_industries)].copy()
                            else:
                                cdf_show = cdf_raw.copy()
                            if not cdf_show.empty:
                                if "Count" in cdf_show.columns:
                                    cdf_show["Count"] = pd.to_numeric(cdf_show["Count"], errors="coerce").fillna(0).astype(int)
                                    cdf_show = cdf_show.sort_values(by="Count", ascending=False)
                                cdf_show.index = range(1, len(cdf_show) + 1)
                                cols_to_display = [c for c in ["Industry", "Count", "Category"] if c in cdf_show.columns]
                                if not cols_to_display:
                                    cols_to_display = cdf_show.columns.tolist()
                                st.markdown(f"##### Matching {entity_label} per Industry ({country_input})")
                                st.dataframe(
                                    cdf_show[cols_to_display],
                                    use_container_width=True,
                                    height=min(320, 38 * (len(cdf_show) + 1))
                                )
                        except Exception:
                            pass

                # ---------- 3b. PLAN ----------
                if counts_ready and not all_planned:
                    _pending = sum(1 for r in planned_data if r["Status"] != "Planned")
                    st.caption(f"Next we calculate reachable coverage. {_pending} of {len(planned_data)} industries still need a partition plan. Free query.")
                    pc1, pc2 = st.columns([3, 1])
                    with pc1:
                        btn_plan = st.button("Calculate coverage", type="primary", use_container_width=True)
                    with pc2:
                        if st.button("Stop", key="stop_step2_btn", type="secondary", use_container_width=True):
                            proc = st.session_state.get("current_process")
                            if proc and proc.poll() is None:
                                proc.terminate()
                                st.session_state["current_process"] = None
                                st.warning("Planning stopped.")
                            else:
                                st.info("No active plan process.")

                # ---------- 3c. RESULT ----------
                if all_planned and planned_data and tot_target == 0:
                    st.info(
                        f"No matching {entity_label.lower()} were found in {country_input} for the "
                        f"{len(selected_industries)} selected industries. There is nothing to download — "
                        f"try different industries or another country."
                    )
                elif all_planned and planned_data:
                    _cov_cls = "ok" if overall_cov >= 95 else ("warn" if overall_cov < 80 else "info")
                    _bar_cls = "" if overall_cov >= 80 else " warn"
                    st.markdown(
                        f"""
                        <div class='wf-metrics'>
                          <div class='wf-metric'><div class='v'>{tot_target:,}</div><div class='l'>Matching {entity_label.lower()}</div></div>
                          <div class='wf-metric'><div class='v info'>{tot_reach:,}</div><div class='l'>Expected downloadable</div></div>
                          <div class='wf-metric'><div class='v {_cov_cls}'>{overall_cov}%</div><div class='l'>Estimated coverage</div></div>
                        </div>
                        <div class='wf-bar-wrap'>
                          <div class='wf-bar'><span class='{_bar_cls}' style='width:{overall_cov}%'></span></div>
                          <div class='wf-bar-pct'>{overall_cov}%</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    if unreachable > 0:
                        st.warning(
                            f"Approximately {unreachable:,} matching {entity_label.lower()} "
                            f"({round(100 * unreachable / max(1, tot_target), 1)}%) may not be reachable "
                            f"through the current extraction plan."
                        )
                        with st.expander("Why is coverage below 100%?"):
                            st.markdown(
                                "Clay exports at most **5,000 rows per table**, so each industry is split into "
                                "slices that each stay under that cap. When a slice still holds more than 5,000 "
                                "records after every available filter has been applied, the surplus cannot be "
                                "reached by the current plan.\n\n"
                                "The figure above is the sum of the planner's own `_uncovered` reports for the "
                                "selected industries. Use **Re-plan** on an individual industry below to try a "
                                "different partitioning before downloading."
                            )

                    # ---- Technical details: the original tables, kept intact
                    with st.expander("Technical details (counts, partitions and estimates)"):
                        if country_input and os.path.exists(counts_file):
                            try:
                                cdf = pd.read_csv(counts_file)
                                if selected_industries:
                                    cdf_sel = cdf[cdf["Industry"].isin(selected_industries)]
                                else:
                                    cdf_sel = cdf
                                if not cdf_sel.empty:
                                    st.markdown(f"**Step 1 count results ({country_input})**")
                                    st.caption("Cached counts loaded from disk. Re-run the count at any time to refresh from Clay.")
                                    cdf_sel_disp = cdf_sel.copy()
                                    cdf_sel_disp.index = range(1, len(cdf_sel_disp) + 1)
                                    st.dataframe(cdf_sel_disp, use_container_width=True)
                                    tot_c = safe_sum(cdf_sel["Count"]) if "Count" in cdf_sel.columns else 0
                                    st.info(f"Total Clay Target Rows: {tot_c:,} rows across {len(cdf_sel)} selected industries.")
                            except Exception:
                                pass

                        st.markdown(f"**Step 2 plan & coverage estimate ({country_input} - {entity_label})**")
                        pdf_plan = pd.DataFrame([{k: v for k, v in r.items() if k != "cov_num"} for r in planned_data])
                        pdf_plan.index = range(1, len(pdf_plan) + 1)
                        st.dataframe(pdf_plan, use_container_width=True)

                        m_col1, m_col2, m_col3 = st.columns(3)
                        with m_col1:
                            st.metric(f"Total Target {entity_label}", f"{tot_target:,}")
                        with m_col2:
                            st.metric(f"Estimated Reachable {entity_label}", f"{tot_reach:,}")
                        with m_col3:
                            st.metric("Overall Estimated Coverage", f"{overall_cov}%")

                        st.markdown(f"**Per-industry re-planning & fine-tuning ({entity_label})**")
                        st.caption("If any industry's coverage is not sufficient, re-plan that specific industry without changing your selection:")

                        for p_row in planned_data:
                            ind_name = p_row["Industry"]
                            cov_num = p_row.get("cov_num", 0.0)
                            c_target = p_row["Clay Target Count"]
                            c_reach = p_row["Estimated Reachable"]
                            c_status = p_row["Status"]

                            if c_status != "Planned":
                                badge = "Pending generation"
                                target_str = f"{c_target:,}" if isinstance(c_target, (int, float)) else c_target
                                exp_title = f"{ind_name} | Plan pending ({target_str} target rows) | {badge}"
                            elif c_target == 0:
                                badge = "0 rows in country"
                                exp_title = f"{ind_name} | 0 Target Rows (100.0% Coverage) | {badge}"
                            else:
                                badge = "High coverage" if cov_num >= 95.0 else ("Partial coverage" if cov_num >= 80.0 else "Gaps identified")
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
                                            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=make_env())
                                            proc.wait()
                                            st.session_state["current_process"] = None
                                            st.success(f"Re-plan complete for '{ind_name}'! Slices refreshed.")
                                            st.rerun()
                                with exp_c3:
                                    if st.button(f"Download '{ind_name[:15]}...'", key=f"dl_{slugify(ind_name)}_{'ppl' if is_people_mode else 'cmp'}", type="primary", use_container_width=True):
                                        t0_single = time.time()
                                        track_event("single_download_started", {"industry": ind_name, "country": country_input, "entity": entity_label})
                                        st.markdown(f"Executing single-industry download for `{ind_name}`...")
                                        render_download_card(0.05, f"Starting '{ind_name}'...", f"Country: {country_input}")
                                        cmd_run = [sys.executable, "-u", run_script, country_input, "--only", ind_name, "--user", current_user]
                                        proc = subprocess.Popen(cmd_run, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, env=make_env())
                                        st.session_state["current_process"] = proc
                                        log_box = st.empty()
                                        logs_single = []
                                        while True:
                                            l = proc.stdout.readline()
                                            if not l and proc.poll() is not None:
                                                break
                                            if l:
                                                stripped_l = l.strip()
                                                if is_ignorable_warning(stripped_l):
                                                    continue
                                                logs_single.append(stripped_l)
                                                log_box.code("\n".join(logs_single[-15:]))
                                                m_s = re.search(r'\[(\d+)/(\d+)\]', stripped_l)
                                                s_pct = 0.5
                                                if m_s:
                                                    s_pct = min(0.95, int(m_s.group(1)) / max(1, int(m_s.group(2))))
                                                render_download_card(s_pct, f"Downloading: {ind_name[:25]}", stripped_l[:45])
                                        proc.wait()
                                        st.session_state["current_process"] = None
                                        dur_single = round(time.time() - t0_single, 1)
                                        track_event("single_download_completed", {
                                            "industry": ind_name,
                                            "country": country_input,
                                            "entity": entity_label,
                                            "duration_seconds": dur_single,
                                            "status": "SUCCESS"
                                        })
                                        render_download_complete_card(f"Download complete: {ind_name}!")
                                        st.success(f"Download complete for '{ind_name}'!")

                    _r1, _r2 = st.columns([3, 1])
                    with _r2:
                        if st.button("Review download", type="primary", use_container_width=True, key="wf_continue_3"):
                            st.session_state["wf_open"] = 4
                            st.rerun()

        if not step3_open:
            wf_hide("wf_step3")

    # ---------- COUNT EXECUTION (unchanged handler) ----------
    if btn_count:
        t0_count = time.time()
        track_event("count_started", {"entity": entity_label, "country": country_input, "industries_count": len(selected_industries)})
        with open(ind_file, "w", encoding="utf-8") as f:
            json.dump(selected_industries, f)
        if os.path.exists(counts_file):
            os.remove(counts_file)

        st.markdown("#### Checking availability")
        count_progress_bar = st.progress(0.0)
        count_status = st.empty()
        count_status.text(f"Starting {entity_label} count for {len(selected_industries)} industries in {country_input}...")

        cmd = [sys.executable, "-u", count_script, country_input, "--industries-file", ind_file, "--user", current_user]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, env=make_env())
        st.session_state["current_process"] = proc

        total_to_count = len(selected_industries)
        count_logs = []

        while True:
            line = proc.stdout.readline()
            if not line and proc.poll() is not None:
                break
            if line:
                stripped_line = line.strip()
                if is_ignorable_warning(stripped_line):
                    continue
                count_logs.append(stripped_line)
                m = re.search(r'\[(\d+)/(\d+)\]', stripped_line)
                if m:
                    current_i = int(m.group(1))
                    tot_i = int(m.group(2))
                    pct = min(1.0, current_i / max(1, tot_i))
                    count_progress_bar.progress(pct)
                    count_status.text(f"Counting: {current_i} of {tot_i} industries ({int(pct*100)}%)")

        proc.wait()
        st.session_state["current_process"] = None
        dur_count = round(time.time() - t0_count, 1)
        if proc.returncode == 0:
            count_progress_bar.progress(1.0)
            count_status.text("Counting complete.")
            total_cnt = 0
            if os.path.exists(counts_file):
                try:
                    with open(counts_file, "r", encoding="utf-8-sig", errors="replace") as f:
                        total_cnt = sum(int(r.get("Count", 0)) for r in csv.DictReader(f) if str(r.get("Count", "")).isdigit())
                except Exception:
                    pass
            track_event("count_completed", {
                "entity": entity_label,
                "country": country_input,
                "industries_count": len(selected_industries),
                "total_available_records": total_cnt,
                "duration_seconds": dur_count,
                "status": "SUCCESS"
            })
            st.session_state["wf_open"] = 3
            st.rerun()
        else:
            full_log_str = "\n".join(count_logs)
            is_auth_err = ("401" in full_log_str or "unauthorized" in full_log_str.lower() or "claysession" in full_log_str.lower())
            if is_auth_err:
                st.error("Count failed: The Clay session cookie may have expired or is invalid. Please check or refresh your cookie in the header.")
            else:
                st.error("Count failed or was stopped before completion.")
            with st.expander("Technical details (count process output)", expanded=not is_auth_err):
                st.code("\n".join(count_logs[-20:]) if count_logs else "No output captured from count process.")
            track_event("count_failed", {
                "entity": entity_label,
                "country": country_input,
                "industries_count": len(selected_industries),
                "duration_seconds": dur_count,
                "status": "FAILED"
            })

    # ---------- PLAN EXECUTION (unchanged handler) ----------
    if btn_plan:
        t0_plan = time.time()
        track_event("plan_started", {"entity": entity_label, "country": country_input, "industries_count": len(selected_industries)})
        with open(ind_file, "w", encoding="utf-8") as f:
            json.dump(selected_industries, f)

        st.markdown("#### Calculating coverage")
        plan_progress_bar = st.progress(0.0)
        plan_status = st.empty()
        plan_log_box = st.empty()
        tot_p = len(selected_industries)

        for idx, ind in enumerate(selected_industries, 1):
            prefix = slugify(f"{ind}_{country_input}{plan_suffix}")
            pj = f"plans/clicklist_{prefix}.json"
            if os.path.exists(pj) and os.path.getsize(pj) > 2:
                try:
                    num_existing = len(json.load(open(pj, encoding="utf-8")))
                    plan_status.text(f"[{idx}/{tot_p}] '{ind}' already planned ({num_existing} slices). Skipping.")
                    plan_progress_bar.progress(idx / tot_p)
                    continue
                except Exception:
                    pass

            plan_status.text(f"Planning {idx} of {tot_p}: {ind} ({entity_label})...")
            cmd = [sys.executable, "-u", plan_script, ind, country_input]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, env=make_env())
            st.session_state["current_process"] = proc

            plan_logs = []
            while True:
                line = proc.stdout.readline()
                if not line and proc.poll() is not None:
                    break
                if line:
                    stripped = line.strip()
                    if is_ignorable_warning(stripped):
                        continue
                    plan_logs.append(stripped)
                    plan_log_box.code("\n".join(plan_logs[-10:]))
                    plan_status.text(f"Planning {idx} of {tot_p}: {ind} — {stripped[:65]}")

            proc.wait()
            if proc.returncode != 0:
                time.sleep(1)
                proc_retry = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, env=make_env())
                st.session_state["current_process"] = proc_retry
                while True:
                    line = proc_retry.stdout.readline()
                    if not line and proc_retry.poll() is not None:
                        break
                    if line:
                        stripped = line.strip()
                        if is_ignorable_warning(stripped):
                            continue
                        plan_logs.append(stripped)
                        plan_log_box.code("\n".join(plan_logs[-10:]))
                        plan_status.text(f"Planning {idx} of {tot_p} (retry): {ind} — {stripped[:65]}")
                proc_retry.wait()
            plan_progress_bar.progress(idx / tot_p)

        st.session_state["current_process"] = None
        dur_plan = round(time.time() - t0_plan, 1)
        plan_status.text("Planning complete.")
        track_event("plan_completed", {
            "entity": entity_label,
            "country": country_input,
            "industries_count": len(selected_industries),
            "duration_seconds": dur_plan,
            "status": "SUCCESS"
        })
        st.session_state["wf_open"] = 3
        st.rerun()

    # ==================================================================
    # STEP 4 -- REVIEW
    # ==================================================================
    def _cb_start_download():
        st.session_state["is_downloading"] = True
        st.session_state["download_trigger"] = True

    def _cb_stop_download():
        proc = st.session_state.get("current_process")
        if proc and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass
        st.session_state["current_process"] = None
        st.session_state["is_downloading"] = False
        st.session_state["download_trigger"] = False
        st.session_state["live_status"] = {"active": False}

    is_dl_active = bool(
        st.session_state.get("is_downloading")
        or (st.session_state.get("current_process") and st.session_state["current_process"].poll() is None)
    )
    run_dl_trigger = bool(st.session_state.get("download_trigger"))
    btn_download = False
    plan_approved = False

    step4_open = (forced == 4) or (not forced and step3_done)
    step4_state = "active" if step4_open else "todo"

    with st.container(border=True):
        wf_head(4, "Review download", step4_state,
                "Confirm what will be downloaded before starting."
                if not step4_open else "")

        with st.container(key="wf_step4"):
            if not step3_done:
                st.caption("Check coverage first.")
                plan_approved = st.checkbox(
                    "I approve the plan & estimated coverage",
                    key=f"plan_approved_check_{'ppl' if is_people_mode else 'cmp'}",
                    disabled=True,
                )
            else:
                rv1, rv2 = st.columns(2)
                with rv1:
                    st.markdown(
                        f"**Entity**  \n{entity_label}\n\n"
                        f"**Country**  \n{country_input}\n\n"
                        f"**Industries**  \n{len(selected_industries)} selected"
                    )
                with rv2:
                    st.markdown(
                        f"**Matching {entity_label.lower()}**  \n{tot_target:,}\n\n"
                        f"**Expected downloadable**  \n~{tot_reach:,}\n\n"
                        f"**Estimated coverage**  \n{overall_cov}%"
                    )

                st.caption(
                    f"Output: CSV master files per industry, merged incrementally into `{delivery_root}/` "
                    f"and de-duplicated on Domain and LinkedIn URL."
                )

                if unreachable > 0:
                    st.warning(
                        f"Estimated coverage {overall_cov}% — approximately {unreachable:,} matching "
                        f"{entity_label.lower()} may not be included in the resulting download."
                    )

                plan_approved = st.checkbox(
                    "I approve the plan & estimated coverage",
                    key=f"plan_approved_check_{'ppl' if is_people_mode else 'cmp'}",
                )

                if is_dl_active:
                    st.info(f"⏳ **Download in progress for {country_input}** ({len(selected_industries)} industries). Live progress and terminal output are streaming in Step 5 below.")

                dl1, dl2 = st.columns([3, 1])
                with dl1:
                    if is_dl_active:
                        st.button(
                            "⏳ Downloading in progress...",
                            type="primary",
                            use_container_width=True,
                            disabled=True,
                            key=f"btn_dl_active_{'ppl' if is_people_mode else 'cmp'}",
                        )
                    else:
                        st.button(
                            "Start download",
                            type="primary",
                            use_container_width=True,
                            disabled=not plan_approved or not country_input or not selected_industries,
                            key=f"btn_dl_start_{'ppl' if is_people_mode else 'cmp'}",
                            on_click=_cb_start_download,
                        )
                with dl2:
                    st.button(
                        "Stop",
                        key=f"stop_step3_btn_{'ppl' if is_people_mode else 'cmp'}",
                        type="secondary",
                        use_container_width=True,
                        on_click=_cb_stop_download,
                    )

        if not step4_open:
            wf_hide("wf_step4")

    # ==================================================================
    # STEP 5 -- DOWNLOAD
    # ==================================================================
    ledger_exists = bool(country_input and ledger_file and os.path.exists(ledger_file))
    run_dl_trigger = bool(st.session_state.get("download_trigger"))
    step5_open = (forced == 5) or is_dl_active or run_dl_trigger or ledger_exists
    step5_state = "active" if (step5_open and not ledger_exists) else ("done" if ledger_exists else "todo")

    with st.container(border=True):
        wf_head(5, "Download data", step5_state,
                "Execute the download, incremental merge and deduplication."
                if not step5_open else "")

        with st.container(key="wf_step5"):
            # ---------- DOWNLOAD EXECUTION ----------
            if run_dl_trigger:
                st.session_state["download_trigger"] = False
                if not plan_approved:
                    st.warning("Please approve the plan above before downloading.")
                    st.session_state["is_downloading"] = False
                else:
                    st.session_state["is_downloading"] = True
                    t0_dl = time.time()
                    st.markdown(f"### Executing Live Download for {country_input} ({entity_label})...")
                    track_event("download_started", {"entity": entity_label, "country": country_input, "industries_count": len(selected_industries), "industries": selected_industries})

                    with open(ind_file, "w", encoding="utf-8") as f:
                        json.dump(selected_industries, f)

                    # Filter zero-record industries if count cache exists
                    active_industries = []
                    zero_count_industries = []
                    if os.path.exists(counts_file):
                        try:
                            cdf = pd.read_csv(counts_file, encoding="utf-8-sig")
                            col_ind = "Industry" if "Industry" in cdf.columns else cdf.columns[0]
                            col_cnt = "Count" if "Count" in cdf.columns else cdf.columns[2]
                            cnt_map = dict(zip(cdf[col_ind].astype(str), pd.to_numeric(cdf[col_cnt], errors="coerce").fillna(0).astype(int)))
                            for ind in selected_industries:
                                if cnt_map.get(ind, 1) > 0:
                                    active_industries.append(ind)
                                else:
                                    zero_count_industries.append(ind)
                        except Exception:
                            active_industries = list(selected_industries)
                    else:
                        active_industries = list(selected_industries)

                    # Mark zero-record industries directly in ledger so they appear completed
                    if zero_count_industries and ledger_file:
                        for z_ind in zero_count_industries:
                            dst_zero = get_delivery_path(country_input, z_ind, is_people=is_people_mode)
                            record_ledger_row(ledger_file, [z_ind, 0, 0, 0, 100.0, 0, 0, dst_zero], is_people=is_people_mode)

                    dl_targets = active_industries if active_industries else selected_industries

                    log_container = st.empty()
                    dl_progress_bar = st.progress(0.0)
                    dl_status_text = st.empty()
                    render_download_card(0.02, f"Starting {entity_label} Download", f"Country: {country_input} ({len(dl_targets)} active industries)")

                    cmd_run = [sys.executable, "-u", run_script, country_input]
                    if len(dl_targets) <= 10:
                        only_str = "|".join(dl_targets)
                        cmd_run.extend(["--only", only_str])
                    else:
                        with open(ind_file, "w", encoding="utf-8") as _f_ind:
                            json.dump(list(dl_targets), _f_ind)
                        cmd_run.extend(["--only-file", ind_file])
                    cmd_run.extend(["--user", current_user])

                    process = subprocess.Popen(cmd_run, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, env=make_env())
                    st.session_state["current_process"] = process

                    logs = []
                    tot_ind = len(dl_targets)
                    curr_ind_idx = 0
                    curr_ind_name = ""

                    try:
                        while True:
                            line = process.stdout.readline()
                            if not line and process.poll() is not None:
                                break
                            if line:
                                stripped = line.strip()
                                if is_ignorable_warning(stripped):
                                    continue
                                logs.append(stripped)
                                log_container.code("\n".join(logs[-20:]))

                                m_ind = re.search(r'\[(\d+)/(\d+)\]\s+([A-Za-z0-9\s,&-]+?)\s+\(~', stripped)
                                if m_ind:
                                    curr_ind_idx = int(m_ind.group(1))
                                    curr_ind_name = m_ind.group(3).strip()
                                    pct = max(0.01, min(0.99, (curr_ind_idx - 1) / max(1, tot_ind)))
                                    dl_progress_bar.progress(pct)
                                    status_msg = f"Downloading [{curr_ind_idx}/{tot_ind}]: {curr_ind_name}..."
                                    dl_status_text.text(status_msg)
                                    st.session_state["live_status"] = {"active": True, "title": f"Download: {country_input} ({entity_label})", "text": status_msg, "pct": pct}
                                    render_download_card(pct, f"[{curr_ind_idx}/{tot_ind}] {curr_ind_name[:24]}", f"{country_input} • {int(pct*100)}% complete")

                                m_slice = re.search(r'\[(\d+)/(\d+)\]\s+([A-Za-z0-9_]+)', stripped)
                                if m_slice and not m_ind and curr_ind_idx > 0:
                                    s_idx = int(m_slice.group(1))
                                    s_tot = int(m_slice.group(2))
                                    pct_ind = (s_idx - 1) / max(1, s_tot)
                                    pct = min(0.99, ((curr_ind_idx - 1) + pct_ind) / max(1, tot_ind))
                                    dl_progress_bar.progress(pct)
                                    status_msg = f"Downloading [{curr_ind_idx}/{tot_ind}] {curr_ind_name} — Slice {s_idx}/{s_tot}..."
                                    dl_status_text.text(status_msg)
                                    st.session_state["live_status"] = {"active": True, "title": f"Download: {country_input} ({entity_label})", "text": status_msg, "pct": pct}
                                    render_download_card(pct, f"[{curr_ind_idx}/{tot_ind}] {curr_ind_name[:20]}", f"Slice {s_idx}/{s_tot} • {int(pct*100)}%")

                        process.wait()
                    finally:
                        st.session_state["current_process"] = None
                        st.session_state["is_downloading"] = False
                        st.session_state["live_status"] = {"active": False}
                    dur_dl = round(time.time() - t0_dl, 1)
                    if process.returncode == 0:
                        dl_progress_bar.progress(1.0)
                        dl_status_text.text(f"Download complete. All {tot_ind} industries downloaded & merged.")
                        render_download_complete_card(f"Download complete: All {tot_ind} industries merged for {country_input}!")
                        st.success(f"Download and centralized merge complete for {country_input} ({entity_label}).")

                        sum_total = 0
                        sum_new = 0
                        if country_input and os.path.exists(ledger_file):
                            try:
                                ldf = load_ledger_dataframe(ledger_file)
                                col_ind = "industry" if "industry" in ldf.columns else ("Industry" if "Industry" in ldf.columns else None)
                                col_u = "unique_companies" if "unique_companies" in ldf.columns else ("unique_people" if "unique_people" in ldf.columns else None)
                                col_n = "new_added" if "new_added" in ldf.columns else None
                                if col_ind and col_u:
                                    ldf_last = ldf.drop_duplicates(subset=[col_ind], keep="last")
                                    if selected_industries:
                                        ldf_last = ldf_last[ldf_last[col_ind].isin(selected_industries)]
                                    sum_total = int(pd.to_numeric(ldf_last[col_u], errors="coerce").sum())
                                    if col_n:
                                        sum_new = int(pd.to_numeric(ldf_last[col_n], errors="coerce").sum())
                            except Exception:
                                pass

                        track_event("download_completed", {
                            "entity": entity_label,
                            "country": country_input,
                            "industries_count": tot_ind,
                            "industries": selected_industries,
                            "total_master_records": sum_total,
                            "new_records_added": sum_new,
                            "duration_seconds": dur_dl,
                            "status": "SUCCESS"
                        })
                    else:
                        render_download_complete_card("Download stopped or completed.")
                        st.error("Download finished with errors or was stopped. Anything already downloaded is kept and listed below.")
                        with st.expander("Technical details (raw process output)"):
                            st.code("\n".join(logs[-60:]) or "No output captured.")
                        track_event("batch_download_failed", {
                            "entity": entity_label,
                            "country": country_input,
                            "industries_count": tot_ind,
                            "duration_seconds": dur_dl,
                            "status": "FAILED"
                        })

            # ---------- DELIVERED MASTER DATASETS (unchanged) ----------
            if ledger_exists:
                st.markdown(f'#### {ic("package", 18)} Delivered master datasets &amp; incremental merge ledger ({country_input} - {entity_label})', unsafe_allow_html=True)
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

                    st.markdown(f'#### {ic("download", 18)} Download &amp; export delivered {entity_label} master files ({country_input})', unsafe_allow_html=True)
                    
                    # 1. Resolve Country Delivery Directory & Gather Delivered Files
                    c_short = SHORT_COUNTRY_DELIVERY.get(country_input, country_input)
                    base_delivery_dir = "delivery_people" if is_people_mode else "delivery"
                    country_delivery_dir = os.path.join(base_delivery_dir, c_short)
                    
                    delivered_files_info = []
                    col_fpath = "file" if "file" in ledger_df.columns else ("File" if "File" in ledger_df.columns else None)
                    
                    if col_fpath:
                        for _, lrow in ledger_df.iterrows():
                            orig_fpath = str(lrow[col_fpath]).replace("\\", "/")
                            ind_lbl = lrow.get(col_ind, os.path.basename(orig_fpath))
                            cat = get_industry_category(ind_lbl)
                            
                            # Check multiple candidate locations (categorized and legacy)
                            fpath = orig_fpath
                            if not os.path.exists(fpath):
                                b_name = os.path.basename(orig_fpath)
                                p_dir = os.path.dirname(orig_fpath)
                                for cand in [
                                    os.path.join(p_dir, cat, b_name),
                                    os.path.join(country_delivery_dir, cat, b_name),
                                    os.path.join(country_delivery_dir, b_name),
                                    os.path.join(country_delivery_dir, "Tech", b_name),
                                    os.path.join(country_delivery_dir, "Non-Tech", b_name),
                                ]:
                                    if os.path.exists(cand):
                                        fpath = cand.replace("\\", "/")
                                        break
                                        
                            if os.path.exists(fpath) and os.path.getsize(fpath) > 0:
                                delivered_files_info.append({
                                    "industry": ind_lbl,
                                    "category": cat,
                                    "path": fpath,
                                    "filename": os.path.basename(fpath),
                                    "size_kb": os.path.getsize(fpath) / 1024
                                })
                    
                    # If ledger didn't list all, scan the country_delivery_dir directly
                    if os.path.exists(country_delivery_dir):
                        known_paths = {item["path"] for item in delivered_files_info}
                        for root, dirs, files in os.walk(country_delivery_dir):
                            for file in files:
                                if file.endswith(".csv"):
                                    fp = os.path.join(root, file).replace("\\", "/")
                                    if fp not in known_paths and os.path.getsize(fp) > 0:
                                        cat = "Tech" if "/Tech" in fp or "\\Tech" in fp else ("Non-Tech" if "/Non-Tech" in fp or "\\Non-Tech" in fp else get_industry_category(file))
                                        ind_name = file.split(" [Clay] -")[-1].replace(".csv", "").replace(" (People)", "").replace("-", " ")
                                        delivered_files_info.append({
                                            "industry": ind_name,
                                            "category": cat,
                                            "path": fp,
                                            "filename": file,
                                            "size_kb": os.path.getsize(fp) / 1024
                                        })
                                        known_paths.add(fp)
                    
                    tech_files = [f for f in delivered_files_info if f["category"] == "Tech"]
                    nontech_files = [f for f in delivered_files_info if f["category"] == "Non-Tech"]
                    
                    if selected_industries:
                        deliv_inds = {f["industry"].lower().replace("-", " ") for f in delivered_files_info}
                        sel_nontech = [i for i in selected_industries if get_industry_category(i) == "Non-Tech"]
                        deliv_nontech = len(nontech_files)
                        if len(sel_nontech) > deliv_nontech:
                            st.info(
                                f"ℹ️ **Selected {len(sel_nontech)} Non-Tech industries — {deliv_nontech} downloaded and delivered to disk so far.** "
                                f"The remaining {len(sel_nontech) - deliv_nontech} industries have not been downloaded yet. "
                                f"To download them, return to **Step 4: Download** and click **Start Download**."
                            )

                    # 2. Multi-File ZIP Downloads Bar
                    if delivered_files_info and os.path.exists(country_delivery_dir):
                        st.markdown("**📦 Bulk Download Complete Folder / Category Archives:**")
                        z_all, c_all = create_country_zip(country_delivery_dir)
                        z_tech, c_tech = create_country_zip(country_delivery_dir, category_filter="Tech")
                        z_nontech, c_nontech = create_country_zip(country_delivery_dir, category_filter="Non-Tech")
                        
                        zb1, zb2, zb3 = st.columns(3)
                        with zb1:
                            if c_all > 0:
                                st.download_button(
                                    label=f"📦 Download Entire Portfolio ({c_all} files .zip)",
                                    data=z_all,
                                    file_name=f"{cl.slugify(country_input)}_{'people' if is_people_mode else 'companies'}_portfolio.zip",
                                    mime="application/zip",
                                    type="primary",
                                    use_container_width=True,
                                    key=f"zip_all_btn_step5_{'ppl' if is_people_mode else 'cmp'}"
                                )
                        with zb2:
                            if c_tech > 0:
                                st.download_button(
                                    label=f"💻 Download Tech ({c_tech} files .zip)",
                                    data=z_tech,
                                    file_name=f"{cl.slugify(country_input)}_tech_{'people' if is_people_mode else 'companies'}.zip",
                                    mime="application/zip",
                                    type="secondary",
                                    use_container_width=True,
                                    key=f"zip_tech_btn_step5_{'ppl' if is_people_mode else 'cmp'}"
                                )
                        with zb3:
                            if c_nontech > 0:
                                st.download_button(
                                    label=f"🏢 Download Non-Tech ({c_nontech} files .zip)",
                                    data=z_nontech,
                                    file_name=f"{cl.slugify(country_input)}_nontech_{'people' if is_people_mode else 'companies'}.zip",
                                    mime="application/zip",
                                    type="secondary",
                                    use_container_width=True,
                                    key=f"zip_nontech_btn_step5_{'ppl' if is_people_mode else 'cmp'}"
                                )
                        st.caption(f"📁 Files on disk are neatly organized inside `{country_delivery_dir}/Tech/` and `{country_delivery_dir}/Non-Tech/`.")
                    
                    # 3. Individual Inspection & Single File Download Section
                    st.markdown("**Individual Dataset Previews & Single Downloads:**")
                    subtab_tech, subtab_nontech, subtab_all = st.tabs([
                        f"💻 Tech Datasets ({len(tech_files)})",
                        f"🏢 Non-Tech Datasets ({len(nontech_files)})",
                        f"📁 All Delivered Files ({len(delivered_files_info)})"
                    ])
                    
                    def render_file_list(file_list, tab_key_prefix):
                        if not file_list:
                            st.info("No files in this category yet.")
                            return
                        for f_info in file_list:
                            fpath = f_info["path"]
                            ind_lbl = f_info["industry"]
                            fn = f_info["filename"]
                            sz = f_info["size_kb"]
                            cat_tag = f"[{f_info['category']}]"
                            
                            with st.expander(f"{cat_tag} {ind_lbl} ({fn} - {sz:.1f} KB)"):
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
                                            label=f"📥 Download CSV: {fn}",
                                            data=raw_csv_data,
                                            file_name=fn,
                                            mime="text/csv; charset=utf-8",
                                            type="primary",
                                            key=f"dl_btn_{tab_key_prefix}_{cl.slugify(fn)}_{'ppl' if is_people_mode else 'cmp'}"
                                        )
                                except Exception as pe:
                                    st.warning(f"Preview error: {pe}")
                                    
                    with subtab_tech:
                        render_file_list(tech_files, "tech")
                    with subtab_nontech:
                        render_file_list(nontech_files, "nontech")
                    with subtab_all:
                        render_file_list(delivered_files_info, "all")
                except Exception as ex:
                    st.warning(f"Unable to display ledger metrics: {ex}")
            elif not btn_download:
                st.caption("Approve the plan in step 4 to start the download.")

        if not step5_open:
            wf_hide("wf_step5")

with tab_geo:
    st.subheader("Country Geographic Division Settings")
    st.caption("When adding a new country, define its major cities, states/provinces and fallback rules so the partitioning engine can split large industries cleanly without code changes.")

    geo_dict = getattr(clay_geo, "GEO", {})

    # Form at a readable width; the freed space shows what is ALREADY configured
    # for the selected country (values this page already loaded but never showed).
    geo_form, geo_side = st.columns([3, 2], gap="large")

    with geo_form:
        _gc, _ = st.columns([1, 1])
        with _gc:
            geo_country = st.selectbox("Select Country to Configure:", ALL_CLAY_COUNTRIES, index=0)

        existing_cfg = geo_dict.get(geo_country, {})

        ex_cities = ", ".join(existing_cfg.get("cities", []))
        ex_states = ", ".join(existing_cfg.get("states", []))
        ex_fallback = existing_cfg.get("fallback", ["size", "revenue"])

        st.markdown(f"#### Configure Geographic Division for {geo_country}")

        input_cities = st.text_area("Major Cities (comma-separated list):", ex_cities, height=110, help="e.g. Madrid, Barcelona, Valencia, Seville, Zaragoza, Malaga")
        input_states = st.text_area("States / Provinces / Regions (optional, comma-separated):", ex_states, height=110, help="e.g. Ontario, Quebec, British Columbia")
        _gf, _gs = st.columns([1, 1], vertical_alignment="bottom")
        with _gf:
            input_fallback = st.selectbox(
                "Fallback Splitting Strategy:",
                [["size", "revenue"], ["revenue", "size"]],
                index=0 if ex_fallback == ["size", "revenue"] else 1,
                format_func=lambda order: "  →  ".join(step.title() for step in order),
            )
        with _gs:
            save_geo = st.button(f"Save configuration for {geo_country}", type="primary", use_container_width=True)

        if save_geo:
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

    with geo_side:
        # clay_geo has two shapes: most countries nest cities under a
        # {state: [cities]} dict, while entries saved from this page use flat
        # top-level "cities" / "states" lists. Count both, or India would
        # read as "0 cities" when it has 54 under its 32 states.
        _cfg_states = existing_cfg.get("states", [])
        _cfg_cities = list(existing_cfg.get("cities", []))
        if isinstance(_cfg_states, dict):
            for _state_cities in _cfg_states.values():
                if isinstance(_state_cities, list):
                    _cfg_cities.extend(_state_cities)
        _cfg_fallback = existing_cfg.get("fallback", ["size", "revenue"])
        _is_configured = geo_country in geo_dict

        with st.container(border=True):
            st.markdown(
                f"<div class='wf-head'>{ic('globe', 18)}"
                f"<div class='wf-title'>Current configuration</div></div>",
                unsafe_allow_html=True,
            )
            if _is_configured:
                st.caption(f"{geo_country} already has a geographic split defined in `clay_geo.py`.")
            else:
                st.caption(f"{geo_country} has no geographic split yet — the planner falls back to keyword, size and revenue slicing.")

            g1, g2 = st.columns(2)
            with g1:
                st.metric("Cities", f"{len(_cfg_cities):,}")
            with g2:
                st.metric("States / regions", f"{len(_cfg_states):,}")

            st.markdown("**Fallback order**")
            st.caption("  →  ".join(step.title() for step in _cfg_fallback))

            if _cfg_cities:
                _preview = ", ".join(_cfg_cities[:8])
                if len(_cfg_cities) > 8:
                    _preview += f" +{len(_cfg_cities) - 8} more"
                st.markdown("**Cities**")
                st.caption(_preview)

        st.caption(
            "The planner recursively splits an oversized industry by state, then city and finer "
            "location filters, then keyword, and finally the fallback order above, until every "
            "slice is under Clay's 5,000-row export cap."
        )

with tab_portfolio:
    st.subheader("Delivered Country Portfolio")
    st.caption("Browse, inspect, and bulk-download delivered dataset portfolios organized by Country and Tech / Non-Tech categories.")
    
    portfolio_choice = st.radio("Select Portfolio View:", ["🏢 Delivered Companies Master Portfolio", "👤 Delivered People Master Portfolio"], horizontal=True)
    delivery_dir = "delivery_people" if "People" in portfolio_choice else "delivery"
    
    if os.path.exists(delivery_dir):
        countries = [d for d in os.listdir(delivery_dir) if os.path.isdir(os.path.join(delivery_dir, d)) and d not in ("Tech", "Non-Tech")]
        if countries:
            st.write(f"Found {len(countries)} completed country folders in `{delivery_dir}/`:")
            
            summary_data = []
            for c in sorted(countries):
                cdir = os.path.join(delivery_dir, c)
                tech_dir = os.path.join(cdir, "Tech")
                nontech_dir = os.path.join(cdir, "Non-Tech")
                
                t_files = [f for f in os.listdir(tech_dir) if f.endswith(".csv")] if os.path.exists(tech_dir) else []
                nt_files = [f for f in os.listdir(nontech_dir) if f.endswith(".csv")] if os.path.exists(nontech_dir) else []
                loose_files = [f for f in os.listdir(cdir) if f.endswith(".csv")]
                
                tot_count = len(t_files) + len(nt_files) + len(loose_files)
                tot_bytes = 0
                for root, _, fs in os.walk(cdir):
                    for f in fs:
                        if f.endswith(".csv"):
                            tot_bytes += os.path.getsize(os.path.join(root, f))
                
                summary_data.append({
                    "Country": c,
                    "Tech Files": len(t_files),
                    "Non-Tech Files": len(nt_files),
                    "Total CSV Files": tot_count,
                    "Total Folder Size": f"{tot_bytes / (1024*1024):.1f} MB",
                    "Folder Path": cdir
                })
                
            st.dataframe(pd.DataFrame(summary_data), use_container_width=True)
            
            selected_country_view = st.selectbox(f"Select a country to view and export portfolio ({portfolio_choice}):", sorted(countries))
            if selected_country_view:
                cpath = os.path.join(delivery_dir, selected_country_view)
                
                # Scan all delivered files inside country folder
                c_all_files = []
                for root, _, fs in os.walk(cpath):
                    for f in fs:
                        if f.endswith(".csv") and os.path.getsize(os.path.join(root, f)) > 0:
                            fp = os.path.join(root, f).replace("\\", "/")
                            norm_cat = "Tech" if "/Tech" in fp or "\\Tech" in fp else ("Non-Tech" if "/Non-Tech" in fp or "\\Non-Tech" in fp else get_industry_category(f))
                            ind_clean = f.split(" [Clay] -")[-1].replace(".csv", "").replace(" (People)", "").replace("-", " ")
                            c_all_files.append({
                                "industry": ind_clean,
                                "category": norm_cat,
                                "path": fp,
                                "filename": f,
                                "size_kb": os.path.getsize(fp) / 1024
                            })
                
                c_tech = [f for f in c_all_files if f["category"] == "Tech"]
                c_nontech = [f for f in c_all_files if f["category"] == "Non-Tech"]
                
                # Bulk ZIP Download Action Bar
                st.markdown(f"#### 📦 Bulk Export / Download Country Portfolio ({selected_country_view})")
                st.caption(f"Download all delivered datasets for **{selected_country_view}** as an organized ZIP archive containing `Tech/` and `Non-Tech/` subfolders:")
                
                z_all, count_all = create_country_zip(cpath)
                z_tech, count_tech = create_country_zip(cpath, category_filter="Tech")
                z_nontech, count_nontech = create_country_zip(cpath, category_filter="Non-Tech")
                
                z_c1, z_c2, z_c3 = st.columns(3)
                with z_c1:
                    if count_all > 0:
                        st.download_button(
                            label=f"📦 Download Entire Portfolio ({count_all} files .zip)",
                            data=z_all,
                            file_name=f"{cl.slugify(selected_country_view)}_{'people' if 'People' in portfolio_choice else 'companies'}_portfolio.zip",
                            mime="application/zip",
                            type="primary",
                            use_container_width=True,
                            key=f"zip_all_port_{selected_country_view}_{'ppl' if 'People' in portfolio_choice else 'cmp'}"
                        )
                with z_c2:
                    if count_tech > 0:
                        st.download_button(
                            label=f"💻 Download Tech ({count_tech} files .zip)",
                            data=z_tech,
                            file_name=f"{cl.slugify(selected_country_view)}_tech_{'people' if 'People' in portfolio_choice else 'companies'}.zip",
                            mime="application/zip",
                            type="secondary",
                            use_container_width=True,
                            key=f"zip_tech_port_{selected_country_view}_{'ppl' if 'People' in portfolio_choice else 'cmp'}"
                        )
                with z_c3:
                    if count_nontech > 0:
                        st.download_button(
                            label=f"🏢 Download Non-Tech ({count_nontech} files .zip)",
                            data=z_nontech,
                            file_name=f"{cl.slugify(selected_country_view)}_nontech_{'people' if 'People' in portfolio_choice else 'companies'}.zip",
                            mime="application/zip",
                            type="secondary",
                            use_container_width=True,
                            key=f"zip_nontech_port_{selected_country_view}_{'ppl' if 'People' in portfolio_choice else 'cmp'}"
                        )
                
                # Category Tabs for Inspection and Single Downloads
                st.markdown(f"**Individual Dataset Previews in `{cpath}`:**")
                port_tab_tech, port_tab_nontech, port_tab_all = st.tabs([
                    f"💻 Tech Datasets ({len(c_tech)})",
                    f"🏢 Non-Tech Datasets ({len(c_nontech)})",
                    f"📁 All Files ({len(c_all_files)})"
                ])
                
                def render_port_file_list(f_list, key_pfx):
                    if not f_list:
                        st.info("No files in this category yet.")
                        return
                    sq = st.text_input(
                        "🔍 Filter by industry name:",
                        placeholder="e.g. Retail, Transportation, Software...",
                        key=f"port_filter_{key_pfx}_{selected_country_view}_{'ppl' if 'People' in portfolio_choice else 'cmp'}"
                    )
                    filtered = [f for f in f_list if not sq.strip() or sq.strip().lower() in f["filename"].lower().replace("-", " ")]
                    if sq.strip():
                        st.caption(f"Showing {len(filtered)} of {len(f_list)} files matching '{sq}':")
                        
                    for f_info in filtered:
                        fp = f_info["path"]
                        ind = f_info["industry"]
                        fn = f_info["filename"]
                        sz = f_info["size_kb"]
                        cat_tag = f"[{f_info['category']}]"
                        
                        with st.expander(f"{cat_tag} {ind} ({fn} - {sz:.1f} KB)"):
                            try:
                                df_prev = pd.read_csv(fp, nrows=20)
                                st.caption(f"Previewing first {len(df_prev)} rows from `{fp}`:")
                                df_prev_disp = df_prev.copy()
                                df_prev_disp.index = range(1, len(df_prev_disp) + 1)
                                st.dataframe(df_prev_disp, use_container_width=True)
                                
                                with open(fp, "rb") as pf_f:
                                    raw_port_data = pf_f.read()
                                    if not raw_port_data.startswith(b"\xef\xbb\xbf"):
                                        raw_port_data = b"\xef\xbb\xbf" + raw_port_data
                                    st.download_button(
                                        label=f"📥 Download CSV: {fn}",
                                        data=raw_port_data,
                                        file_name=fn,
                                        mime="text/csv; charset=utf-8",
                                        type="primary",
                                        key=f"port_dl_{key_pfx}_{cl.slugify(fn)}_{'ppl' if 'People' in portfolio_choice else 'cmp'}"
                                    )
                            except Exception as pfe:
                                st.warning(f"Could not preview file: {pfe}")
                                
                with port_tab_tech:
                    render_port_file_list(c_tech, "port_tech")
                with port_tab_nontech:
                    render_port_file_list(c_nontech, "port_nontech")
                with port_tab_all:
                    render_port_file_list(c_all_files, "port_all")
        else:
            st.info(f"No country folders found in `{delivery_dir}/` yet.")
    else:
        st.info(f"No `{delivery_dir}/` directory created yet.")

with tab_faq:
    st.subheader("Platform FAQ & Teammate Setup Guide")
    
    with st.expander("📖 Step-by-Step: How to Connect Your Clay Cookie (For Teammates)", expanded=True):
        st.markdown("""
        #### 1. Grab Your Cookie (Takes 30 seconds - Only done once!)
        1. Open your regular browser (Chrome, Edge, Brave) where you are **logged into Clay** (`https://app.clay.com`).
        2. Press **`F12`** (or right-click anywhere $\\rightarrow$ **Inspect**) to open Developer Tools.
        3. Click the **Network** tab at the top, then refresh the Clay page (**`F5`**).
        4. In the filter box, type `api.clay.com` or `my-workspaces`.
        5. Click on any request in the list $\\rightarrow$ go to the **Headers** tab on the right $\\rightarrow$ scroll to **Request Headers** $\\rightarrow$ copy the **`cookie:`** text (or right click request $\\rightarrow$ **Copy as cURL**).

        #### 2. Paste into Platform
        1. In this web app, look at the **top right navigation bar** (next to your username).
        2. Click the **`📝 Paste`** button.
        3. Paste what you copied into the box and click **"Save & Verify Cookie"**.
        4. The header status will switch to **`Clay connected`** and you are ready to download!
        """)

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
