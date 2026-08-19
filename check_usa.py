import glob, os, csv

files = sorted(glob.glob('delivery/USA/*.csv'))
tot_rows = 0
tot_bytes = 0

print("| # | File Name | Unique Companies Delivered | Size (MB) |")
print("| :-: | :--- | :-: | :-: |")

for i, f in enumerate(files, 1):
    size = os.path.getsize(f)
    tot_bytes += size
    with open(f, newline='', encoding='utf-8', errors='replace') as fp:
        r = csv.reader(fp)
        next(r, None)
        cnt = sum(1 for _ in r)
        tot_rows += cnt
        name = os.path.basename(f)
        print(f"| **{i}** | `{name}` | **{cnt:,}** | {size/1e6:.2f} MB |")

print(f"| **TOTAL** | **17 USA Target Industries** | **{tot_rows:,}** | **{tot_bytes/1e6:.1f} MB** |")
