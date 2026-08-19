import glob, csv, os

# USA numbers from USA planning: target 187,487, unique delivered 181,153
data = [
    ("USA", 187487, 181153, "17 files"),
    ("UK", 84086, 77091, "17 files"),
    ("France", 54824, 54800, "17 files"),
    ("Germany", 24683, 24341, "17 files"),
    ("Australia", 14131, 14123, "17 files"),
    ("UAE", 4594, 4594, "17 files"),
    ("Singapore", 3752, 3751, "17 files"),
    ("Ireland", 2470, 2468, "16 files"),
]

print("| Country | Clay Target Rows | Unique Delivered | Overall Coverage % | Delivery Files |")
print("| :--- | :-: | :-: | :-: | :-: |")

tot_tgt = 0
tot_uniq = 0

for country, tgt, uniq, files_str in data:
    cov = (uniq / tgt) * 100
    tot_tgt += tgt
    tot_uniq += uniq
    print(f"| **{country}** | {tgt:,} | **{uniq:,}** | **{cov:.1f}%** | {files_str} |")

tot_cov = (tot_uniq / tot_tgt) * 100
print(f"| **TOTAL** | **{tot_tgt:,}** | **{tot_uniq:,}** | **{tot_cov:.1f}%** | **135 files** |")
