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

def _ensure_csv():
    if not os.path.exists(LOG_FILE) or os.path.getsize(LOG_FILE) == 0:
        with open(LOG_FILE, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(LOG_HEADERS)

def log_activity(action, entity="Companies", country="", industries=None, total_rows=0, status="SUCCESS", details="", user_id="team", **kwargs):
    """
    Appends a simple, structured activity log row to logs/activity_log.csv.
    Captures rich operational metrics: rows pulled, net new added, master totals, and duration.
    """
    try:
        _ensure_csv()
        now_local = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Format industries list and count
        if isinstance(industries, list):
            num_ind = len(industries)
            ind_json = json.dumps(industries)
        elif isinstance(industries, str) and industries.strip():
            num_ind = 1
            ind_json = json.dumps([industries.strip()])
        else:
            num_ind = 0
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


def log_count_observation(entity, country, industry, new_count=None, previous_count=None, notes=""):
    """
    Time-series count observation logger to track inventory growth over time.
    Safely records without interrupting live pipeline execution.
    """
    try:
        obs_file = os.path.join(LOG_DIR, "count_history.csv")
        headers = ["Timestamp", "Entity", "Country", "Industry", "Count", "Previous_Count", "Notes"]
        write_header = not os.path.exists(obs_file) or os.path.getsize(obs_file) == 0
        now_ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(obs_file, "a", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            if write_header:
                w.writerow(headers)
            w.writerow([now_ts, str(entity), str(country), str(industry), new_count or 0, previous_count or "", str(notes)])
    except Exception:
        pass

