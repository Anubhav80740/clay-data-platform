"""
TASK: plan. Partition an industry+country into export slices (each <= 4,800),
free counting only. Writes:
  clicklist_<industry>_<country>.csv   (human-readable click-list)
  clicklist_<industry>_<country>.json  (exact per-slice filters, for the downloader)

Usage: python3 generate_clicklist.py "Software Development" ["United States"]
"""
import csv
import json
import os
import sys

import clay_lib as cl


def _fmt(vals):
    return vals[0] if len(vals) == 1 else "[" + " | ".join(map(str, vals)) + "]"


def slice_desc(f):
    p = []
    if f.get("location_states_include"):
        p.append(f"state={_fmt(f['location_states_include'])}")
    if f.get("location_states_exclude"):
        p.append(f"state NOT IN [{len(f['location_states_exclude'])} listed]")
    if f.get("location_cities_include"):
        p.append(f"city={_fmt(f['location_cities_include'])}")
    if f.get("location_cities_exclude"):
        p.append(f"city NOT IN [{len(f['location_cities_exclude'])} listed]")
    if f.get("location_postal_codes_include"):
        p.append(f"zip={_fmt(f['location_postal_codes_include'])}")
    if f.get("location_postal_codes_exclude"):
        p.append(f"zip NOT IN [{len(f['location_postal_codes_exclude'])} listed]")
    if f.get("locations"):
        p.append(f"county={_fmt(f['locations'])}")
    if f.get("locations_exclude"):
        p.append(f"county NOT IN [{len(f['locations_exclude'])} listed]")
    if f.get("description_keywords"):
        p.append(f"desc~{_fmt(f['description_keywords'])}")
    if f.get("description_keywords_exclude"):
        p.append(f"desc NOT~ [{len(f['description_keywords_exclude'])} listed]")
    if f.get("sizes"):
        p.append(f"size={_fmt(f['sizes'])}")
    if f.get("annual_revenues"):
        p.append(f"revenue={_fmt(f['annual_revenues'])}")
    if f.get("types"):
        p.append(f"type={_fmt(f['types'])}")
    return "; ".join(p) if p else "(industry+country only)"


def slug_for(prefix, f):
    parts = [prefix]
    for tag, key in [("st", "location_states_include"), ("city", "location_cities_include"),
                     ("zip", "location_postal_codes_include"), ("cty", "locations"),
                     ("kw", "description_keywords"),
                     ("sz", "sizes"), ("rev", "annual_revenues"), ("typ", "types")]:
        if f.get(key):
            parts.append(tag + "-" + "-".join(map(str, f[key])))
    for tag, key in [("stX", "location_states_exclude"), ("cityX", "location_cities_exclude"),
                     ("zipX", "location_postal_codes_exclude"), ("ctyX", "locations_exclude"),
                     ("kwX", "description_keywords_exclude")]:
        if f.get(key):
            parts.append(f"{tag}{len(f[key])}")
    return cl.slugify("_".join(parts))


def main():
    industry = sys.argv[1] if len(sys.argv) > 1 else "Software Development"
    country = sys.argv[2] if len(sys.argv) > 2 else "United States"
    print(f"Planning: {industry} + {country}  (cap {cl.EXPORT_LIMIT}/leaf, free counts)")

    stats, base = cl.run(industry, country)
    leaves = sorted(stats.leaves, key=lambda l: -l.count)
    covered = sum(l.count for l in leaves)
    root = cl.count(base)
    prefix = cl.slugify(f"{industry}_{country}")

    os.makedirs(cl.PLAN_DIR, exist_ok=True)
    with open(f"{cl.PLAN_DIR}/clicklist_{prefix}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["industry", "country", "states", "cities", "postal",
                    "sizes", "revenues", "count", "oversized", "ui_filters"])
        j = lambda vs: " | ".join(map(str, vs))
        for l in leaves:
            fl = l.filters
            w.writerow([industry, country,
                        j(fl.get("location_states_include") or []),
                        j(fl.get("location_cities_include") or []),
                        j(fl.get("location_postal_codes_include") or []),
                        j(fl.get("sizes") or []), j(fl.get("annual_revenues") or []),
                        l.count, "YES" if l.oversized else "", slice_desc(fl)])

    with open(f"{cl.PLAN_DIR}/clicklist_{prefix}.json", "w") as f:
        json.dump([{"slug": slug_for(prefix, l.filters), "count": l.count,
                    "oversized": l.oversized, "filters": l.filters} for l in leaves],
                  f, indent=1)

    # Uncovered-detail file: exactly which geo cells leaked, and on which field.
    if stats.uncovered:
        with open(f"{cl.PLAN_DIR}/clicklist_{prefix}_uncovered.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["blank_field", "count", "cell_filters (apply these in Clay UI)"])
            for label, cnt, filt in sorted(stats.uncovered, key=lambda t: -t[1]):
                blank = ("size" if label.endswith("size-blank")
                         else "revenue" if label.endswith("revenue-blank")
                         else "count-failed")
                w.writerow([blank, cnt, slice_desc(filt)])

    unc = sum(t[1] for t in stats.uncovered)
    reachable = (root - unc) if root else 0
    overlap = max(0, covered - reachable)   # multi-location double-count in the pull
    print(f"  count() calls   : {stats.count_calls}")
    print(f"  slices (merged) : {len(leaves)}  (from {stats.merged_from} raw leaves)")
    print(f"  still oversized : {len(stats.oversized)}")
    print(f"  uncovered (gap) : {unc:,} companies across {len(stats.uncovered)} buckets "
          f"(blank size+revenue -- can't be filter-isolated)")
    sweeps = [l for l in leaves if l.label.endswith("-sweep")]
    if sweeps:
        # NOT added to TRUE coverage: a sweep pulls the cell's top-ranked rows, which
        # overlap what its sibling slices already cover, so the new-unique yield is
        # unknown. Counting it as recovered is the over-claim we got burned by.
        print(f"  blank sweeps    : {len(sweeps)} slices, up to {sum(l.count for l in sweeps):,} "
              f"rows of partial recovery from the gap (overlap-heavy, not counted below)")
    if root:
        print(f"  TRUE coverage   : {reachable:,} / {root:,} = {100*reachable/root:.1f}% "
              f"(unique companies reachable)")
        print(f"  slices sum to   : {covered:,} rows incl. ~{overlap:,} multi-location "
              f"overlap (removed by domain/LinkedIn dedup at merge)")
    print(f"  saved: {cl.PLAN_DIR}/clicklist_{prefix}.csv / .json"
          + (" / _uncovered.csv" if stats.uncovered else ""))


if __name__ == "__main__":
    main()
