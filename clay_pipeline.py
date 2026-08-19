#!/usr/bin/env python3
"""
TASK: download + merge. Reads a plan (clicklist_<prefix>.json) and materializes
each slice into a Clay table, exports it, downloads the CSV. SPENDS CREDITS
(~1 credit per record pulled). Resumable: skips slices already downloaded.

Usage:
  python3 clay_pipeline.py download <prefix> [max_slices] [asc|desc]
  python3 clay_pipeline.py merge    <prefix>
where <prefix> is the clicklist stem, e.g. Software_Development_United_States
"""
import csv
import json
import os
import sys
import traceback

import clay_lib as cl


def download(prefix, limit=5000, max_slices=None, order="desc"):
    with open(f"{cl.PLAN_DIR}/clicklist_{prefix}.json") as f:
        slices = json.load(f)
    slices = sorted(slices, key=lambda s: s["count"], reverse=(order != "asc"))
    total, done, skipped = 0, 0, 0
    for i, s in enumerate(slices, 1):
        if max_slices and done >= max_slices:
            print(f"\nbatch limit ({max_slices}) reached.", flush=True); break
        slug = cl.slugify(s["slug"])
        have = os.path.join("downloads", slug, slug + ".csv")
        # Treat a header-only file as NOT downloaded -- repairs empty slices left
        # by older runs, which would otherwise be skipped forever.
        if os.path.exists(have) and os.path.getsize(have) > 0:
            with open(have, newline="", encoding="utf-8", errors="replace") as fh:
                if sum(1 for _ in csv.reader(fh)) > 1:
                    skipped += 1
                    print(f"[{i}] SKIP (exists): {slug}", flush=True); continue
        tag = " OVERSIZED->truncates@5000" if s.get("oversized") else ""
        print(f"[{i}/{len(slices)}] {slug}  (~{s['count']} rows){tag}", flush=True)
        try:
            resp, cnt = cl.create_table(s["filters"], name=slug[:60], limit=limit)
            tid, vid, sid = resp.get("tableId"), resp.get("viewId"), resp.get("sourceId")
            if not tid:
                print(f"   CREATE FAILED (will retry next run): {str(resp)[:160]}", flush=True)
                continue
            cl.wait_populated(sid, min(cnt or s["count"] or 0, limit))
            got, path = cl.export_download(tid, vid, slug)
            cl.delete_table(tid)     # quota is the binding constraint, not storage
            if not path:
                print("   EXPORT FAILED (will retry next run)", flush=True)
                continue
            total += got or 0; done += 1
            print(f"   -> {got} rows -> {path}   (running total: {total:,})", flush=True)
        except Exception as e:                 # never let one slice kill the batch
            print(f"   SLICE ERROR (will retry next run): {e}", flush=True)
            traceback.print_exc()              # bare message hid a real TypeError
            continue
    print(f"\nDONE: {done} downloaded, {skipped} skipped, {total:,} records total.")


