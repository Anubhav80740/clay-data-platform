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
            
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if header:
            w.writerow(header)
        w.writerows(rows)
        
    print(f"Merged {len(paths)} slice files -> {len(rows):,} total rows -> {out}", flush=True)
    return out


def record_ledger_progress(ledger_path, row_data):
    rows = {}
    header = ["industry", "clay_count", "rows_downloaded", "unique_people", "coverage_pct", "existing_in_file", "new_added", "file"]
    if os.path.exists(ledger_path):
        with open(ledger_path, "r", encoding="utf-8", errors="replace") as f:
            r = csv.reader(f)
            h = next(r, None)
            for line in r:
                if line and len(line) >= 1 and line[0].strip():
                    rows[line[0].strip()] = line
    rows[row_data[0].strip()] = row_data
    os.makedirs(os.path.dirname(ledger_path) or ".", exist_ok=True)
    with open(ledger_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        for k, v in rows.items():
            w.writerow(v)

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 run_people.py <Country> [--only \"Industry1|Industry2\"]")
        sys.exit(1)
        
    country = sys.argv[1]
    
    if country.lower() in ("global", "all supported countries (global)", "all_countries", "all countries"):
        import clay_geo
        supported_countries = list(clay_geo.GEO.keys())
        a = sys.argv[2:]
        only = set(a[a.index("--only") + 1].split("|")) if "--only" in a else None
        print(f"🌍 GLOBAL PEOPLE EXTRACTION: Running sequentially across {len(supported_countries)} countries...", flush=True)
        for c_idx, c_name in enumerate(supported_countries, 1):
            print(f"\n==========================================", flush=True)
            print(f"🌍 [{c_idx}/{len(supported_countries)}] Processing Country (People): {c_name}", flush=True)
            print(f"==========================================", flush=True)
            cmd = [sys.executable, "run_people.py", c_name] + a
            subprocess.call(cmd)
            
        # Centralized Global People Union per industry
        os.makedirs("delivery_people/Global", exist_ok=True)
        if only:
            for ind_target in only:
                g_paths = []
                for c_name in supported_countries:
                    c_file = os.path.join("delivery_people", c_name, f"{c_name} People [Clay] -{cl.slugify(ind_target)}.csv")
                    if os.path.exists(c_file):
                        g_paths.append(c_file)
                if g_paths:
                    g_out = os.path.join("delivery_people", "Global", f"Global People [Clay] -{cl.slugify(ind_target)}.csv")
                    u_count = cp.merge_people_into_master(g_paths[0], g_out) if len(g_paths) == 1 else cp.union_people_csvs(g_out, g_paths)
                    print(f"🌍 [GLOBAL PEOPLE MASTER COMPILED] '{ind_target}': {u_count:,} unique people across {len(g_paths)} countries -> {g_out}", flush=True)
        return

    os.makedirs("data", exist_ok=True)
    c_fn = f"{cl.slugify(country)}_people_counts.csv"
    src = os.path.join("data", c_fn) if os.path.exists(os.path.join("data", c_fn)) else c_fn
    l_fn = f"{cl.slugify(country)}_people_progress.csv"
    ledger = os.path.join("data", l_fn) if (os.path.exists(os.path.join("data", l_fn)) or not os.path.exists(l_fn)) else l_fn
    a = sys.argv[2:]
    only = set(a[a.index("--only") + 1].split("|")) if "--only" in a else None
    
    rows = []
    if os.path.exists(src):
        with open(src, "r", encoding="utf-8") as f:
            rows = [r for r in csv.DictReader(f) if r.get("Industry") and str(r.get("Count", "0")).isdigit() and int(r.get("Count", 0)) > 0]

    if only:
        have_ind = {r["Industry"] for r in rows}
        for ind_target in only:
            if ind_target and ind_target not in have_ind:
                pf = f"{cp.PEOPLE_PLAN_DIR}/clicklist_{cl.slugify(f'{ind_target}_{country}_people')}.json"
                c_val = None
                if os.path.exists(pf):
                    try:
                        p_slices = json.load(open(pf))
                        c_val = sum(int(s.get("count", 0)) for s in p_slices)
                    except Exception:
                        pass
                if not c_val:
                    c_val = cp.count_people({"location_countries_include": [country], "company_industries_include": [ind_target]})
                if c_val and c_val > 0:
                    rows.append({"Industry": ind_target, "Count": c_val})
                    have_ind.add(ind_target)
        
    rows.sort(key=lambda r: -int(r["Count"]))
    if only:
        rows = [r for r in rows if r["Industry"] in only]
        
    print(f"{country} (People): {len(rows)} industries selected, ~{sum(int(r['Count']) for r in rows):,} target people", flush=True)
        
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
        
        record_ledger_progress(ledger, [ind, expected, total_unique, total_unique, cov, existing_cnt, new_added_cnt, dst])
        print(f"DELIVERED PEOPLE DATA: Existing: {existing_cnt:,} | Added: +{new_added_cnt:,} | Total Master Unique: {total_unique:,} -> {dst}", flush=True)
        
    if only:
        ind_label = ", ".join(sorted(only))
        print(f"\n=== {country} PEOPLE EXTRACTION COMPLETE (Industry: {ind_label}) ===", flush=True)
    else:
        print(f"\n=== {country} PEOPLE DATA EXTRACTION & MERGE COMPLETE ===", flush=True)

if __name__ == "__main__":
    main()
