#!/usr/bin/env python3
"""One summary sheet per country: industry, clay_count, rows_downloaded
(UNIQUE companies, not raw rows), coverage_pct, Status.

Unique is keyed on LinkedIn URL falling back to Domain -- domain-first would
collapse genuinely distinct companies that share a website (university
departments, hotel franchises, broker networks) and understate coverage badly.
"""
import csv, os, sys
import clay_lib as cl
from run_nontech import delivery_name, tally

JOBS = [("United Kingdom", "UK", "United_Kingdom_nontech_counts.csv", "Count"),
        ("United States", "US", "United_States_nontech_counts.csv", "Count"),
        ("Canada", "Canada", "../Canada Non-Tech Industries Counts.csv", "Canada_Count")]

def status(cov, delivered):
    if not delivered:
        return "NOT DOWNLOADED"
    if cov >= 95:
        return "Complete"
    if cov >= 85:
        return "Partial - minor gap"
    return "Partial - capped/blank-attribute"

for country, short, sheet, col in JOBS:
    if not os.path.exists(sheet):
        print("skip %s (no counts sheet)" % short); continue
    rows, tot_c, tot_u = [], 0, 0
    for r in csv.DictReader(open(sheet)):
        if not r.get("Industry") or not str(r[col]).isdigit() or int(r[col]) <= 0:
            continue
        ind, clay = r["Industry"], int(r[col])
        p = os.path.join("delivery", short, "non-tech", delivery_name(country, ind))
        uniq = tally(p)[1] if os.path.exists(p) else 0
        cov = round(100 * uniq / clay, 1) if clay else 0
        rows.append({"industry": ind, "clay_count": clay, "rows_downloaded": uniq,
                     "coverage_pct": cov, "Status": status(cov, uniq)})
        tot_c += clay; tot_u += uniq
    rows.sort(key=lambda d: -d["clay_count"])
    out = "%s_non_tech_summary.csv" % short
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["industry", "clay_count", "rows_downloaded",
                                          "coverage_pct", "Status"])
        w.writeheader(); w.writerows(rows)
        w.writerow({"industry": "TOTAL", "clay_count": tot_c, "rows_downloaded": tot_u,
                    "coverage_pct": round(100 * tot_u / tot_c, 1), "Status": ""})
    import collections
    st = collections.Counter(d["Status"] for d in rows)
    print("%-8s %3d industries | clay %10s | unique %10s | %5.1f%%  -> %s" %
          (short, len(rows), format(tot_c, ","), format(tot_u, ","), 100*tot_u/tot_c, out))
    for k, v in st.most_common():
        print("            %-36s%4d" % (k, v))
