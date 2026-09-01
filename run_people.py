#!/usr/bin/env python3
"""
run_people.py -- Batch extraction and incremental merge runner for People data.

Usage: python3 run_people.py <Country> [--only "Industry1|Industry2"] [--min N] [--max N]
Outputs:
- Slice downloads in downloads_people/
- Centralized master files in delivery_people/<Country>/
- Progress ledger in <country_slug>_people_progress.csv
"""
import csv
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time

import clay_lib as cl
import clay_people as cp

SHORT = {"United States": "USA", "United Arab Emirates": "UAE", "United Kingdom": "UK"}
BASE_DIR = "downloads_people"
DELIVERY_DIR = "delivery_people"

def delivery_name(country, industry):
    label = SHORT.get(country, country)
    clean = re.sub(r'[^A-Za-z0-9]+', '-', industry).strip('-')
    return os.path.join(label, f"{label} Data [Clay] -{clean} (People).csv")


def sh(*args):
    print(f"$ {' '.join(args)}", flush=True)
    return subprocess.call([sys.executable, "-u", *args])


def download_people_slices(prefix):
    """Downloads all planned slices for a people industry prefix."""
    plan_path = f"{cl.PLAN_DIR}/clicklist_{prefix}.json"
    if not os.path.exists(plan_path):
        print(f"NO PLAN FOUND: {plan_path}", flush=True)
        return 0
        
    with open(plan_path, "r", encoding="utf-8") as f:
        slices = json.load(f)
        
    os.makedirs(BASE_DIR, exist_ok=True)
    downloaded = 0
    skipped = 0
    
    for i, s in enumerate(slices, 1):
        slug = s["slug"]
        out_csv = os.path.join(BASE_DIR, slug, slug + ".csv")
        
        # Skip if already exists with rows
        if os.path.exists(out_csv) and os.path.getsize(out_csv) > 0:
            try:
                with open(out_csv, newline="", encoding="utf-8", errors="replace") as fh:
                    if sum(1 for _ in csv.reader(fh)) > 1:
                        print(f"   [{i}/{len(slices)}] SKIP (exists): {slug}", flush=True)
                        skipped += 1
                        continue
            except Exception:
                pass
                
        print(f"   [{i}/{len(slices)}] {slug} (~{s.get('count', 0):,} rows)", flush=True)
        tbl, cnt = cp.create_people_table(s["filters"], name=f"People_{slug}", limit=min(5000, s.get("count", 5000) or 5000))
        t_id = tbl.get("tableId")
        v_id = tbl.get("viewId")
        s_id = tbl.get("sourceId")
        
        if not t_id or not v_id:
            print(f"   CREATE FAILED: {tbl}", flush=True)
            continue
            
        try:
            cl.wait_populated(s_id, s.get("count", 0), timeout=90)
            n, path = cl.export_download(t_id, v_id, slug, base_dir=BASE_DIR, poll_timeout=120)
            if n:
                downloaded += 1
        finally:
            cl.delete_table(t_id)
            
    print(f"DONE: {downloaded} downloaded, {skipped} skipped of {len(slices)} slices.", flush=True)
    return downloaded + skipped


