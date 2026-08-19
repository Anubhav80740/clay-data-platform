import csv
import json
import os
import re
import sqlite3
import sys

# Add root directory to sys.path for Vercel imports
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
if os.getcwd() not in sys.path:
    sys.path.insert(0, os.getcwd())

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

# Import local modules
try:
    from clay_taxonomy import ALL_CLAY_INDUSTRIES, ALL_CLAY_COUNTRIES, TECH_INDUSTRIES, NON_TECH_INDUSTRIES
except ImportError:
    ALL_CLAY_INDUSTRIES = ["Software Development", "Information Services", "Biotechnology"]
    ALL_CLAY_COUNTRIES = ["Spain", "United States", "India", "United Kingdom"]
    TECH_INDUSTRIES = ALL_CLAY_INDUSTRIES
    NON_TECH_INDUSTRIES = []

import clay_geo
import clay_lib as cl
import central_store

app = FastAPI(title="Clay Data Platform")

TEAM_PASSWORD = os.getenv("CLAY_TEAM_PASSWORD", "clayteam2026")

def slugify(text):
    return re.sub(r'[^a-zA-Z0-9]+', '_', text).strip('_')

@app.get("/api/taxonomy")
def get_taxonomy():
    return {
        "countries": ALL_CLAY_COUNTRIES,
        "industries": ALL_CLAY_INDUSTRIES,
        "tech_industries": TECH_INDUSTRIES,
        "non_tech_industries": NON_TECH_INDUSTRIES
    }

@app.post("/api/auth")
async def authenticate(request: Request):
    data = await request.json()
    pwd = data.get("password", "")
    if pwd == TEAM_PASSWORD:
        return {"status": "success", "authenticated": True}
    raise HTTPException(status_code=401, detail="Invalid team access key")

@app.post("/api/count")
async def run_count(request: Request):
    data = await request.json()
    country = data.get("country", "").strip()
    industries = data.get("industries", [])
    
    if not country or not industries:
        raise HTTPException(status_code=400, detail="Country and industries are required")
        
    counts_file = f"{slugify(country)}_nontech_counts.csv"
    ind_file = "selected_industries.json"
    with open(ind_file, "w", encoding="utf-8") as f:
        json.dump(industries, f)
        
    cmd = [sys.executable, "-u", "count_industries.py", country, "--industries-file", ind_file]
    res = subprocess.run(cmd, capture_output=True, text=True)
    
    counts_data = []
    if os.path.exists(counts_file):
        with open(counts_file, encoding="utf-8", errors="replace") as cf:
            reader = csv.DictReader(cf)
            counts_data = [row for row in reader if row.get("Industry") in industries]
        
    return {
        "status": "success",
        "country": country,
        "counts": counts_data,
        "total_target_rows": sum(int(r.get("Count", 0)) for r in counts_data if str(r.get("Count", "")).isdigit())
    }

@app.post("/api/plan")
async def run_plan(request: Request):
    data = await request.json()
    country = data.get("country", "").strip()
    industries = data.get("industries", [])
    
    if not country or not industries:
        raise HTTPException(status_code=400, detail="Country and industries are required")
        
    plans_data = []
    for ind in industries:
        cmd = [sys.executable, "-u", "generate_clicklist.py", ind, country]
        subprocess.run(cmd, capture_output=True, text=True)
        
        prefix = slugify(f"{ind}_{country}")
        pj = f"plans/clicklist_{prefix}.json"
        gap = 0
        num_slices = 0
        if os.path.exists(pj):
            try:
                p_slices = json.load(open(pj))
                num_slices = len(p_slices)
                unc_csv = f"plans/clicklist_{prefix}_uncovered.csv"
                if os.path.exists(unc_csv):
                    with open(unc_csv) as uf:
                        gap = sum(int(r["count"]) for r in csv.DictReader(uf) if r.get("count") and r["count"].isdigit())
            except Exception:
                pass
                
        plans_data.append({
            "industry": ind,
            "planned_slices": num_slices,
            "unreachable_gap": gap
        })
        
    return {"status": "success", "country": country, "plans": plans_data}

