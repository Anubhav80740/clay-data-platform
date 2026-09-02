"""
clay_logger.py -- Unified Activity Audit Logging and Clay Count Drift Analytics.

Tracks:
1. Activity Audit Log (logs/activity_audit_log.csv): All user actions, downloads, plans, logins, and operations.
2. Clay Count History Log (logs/clay_count_history.csv): Historical time-series tracking of count changes and volatility.
"""
import os
import csv
import json
import datetime
import pandas as pd

LOG_DIR = "logs"
ACTIVITY_LOG_FILE = os.path.join(LOG_DIR, "activity_audit_log.csv")
COUNT_HISTORY_FILE = os.path.join(LOG_DIR, "clay_count_history.csv")

os.makedirs(LOG_DIR, exist_ok=True)

ACTIVITY_HEADERS = [
    "Timestamp",
    "Timestamp_UTC",
    "User_ID",
    "Action",
    "Entity",
    "Country",
    "Industry",
    "Status",
    "Details"
]

COUNT_HISTORY_HEADERS = [
    "Timestamp",
    "Timestamp_UTC",
    "User_ID",
    "Entity",
    "Country",
    "Industry",
    "New_Count",
    "Previous_Count",
    "Delta",
    "Delta_Pct",
    "Notes"
]

def _ensure_csv(filepath, headers):
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(headers)

def log_activity(action, entity="Companies", country="", industry="", status="SUCCESS", details="", user_id="system"):
    try:
        _ensure_csv(ACTIVITY_LOG_FILE, ACTIVITY_HEADERS)
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        now_local = datetime.datetime.now()
        ts_local = now_local.strftime("%Y-%m-%d %H:%M:%S")
        ts_utc = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        details_str = json.dumps(details) if isinstance(details, (dict, list)) else str(details)
        
        row = [
            ts_local,
            ts_utc,
            str(user_id or "system"),
            str(action).upper(),
            str(entity or "Companies"),
            str(country or "-"),
            str(industry or "-"),
            str(status).upper(),
            details_str
        ]
        
        with open(ACTIVITY_LOG_FILE, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(row)
    except Exception as e:
        print(f"[LOGGER ERROR] {e}")

def log_count_observation(entity, country, industry, new_count, previous_count=None, user_id="system", notes=""):
    try:
        _ensure_csv(COUNT_HISTORY_FILE, COUNT_HISTORY_HEADERS)
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        now_local = datetime.datetime.now()
        ts_local = now_local.strftime("%Y-%m-%d %H:%M:%S")
        ts_utc = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        ncnt = int(new_count) if new_count is not None and str(new_count).isdigit() else 0
        pcnt = int(previous_count) if previous_count is not None and str(previous_count).isdigit() else None
        
        if pcnt is not None:
            delta = ncnt - pcnt
            if pcnt > 0:
                pct = round((delta / pcnt) * 100, 2)
                delta_pct = ("+" if pct > 0 else "") + str(pct) + "%"
            elif ncnt > 0:
                delta_pct = "+100%"
            else:
                delta_pct = "0.0%"
        else:
            delta = 0
            delta_pct = "BASELINE"
            
        row = [
            ts_local,
            ts_utc,
            str(user_id or "system"),
            str(entity or "Companies"),
            str(country or "Unknown"),
            str(industry or "Unknown"),
            ncnt,
            "" if pcnt is None else pcnt,
            delta,
            delta_pct,
            str(notes or "")
        ]
        
        with open(COUNT_HISTORY_FILE, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(row)
    except Exception as e:
        print(f"[LOGGER ERROR] {e}")

def get_activity_logs(limit=500):
    if not os.path.exists(ACTIVITY_LOG_FILE):
        return pd.DataFrame(columns=ACTIVITY_HEADERS)
    try:
        df = pd.read_csv(ACTIVITY_LOG_FILE, encoding="utf-8-sig")
        return df.tail(limit).iloc[::-1]
    except Exception:
        return pd.DataFrame(columns=ACTIVITY_HEADERS)

def get_count_history_logs(country=None, entity=None, limit=1000):
    if not os.path.exists(COUNT_HISTORY_FILE):
        return pd.DataFrame(columns=COUNT_HISTORY_HEADERS)
    try:
        df = pd.read_csv(COUNT_HISTORY_FILE, encoding="utf-8-sig")
        if country and country != "All":
            df = df[df["Country"] == country]
        if entity and entity != "All":
            df = df[df["Entity"] == entity]
        return df.tail(limit).iloc[::-1]
    except Exception:
        return pd.DataFrame(columns=COUNT_HISTORY_HEADERS)

def get_count_drift_summary(country=None, entity=None):
    if not os.path.exists(COUNT_HISTORY_FILE):
        return pd.DataFrame()
    try:
        df = pd.read_csv(COUNT_HISTORY_FILE, encoding="utf-8-sig")
        if country and country != "All":
            df = df[df["Country"] == country]
        if entity and entity != "All":
            df = df[df["Entity"] == entity]
        if df.empty:
            return pd.DataFrame()
            
        summary_rows = []
        for (ctry, ent, ind), grp in df.groupby(["Country", "Entity", "Industry"]):
            grp_sorted = grp.sort_values(by="Timestamp_UTC")
            first_count = int(grp_sorted.iloc[0]["New_Count"])
            latest_count = int(grp_sorted.iloc[-1]["New_Count"])
            total_observations = len(grp_sorted)
            latest_time = grp_sorted.iloc[-1]["Timestamp"]
            
            delta = latest_count - first_count
            if first_count > 0:
                pct = round((delta / first_count) * 100, 2)
                pct_str = ("+" if pct > 0 else "") + str(pct) + "%"
            elif latest_count > 0:
                pct_str = "+100%"
            else:
                pct_str = "0.0%"
                
            summary_rows.append({
                "Country": ctry,
                "Entity": ent,
                "Industry": ind,
                "Latest Count": f"{latest_count:,}",
                "First Count": f"{first_count:,}",
                "Net Drift (Rows)": f"{'+' if delta > 0 else ''}{delta:,}",
                "Drift %": pct_str,
                "Observations": total_observations,
                "Last Updated": latest_time,
                "delta_num": delta
            })
            
        res = pd.DataFrame(summary_rows)
        if not res.empty:
            res = res.sort_values(by="delta_num", ascending=False)
        return res
    except Exception as e:
        print(f"[LOGGER ERROR] {e}")
        return pd.DataFrame()