def merge_people_slices(prefix):
    """Concatenate all slice CSVs for a prefix."""
    paths = sorted(glob.glob(f"{BASE_DIR}/{prefix}_s*/*.csv"))
    # Exclude _raw.csv
    paths = [p for p in paths if not p.endswith("_raw.csv")]
    out = f"{BASE_DIR}/{prefix}_ALL.csv"
    os.makedirs(BASE_DIR, exist_ok=True)
    
    header = None
    rows = []
    for p in paths:
        with open(p, newline="", encoding="utf-8", errors="replace") as f:
            r = csv.reader(f)
            h = next(r, None)
            if not h:
                continue
            if not header:
                header = h
            rows.extend(list(r))
            
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if header:
            w.writerow(header)
        w.writerows(rows)
        
    print(f"Merged {len(paths)} slice files -> {len(rows):,} total rows -> {out}", flush=True)
    return out


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 run_people.py <Country> [--only \"Industry1|Industry2\"]")
        sys.exit(1)
        
    country = sys.argv[1]
    os.makedirs("data", exist_ok=True)
    c_fn = f"{cl.slugify(country)}_people_counts.csv"
    src = os.path.join("data", c_fn) if os.path.exists(os.path.join("data", c_fn)) else c_fn
    l_fn = f"{cl.slugify(country)}_people_progress.csv"
    ledger = os.path.join("data", l_fn) if (os.path.exists(os.path.join("data", l_fn)) or not os.path.exists(l_fn)) else l_fn
    a = sys.argv[2:]
    only = set(a[a.index("--only") + 1].split("|")) if "--only" in a else None
    
    if not os.path.exists(src):
        if only:
            counts = []
            for ind in sorted(only):
                cnt = cp.count_people({"location_countries_include": [country], "company_industries_include": [ind]})
                counts.append({"Industry": ind, "Count": cnt or 0})
            with open(src, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=["Industry", "Count"])
                w.writeheader()
                w.writerows(counts)
        else:
            sh("count_people.py", country)
        
    with open(src, "r", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r.get("Industry") and str(r.get("Count", "0")).isdigit() and int(r.get("Count", 0)) > 0]
        
    rows.sort(key=lambda r: -int(r["Count"]))
    if only:
        rows = [r for r in rows if r["Industry"] in only]
        
    print(f"{country} (People): {len(rows)} industries selected, ~{sum(int(r['Count']) for r in rows):,} target people", flush=True)
    
    new = not os.path.exists(ledger)
    lf = open(ledger, "a", newline="", encoding="utf-8")
    lw = csv.writer(lf)
    if new:
        lw.writerow(["industry", "clay_count", "rows_downloaded",
                     "unique_people", "coverage_pct", "existing_in_file", "new_added", "file"])
        lf.flush()
        
    for i, r in enumerate(rows, 1):
        ind, expected = r["Industry"], int(r["Count"])
        prefix = cl.slugify(f"{ind}_{country}_people")
        dst = os.path.join(DELIVERY_DIR, delivery_name(country, ind))
        print(f"\n===== [{i}/{len(rows)}] {ind} (People) (~{expected:,}) =====", flush=True)
        
        # 1. Plan if not planned
        plan_path = f"{cl.PLAN_DIR}/clicklist_{prefix}.json"
        if not os.path.exists(plan_path):
            sh("generate_people_clicklist.py", ind, country)
            
        # 2. Download slices
        download_people_slices(prefix)
        
        # 3. Merge slices
        out_all = merge_people_slices(prefix)
        if not os.path.exists(out_all) or os.path.getsize(out_all) == 0:
            print(f"NO OUTPUT FOR {ind}", flush=True)
            continue
            
        # 4. Incremental Merge & Deduplicate
        total_unique, existing_cnt, new_added_cnt = cp.dedupe_people_file(out_all, dst)
        cov = round(100 * total_unique / expected, 1) if expected else 100.0
        
        lw.writerow([ind, expected, total_unique, total_unique, cov, existing_cnt, new_added_cnt, dst])
        lf.flush()
        print(f"DELIVERED PEOPLE DATA: Existing: {existing_cnt:,} | Added: +{new_added_cnt:,} | Total Master Unique: {total_unique:,} -> {dst}", flush=True)
        
    lf.close()
    if only:
        ind_label = ", ".join(sorted(only))
        print(f"\n=== {country} PEOPLE EXTRACTION COMPLETE (Industry: {ind_label}) ===", flush=True)
    else:
        print(f"\n=== {country} PEOPLE DATA EXTRACTION & MERGE COMPLETE ===", flush=True)

if __name__ == "__main__":
    main()
