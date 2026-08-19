# 🌍 Clay Data Extraction Local App - User Guide

This lightweight desktop application allows anyone on the team to download, deduplicate, and organize company datasets from Clay **100% locally on their own computer**, without spending any AI credits.

---

## ⚡ Quick Start (Double-Click Launch)

1. Open the project folder: `Clay_Data_Downloader`
2. Double-click **`START_APP.bat`** (or run `START_APP.sh` on Mac/Linux).
3. The app will automatically launch in your browser at `http://localhost:8501`.

---

## 🚀 How to Download Data (3-Step Workflow)

### 1. Target Country & Industry Selection
* **Select Country**: Pick from 218 Clay countries or type any custom country name.
* **Select Target Industries**: Use category quick-buttons (`💻 Select Tech Industries` or `🏢 Select Non-Tech Industries` or `🌐 Select All 458 Clay Industries`) or search/select specific industries. No industries are selected by default.

### 2. 3-Step Action Execution
* **Step 1: 🔍 Count Target Rows (FREE)**: Queries Clay for raw target counts for your selected industries.
* **Step 2: 📋 Plan & Estimate Coverage (FREE)**: Generates slice partitions and estimates reachable unique companies and coverage percentage BEFORE spending any download credits.
* **Review & Approve**: Review the estimated coverage table and check **`[x] I approve the plan & estimated coverage`**.
* **Step 3: 🚀 Download Data (Spends Credits)**: Executes download, merges slices, deduplicates in-place on **LinkedIn URL** and **Domain**, and delivers clean CSV files to `delivery/<Country>/`.

---

## 🗺️ Adding New Countries (Self-Service Division)

If you introduce a brand new country with a large number of companies:
1. Open the **`🗺️ Country Division Settings`** tab in the app.
2. Select your country and enter major cities (e.g. `Madrid, Barcelona, Valencia`), states, or regions.
3. Click **`💾 Save Geographic Configuration`**. The partition engine will automatically use these cities to split large industry queries cleanly without any code changes!

---

## 📁 Accessing Delivered Data

All completed datasets are automatically organized in:
`delivery/<Country>/`

You can also view and inspect all delivered files directly inside the app under the **`📁 View Completed Portfolio`** tab!
