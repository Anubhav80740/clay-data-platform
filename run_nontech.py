#!/usr/bin/env python3
"""
Drive plan -> download -> merge -> deliver for every industry with count > 0 in
<Country>_nontech_counts.csv (produced by count_industries.py). Resumable: an
industry whose delivery CSV already exists is skipped.

Largest industry first. Planning (free) for the NEXT industry runs concurrently
with the current industry's download, so the downloader never waits on a plan.
Downloads stay serial -- one Clay session, and parallel exports trip its limits.

Usage: python3 run_nontech.py "Germany" [--min N] [--max N]
  --max 10000   only industries with a Clay count < 10,000  (the easy bulk)
  --min 10000   only industries with a Clay count >= 10,000 (the hard tail)
"""
import csv
import json
import os
import re
import shutil
import subprocess
import sys

import clay_lib as cl

# delivery files use the short name where we already established one
SHORT = {"United States": "USA", "United Arab Emirates": "UAE", "United Kingdom": "UK"}


def get_industry_category(industry):
    try:
        from clay_taxonomy import TECH_INDUSTRIES
        name = str(industry).strip()
        if " [Clay] -" in name:
            name = name.split(" [Clay] -")[-1].replace(".csv", "")
        clean_slug = cl.slugify(name)
        tech_slugs = {cl.slugify(i) for i in TECH_INDUSTRIES}
        if clean_slug in tech_slugs:
            return "Tech"
        for ti in TECH_INDUSTRIES:
            if cl.slugify(ti) == clean_slug or ti.lower() == name.lower():
                return "Tech"
        return "Non-Tech"
    except Exception:
        return "Non-Tech"


def delivery_name(country, industry):
    label = SHORT.get(country, country)
    cat = get_industry_category(industry)
    clean_ind = re.sub(r'[^A-Za-z0-9]+', '-', industry).strip('-')
    return os.path.join(label, cat, f"{label} Data [Clay] -{clean_ind}.csv")


def dedupe_file(in_csv, out_csv):
    seen = set()
    deduped_rows = []
    header = None
    
    # Auto-migrate legacy flat file if present
    legacy_out = out_csv.replace("\\Tech\\", "\\").replace("\\Non-Tech\\", "\\").replace("/Tech/", "/").replace("/Non-Tech/", "/")
    if not os.path.exists(out_csv) and os.path.exists(legacy_out):
        try:
            os.makedirs(os.path.dirname(out_csv), exist_ok=True)
            shutil.move(legacy_out, out_csv)
        except Exception:
            pass

    # 1. Read existing delivered dataset if present (Centralized Data Store)
    if os.path.exists(out_csv) and os.path.getsize(out_csv) > 0:
        with open(out_csv, newline="", encoding="utf-8", errors="replace") as f:
            r = csv.reader(f)
            header = next(r, None)
            if header:
                li = header.index("LinkedIn URL") if "LinkedIn URL" in header else None
                di = header.index("Domain") if "Domain" in header else None
                for row in r:
                    lnk = row[li].strip().lower() if li is not None and li < len(row) else ""
                    dom = row[di].strip().lower() if di is not None and di < len(row) else ""
                    key = lnk or ("dom:" + dom)
                    if key and key not in seen:
                        seen.add(key)
                        deduped_rows.append(row)

    # 2. Merge new pull rows, adding only new unmatched companies
    initial_count = len(deduped_rows)
    with open(in_csv, newline="", encoding="utf-8", errors="replace") as f:
        r = csv.reader(f)
        in_header = next(r, None)
        if in_header:
            if not header:
                header = in_header
            li = in_header.index("LinkedIn URL") if "LinkedIn URL" in in_header else None
            di = in_header.index("Domain") if "Domain" in in_header else None
            for row in r:
                lnk = row[li].strip().lower() if li is not None and li < len(row) else ""
                dom = row[di].strip().lower() if di is not None and di < len(row) else ""
                key = lnk or ("dom:" + dom)
                if key and key in seen:
                    continue
                if key:
                    seen.add(key)
                deduped_rows.append(row)
                
    new_added = len(deduped_rows) - initial_count
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if header:
            w.writerow(header)
        w.writerows(deduped_rows)
        
    print(f"[CENTRALIZED MERGE] Existing in Master: {initial_count:,} | Newly Added: +{new_added:,} | Total Master Unique: {len(deduped_rows):,}", flush=True)
    return len(deduped_rows), initial_count, new_added


def sh(*args):
    print(f"$ {' '.join(args)}", flush=True)
    return subprocess.call([sys.executable, "-u", *args])


