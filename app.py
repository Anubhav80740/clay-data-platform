import csv
import glob
import json
import os
import re
import subprocess
import sys
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

# Page Configuration
st.set_page_config(
    page_title="Clay Data Platform",
    layout="wide"
)

# Shared Single-Login Authentication
TEAM_USER_ID = os.environ.get("CLAY_USER_ID", "team")
TEAM_PASSWORD = os.environ.get("CLAY_PASSWORD", "clay2026")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

def login_screen():
    st.markdown("### Clay Data Platform - Single Team Login")
    st.caption("Please enter your team credentials to access the extraction workspace.")
    
    col_login, _ = st.columns([1, 2])
    with col_login:
        user_id = st.text_input("User ID")
        password = st.text_input("Password", type="password")
        if st.button("Login", type="primary"):
            if user_id.strip() == TEAM_USER_ID and password.strip() == TEAM_PASSWORD:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Invalid User ID or Password.")

if not st.session_state["authenticated"]:
    login_screen()
    st.stop()

# Header
head_col1, head_col2 = st.columns([4, 1])
with head_col1:
    st.title("Clay Data Platform")
    st.caption("Centralized Company Data Extraction, Deduplication and Portfolio System")
with head_col2:
    if st.button("Logout"):
        st.session_state["authenticated"] = False
        st.rerun()

st.divider()

tab_download, tab_geo, tab_portfolio, tab_faq = st.tabs([
    "Run Data Extraction",
    "Country Division Settings",
    "Delivered Portfolio",
    "Centralized Store & Deduplication FAQ"
])

