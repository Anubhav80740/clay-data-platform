import subprocess, sys

countries = ["Sweden", "New Zealand", "Netherlands", "India", "Denmark", "Canada"]

for c in countries:
    print(f"\n==================== COUNTING {c.upper()} ====================", flush=True)
    subprocess.call([sys.executable, "-u", "count_industries.py", c])

print("\n=== ALL 6 COUNTRIES COUNTED ===", flush=True)
