import csv
import glob
import json
import os
import re
import subprocess
import sys
import pandas as pd
import streamlit as st

# Safe numeric handlers
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
import central_store

st.set_page_config(
    page_title="Clay Data Platform",
    layout="wide"
)

# ----------------------------------------------------
# SINGLE SHARED TEAM LOGIN AUTHENTICATION
# ----------------------------------------------------
TEAM_PASSWORD = os.getenv("CLAY_TEAM_PASSWORD", "clayteam2026")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("Clay Data Platform — Team Access")
    st.caption("Enter your shared team password to access the platform.")
    
    auth_col1, auth_col2 = st.columns([2, 1])
    with auth_col1:
        pwd_input = st.text_input("Team Access Key", type="password")
        btn_login = st.button("Access Platform", type="primary")
        
        if btn_login:
            if pwd_input == TEAM_PASSWORD:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Invalid team access key.")
    st.stop()

# ----------------------------------------------------
# MAIN PLATFORM INTERFACE (CLEAN & MINIMAL)
# ----------------------------------------------------
top_c1, top_c2 = st.columns([4, 1])
with top_c1:
    st.title("Clay Data Extraction & Centralization Platform")
    st.caption("Internal Data Downloader & Central Master Repository")

with top_c2:
    if st.button("Logout", use_container_width=True):
        st.session_state["authenticated"] = False
        st.rerun()

tab_download, tab_geo, tab_portfolio, tab_central, tab_faq = st.tabs([
    "Data Download & Pipeline",
    "Geographic Division Settings",
    "Delivered Datasets",
    "Central Master Database",
    "Documentation & Workflow"
])

