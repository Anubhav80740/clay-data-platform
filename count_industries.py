#!/usr/bin/env python3
"""
Fetch Clay counts for any list of industries for a country.
Usage:
  python3 count_industries.py "Spain" [--industries-file industries.json]
"""
import csv
import json
import os
import sys

import clay_lib as cl
import clay_logger
from clay_taxonomy import ALL_CLAY_INDUSTRIES

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 count_industries.py <Country> [--industries-file file.json]")
        sys.exit(1)
        
    country = sys.argv[1]
    user_id = os.environ.get("CLAY_USER_ID", "team")
    if "--user" in sys.argv:
        u_idx = sys.argv.index("--user")
        if u_idx + 1 < len(sys.argv):
            user_id = sys.argv[u_idx + 1]
            os.environ["CLAY_USER_ID"] = user_id
    os.makedirs("data", exist_ok=True)
    out = os.path.join("data", f"{cl.slugify(country)}_nontech_counts.csv")
    
    industries = ALL_CLAY_INDUSTRIES
    
    # Check if a custom industries file is passed
    if "--industries-file" in sys.argv:
        idx = sys.argv.index("--industries-file") + 1
        if idx < len(sys.argv) and os.path.exists(sys.argv[idx]):
            with open(sys.argv[idx], encoding="utf-8") as f:
                industries = json.load(f)
    elif len(sys.argv) > 2 and os.path.exists(sys.argv[2]):
        path = sys.argv[2]
        with open(path, encoding="utf-8") as f:
            if path.endswith(".json"):
                industries = json.load(f)
            else:
                industries = [r["Industry"].strip() for r in csv.DictReader(f) if r.get("Industry") and r["Industry"].strip()]

    have_prev = {}
    if os.path.exists(out):
        try:
            with open(out, encoding="utf-8", errors="replace") as f:
                have_prev = {r["Industry"]: r["Count"] for r in csv.DictReader(f) if "Industry" in r and "Count" in r}
        except Exception:
            pass

    have = {}
    print(f"Fetching fresh Clay counts for {len(industries)} industries in {country}...", flush=True)

    for i, ind in enumerate(industries, 1):
        prev_val = have_prev.get(ind)
        c = cl.count({"industries": [ind], "country_names": [country]})
        have[ind] = "" if c is None else c
        print(f"[{i}/{len(industries)}] {ind}: {c if c is not None else 0:,} (previous: {prev_val if prev_val is not None else 'N/A'})", flush=True)
        if i % 10 == 0:
            write(out, country, industries, have)

    write(out, country, industries, have)
    nz = [i for i in industries if str(have.get(i, "")).isdigit() and int(have[i]) > 0]
    total = sum(int(have[i]) for i in nz)
    failed = [i for i in industries if have.get(i) == ""]
    
    clay_logger.log_activity("COUNT", "Companies", country, industries=industries, total_rows=total, status="SUCCESS" if not failed else "PARTIAL", details=f"{total:,} rows across {len(industries)} industries")
    print(f"\n{len(industries)} industries | {len(nz)} with count>0 | total {total:,} rows")
    if failed:
        print(f"COUNT FAILED (re-run to retry): {len(failed)} -> {failed[:5]}")
    print(f"saved: {out}")


def write(out, country, industries, have):
    done = [i for i in industries if i in have]
    done.sort(key=lambda i: -(int(have[i]) if str(have[i]).isdigit() else -1))
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Industry", "Category", "Count", "Country"])
        for i in done:
            w.writerow([i, "Custom", have[i], country])


if __name__ == "__main__":
    main()

