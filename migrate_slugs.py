#!/usr/bin/env python3
"""
One-off: rename downloads/<old-slug>/ dirs to the new collision-safe slug so the
resume logic still finds them (otherwise every truncated slice re-downloads at
full credit cost).

  unique old slug  -> rename to the new hashed slug, no re-download
  COLLIDING old slug (several slices shared one truncated name) -> we can't tell
      which slice the CSV belongs to, so park it as <slug>_legacy. Its rows still
      merge (merge globs the prefix) and every colliding slice re-downloads clean.

Usage: python3 migrate_slugs.py [--apply]
"""
import glob
import json
import os
import re
import sys
from collections import defaultdict

import clay_lib as cl

APPLY = "--apply" in sys.argv


def old_slugify(s):
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")[:90] or "slice"


owners = defaultdict(list)                      # old slug -> [raw slug strings]
for p in glob.glob(f"{cl.PLAN_DIR}/clicklist_*.json"):
    for s in json.load(open(p)):
        owners[old_slugify(s["slug"])].append(s["slug"])

renamed = parked = missing = 0
for old, raws in owners.items():
    src = os.path.join("downloads", old)
    if not os.path.isdir(src):
        missing += 1
        continue
    uniq = list(dict.fromkeys(raws))
    if len(uniq) == 1:
        new = cl.slugify(uniq[0])
        if new == old:
            continue
        dst = os.path.join("downloads", new)
        print(f"RENAME {old[:60]}... -> ...{new[-12:]}")
        if APPLY and not os.path.exists(dst):
            os.rename(src, dst)
            for f in glob.glob(os.path.join(dst, "*.csv")):   # file inside is named too
                os.rename(f, os.path.join(dst, new + ".csv"))
        renamed += 1
    else:
        dst = os.path.join("downloads", old + "_legacy")
        print(f"PARK   {old[:60]}... ({len(uniq)} slices collided)")
        if APPLY and not os.path.exists(dst):
            os.rename(src, dst)
        parked += 1

print(f"\n{'APPLIED' if APPLY else 'DRY RUN'}: {renamed} renamed, {parked} parked "
      f"(collided), {missing} planned-but-never-downloaded")
if not APPLY:
    print("re-run with --apply to perform it")