with tab_download:
    st.subheader("1. Target Country & Industries Selection")
    
    col_c, col_i = st.columns([1, 2])
    
    with col_c:
        st.markdown("**Country Selection**")
        def_idx = ALL_CLAY_COUNTRIES.index("Spain") if "Spain" in ALL_CLAY_COUNTRIES else 0
        country_select = st.selectbox(
            "Select Country (218 Available):",
            options=ALL_CLAY_COUNTRIES,
            index=def_idx
        )
        
        custom_country_toggle = st.checkbox("Enter custom country name manually")
        if custom_country_toggle:
            country_input = st.text_input("Manual Country Name", country_select)
        else:
            country_input = country_select
            
        country_input = country_input.strip()
        
        # Check Geo Division Status for selected country
        geo_dict = getattr(clay_geo, "GEO", {})
        has_geo = country_input in geo_dict
        if has_geo:
            g_cfg = geo_dict[country_input]
            num_cities = len(g_cfg.get("cities", []))
            num_states = len(g_cfg.get("states", []))
            st.info(f"Geographic Division: Active for {country_input} ({num_cities} Cities, {num_states} States/Regions).")
        else:
            st.warning(f"{country_input} has no custom city list defined. Default size/revenue fallbacks will be used.")

    with col_i:
        st.markdown("**Industry Selection**")
        
        if "selected_industries" not in st.session_state:
            st.session_state["selected_industries"] = []

        b_col1, b_col2, b_col3, b_col4 = st.columns(4)
        
        with b_col1:
            if st.button("Select Tech Industries", use_container_width=True):
                st.session_state["selected_industries"] = TECH_INDUSTRIES
                
        with b_col2:
            if st.button("Select Non-Tech Industries", use_container_width=True):
                st.session_state["selected_industries"] = NON_TECH_INDUSTRIES
                
        with b_col3:
            if st.button("Select All 458 Industries", use_container_width=True):
                st.session_state["selected_industries"] = ALL_CLAY_INDUSTRIES
                
        with b_col4:
            if st.button("Clear Selection", use_container_width=True):
                st.session_state["selected_industries"] = []

        selected_industries = st.multiselect(
            "Search and select industries (no default selected):",
            options=ALL_CLAY_INDUSTRIES,
            key="selected_industries"
        )
        
        st.caption(f"Currently Selected: {len(selected_industries)} industries selected out of 458 total.")

    st.divider()
    st.subheader("2. Action Pipeline Execution")
    
    def slugify(text):
        return re.sub(r'[^a-zA-Z0-9]+', '_', text).strip('_')

    country_slug = slugify(country_input) if country_input else ""
    counts_file = f"{country_slug}_nontech_counts.csv"
    ledger_file = f"{country_slug}_nontech_progress.csv"
    ind_file = "selected_industries.json"

    step_col1, step_col2, step_col3 = st.columns([1, 1, 1])

    # ----------------------------------------------------
    # STEP 1: COUNT
    # ----------------------------------------------------
    with step_col1:
        st.markdown("#### Step 1: Count Target Rows")
        st.caption("Queries Clay for raw target counts.")
        btn_count = st.button("Run Step 1: Count", use_container_width=True)

    # ----------------------------------------------------
    # STEP 2: PLAN & ESTIMATE
    # ----------------------------------------------------
    with step_col2:
        st.markdown("#### Step 2: Plan & Estimate Coverage")
        st.caption("Estimates reachable unique companies & slice partitions.")
        btn_plan = st.button("Run Step 2: Generate Plan", use_container_width=True)

    # ----------------------------------------------------
    # STEP 3: DOWNLOAD & DELIVER
    # ----------------------------------------------------
    with step_col3:
        st.markdown("#### Step 3: Download Data")
        st.caption("Executes download, deduplication & central ingestion.")
        plan_approved = st.checkbox("I approve the plan & estimated coverage", key="plan_approved_check")
        btn_download = st.button("Run Step 3: Download Data", type="primary", use_container_width=True, disabled=not plan_approved)

    # ----------------------------------------------------
    # REAL-TIME PROGRESS BARS & EXECUTION LOGIC
    # ----------------------------------------------------
    if btn_count:
        if not country_input:
            st.error("Please select a country.")
        elif not selected_industries:
            st.error("Please select at least one industry.")
        else:
            with open(ind_file, "w", encoding="utf-8") as f:
                json.dump(selected_industries, f)
            if os.path.exists(counts_file):
                os.remove(counts_file)
                
            st.markdown(f"**Step 1 Counting Progress for {country_input}**")
            count_progress_bar = st.progress(0)
            count_status_text = st.empty()
            count_log_box = st.empty()
            
            cmd = [sys.executable, "-u", "count_industries.py", country_input, "--industries-file", ind_file]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            
            c_logs = []
            while True:
                line = proc.stdout.readline()
                if not line and proc.poll() is not None:
                    break
                if line:
                    line_str = line.strip()
                    c_logs.append(line_str)
                    count_log_box.code("\n".join(c_logs[-10:]))
                    
                    if line_str.startswith("PROGRESS:count:"):
                        parts = line_str.split(":")
                        if len(parts) >= 6:
                            curr_i = safe_int(parts[2])
                            tot_i = safe_int(parts[3])
                            ind_name = parts[4]
                            cnt_val = parts[5]
                            pct = min(1.0, curr_i / max(1, tot_i))
                            count_progress_bar.progress(pct)
                            count_status_text.markdown(f"**Counting Progress**: Industry {curr_i} of {tot_i} ({int(pct*100)}%) — *{ind_name}*: {cnt_val} rows")
                            
            proc.wait()
            if proc.returncode == 0:
                count_progress_bar.progress(1.0)
                st.success("Count Step Complete!")
            else:
                st.error("Count step failed. See log above.")

    if btn_plan:
        if not country_input:
            st.error("Please select a country.")
        elif not selected_industries:
            st.error("Please select at least one industry.")
        else:
            with open(ind_file, "w", encoding="utf-8") as f:
                json.dump(selected_industries, f)
                
            st.markdown(f"**Step 2 Planning Progress for {country_input}**")
            plan_progress_bar = st.progress(0)
            plan_status_text = st.empty()
            plan_log_box = st.empty()
            
            tot_p = len(selected_industries)
            for idx_p, ind in enumerate(selected_industries, 1):
                pct = min(1.0, idx_p / max(1, tot_p))
                plan_progress_bar.progress(pct)
                plan_status_text.markdown(f"**Planning Progress**: Industry {idx_p} of {tot_p} ({int(pct*100)}%) — *{ind}*")
                
                cmd = [sys.executable, "-u", "generate_clicklist.py", ind, country_input]
                res_p = subprocess.run(cmd, capture_output=True, text=True)
                plan_log_box.code(res_p.stdout[-500:])
                
            plan_progress_bar.progress(1.0)
            st.success("Planning Step Complete! Review estimated coverage below.")

    if btn_download:
        if not plan_approved:
            st.warning("Please check the approval box in Step 3 to confirm plan approval before downloading.")
        else:
            st.markdown(f"### Executing Live Download Pipeline for `{country_input}`...")
            
            with open(ind_file, "w", encoding="utf-8") as f:
                json.dump(selected_industries, f)

            dl_progress_bar = st.progress(0)
            dl_status_text = st.empty()
            dl_log_box = st.empty()
            
            cmd_run = [sys.executable, "-u", "run_nontech.py", country_input]
            only_str = "|".join(selected_industries)
            cmd_run.extend(["--only", only_str])

            process = subprocess.Popen(cmd_run, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            
            logs = []
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    line_str = line.strip()
                    logs.append(line_str)
                    dl_log_box.code("\n".join(logs[-15:]))
                    
                    if line_str.startswith("PROGRESS:download:"):
                        parts = line_str.split(":")
                        if len(parts) >= 7:
                            curr_d = safe_int(parts[2])
                            tot_d = safe_int(parts[3])
                            ind_d = parts[4]
                            rows_d = parts[5]
                            uniq_d = parts[6]
                            pct_d = min(1.0, curr_d / max(1, tot_d))
                            dl_progress_bar.progress(pct_d)
                            dl_status_text.markdown(f"**Download Progress**: Industry {curr_d} of {tot_d} ({int(pct_d*100)}%) — *{ind_d}*: {rows_d} rows pulled ({uniq_d} unique)")
                            
            process.wait()
            if process.returncode == 0:
                dl_progress_bar.progress(1.0)
                st.success(f"Step 3 Download complete for {country_input}!")
            else:
                st.error("Download finished with errors. See log above.")

    # ----------------------------------------------------
    # DISPLAY TABLES & METRICS
    # ----------------------------------------------------
    if os.path.exists(counts_file):
        st.markdown(f"### Step 1 Count Results (`{country_input}`)")
        cdf = pd.read_csv(counts_file)
        if selected_industries:
            cdf = cdf[cdf["Industry"].isin(selected_industries)]
        st.dataframe(cdf, use_container_width=True)
        tot_c = safe_sum(cdf["Count"]) if "Count" in cdf.columns and not cdf.empty else 0
        st.info(f"Total Clay Target Rows: {tot_c:,} rows across {len(cdf)} selected industries.")

    # Check for plan files
    planned_data = []
    for ind in selected_industries:
        prefix = slugify(f"{ind}_{country_input}")
        pj = f"plans/clicklist_{prefix}.json"
        if os.path.exists(pj):
            try:
                p_slices = json.load(open(pj))
                num_slices = len(p_slices)
                unc_csv = f"plans/clicklist_{prefix}_uncovered.csv"
                gap = 0
                if os.path.exists(unc_csv):
                    with open(unc_csv) as uf:
                        gap = sum(safe_int(r.get("count")) for r in csv.DictReader(uf))
                exp = 0
                if os.path.exists(counts_file):
                    cdf = pd.read_csv(counts_file)
                    row_c = cdf[cdf["Industry"] == ind]
                    if not row_c.empty:
                        exp = safe_int(row_c.iloc[0]["Count"])
                reachable = max(0, exp - gap) if exp else sum(safe_int(s.get("count")) for s in p_slices)
                cov_pct = round(100 * reachable / exp, 1) if exp else 100.0
                planned_data.append({
                    "Industry": ind,
                    "Clay Target Count": exp,
                    "Estimated Reachable": reachable,
                    "Unreachable Gap (blank sz+rev)": gap,
                    "Est. Coverage %": f"{cov_pct}%",
                    "Planned Slices": num_slices
                })
            except Exception:
                pass

    if planned_data:
        st.markdown(f"### Step 2 Plan & Coverage Estimate Results (`{country_input}`)")
        pdf_plan = pd.DataFrame(planned_data)
        st.dataframe(pdf_plan, use_container_width=True)
        tot_reach = sum(r["Estimated Reachable"] for r in planned_data)
        tot_target = sum(r["Clay Target Count"] for r in planned_data)
        overall_cov = round(100 * tot_reach / max(1, tot_target), 1)
        st.success(f"Plan Summary: Estimated Reachable Unique Companies: {tot_reach:,} / {tot_target:,} ({overall_cov}% Estimated Coverage). Check the approval box in Step 3 above to proceed to download.")

    if os.path.exists(ledger_file):
        st.markdown(f"### Delivered Files & Metrics for `{country_input}`")
        ledger_df = pd.read_csv(ledger_file)
        if selected_industries:
            ledger_df = ledger_df[ledger_df["industry"].isin(selected_industries)]
        st.dataframe(ledger_df, use_container_width=True)
        delivered_total = safe_sum(ledger_df["unique_companies"]) if "unique_companies" in ledger_df.columns and not ledger_df.empty else 0
        st.success(f"Total Unique Companies Delivered: {delivered_total:,} Unique Companies")

with tab_geo:
    st.subheader("Country Geographic Division Settings")
    st.write("When adding a new country, you can define its major cities, states/provinces, and fallback rules here so the partitioning engine splits large industries cleanly without code intervention.")
    
    geo_country = st.selectbox("Select Country to Configure:", ALL_CLAY_COUNTRIES, index=def_idx)
    
    geo_dict = getattr(clay_geo, "GEO", {})
    existing_cfg = geo_dict.get(geo_country, {})
    
    ex_cities = ", ".join(existing_cfg.get("cities", []))
    ex_states = ", ".join(existing_cfg.get("states", []))
    ex_fallback = existing_cfg.get("fallback", ["size", "revenue"])
    
    st.markdown(f"#### Configure Geographic Division for `{geo_country}`")
    
    input_cities = st.text_area("Major Cities (comma-separated list):", ex_cities)
    input_states = st.text_area("States / Provinces / Regions (optional, comma-separated):", ex_states)
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
            st.success(f"Saved new geographic configuration for {geo_country} to `clay_geo.py`!")
        else:
            st.info(f"Configuration for {geo_country} is active.")

with tab_portfolio:
    st.subheader("Delivered Country Portfolio")
    delivery_dir = "delivery"
    if os.path.exists(delivery_dir):
        countries = [d for d in os.listdir(delivery_dir) if os.path.isdir(os.path.join(delivery_dir, d))]
        if countries:
            st.write(f"Found {len(countries)} completed country folders in `delivery/`:")
            summary_data = []
            for c in sorted(countries):
                cdir = os.path.join(delivery_dir, c)
                files = [f for f in os.listdir(cdir) if f.endswith(".csv")]
                tot_bytes = sum(os.path.getsize(os.path.join(cdir, f)) for f in files)
                summary_data.append({
                    "Country": c,
                    "Delivered CSV Files": len(files),
                    "Total Folder Size": f"{tot_bytes / (1024*1024):.1f} MB",
                    "Folder Path": cdir
                })
            st.dataframe(pd.DataFrame(summary_data), use_container_width=True)
            
            selected_country_view = st.selectbox("Select a country to view individual delivered files:", sorted(countries))
            if selected_country_view:
                st.markdown(f"#### Delivered Files in `delivery/{selected_country_view}/`")
                cpath = os.path.join(delivery_dir, selected_country_view)
                cfiles = sorted([f for f in os.listdir(cpath) if f.endswith(".csv")])
                file_details = []
                for cf in cfiles:
                    full_p = os.path.join(cpath, cf)
                    file_details.append({
                        "File Name": cf,
                        "File Size": f"{os.path.getsize(full_p)/1024:.1f} KB",
                        "Full Local Path": full_p
                    })
                st.dataframe(pd.DataFrame(file_details), use_container_width=True)

with tab_central:
    st.subheader("Central Master Database & Differential Ingestion Store")
    st.write("All downloads executed by any team member are centrally ingested and deduplicated here. If a download is re-run for a country/industry, the central store identifies and delivers ONLY newly discovered companies.")
    
    central_store.init_db()
    conn = sqlite3.connect(central_store.DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM master_companies")
    tot_master = cur.fetchone()[0]
    conn.close()
    
    st.metric("Total Unique Companies in Master Central Store", f"{tot_master:,} Companies")
    
    st.markdown("#### Master Central Store Metrics by Country & Industry")
    if tot_master > 0:
        conn = sqlite3.connect(central_store.DB_PATH)
        m_df = pd.read_sql_query("SELECT country, industry, COUNT(*) as unique_companies_in_master, MIN(first_seen_at) as earliest_download, MAX(last_seen_at) as latest_download FROM master_companies GROUP BY country, industry ORDER BY COUNT(*) DESC", conn)
        conn.close()
        st.dataframe(m_df, use_container_width=True)

with tab_faq:
    st.subheader("Documentation & Workflow Guide")
    st.markdown("""
    ### Workflow Overview:
    1. **Single Login Authentication**: Enter the shared team password to access the platform.
    2. **Country & Industry Selection**: Pick from 218 countries. Use category buttons for Tech (48) vs Non-Tech (410) industries.
    3. **3-Step Execution**:
       - **Step 1 (Count)**: Free availability count preview with real-time progress bar.
       - **Step 2 (Plan)**: Free slice partitioning and reachable coverage calculation with real-time progress bar.
       - **Step 3 (Download)**: Download and deduplication pipeline with real-time progress bar.
    4. **Data Centralization**: All downloads update the central database. Differential CSVs (`[NEW_DELTA].csv`) contain only new companies discovered since previous runs.
    """)