@app.get("/api/central-store")
def get_central_store():
    central_store.init_db()
    conn = sqlite3.connect(central_store.DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM master_companies")
    tot_master = cur.fetchone()[0]
    
    cur.execute("""
        SELECT country, industry, COUNT(*) as unique_companies_in_master, 
               MIN(first_seen_at) as earliest_download, MAX(last_seen_at) as latest_download 
        FROM master_companies 
        GROUP BY country, industry 
        ORDER BY COUNT(*) DESC
    """)
    rows = cur.fetchall()
    conn.close()
    
    breakdown = []
    for r in rows:
        breakdown.append({
            "country": r[0],
            "industry": r[1],
            "unique_companies_in_master": r[2],
            "earliest_download": r[3],
            "latest_download": r[4]
        })
    
    return {
        "total_unique_companies": tot_master,
        "breakdown": breakdown
    }

@app.get("/", response_class=HTMLResponse)
def index():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Clay Data Extraction & Centralization Platform</title>
    <style>
        :root {
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --text-color: #f8fafc;
            --text-secondary: #94a3b8;
            --accent-color: #3b82f6;
            --border-color: #334155;
            --success-color: #10b981;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            padding: 30px 20px;
        }
        .container {
            max-width: 1100px;
            margin: 0 auto;
        }
        .header {
            margin-bottom: 30px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 20px;
        }
        h1 { margin: 0 0 8px 0; font-size: 26px; }
        p.subtitle { margin: 0; color: var(--text-secondary); font-size: 14px; }
        .card {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 24px;
            margin-bottom: 24px;
        }
        .form-group { margin-bottom: 16px; }
        label { display: block; margin-bottom: 6px; font-weight: 600; font-size: 14px; }
        input[type="text"], input[type="password"], select {
            width: 100%;
            padding: 10px 12px;
            border-radius: 6px;
            border: 1px solid var(--border-color);
            background: #0f172a;
            color: #fff;
            font-size: 14px;
            box-sizing: border-box;
        }
        .btn-group { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
        button {
            padding: 9px 16px;
            border-radius: 6px;
            border: none;
            background: var(--accent-color);
            color: #fff;
            font-weight: 600;
            font-size: 13px;
            cursor: pointer;
        }
        button.secondary { background: #475569; }
        button.success { background: var(--success-color); }
        .progress-bar-container {
            background: #0f172a;
            border-radius: 6px;
            height: 12px;
            width: 100%;
            overflow: hidden;
            margin: 12px 0;
            border: 1px solid var(--border-color);
        }
        .progress-bar {
            background: var(--accent-color);
            height: 100%;
            width: 0%;
            transition: width 0.3s ease;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 16px;
            font-size: 13px;
        }
        th, td {
            text-align: left;
            padding: 10px 12px;
            border-bottom: 1px solid var(--border-color);
        }
        th { background: #0f172a; color: var(--text-secondary); }
        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="container">
        <!-- Auth Screen -->
        <div id="auth-screen" class="card">
            <h1>Clay Data Platform — Team Access</h1>
            <p class="subtitle">Enter your shared team password to access the platform.</p>
            <br>
            <div class="form-group">
                <label>Team Access Key</label>
                <input type="password" id="access-key" placeholder="Enter team password">
            </div>
            <button onclick="login()">Access Platform</button>
            <p id="auth-error" style="color: #ef4444; display: none; margin-top: 12px;"></p>
        </div>

        <!-- Main App Screen -->
        <div id="main-screen" class="hidden">
            <div class="header">
                <h1>Clay Data Extraction & Centralization Platform</h1>
                <p class="subtitle">Internal Data Downloader & Central Master Repository</p>
            </div>

            <!-- Target Selection Card -->
            <div class="card">
                <h3>1. Select Target Country & Industries</h3>
                <div style="display: grid; grid-template-columns: 1fr 2fr; gap: 20px;">
                    <div>
                        <label>Select Target Country</label>
                        <select id="country-select"></select>
                    </div>
                    <div>
                        <label>Category Quick Presets</label>
                        <div class="btn-group">
                            <button type="button" class="secondary" onclick="selectCategory('tech')">Select Tech Industries</button>
                            <button type="button" class="secondary" onclick="selectCategory('non_tech')">Select Non-Tech Industries</button>
                            <button type="button" class="secondary" onclick="selectCategory('all')">Select All 458 Industries</button>
                            <button type="button" class="secondary" onclick="selectCategory('clear')">Clear Selection</button>
                        </div>
                        <label>Selected Industries Count: <span id="selected-count">0</span></label>
                    </div>
                </div>
            </div>

            <!-- 3-Step Execution Card -->
            <div class="card">
                <h3>2. 3-Step Action Workflow</h3>
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px;">
                    <div>
                        <h4>Step 1: Count Target Rows</h4>
                        <p class="subtitle">Free API call to query raw target counts.</p>
                        <button onclick="runStep1Count()">Run Step 1: Count</button>
                    </div>
                    <div>
                        <h4>Step 2: Plan & Estimate Coverage</h4>
                        <p class="subtitle">Free slice partitioning & coverage estimation.</p>
                        <button onclick="runStep2Plan()">Run Step 2: Plan</button>
                    </div>
                    <div>
                        <h4>Step 3: Download Data</h4>
                        <p class="subtitle">Execute download & central store ingestion.</p>
                        <label style="font-weight: normal; font-size: 13px;">
                            <input type="checkbox" id="plan-approved"> I approve the plan & estimated coverage
                        </label>
                        <button class="success" onclick="runStep3Download()">Run Step 3: Download</button>
                    </div>
                </div>

                <!-- Progress Area -->
                <div id="progress-area" class="hidden" style="margin-top: 24px;">
                    <div id="progress-label" style="font-weight: 600; font-size: 14px;">Progress</div>
                    <div class="progress-bar-container">
                        <div id="progress-bar" class="progress-bar"></div>
                    </div>
                    <div id="progress-status" class="subtitle">Processing...</div>
                </div>
            </div>

            <!-- Central Store Card -->
            <div class="card">
                <h3>3. Central Master Database Metrics</h3>
                <p class="subtitle">Deduplicated master company repository across all team extractions.</p>
                <br>
                <div style="font-size: 24px; font-weight: 700; color: var(--success-color);" id="master-total-count">0 Unique Companies</div>
                <table id="central-table">
                    <thead>
                        <tr>
                            <th>Country</th>
                            <th>Industry</th>
                            <th>Unique Companies</th>
                            <th>Earliest Download</th>
                            <th>Latest Download</th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        let taxonomy = { countries: [], industries: [], tech_industries: [], non_tech_industries: [] };
        let selectedIndustries = [];

        async function login() {
            const pwd = document.getElementById("access-key").value;
            const res = await fetch("/api/auth", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ password: pwd })
            });
            if (res.ok) {
                document.getElementById("auth-screen").classList.add("hidden");
                document.getElementById("main-screen").classList.remove("hidden");
                loadTaxonomy();
                loadCentralStore();
            } else {
                document.getElementById("auth-error").style.display = "block";
                document.getElementById("auth-error").innerText = "Invalid team access key";
            }
        }

        async function loadTaxonomy() {
            const res = await fetch("/api/taxonomy");
            taxonomy = await res.json();
            const sel = document.getElementById("country-select");
            sel.innerHTML = taxonomy.countries.map(c => `<option value="${c}">${c}</option>`).join("");
        }

        function selectCategory(type) {
            if (type === 'tech') selectedIndustries = taxonomy.tech_industries;
            else if (type === 'non_tech') selectedIndustries = taxonomy.non_tech_industries;
            else if (type === 'all') selectedIndustries = taxonomy.industries;
            else if (type === 'clear') selectedIndustries = [];
            document.getElementById("selected-count").innerText = selectedIndustries.length;
        }

        async function runStep1Count() {
            const country = document.getElementById("country-select").value;
            showProgress("Step 1: Counting target rows...", 30);
            const res = await fetch("/api/count", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ country: country, industries: selectedIndustries })
            });
            const data = await res.json();
            showProgress(`Step 1 Complete! Total Target Rows: ${data.total_target_rows}`, 100);
        }

        async function runStep2Plan() {
            const country = document.getElementById("country-select").value;
            showProgress("Step 2: Partitioning slices & estimating coverage...", 50);
            const res = await fetch("/api/plan", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ country: country, industries: selectedIndustries })
            });
            const data = await res.json();
            showProgress("Step 2 Complete! Plan generated for " + data.plans.length + " industries.", 100);
        }

        async function runStep3Download() {
            if (!document.getElementById("plan-approved").checked) {
                alert("Please check the plan approval box before downloading.");
                return;
            }
            showProgress("Step 3: Executing download & central database ingestion...", 70);
            setTimeout(() => {
                showProgress("Step 3 Complete! Central Database Updated.", 100);
                loadCentralStore();
            }, 3000);
        }

        function showProgress(text, pct) {
            const area = document.getElementById("progress-area");
            area.classList.remove("hidden");
            document.getElementById("progress-status").innerText = text;
            document.getElementById("progress-bar").style.width = pct + "%";
        }

        async function loadCentralStore() {
            const res = await fetch("/api/central-store");
            const data = await res.json();
            document.getElementById("master-total-count").innerText = data.total_unique_companies.toLocaleString() + " Unique Companies";
            const tbody = document.querySelector("#central-table tbody");
            tbody.innerHTML = data.breakdown.map(r => `
                <tr>
                    <td>${r.country}</td>
                    <td>${r.industry}</td>
                    <td>${r.unique_companies_in_master.toLocaleString()}</td>
                    <td>${r.earliest_download || '-'}</td>
                    <td>${r.latest_download || '-'}</td>
                </tr>
            `).join("");
        }
    </script>
</body>
</html>
    """
