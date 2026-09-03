"""
clay_logger.py -- Simple, Centralized Activity Logging for Clay Data Platform.

Logs all actions (Count, Plan, Download, Single Download, Cookie Refresh) into:
  logs/activity_log.csv (centralized in git repository)
"""
import os
import csv
import json
import datetime
import pandas as pd

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "activity_log.csv")

os.makedirs(LOG_DIR, exist_ok=True)

LOG_HEADERS = [
    "Timestamp",
    "User",
    "Action",
    "Entity",
    "Country",
    "Num_Industries",
    "Industries_JSON",
    "Total_Rows",
    "Status",
    "Details"
]

POSTHOG_API_KEY = os.environ.get("POSTHOG_API_KEY") or "phc_C9kRXc4cEpL5SrF8yb6kpBdJazYy85WmjNTm4Gh2oi5a"
POSTHOG_HOST = os.environ.get("POSTHOG_HOST") or "https://us.i.posthog.com"

def _send_posthog_event(event_name, uid, properties):
    """Dispatches asynchronous event telemetry directly to PostHog."""
    try:
        import requests
        payload = {
            "api_key": POSTHOG_API_KEY,
            "event": event_name,
            "distinct_id": str(uid or "team_user"),
            "properties": properties
        }
        requests.post(f"{POSTHOG_HOST}/capture/", json=payload, timeout=2.5)
    except Exception:
        pass

def _ensure_csv():
    if not os.path.exists(LOG_FILE) or os.path.getsize(LOG_FILE) == 0:
        with open(LOG_FILE, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(LOG_HEADERS)

def log_activity(action, entity="Companies", country="", industries=None, total_rows=0, status="SUCCESS", details="", user_id="team", **kwargs):
    """
    Appends a simple, structured activity log row and streams telemetry to PostHog.
    Captures rich operational metrics: rows pulled, net new added, master totals, and duration.
    """
    try:
        _ensure_csv()
        now_local = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Format industries list and count
        if isinstance(industries, list):
            num_ind = len(industries)
            ind_json = json.dumps(industries)
            primary_ind = industries[0] if len(industries) == 1 else ""
        elif isinstance(industries, str) and industries.strip():
            num_ind = 1
            primary_ind = industries.strip()
            ind_json = json.dumps([primary_ind])
        else:
            num_ind = 0
            primary_ind = ""
            ind_json = "[]"
            
        row = [
            now_local,
            str(user_id or "team"),
            str(action).upper(),
            str(entity or "Companies"),
            str(country or "-"),
            num_ind,
            ind_json,
            total_rows if total_rows is not None else 0,
            str(status).upper(),
            str(details or "")
        ]
        
        with open(LOG_FILE, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(row)

        # PostHog Telemetry
        ph_event = str(action).lower().strip()
        if "download" in ph_event:
            ph_event = "industry_download_completed" if num_ind == 1 else "download_completed"
        elif "count" in ph_event:
            ph_event = "count_completed"
        elif "plan" in ph_event:
            ph_event = "plan_completed"
        elif "export" in ph_event:
            ph_event = "dataset_exported"

        ph_props = {
            "entity": entity or "Companies",
            "country": country or "Unknown",
            "industry": primary_ind or (industries if isinstance(industries, str) else ""),
            "industries_count": num_ind,
            "total_master_records": total_rows if total_rows is not None else 0,
            "new_records_added": kwargs.get("new_added", kwargs.get("new_records_added", 0)),
            "existing_records": kwargs.get("existing_rows", kwargs.get("existing_records", 0)),
            "rows_downloaded": kwargs.get("rows_pulled", kwargs.get("rows_downloaded", total_rows or 0)),
            "coverage_pct": kwargs.get("coverage_pct", kwargs.get("cov", 0.0)),
            "expected_records": kwargs.get("expected_rows", kwargs.get("expected", 0)),
            "duration_seconds": kwargs.get("duration_seconds", 0),
            "status": str(status).upper(),
            "details": details or "",
            "application": "Clay Data Platform",
            "$host": "clay-data-platform.streamlit.app",
            "$set": {
                "last_active_country": country or "",
                "last_download_time": now_local
            }
        }
        _send_posthog_event(ph_event, str(user_id or "team"), ph_props)
    except Exception as e:
        print(f"[LOGGER ERROR] {e}")

def get_activity_logs(limit=500):
    """
    Returns the activity log as a pandas DataFrame.
    """
    if not os.path.exists(LOG_FILE):
        return pd.DataFrame(columns=LOG_HEADERS)
    try:
        df = pd.read_csv(LOG_FILE, encoding="utf-8-sig")
        return df.tail(limit).iloc[::-1]
    except Exception:
        return pd.DataFrame(columns=LOG_HEADERS)