def merge(prefix):
    files, rows, out = cl.concat_slices(prefix)
    print(f"merged {files} files -> {rows:,} rows (no dedup) -> {out}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "download":
        prefix = sys.argv[2]
        mx = int(sys.argv[3]) if len(sys.argv) > 3 else None
        order = sys.argv[4] if len(sys.argv) > 4 else "desc"
        download(prefix, max_slices=mx, order=order)
    elif mode == "merge":
        merge(sys.argv[2])
    elif mode == "combine":
        # Union multiple master CSVs -> one combined master. combine <out> <in...>
        n = cl.union_csvs(sys.argv[2], sys.argv[3:])
        print(f"combined -> {n:,} unique companies -> {sys.argv[2]}")
    elif mode == "audit":
        # Point 4: broad reconnaissance BEFORE planning. Counts the industry total
        # and breakdowns by size / revenue / state, and shows the two discrepancies
        # that cap the pull: BLANK attributes (sum < total) and multi-location
        # OVERLAP (sum > total). Free (counts only).
        from clay_geo import GEO
        industry = sys.argv[2]
        country = sys.argv[3] if len(sys.argv) > 3 else "United States"
        base = {"industries": [industry], "country_names": [country]}
        total = cl.count(base) or 0
        print(f"TOTAL: {industry} + {country} = {total:,}\n")

        ssum = sum(cl.count({**base, "sizes": [c]}) or 0 for c in cl.SIZE_CODES)
        print(f"  by SIZE    sum={ssum:,}   blank-size ≈ {total-ssum:,} "
              f"({100*(total-ssum)/total:.1f}% have no size)")
        rsum = sum(cl.count({**base, "annual_revenues": [b]}) or 0 for b in cl.REVENUE_BANDS)
        print(f"  by REVENUE sum={rsum:,}   blank-revenue ≈ {total-rsum:,} "
              f"({100*(total-rsum)/total:.1f}% have no revenue)")
        states = GEO.get(country, {}).get("states", {})
        stsum = sum(cl.count({**base, "location_states_include": [s]}) or 0 for s in states)
        print(f"  by STATE   sum={stsum:,}   overlap ≈ {stsum-total:+,} "
              f"({100*(stsum-total)/total:+.1f}% multi-state / pulled twice)")
        print("\nInterpretation: blank-% caps coverage (can't filter blanks); "
              "overlap-% is the dedup waste (pulled repeatedly). Both lower the "
              "unique yield below TOTAL. Combining multiple pulls recovers more.")
    elif mode == "diag":
        # Point 2: how much does the ACTUAL pull differ from Clay's stated count?
        prefix = sys.argv[2]
        slices = json.load(open(f"{cl.PLAN_DIR}/clicklist_{prefix}.json"))
        pred_tot = act_tot = exact = present = 0
        shrink = []
        for s in slices:
            slug = cl.slugify(s["slug"])
            p = os.path.join("downloads", slug, slug + ".csv")
            if not os.path.exists(p):
                continue
            present += 1
            with open(p, newline="", encoding="utf-8", errors="replace") as f:
                n = max(0, sum(1 for _ in csv.reader(f)) - 1)
            pred_tot += s["count"]; act_tot += n
            if s["count"] == n:
                exact += 1
            shrink.append((s["count"] - n, s["count"], n, s["slug"][:55]))
        print(f"slices with CSV: {present}/{len(slices)}")
        print(f"predicted (sum of stated counts): {pred_tot:,}")
        print(f"actual    (sum of pulled rows):   {act_tot:,}  "
              f"(shortfall {pred_tot-act_tot:,} = {100*(pred_tot-act_tot)/pred_tot:.1f}%)")
        print(f"slices where pulled == stated exactly: {exact}/{present}")
        shrink.sort(reverse=True)
        print("biggest per-slice shortfalls (stated -> pulled):")
        for d, p_, a_, name in shrink[:8]:
            print(f"  -{d:<4} {p_:>5}->{a_:<5} {name}")
    elif mode == "compare":
        def keys(path):
            s = set()
            with open(path, newline="", encoding="utf-8", errors="replace") as f:
                r = csv.reader(f); h = next(r, None)
                di = h.index("Domain"); li = h.index("LinkedIn URL")
                for row in r:
                    d = row[di].strip().lower() if di < len(row) else ""
                    k = d or (("li:" + row[li].strip().lower())
                              if li < len(row) and row[li].strip() else None)
                    if k:
                        s.add(k)
            return s
        a, b = keys(sys.argv[2]), keys(sys.argv[3])
        print(f"A (old) = {len(a):,}")
        print(f"B (new) = {len(b):,}")
        print(f"common  = {len(a & b):,}")
        print(f"A only  = {len(a - b):,}  (in old, missing from new)")
        print(f"B only  = {len(b - a):,}  (in new, missing from old)")
        print(f"UNION   = {len(a | b):,}  (combined + deduped)")
    elif mode == "overlapcheck":
        from clay_geo import US_STATES
        base = {"industries": ["Software Development"], "country_names": ["United States"]}
        hq = {**base, "location_headquarters_only": True}
        total_any, total_hq = cl.count(base), cl.count(hq)
        cl.log(f"total  any-location={total_any:,}   HQ-only={total_hq:,}")
        s_any = s_hq = 0
        for st in US_STATES:
            a = cl.count({**base, "location_states_include": [st]}) or 0
            h = cl.count({**hq, "location_states_include": [st]}) or 0
            s_any += a; s_hq += h
        print(f"\nANY-LOCATION: total={total_any:,}  sum(states)={s_any:,}  "
              f"overlap={s_any - total_any:+,} ({100*(s_any-total_any)/total_any:+.1f}%)")
        print(f"HQ-ONLY     : total={total_hq:,}  sum(states)={s_hq:,}  "
              f"overlap={s_hq - total_hq:+,} ({100*(s_hq-total_hq)/total_hq:+.1f}%)")
    elif mode == "selftest":
        # Exercise the planner logic with a deterministic MOCK count (no credits).
        def mock(filters):
            applied = [k for k in filters if k not in ("industries", "country_names")]
            n = 200000
            for k in applied:
                frag = json.dumps(filters[k], sort_keys=True)
                n = max(1, n // (sum(ord(c) for c in (k + frag)) % 7 + 3))
            return n
        stats, base = cl.run("Test", "United States", count_fn=mock)
        cov = sum(l.count for l in stats.leaves)
        assert all(l.count <= cl.EXPORT_LIMIT or l.oversized for l in stats.leaves)
        print(f"selftest OK: {len(stats.leaves)} leaves "
              f"({len(stats.oversized)} oversized), {len(stats.uncovered)} uncovered, "
              f"covered={cov:,}, count_calls={stats.count_calls}")
        for l in sorted(stats.leaves, key=lambda x: -x.count)[:6]:
            f = l.filters
            print(f"  {l.count:>6}  st={f.get('location_states_include')} "
                  f"city={f.get('location_cities_include')} "
                  f"zip={f.get('location_postal_codes_include')} sz={f.get('sizes')}")
    else:
        print("usage: download <prefix> [max] [asc|desc]  |  merge <prefix>")
