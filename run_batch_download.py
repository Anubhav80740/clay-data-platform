import subprocess, sys, time, os

countries = ["Sweden", "New Zealand", "Netherlands", "India", "Denmark", "Canada"]

for c in countries:
    counts_file = f"{c.lower().replace(' ', '_')}_nontech_counts.csv"
    # Wait if counting is still in progress for this country
    while not os.path.exists(counts_file):
        print(f"Waiting for {counts_file}...", flush=True)
        time.sleep(5)
    
    print(f"\n==================== STARTING DOWNLOAD: {c.upper()} ====================", flush=True)
    subprocess.call([sys.executable, "-u", "run_nontech.py", c])

print("\n=== ALL 6 COUNTRIES DOWNLOADED & DELIVERED ===", flush=True)
