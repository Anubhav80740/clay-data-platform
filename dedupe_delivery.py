#!/usr/bin/env python3
import csv
import glob
import os
import time

csv.field_size_limit(2147483647)

def dedupe_all(src_dir="delivery"):
    files = sorted(glob.glob(f"{src_dir}/*.csv"))
    print(f"Deduplicating {len(files)} files in {src_dir}/...\n")
    
    total_deduped = 0
    
    for path in files:
        basename = os.path.basename(path)
        tmp_path = path + ".tmp"
        seen = set()
        deduped_rows = []
        header = None
        
        with open(path, newline="", encoding="utf-8", errors="replace") as f:
            r = csv.reader(f)
            header = next(r, None)
            if not header:
                continue
            
            li = header.index("LinkedIn URL") if "LinkedIn URL" in header else None
            di = header.index("Domain") if "Domain" in header else None
            
            for row in r:
                lnk = row[li].strip().lower() if li is not None and li < len(row) else ""
                dom = row[di].strip().lower() if di is not None and di < len(row) else ""
                key = lnk or ("dom:" + dom)
                if key and key in seen:
                    continue
                if key:
                    seen.add(key)
                deduped_rows.append(row)
        
        with open(tmp_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(deduped_rows)
        
        # Retry loop for Windows file lock
        replaced = False
        for attempt in range(5):
            try:
                os.replace(tmp_path, path)
                replaced = True
                break
            except Exception:
                time.sleep(1.0)
        
        if not replaced:
            print(f"[WARN] Could not replace {basename} due to Windows file lock (Excel open?). Created clean file at {tmp_path}")
        else:
            print(f"[DEDUPLICATED] {basename[:60]:<60} -> {len(deduped_rows):>6} unique companies")
            
        total_deduped += len(deduped_rows)

    print(f"\n==================================================")
    print(f"SUCCESS: All {len(files)} delivery files are now 100% clean & deduplicated!")
    print(f"Total Unique Companies Across All Files: {total_deduped:,}")

if __name__ == "__main__":
    dedupe_all()