def tally(path):
    """(rows, unique companies) -- unique keyed on LinkedIn URL, falling back to
    Domain. Domain-first would collapse distinct entities that share a website
    (university departments, hotel franchises, broker networks)."""
    keys, rows = set(), 0
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        r = csv.reader(f)
        h = next(r, None)
        if not h:
            return 0, 0
        li = h.index("LinkedIn URL") if "LinkedIn URL" in h else None
        di = h.index("Domain") if "Domain" in h else None
        for row in r:
            rows += 1
            lnk = row[li].strip().lower() if li is not None and li < len(row) else ""
            dom = row[di].strip().lower() if di is not None and di < len(row) else ""
            if lnk or dom:
                keys.add(lnk or "dom:" + dom)
    return rows, len(keys)


ALERT_MIN = 95.0            # coverage % below which we shout


def alert(country, stage, industry, pct, detail):
    line = f"!! LOW COVERAGE [{stage}] {industry}: {pct}% -- {detail}"
    print(line, flush=True)
    path = f"alerts_{cl.slugify(country)}.csv"
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["stage", "industry", "coverage_pct", "detail"])
        w.writerow([stage, industry, pct, detail])


def plan_coverage(country, industry, clay_count):
    """Reachable % from the free plan -- known BEFORE any credits are spent.
    Uncovered = cells with blank size AND revenue, which no filter can isolate."""
    unc = f"{cl.PLAN_DIR}/clicklist_{cl.slugify(f'{industry}_{country}')}_uncovered.csv"
    gap = 0
    if os.path.exists(unc):
        with open(unc) as f:
            gap = sum(int(r["count"]) for r in csv.DictReader(f) if r["count"].isdigit())
    return round(100 * (clay_count - gap) / clay_count, 1) if clay_count else 100.0, gap


def missing_slices(prefix):
    """Planned slices with no CSV on disk -- i.e. failed, not yet retried."""
    plan = json.load(open(f"{cl.PLAN_DIR}/clicklist_{prefix}.json"))
    return sum(1 for s in plan
               if not os.path.exists(os.path.join("downloads", cl.slugify(s["slug"]),
                                                  cl.slugify(s["slug"]) + ".csv")))


def planned(country, industry):
    return os.path.exists(f"{cl.PLAN_DIR}/clicklist_{cl.slugify(f'{industry}_{country}')}.json")


def start_plan(country, industry):
    """Kick off the (free) planner in the background. None if already planned."""
    if planned(country, industry):
        return None
    os.makedirs("logs", exist_ok=True)
    log = f"logs/plan_{cl.slugify(f'{industry}_{country}')}.out"
    print(f"   [plan-ahead] {industry} -> {log}", flush=True)
    return subprocess.Popen([sys.executable, "-u", "generate_clicklist.py", industry, country],
                            stdout=open(log, "w"), stderr=subprocess.STDOUT)


