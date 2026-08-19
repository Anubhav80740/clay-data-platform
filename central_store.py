import csv
import json
import os
import sqlite3
import pandas as pd
from datetime import datetime

DB_PATH = "central_data.db"

def init_db(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS master_companies (
            key TEXT PRIMARY KEY,
            linkedin_url TEXT,
            domain TEXT,
            company_name TEXT,
            country TEXT,
            industry TEXT,
            first_seen_at TEXT,
            last_seen_at TEXT,
            data_json TEXT
        )
    """)
    conn.commit()
    conn.close()

def ingest_and_diff(in_csv, country, industry, db_path=DB_PATH):
    """
    Ingests a CSV file into the central master database.
    Deduplicates against all previous downloads across all users.
    Generates:
      1. Full master dataset CSV
      2. Delta CSV containing ONLY newly discovered companies since last run.
    """
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    if not os.path.exists(in_csv):
        return 0, 0, 0, None, None
        
    df = pd.read_csv(in_csv, dtype=str).fillna("")
    if df.empty:
        return 0, 0, 0, None, None
        
    li_col = "LinkedIn URL" if "LinkedIn URL" in df.columns else None
    dom_col = "Domain" if "Domain" in df.columns else None
    name_col = "Company Name" if "Company Name" in df.columns else (df.columns[0] if len(df.columns) > 0 else None)

    now_str = datetime.now().isoformat()
    
    new_rows = []
    existing_rows = []
    
    for idx, row in df.iterrows():
        lnk = row[li_col].strip().lower() if li_col and row[li_col] else ""
        dom = row[dom_col].strip().lower() if dom_col and row[dom_col] else ""
        comp_name = row[name_col].strip() if name_col and row[name_col] else ""
        
        key = lnk or ("dom:" + dom)
        if not key:
            continue
            
        cur.execute("SELECT first_seen_at FROM master_companies WHERE key = ?", (key,))
        res = cur.fetchone()
        
        row_dict = row.to_dict()
        data_json = json.dumps(row_dict)
        
        if res is None:
            # Brand new company never seen before!
            cur.execute("""
                INSERT INTO master_companies (key, linkedin_url, domain, company_name, country, industry, first_seen_at, last_seen_at, data_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (key, lnk, dom, comp_name, country, industry, now_str, now_str, data_json))
            new_rows.append(row_dict)
        else:
            # Company already exists in master store - update last seen
            cur.execute("""
                UPDATE master_companies SET last_seen_at = ?, data_json = ? WHERE key = ?
            """, (now_str, data_json, key))
            existing_rows.append(row_dict)
            
    conn.commit()
    conn.close()
    
    new_df = pd.DataFrame(new_rows) if new_rows else pd.DataFrame(columns=df.columns)
    
    return len(df), len(new_rows), len(existing_rows), new_df, df

if __name__ == "__main__":
    init_db()
    print("Central master database initialized.")
