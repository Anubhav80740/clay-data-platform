#!/usr/bin/env python3
"""Regenerate oversized_slices.csv from the CURRENT plans + what's on disk.
Uses a live count() as the denominator (the plan's stated count is capped at
EXPORT_LIMIT for sweep leaves, which under-reports the loss)."""
import csv, json, os
import clay_lib as cl
import importlib.util
spec = importlib.util.spec_from_file_location("gc", "generate_clicklist.py")
gc = importlib.util.module_from_spec(spec); spec.loader.exec_module(gc)

out = []
for country, cfile in [("United Kingdom", "United_Kingdom_nontech_counts.csv"),
                       ("United States", "United_States_nontech_counts.csv")]:
    for r in [x for x in csv.DictReader(open(cfile)) if x["Count"].isdigit() and int(x["Count"]) > 0]:
        ind = r["Industry"]
        pf = "%s/clicklist_%s.json" % (cl.PLAN_DIR, cl.slugify("%s_%s" % (ind, country)))
        if not os.path.exists(pf):
            continue
        for s in json.load(open(pf)):
            if not s.get("oversized"):
                continue
            slug = cl.slugify(s["slug"]); p = "downloads/%s/%s.csv" % (slug, slug)
            dl = os.path.exists(p)
            pulled = None
            if dl:
                with open(p, newline="", encoding="utf-8", errors="replace") as f:
                    pulled = max(0, sum(1 for _ in csv.reader(f)) - 1)
            live = cl.count(s["filters"]) or 0
            lost = max(0, live - pulled) if dl else max(0, live - cl.EXPORT_LIMIT)
            if lost <= 0:
                continue
            out.append({"country": country, "industry": ind, "cell_true_size": live,
                        "pulled": pulled if dl else "", "lost": lost,
                        "loss_type": "actual" if dl else "projected",
                        "reach_pct": (round(100*pulled/live, 1) if dl and live else
                                      (round(100*cl.EXPORT_LIMIT/live, 1) if live else "")),
                        "downloaded": "yes" if dl else "no",
                        "filters": gc.slice_desc(s["filters"]).replace("\n", " "), "slug": slug})

out.sort(key=lambda d: (d["country"], -d["cell_true_size"]))
with open("oversized_slices.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
back = list(csv.DictReader(open("oversized_slices.csv")))
print("written %d | read back %d %s" % (len(out), len(back), "OK" if len(out) == len(back) else "MISMATCH"))
for c in ("United Kingdom", "United States"):
    g = [d for d in out if d["country"] == c]
    print("  %-16s %2d slices, ~%s behind the cap" % (c, len(g), format(sum(d["lost"] for d in g), ",")))
print("  TOTAL           %2d slices, ~%s" % (len(out), format(sum(d["lost"] for d in out), ",")))