def record_ledger_progress(ledger_path, row_data):
    rows = {}
    header = ["industry", "clay_count", "rows_downloaded", "unique_companies", "coverage_pct", "existing_in_file", "new_added", "file"]
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
    country = sys.argv[1]
    user_id = os.environ.get("CLAY_USER_ID", "team")
    if "--user" in sys.argv:
        u_idx = sys.argv.index("--user")
        if u_idx + 1 < len(sys.argv):
            user_id = sys.argv[u_idx + 1]
            os.environ["CLAY_USER_ID"] = user_id
            
    import clay_users
    if not clay_users.get_user_cookie(user_id):
        print(f"❌ [AUTH ERROR] User '{user_id}' has not configured a Clay cookie! Please configure your cookie in the platform navbar before running downloads.", flush=True)
        sys.exit(1)
    
    if country.lower() in ("global", "all supported countries (global)", "all_countries", "all countries"):
        import clay_geo
        supported_countries = list(clay_geo.GEO.keys())
        a = sys.argv[2:]
        only = set(a[a.index("--only") + 1].split("|")) if "--only" in a else None
        print(f"🌍 GLOBAL EXTRACTION: Running sequentially across {len(supported_countries)} countries...", flush=True)
        for c_idx, c_name in enumerate(supported_countries, 1):
            print(f"\n==========================================", flush=True)
            print(f"🌍 [{c_idx}/{len(supported_countries)}] Processing Country: {c_name}", flush=True)
            print(f"==========================================", flush=True)
            cmd = [sys.executable, "run_nontech.py", c_name] + a
            subprocess.call(cmd)
            
        # Centralized Global Union per industry
        os.makedirs("delivery/Global", exist_ok=True)
        if only:
            for ind_target in only:
                g_paths = []
                for c_name in supported_countries:
                    c_file = os.path.join("delivery", c_name, f"{c_name} Data [Clay] -{cl.slugify(ind_target)}.csv")
                    if os.path.exists(c_file):
                        g_paths.append(c_file)
                if g_paths:
                    g_out = os.path.join("delivery", "Global", f"Global Data [Clay] -{cl.slugify(ind_target)}.csv")
                    u_count = cl.union_csvs(g_out, g_paths)
                    print(f"🌍 [GLOBAL MASTER COMPILED] '{ind_target}': {u_count:,} unique companies across {len(g_paths)} countries -> {g_out}", flush=True)
        return

    os.makedirs("data", exist_ok=True)
    c_fn = f"{cl.slugify(country)}_nontech_counts.csv"
    src = os.path.join("data", c_fn) if os.path.exists(os.path.join("data", c_fn)) else c_fn
    l_fn = f"{cl.slugify(country)}_nontech_progress.csv"
    ledger = os.path.join("data", l_fn) if (os.path.exists(os.path.join("data", l_fn)) or not os.path.exists(l_fn)) else l_fn

    rows = []
    zero_ind = set()
    if os.path.exists(src):
        with open(src, "r", encoding="utf-8-sig", errors="replace") as f:
            for r in csv.DictReader(f):
                ind_name = r.get("Industry") or r.get("\ufeffIndustry")
                if not ind_name:
                    continue
                cnt_str = str(r.get("Count", "0")).strip()
                cnt_val = int(cnt_str) if cnt_str.isdigit() else 0
                if cnt_val > 0:
                    rows.append({"Industry": ind_name, "Count": cnt_val})
                else:
                    zero_ind.add(ind_name)
    
    a = sys.argv[2:]
    only = None
    if "--only" in a:
        only = set(a[a.index("--only") + 1].split("|"))
    elif "--only-file" in a:
        of_path = a[a.index("--only-file") + 1]
        if os.path.exists(of_path):
            with open(of_path, "r", encoding="utf-8") as f:
                only = set(json.load(f))

    if only:
        have_ind = {r["Industry"] for r in rows}
        for ind_target in only:
            if not ind_target or ind_target in have_ind or ind_target in zero_ind:
                continue
            pf = f"{cl.PLAN_DIR}/clicklist_{cl.slugify(f'{ind_target}_{country}')}.json"
            c_val = None
            if os.path.exists(pf):
                try:
                    p_slices = json.load(open(pf, encoding="utf-8"))
                    c_val = sum(int(s.get("count", 0)) for s in p_slices)
                except Exception:
                    pass
            if not c_val:
                print(f"   [counting] '{ind_target}' not found in count cache, checking Clay...", flush=True)
                c_val = cl.count({"industries": [ind_target], "country_names": [country]})
            if c_val and c_val > 0:
                rows.append({"Industry": ind_target, "Count": c_val})
                have_ind.add(ind_target)
            else:
                zero_ind.add(ind_target)

        # Pre-record any zero-count industries into ledger so they are marked completed
        for z_ind in only:
            if z_ind in zero_ind:
                dst_zero = os.path.join("delivery", delivery_name(country, z_ind))
                record_ledger_progress(ledger, [z_ind, 0, 0, 0, 100.0, 0, 0, dst_zero])

    lo = int(a[a.index("--min") + 1]) if "--min" in a else 0
    hi = int(a[a.index("--max") + 1]) if "--max" in a else 10 ** 12
    # --shard i/n : run n of these side by side, each taking every n-th industry.
    si, sn = (int(x) for x in a[a.index("--shard") + 1].split("/")) if "--shard" in a else (0, 1)

    force_rerun = "--force" in a or "--only" in a
    rows.sort(key=lambda r: -int(r["Count"]))                # largest first

    def file_delivered(ind):
        p_new = os.path.join("delivery", delivery_name(country, ind))
        label = SHORT.get(country, country)
        clean_ind = re.sub(r'[^A-Za-z0-9]+', '-', ind).strip('-')
        p_old = os.path.join("delivery", label, f"{label} Data [Clay] -{clean_ind}.csv")
        return os.path.exists(p_new) or os.path.exists(p_old)

    rows = [r for r in rows if lo <= int(r["Count"]) < hi
            and (only is None or r["Industry"] in only)
            and (force_rerun or not file_delivered(r["Industry"]))]
    rows = rows[si::sn]
    print(f"{country}: {len(rows)} industries selected in [{lo:,}, {hi:,}), "
          f"~{sum(int(r['Count']) for r in rows):,} target rows", flush=True)

    for i, r in enumerate(rows, 1):
        ind, expected = r["Industry"], int(r["Count"])
        prefix = cl.slugify(f"{ind}_{country}")
        dst = os.path.join("delivery", delivery_name(country, ind))
        print(f"\n===== [{i}/{len(rows)}] {ind}  (~{expected:,}) =====", flush=True)

        if expected <= 0:
            print(f"   [skip 0-record] '{ind}' has 0 matching records in {country}. Skipping download.", flush=True)
            record_ledger_progress(ledger, [ind, 0, 0, 0, 100.0, 0, 0, dst])
            continue

        if not planned(country, ind):
            print(f"   [planning] Calculating plan for {ind}...", flush=True)
            if sh("generate_clicklist.py", ind, country) != 0:
                print(f"PLAN FAILED: {ind}", flush=True)
                continue
        # A transient count() failure aborts a branch and can yield an EMPTY plan
        # that still reports 100% coverage. Delivering it writes a 0-row file, and
        # the resume check would then skip this industry forever. Bin it and retry.
        pf = f"{cl.PLAN_DIR}/clicklist_{prefix}.json"
        if not os.path.exists(pf) or not json.load(open(pf, encoding="utf-8")):
            if os.path.exists(pf):
                os.remove(pf)
            print(f"EMPTY PLAN (counts failed) -- discarded, will re-plan: {ind}", flush=True)
            continue

        pcov, gap = plan_coverage(country, ind, expected)
        if pcov < ALERT_MIN:
            alert(country, "plan", ind, pcov,
                  f"{gap:,} of {expected:,} unreachable (blank size+revenue)")

        # A slice lost to CREATE FAILED (Clay throttling the preview call) writes no
        # CSV, so it retries on the next download pass -- but delivering marks the
        # industry done and it never gets one. Retry here, before that happens.
        import time
        for attempt in range(3):
            sh("clay_pipeline.py", "download", prefix)
            missing = missing_slices(prefix)
            if not missing:
                break
            print(f"   {missing} slice(s) still missing -- retry pass {attempt + 2} in 5s...", flush=True)
            time.sleep(5)
        if missing:
            alert(country, "incomplete", ind, "",
                  f"{missing} of {len(json.load(open(pf, encoding='utf-8')))} slices never downloaded")
        sh("clay_pipeline.py", "merge", prefix)

        out = f"downloads/{prefix}_ALL.csv"
        if not os.path.exists(out):
            print(f"NO OUTPUT: {ind}", flush=True); continue
        rows_dl, uniq = tally(out)
        # Never write a delivery that's obviously broken -- the resume check reads
        # "file exists" as done, so a bad file sticks forever. Genuine partial
        # coverage (Construction ~75%) is fine; <10% of Clay's count is not.
        if rows_dl < max(1, 0.1 * expected):
            print(f"BROKEN PULL ({rows_dl:,} rows vs {expected:,} on Clay) -- "
                  f"not delivering, will retry: {ind}", flush=True)
            continue
        cov = round(100 * uniq / expected, 1) if expected else ""
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        total_unique, existing_cnt, new_added_cnt = dedupe_file(out, dst)
        
        # Cloud Storage Auto-Sync
        try:
            import cloud_storage
            ok, cloud_msg = cloud_storage.upload_file_to_cloud(dst)
            if ok and "http" in cloud_msg:
                print(f"CLOUD UPLOAD SUCCESS: {cloud_msg}", flush=True)
        except Exception:
            pass

        record_ledger_progress(ledger, [ind, expected, rows_dl, total_unique, cov, existing_cnt, new_added_cnt, dst])
        print(f"DELIVERED {rows_dl:,} rows | Existing: {existing_cnt:,} | Added: +{new_added_cnt:,} | Total Master: {total_unique:,} -> {dst}", flush=True)
        try:
            import clay_logger
            clay_logger.log_activity(
                action="DOWNLOAD",
                entity="Companies",
                country=country,
                industries=[ind],
                total_rows=total_unique,
                new_added=new_added_cnt,
                existing_rows=existing_cnt,
                rows_pulled=rows_dl,
                coverage_pct=float(cov) if cov != "" else 0.0,
                expected_rows=expected,
                status="SUCCESS",
                details=f"Delivered {rows_dl:,} rows, +{new_added_cnt:,} new added ({cov}% coverage)",
                user_id=user_id
            )
        except Exception:
            pass
        if cov != "" and cov < ALERT_MIN:
            alert(country, "downloaded", ind, cov,
                  f"{uniq:,} unique of {expected:,} on Clay")

    if only:
        ind_label = ", ".join(sorted(only))
        print(f"\n=== {country} EXTRACTION COMPLETE (Industry: {ind_label}) ===", flush=True)
    else:
        print(f"\n=== {country} DATA EXTRACTION & MERGE COMPLETE ===", flush=True)


if __name__ == "__main__":
    main()