with tab_download:
    st.subheader("Step A: Select Country and Target Industries")
    
    col_c, col_i = st.columns([1, 2])
    
    with col_c:
        st.markdown("**1. Target Country Selection**")
        def_idx = ALL_CLAY_COUNTRIES.index("Spain") if "Spain" in ALL_CLAY_COUNTRIES else 0
        country_select = st.selectbox(
            "Search and select country (218 countries available):",
            options=ALL_CLAY_COUNTRIES,
            index=def_idx,
            help="Type to search any country name"
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
            st.info(f"Geographic Division Active for {country_input}: {num_cities} Cities, {num_states} States/Regions.")
        else:
            st.warning(f"Note: {country_input} has no custom city list defined. Default size/revenue fallbacks will be used. You can add cities under 'Country Division Settings'.")

    with col_i:
        st.markdown("**2. Target Industries Selection**")
        
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
            "Search and select industries (starts empty; select manually or use category buttons above):",
            options=ALL_CLAY_INDUSTRIES,
            key="selected_industries"
        )
        
        st.caption(f"Currently selected: {len(selected_industries)} industries out of 458 total Clay industries.")

    st.divider()
    st.subheader("Step B: 3-Step Execution Workflow")
    
    def slugify(text):
        return re.sub(r'[^a-zA-Z0-9]+', '_', text).strip('_')

    country_slug = slugify(country_input) if country_input else ""
    counts_file = f"{country_slug}_nontech_counts.csv"
    ledger_file = f"{country_slug}_nontech_progress.csv"
    ind_file = "selected_industries.json"

    step_col1, step_col2, step_col3 = st.columns([1, 1, 1])

    # ----------------------------------------------------
    # STEP 1: COUNT WITH PROGRESS BAR
    # ----------------------------------------------------
    with step_col1:
        st.markdown("#### Step 1: Count Target Rows")
        st.caption("Free counting query. Estimates raw Clay target counts.")
        btn_count = st.button("Run Step 1: Count", use_container_width=True)

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
                
                count_progress_bar = st.progress(0.0)
                count_status = st.empty()
                count_status.text(f"Starting count for {len(selected_industries)} industries in {country_input}...")
                
                cmd = [sys.executable, "-u", "count_industries.py", country_input, "--industries-file", ind_file]
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
                
                total_to_count = len(selected_industries)
                counted_so_far = 0
                
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
                            count_status.text(f"Counting: {current_i} of {tot_i} industries ({int(pct*100)}%) - {line.strip()}")
                
                proc.wait()
                if proc.returncode == 0:
                    count_progress_bar.progress(1.0)
                    count_status.text("Counting complete.")
                    st.success("Step 1 Count complete.")
                else:
                    st.error("Step 1 Count failed.")

    # ----------------------------------------------------
    # STEP 2: PLAN & ESTIMATE COVERAGE
    # ----------------------------------------------------
    with step_col2:
        st.markdown("#### Step 2: Plan & Estimate Coverage")
        st.caption("Free planning query. Partitions slices and estimates reachable coverage.")
        btn_plan = st.button("Run Step 2: Generate Plan", use_container_width=True)

        if btn_plan:
            if not country_input:
                st.error("Please select a country.")
            elif not selected_industries:
                st.error("Please select at least one industry.")
            else:
                with open(ind_file, "w", encoding="utf-8") as f:
                    json.dump(selected_industries, f)
                    
                plan_progress_bar = st.progress(0.0)
                plan_status = st.empty()
                tot_p = len(selected_industries)
                
                for idx, ind in enumerate(selected_industries, 1):
                    plan_status.text(f"Planning {idx} of {tot_p}: {ind}...")
                    cmd = [sys.executable, "-u", "generate_clicklist.py", ind, country_input]
                    subprocess.run(cmd, capture_output=True, text=True)
                    plan_progress_bar.progress(idx / tot_p)
                    
                plan_status.text("Planning complete.")
                st.success("Step 2 Planning complete. Review estimated coverage below.")

    # ----------------------------------------------------
    # STEP 3: DOWNLOAD & DELIVER WITH PROGRESS BAR
    # ----------------------------------------------------
    with step_col3:
        st.markdown("#### Step 3: Download Data")
        st.caption("Executes download, incremental merge, and deduplication.")
        
        plan_approved = st.checkbox("I approve the plan & estimated coverage", key="plan_approved_check")
        btn_download = st.button("Run Step 3: Download Data", type="primary", use_container_width=True, disabled=not plan_approved)

    # ----------------------------------------------------
    # DISPLAY RESULTS FOR STEP 1 AND STEP 2
    # ----------------------------------------------------
    if os.path.exists(counts_file):
        st.markdown(f"### Step 1 Count Results ({country_input})")
        cdf = pd.read_csv(counts_file)
        if selected_industries:
            cdf = cdf[cdf["Industry"].isin(selected_industries)]
        st.dataframe(cdf, use_container_width=True)
        tot_c = safe_sum(cdf["Count"]) if "Count" in cdf.columns and not cdf.empty else 0
        st.info(f"Total Clay Target Rows: {tot_c:,} rows across {len(cdf)} selected industries.")

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
                    "Unreachable Gap": gap,
                    "Est Coverage %": f"{cov_pct}%",
                    "Planned Slices": num_slices
                })
            except Exception:
                pass

    if planned_data:
        st.markdown(f"### Step 2 Plan & Coverage Estimate Results ({country_input})")
        pdf_plan = pd.DataFrame(planned_data)
        st.dataframe(pdf_plan, use_container_width=True)
        tot_reach = sum(r["Estimated Reachable"] for r in planned_data)
        tot_target = sum(r["Clay Target Count"] for r in planned_data)
        overall_cov = round(100 * tot_reach / max(1, tot_target), 1)
        st.success(f"Plan Summary: Estimated Reachable Unique Companies: {tot_reach:,} / {tot_target:,} ({overall_cov}% Estimated Coverage). Check the approval box in Step 3 above to proceed to download.")

    # Execute Step 3 Download with Progress Bar
    if btn_download:
        if not plan_approved:
            st.warning("Please check the approval box in Step 3 to confirm plan approval before downloading.")
        else:
            st.markdown(f"### Executing Live Step 3 Download for {country_input}...")
            
            with open(ind_file, "w", encoding="utf-8") as f:
                json.dump(selected_industries, f)

            log_container = st.empty()
            dl_progress_bar = st.progress(0.0)
            dl_status_text = st.empty()
            
            cmd_run = [sys.executable, "-u", "run_nontech.py", country_input]
            only_str = "|".join(selected_industries)
            cmd_run.extend(["--only", only_str])

            process = subprocess.Popen(cmd_run, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            
            logs = []
            tot_ind = len(selected_industries)
            
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    logs.append(line.strip())
                    log_container.code("\n".join(logs[-20:]))
                    
                    if os.path.exists(ledger_file):
                        try:
                            pdf_prog = pd.read_csv(ledger_file)
                            col_i = "industry" if "industry" in pdf_prog.columns else ("Industry" if "Industry" in pdf_prog.columns else None)
                            if col_i:
                                pdf_sel = pdf_prog[pdf_prog[col_i].isin(selected_industries)]
                                done_count = len(pdf_sel)
                                pct = min(1.0, done_count / max(1, tot_ind))
                                dl_progress_bar.progress(pct)
                                dl_status_text.text(f"Downloading: {done_count} of {tot_ind} selected industries complete ({int(pct*100)}%)")
                        except Exception:
                            pass
                            
            process.wait()
            if process.returncode == 0:
                dl_progress_bar.progress(1.0)
                dl_status_text.text("Step 3 Download complete.")
                st.success(f"Step 3 Download and Centralized Merge complete for {country_input}.")
            else:
                st.error("Download finished with errors. See log above.")

    if os.path.exists(ledger_file):
        st.markdown(f"### Delivered Datasets and Metrics ({country_input})")
        try:
            ledger_df = pd.read_csv(ledger_file)
            col_ind = "industry" if "industry" in ledger_df.columns else ("Industry" if "Industry" in ledger_df.columns else None)
            if selected_industries and col_ind:
                ledger_df = ledger_df[ledger_df[col_ind].isin(selected_industries)]
            st.dataframe(ledger_df, use_container_width=True)
            
            col_uniq = "unique_companies" if "unique_companies" in ledger_df.columns else ("Count" if "Count" in ledger_df.columns else None)
            delivered_total = safe_sum(ledger_df[col_uniq]) if col_uniq and not ledger_df.empty else 0
            st.success(f"Total Unique Companies Delivered: {delivered_total:,} Unique Companies")
        except Exception as ex:
            st.warning(f"Unable to display ledger metrics: {ex}")

with tab_geo:
    st.subheader("Country Geographic Division Settings")
    st.write("When adding a new country, you can define its major cities, states/provinces, and fallback rules here so the partitioning engine splits large industries cleanly without code intervention.")
    
    geo_country = st.selectbox("Select Country to Configure:", ALL_CLAY_COUNTRIES, index=def_idx)
    
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
            st.success(f"Saved new geographic configuration for {geo_country} to clay_geo.py")
        else:
            st.info(f"Configuration for {geo_country} is active. Restart the app if updating existing entries.")

with tab_portfolio:
    st.subheader("Delivered Country Portfolio")
    
    delivery_dir = "delivery"
    if os.path.exists(delivery_dir):
        countries = [d for d in os.listdir(delivery_dir) if os.path.isdir(os.path.join(delivery_dir, d))]
        if countries:
            st.write(f"Found {len(countries)} completed country folders in delivery/:")
            
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
            
            selected_country_view = st.selectbox("Select a country to view individual delivered files:", sorted(countries))
            if selected_country_view:
                st.markdown(f"#### Delivered Files in delivery/{selected_country_view}/")
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
        else:
            st.info("No country folders found in delivery/ yet.")
    else:
        st.info("No delivery directory created yet.")

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
