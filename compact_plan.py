#!/usr/bin/env python3
"""
Collapse a plan's long tail of tiny chained slices into one slice each.

Wall-clock is driven by SLICE COUNT, not rows: every slice costs ~40s of
table-create + populate-poll regardless of whether it returns 3 rows or 5,000.
Medical Practices had 621 slices holding 1.8% of the data.

The only lossless merge for chained buckets. Bucket i is "matches kw_i AND none
of kw_0..kw_i-1", so an arbitrary subset union is NOT expressible -- merging
non-adjacent buckets silently drops companies that match both. But the union of
every bucket from position i onward, PLUS the exclude-remainder, is exactly:

    base + {exclude_key: order[:i]}          ("none of the first i")

so a suffix collapse is safe. We take the longest suffix that still fits the
export cap.

Usage: python3 compact_plan.py <prefix> [--apply]
"""
import json
import sys

import hashlib

import clay_lib as cl


def _fhash(f):
    """Slugs must encode the WHOLE filter set: two cells differing only by
    state produced identical slugs, and the second silently inherited the
    first's CSV (New York rows delivered as Ohio)."""
    return hashlib.md5(json.dumps(f, sort_keys=True).encode()).hexdigest()[:10]

CHAINS = [("description_keywords", "description_keywords_exclude",
           [k for rnd in cl.KEYWORD_ROUNDS for k in rnd]),
          ("locations", "locations_exclude", None),      # counties, order from GEO
          ("location_cities_include", "location_cities_exclude", None)]  # city sub-slices

prefix = sys.argv[1]
apply = "--apply" in sys.argv
path = f"{cl.PLAN_DIR}/clicklist_{prefix}.json"
plan = json.load(open(path))


def base_of(f, inc, exc):
    return tuple(sorted((k, tuple(v) if isinstance(v, list) else v)
                        for k, v in f.items() if k not in (inc, exc) and v not in (None, [], "")))


out, merged_groups, saved = [], 0, 0
for inc, exc, order in CHAINS:
    groups = {}
    for leaf in plan:
        f = leaf["filters"]
        if inc not in f and exc not in f:
            continue
        groups.setdefault(base_of(f, inc, exc), []).append(leaf)

    for base, leaves in groups.items():
        if len(leaves) < 3:
            continue
        # position in the chain == how many keywords this leaf excludes
        leaves.sort(key=lambda l: len(l["filters"].get(exc) or []))
        # longest suffix that fits the cap
        cut = None
        for i in range(len(leaves)):
            if sum(l["count"] for l in leaves[i:]) <= cl.EXPORT_LIMIT and len(leaves) - i >= 3:
                cut = i
                break
        if cut is None:
            continue
        tail = leaves[cut:]
        excl = list(tail[0]["filters"].get(exc) or [])
        if not excl:                      # nothing to exclude == whole cell, skip
            continue
        f = {k: v for k, v in tail[0]["filters"].items() if k not in (inc, exc)}
        f[exc] = excl
        # "exclude the first i" only equals this tail when the exclude-remainder
        # is IN the tail. If the remainder was split further (by size/revenue) it
        # sits in another group, and this filter re-swallows that whole
        # population -- measured 28,806 rows for a claimed 3,625. A free count()
        # settles it; skip the group unless the filter matches what we claim.
        claimed = sum(l["count"] for l in tail)
        live = cl.count(f)
        if live is None or live > cl.EXPORT_LIMIT or abs(live - claimed) > max(50, 0.05 * claimed):
            print(f"  skip merge ({len(tail)} slices): claimed {claimed:,} but filter returns {live}")
            continue
        merged = {"slug": cl.slugify("_".join([prefix] + [f"{exc[:3]}X{len(excl)}"] +
                                              [str(v) for k, v in sorted(f.items())
                                               if k.endswith("_include") for v in (v if isinstance(v, list) else [v])])),
                  "count": live, "oversized": False, "filters": f}
        for l in tail:
            l["_drop"] = True
        out.append(merged)
        merged_groups += 1
        saved += len(tail) - 1

# ---------------------------------------------------------------------------
# Strategy 2: OR-merge the tiny tail.
# Dropping a chained bucket's exclude list only WIDENS it, so OR-ing several
# tiny buckets' include values yields a SUPERSET of their union -- every row
# they held is still in it. Overlap with already-covered rows is harmless: we
# concatenate at merge, we don't dedupe. The one real risk is the cap, so the
# merged filter is only accepted when a live count comes back <= EXPORT_LIMIT
# (otherwise it would truncate and drop the very rows we're trying to keep).
# Unlike the suffix collapse this can merge buckets from ANY chain position.
# ---------------------------------------------------------------------------
TINY = 1500   # merge is live-count verified + halves on overflow, so aim high

for inc, exc, _order in CHAINS:
    groups = {}
    for leaf in plan:
        f = leaf["filters"]
        if leaf.get("_drop") or not f.get(inc) or leaf["count"] >= TINY:
            continue
        groups.setdefault(base_of(f, inc, exc), []).append(leaf)

    def or_merge(tiny, depth=0):
        """Merge these into one slice; if the union overflows the cap, halve and
        recurse rather than giving up -- two merged slices still beat thirty."""
        global merged_groups, saved
        if len(tiny) < 3 or depth > 3:
            return
        f = {k: v for k, v in tiny[0]["filters"].items() if k not in (inc, exc)}
        f[inc] = sorted({v for l in tiny for v in l["filters"][inc]})
        live = cl.count(f)
        if live is None:
            return
        if live > cl.EXPORT_LIMIT:
            mid = len(tiny) // 2
            or_merge(tiny[:mid], depth + 1)
            or_merge(tiny[mid:], depth + 1)
            return
        for l in tiny:
            l["_drop"] = True
        out.append({"slug": cl.slugify(f"{prefix}_{inc[:2]}or{len(f[inc])}_{_fhash(f)}"),
                    "count": live, "oversized": False, "filters": f})
        merged_groups += 1
        saved += len(tiny) - 1
        print(f"  OR-merged {len(tiny)} tiny slices -> 1 ({live} rows)")

    for base, tiny in groups.items():
        or_merge(sorted(tiny, key=lambda l: l["count"]))

kept = [l for l in plan if not l.get("_drop")]
new = kept + out
print(f"{prefix}: {len(plan)} slices -> {len(new)} ({saved} fewer, {merged_groups} tails collapsed)")
print(f"  stated rows: {sum(l['count'] for l in plan):,} -> {sum(l['count'] for l in new):,}")
if apply:
    json.dump(new, open(path, "w"), indent=1)
    print(f"  written: {path}")
else:
    print("  re-run with --apply")
