#!/usr/bin/env python3
"""
clay_lib -- shared library for the Clay company-extraction pipeline.

Consolidates auth, the free count oracle, table create/populate, export/download,
dedup, and the partition PLANNER (generic per-country, geography-first + postal).
Not run directly; imported by the task scripts:
  generate_clicklist.py  (plan)   clay_pipeline.py (download+merge)   map_industries.py (map)

Auth = the browser session cookie in .clay_cookie.txt (kept out of code).
Rotate the Clay session when done.
"""
from __future__ import annotations

import csv
import glob
import hashlib
import json
import os
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

csv.field_size_limit(2147483647)

# ---------------------------------------------------------------------------
# Config / auth
# ---------------------------------------------------------------------------
import clay_users

WORKSPACE_ID = "744216"
COOKIE_FILE = ".clay_cookie.txt"
PLAN_DIR = "plans"          # clicklist_*.json/.csv live here (see archive/ for junk)
FRONTEND_VERSION = "v20260815_170454z_6bd76386ec"
CONVERSATION_ID = ""

COUNT_URL = "https://api.clay.com/v3/actions/run-cpj-preview-enrichment"
CREATE_URL = "https://api.clay.com/v3/sources/create-cpj-table"
EXPORT_URL = "https://api.clay.com/v3/tables/{t}/views/{v}/export"
POLL_URL = "https://api.clay.com/v3/exports/{id}"
SOURCE_URL = "https://api.clay.com/v3/sources/{s}"

HEADERS = [
    "accept: application/json, text/plain, */*",
    "content-type: application/json",
    "origin: https://app.clay.com",
    "referer: https://app.clay.com/",
    "x-clay-frontend-version: " + FRONTEND_VERSION,
    "user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
]

_CACHED_WORKSPACES = {}

def get_active_workspace_id(cookie_str=None, user_id=None):
    """Dynamically resolves the active Clay workspace ID from API without hardcoded IDs."""
    c = cookie_str or _cookie(user_id=user_id)
    if not c:
        return os.environ.get("CLAY_WORKSPACE_ID", WORKSPACE_ID)
    if c in _CACHED_WORKSPACES:
        return _CACHED_WORKSPACES[c]
    try:
        clean_c = clay_users.extract_clean_cookie(c)
        headers_dict = {
            "accept": "application/json, text/plain, */*",
            "cookie": clean_c,
            "origin": "https://app.clay.com",
            "referer": "https://app.clay.com/",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
            "x-clay-frontend-version": FRONTEND_VERSION
        }
        import requests
        r = requests.get("https://api.clay.com/v3/my-workspaces", headers=headers_dict, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict) and "results" in data and len(data["results"]) > 0:
                wid = str(data["results"][0].get("id", WORKSPACE_ID))
                _CACHED_WORKSPACES[c] = wid
                return wid
            elif isinstance(data, list) and len(data) > 0:
                wid = str(data[0].get("id", WORKSPACE_ID))
                _CACHED_WORKSPACES[c] = wid
                return wid
            elif isinstance(data, dict) and "id" in data:
                wid = str(data.get("id", WORKSPACE_ID))
                _CACHED_WORKSPACES[c] = wid
                return wid
    except Exception:
        pass
    return os.environ.get("CLAY_WORKSPACE_ID", WORKSPACE_ID)

# Full inputs template captured from the UI; we override only the filter keys.
INPUTS_TEMPLATE = {
    "annual_revenues": [], "company_identifier": [], "country_names": [],
    "country_names_exclude": [], "derived_business_types": [],
    "derived_industries": [], "derived_revenue_streams": [],
    "derived_subindustries": [], "derived_subindustries_exclude": [],
    "description_keywords": [], "description_keywords_exclude": [],
    "domainFieldId": None, "exclude_entities_configuration": [],
    "exclude_entities_bitmap": None, "previous_entities_bitmap": None,
    "exclude_company_identifiers_mixed": [], "funding_amounts": [],
    "industries": [], "industries_exclude": [], "include_company_identifiers": [],
    "limit": 1, "lookalike_max_results": 100, "lookalike_similarity_tier": "A",
    "cluster_count": None, "clustering_method": "agglomerative",
    "locations": [], "locations_exclude": [], "location_cities_include": [],
    "location_cities_exclude": [], "location_states_include": [],
    "location_states_exclude": [], "location_regions_include": [],
    "location_regions_exclude": [], "location_postal_codes_include": [],
    "location_postal_codes_exclude": [], "location_headquarters_only": False,
    "search_raw_location": False, "maximum_member_count": None,
    "minimum_follower_count": None, "minimum_member_count": None, "name": "",
    "radialKnnMinScore": None, "has_resolved_domain": None,
    "resolved_domain_is_live": None, "resolved_domain_redirects": None,
    "semantic_description": "", "sizes": [], "start_from_method": "CsvOfCompanies",
    "company_record_id": [], "company_table_field_id": None, "company_table_id": "",
    "company_table_view_id": None, "company_audience_segment_id": None,
    "startFromCompanyType": "company_identifier", "tableId": None,
    "technographics_main_categories": [], "technographics_parent_categories": [],
    "technographics_products": [], "technographics_vendors": [], "types": [],
    "useRadialKnn": False, "result_count": True,
}

BASIC_FIELDS = [
    {"name": "Name", "dataType": "text", "formulaText": "{{source}}.name"},
    {"name": "Description", "dataType": "text", "formulaText": "{{source}}.description"},
    {"name": "Primary Industry", "dataType": "text", "formulaText": "{{source}}.industry"},
    {"name": "Size", "dataType": "select", "options": [
        {"id": "27602780-bd69-4225-a0e6-f0a4d09990f4", "text": "Self-employed", "color": "yellow"},
        {"id": "10b97b08-e0f5-42e0-818d-ac67de09e89f", "text": "2-10 employees", "color": "blue"},
        {"id": "71629641-412f-49e3-9c02-625791077afa", "text": "11-50 employees", "color": "green"},
        {"id": "7dcb1b9d-b74c-4c3c-98c4-f9af47f601b0", "text": "51-200 employees", "color": "red"},
        {"id": "7947eadf-58f3-4f18-bd61-1bd70e3b411c", "text": "201-500 employees", "color": "violet"},
        {"id": "2034ec6e-1978-48be-b81a-5d9ffb21f870", "text": "501-1,000 employees", "color": "grey"},
        {"id": "db88beb1-f4f5-40a2-925c-d626af73a858", "text": "1,001-5,000 employees", "color": "orange"},
        {"id": "61d44f95-e4e5-4ae2-96e2-bb330f9be87a", "text": "5,001-10,000 employees", "color": "pink"},
        {"id": "5f3bcc21-bdd6-4795-a069-3bdfdd422088", "text": "10,001+ employees", "color": "yellow"},
    ], "formulaText": "{{source}}.size"},
    {"name": "Type", "dataType": "text", "formulaText": "{{source}}.type"},
    {"name": "Location", "dataType": "text", "formulaText": "{{source}}.location"},
    {"name": "Country", "dataType": "text", "formulaText": "{{source}}.country"},
    {"name": "Domain", "dataType": "url", "formulaText": "{{source}}.domain"},
    {"name": "LinkedIn URL", "dataType": "url", "formulaText": "{{source}}.linkedin_url",
     "isDedupeField": True},
]


def _cookie(*args, **kwargs):
    uid = None
    if args:
        uid = args[0]
    elif "user_id" in kwargs:
        uid = kwargs["user_id"]
    elif "username" in kwargs:
        uid = kwargs["username"]

    if not uid:
        uid = os.environ.get("CLAY_USER_ID")
    if not uid:
        try:
            import streamlit as st
            uid = st.session_state.get("user_id")
        except Exception:
            pass

    # 1. User specific cookie
    if uid:
        user_c = clay_users.get_user_cookie(uid)
        if user_c:
            return user_c
        # Specific user has no cookie configured -> do NOT leak another user's cookie!
        return ""

    # 2. Environment variable
    if os.environ.get("CLAY_COOKIE"):
        return os.environ.get("CLAY_COOKIE").strip()

    # 3. Streamlit secrets
    try:
        import streamlit as st
        if "CLAY_COOKIE" in st.secrets:
            return str(st.secrets["CLAY_COOKIE"]).strip()
    except Exception:
        pass

    # No fallback to other users
    return ""


def _post(url, body, retries=3, timeout=30):
    cmd = ["curl", "-s", "--max-time", str(timeout), "-X", "POST", url, "-b", _cookie()]
    for h in HEADERS:
        cmd += ["-H", h]
    cmd += ["-d", "@-"]
    payload = json.dumps(body)
    for attempt in range(retries):
        try:
            return subprocess.run(cmd, input=payload, capture_output=True, encoding="utf-8", errors="replace", timeout=timeout + 5).stdout
        except subprocess.TimeoutExpired:
            time.sleep(1.5 * (attempt + 1))
    return ""            # caller's json.loads fails -> handled as transient


def _get(url, retries=3):
    cmd = ["curl", "-s", "--max-time", "55", "-w", "\n__HTTP__%{http_code}", url,
           "-b", _cookie()]
    for h in HEADERS:
        cmd += ["-H", h]
    for attempt in range(retries):
        try:
            out = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", timeout=60).stdout
            body, _, code = out.rpartition("__HTTP__")
            return code.strip(), body.strip()
        except subprocess.TimeoutExpired:
            time.sleep(2 * (attempt + 1))
    return "timeout", ""


def slugify(s):
    slug = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_") or "slice"
    if len(slug) > 90:
        # Truncation alone can collide (two different filter combos sharing a
        # 90-char prefix) and silently drop a slice via the download-resume skip.
        slug = slug[:81].rstrip("_") + "_" + hashlib.md5(s.encode()).hexdigest()[:8]
    return slug


# ---------------------------------------------------------------------------
# Logging -- flushed + elapsed-time stamped so background runs are watchable.
# ---------------------------------------------------------------------------
import sys as _sys  # noqa: E402

VERBOSE = True
_T0 = [None]


def log(msg):
    if not VERBOSE:
        return
    if _T0[0] is None:
        _T0[0] = time.time()
    el = int(time.time() - _T0[0])
    print(f"[{el // 60:02d}:{el % 60:02d}] {msg}", flush=True, file=_sys.stdout)


# ---------------------------------------------------------------------------
# Count oracle (free) + table create / populate / export
# ---------------------------------------------------------------------------
def build_inputs(filters):
    inputs = dict(INPUTS_TEMPLATE)
    inputs.update(filters)
    return inputs


def count_raw(filters):
    body = {"workspaceId": WORKSPACE_ID,
            "enrichmentType": "find-lists-of-companies-with-mixrank-source-preview",
            "options": {"returnTaskId": True, "returnActionMetadata": True},
            "inputs": build_inputs(filters)}
    return _post(COUNT_URL, body, timeout=15)


_COUNT_CACHE = {}


def count(filters, retries=6):
    """Exact companyCount (free, no 1M-cap impact). None on repeated failure."""
    import random
    key = json.dumps(filters, sort_keys=True)
    if key in _COUNT_CACHE:
        return _COUNT_CACHE[key]
    for attempt in range(1, retries + 1):
        raw = count_raw({**filters, "limit": 1})
        try:
            if raw:
                parsed = json.loads(raw)
                res = parsed.get("result")
                if res is not None:
                    c = res.get("companyCount")
                    if c is None or isinstance(c, int):
                        _COUNT_CACHE[key] = c
                    return c
                # If rate limited (TooManyRequests), backoff longer
                if parsed.get("type") == "TooManyRequests":
                    time.sleep(2.0 * attempt + random.uniform(1.0, 3.0))
                    continue
        except Exception:
            pass
        time.sleep(min(15, 1.2 ** attempt + random.uniform(0.5, 1.5)))
    return None


def preview(filters, retries=7):
    """limit:1 -> valid previewActionTaskId AND exact count. Retries if the count
    endpoint transiently returns a null taskId (which would fail create_table).

    Under concurrent downloads Clay throttles this endpoint by returning a null
    taskId rather than a 429 -- measured ~22% of slices with 3 shards running vs
    ~1% single-threaded -- so the backoff has to outlast a throttling window."""
    for attempt in range(retries):
        try:
            o = json.loads(count_raw({**filters, "limit": 1}))
            if o.get("taskId"):
                return o["taskId"], (o.get("result") or {}).get("companyCount")
        except Exception:
            pass
        time.sleep(min(30, 2 * (attempt + 1) ** 2))
    return None, None


def create_table(filters, name="Companies Search", limit=5000):
    task_id, cnt = preview(filters)
    if not task_id:            # don't POST a null previewActionTaskId -- Clay 400s
        return {"error": "preview throttled (null taskId); slice deferred"}, cnt
    inputs = build_inputs(filters)
    inputs["limit"] = limit
    inputs.pop("result_count", None)
    body = {
        "workspaceId": get_active_workspace_id(), "workbookName": name, "workbookId": None,
        "conversationId": CONVERSATION_ID, "assignedFieldId": "f_companies_search",
        "cpjConfig": {
            "type": "companies",
            "typeSettings": {
                "name": "Find companies", "iconType": "BuildingWithMagnifyingGlass",
                "actionKey": "find-lists-of-companies-with-mixrank-source",
                "actionPackageId": "e251a70e-46d7-4f3a-b3ef-a211ad3d8bd2",
                "previewTextPath": "name", "defaultPreviewText": "Profile",
                "recordsPath": "companies", "idPath": "linkedin_company_id",
                "scheduleConfig": {"runSettings": "once"}, "hasEvaluatedInputs": False,
                "inputs": inputs,
                "previewActionKey": "find-lists-of-companies-with-mixrank-source-preview",
            },
            "clientSettings": {"tableType": "company"},
            "basicFields": BASIC_FIELDS, "previewActionTaskId": task_id,
        },
    }
    return json.loads(_post(CREATE_URL, body)), cnt


def delete_table(table_id):
    """Drop the Clay table once its CSV is on disk. The workspace has a hard 15M
    row ceiling; leaving tables behind eventually makes every NEW view materialise
    empty (source populates, totalRecordsInViewCount stays 0) -- which reads as
    'EXPORT FAILED' with no hint of the real cause. Best-effort, never fatal."""
    cmd = ["curl", "-s", "--max-time", "45", "-X", "DELETE",
           f"https://api.clay.com/v3/tables/{table_id}", "-b", _cookie()]
    for h in HEADERS:
        cmd += ["-H", h]
    try:
        subprocess.run(cmd, capture_output=True, timeout=60)
    except Exception:
        pass


def source_records(source_id):
    code, b = _get(SOURCE_URL.format(s=source_id))
    try:
        st = json.loads(b).get("state", {})
        return st.get("action", {}).get("status"), st.get("numSourceRecords", 0)
    except Exception:
        return None, 0


def wait_populated(source_id, expected, timeout=600):
    """Wait for Clay to populate the table before exporting.

    "Count stopped changing" is only trustworthy once we're near the expected
    size: a throttled populate can sit at 1 record for several polls, and
    exporting there yields a 1-row CSV that looks like a successful slice.
    Far from target we demand a much longer plateau before giving up."""
    last, stable, zero = -1, 0, 0
    for _ in range(timeout // 3):
        _, n = source_records(source_id)
        if expected and n >= expected:
            return n
        # A table stuck at ZERO never trips the stability rule below (it requires
        # n > 0), so it burned the whole timeout -- 10 minutes on a 1-row slice.
        zero = zero + 1 if n == 0 else 0
        if zero >= 20:                      # 60s of nothing: it is not coming
            log("   populate stalled at 0 -- giving up on this slice")
            return 0
        stable = stable + 1 if (n == last and n > 0) else 0
        if stable >= (3 if (not expected or n >= 0.9 * expected) else 20):
            if expected and n < 0.9 * expected:
                log(f"   WARN populate plateaued at {n}/{expected}")
            return n
        last = n
        time.sleep(3)
    return last


def export_raw(table_id, view_id, body="{}", retries=3):
    cmd = ["curl", "-s", "--max-time", "170", "-X", "POST",
           EXPORT_URL.format(t=table_id, v=view_id), "-b", _cookie()]
    for h in HEADERS:
        cmd += ["-H", h]
    cmd += ["-d", "@-"]
    for attempt in range(retries):
        try:
            return subprocess.run(cmd, input=body, capture_output=True, text=True, timeout=180).stdout
        except subprocess.TimeoutExpired:
            time.sleep(2 * (attempt + 1))
    return ""


def export_download(table_id, view_id, slug, base_dir="downloads", poll_timeout=120):
    """Trigger export, wait, download CSV into its own folder, drop Clay's empty
    leading title column. Returns (record_count, path)."""
    t0 = time.time()
    dl = None
    # The VIEW lags behind the source: wait_populated() confirms the source has
    # records, but the export runs against the view, which can still be empty.
    # That yields a FINISHED job with recordsExportedCount=0 and a header-only
    # CSV. Re-trigger the export until the view catches up.
    for attempt in range(4):
        resp = export_raw(table_id, view_id)
        try:
            job = json.loads(resp[resp.find("{"):resp.rfind("}") + 1])
        except Exception:
            return None, None
        jid = job.get("id")
        if not jid:
            return None, None
        exported = 0
        for _ in range(poll_timeout // 2):
            _, b = _get(POLL_URL.format(id=jid))
            try:
                j = json.loads(b)
            except Exception:      # transient poll failure -> keep polling
                time.sleep(2)
                continue
            if j.get("downloadUrl") and j.get("status") == "FINISHED":
                exported = j.get("recordsExportedCount") or 0
                if exported:
                    dl = j["downloadUrl"]
                break
            time.sleep(2)
        if dl:
            break
        log(f"   export returned 0 records (view lagging) -- retry {attempt + 2}/4")
        time.sleep(5 * (attempt + 1))
    if not dl:
        return None, None
    t1 = time.time()
    slug = slugify(slug)
    out_dir = os.path.join(base_dir, slug)
    os.makedirs(out_dir, exist_ok=True)
    raw = os.path.join(out_dir, slug + "_raw.csv")
    final = os.path.join(out_dir, slug + ".csv")
    
    # Download the CSV from S3 downloadUrl with retries
    downloaded_ok = False
    for dl_attempt in range(3):
        try:
            import urllib.request
            urllib.request.urlretrieve(dl, raw)
            if os.path.exists(raw) and os.path.getsize(raw) > 0:
                downloaded_ok = True
                break
        except Exception:
            pass
        try:
            subprocess.run(["curl", "-s", "-o", raw, dl], timeout=180)
            if os.path.exists(raw) and os.path.getsize(raw) > 0:
                downloaded_ok = True
                break
        except Exception:
            pass
        time.sleep(2 * (dl_attempt + 1))
        
    if not downloaded_ok or not os.path.exists(raw) or os.path.getsize(raw) == 0:
        log(f"   [download error] Failed to download CSV file from S3 for slice {slug}")
        return 0, None

    t2 = time.time()
    raw_size_mb = os.path.getsize(raw) / 1e6 if os.path.exists(raw) else 0.0
    log(f"   export job {t1-t0:.1f}s | file transfer {t2-t1:.1f}s ({raw_size_mb:.2f} MB)")
    n = 0
    with open(raw, newline="", encoding="utf-8", errors="replace") as fin, \
         open(final, "w", newline="", encoding="utf-8-sig") as fout:
        w = csv.writer(fout)
        for i, row in enumerate(csv.reader(fin)):
            w.writerow(row[1:])
            if i:
                n += 1
    time.sleep(0.1)
    for _ in range(5):
        try:
            if os.path.exists(raw):
                os.remove(raw)
            break
        except Exception:
            time.sleep(0.5)
    if n == 0:
        # An empty CSV is worse than none: download() skips any slice whose file
        # exists, so a header-only export would block this slice permanently.
        try:
            if os.path.exists(final):
                os.remove(final)
        except Exception:
            pass
        return 0, None
    return n, final


def union_csvs(out_path, paths):
    """Union several company CSVs into out_path, deduped by Domain (falling back
    to LinkedIn URL). Returns unique count. Used for cumulative accumulation."""
    seen, rows, header = set(), [], None
    for p in paths:
        if not os.path.exists(p):
            continue
        with open(p, newline="", encoding="utf-8", errors="replace") as f:
            r = csv.reader(f)
            h = next(r, None)
            if not h:
                continue
            header = header or h
            di = h.index("Domain") if "Domain" in h else None
            li = h.index("LinkedIn URL") if "LinkedIn URL" in h else None
            for row in r:
                dom = row[di].strip().lower() if di is not None and di < len(row) else ""
                lnk = row[li].strip().lower() if li is not None and li < len(row) else ""
                key = dom or (("li:" + lnk) if lnk else None)
                if key is not None and key in seen:
                    continue
                if key is not None:
                    seen.add(key)
                rows.append(row)
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if header:
            w.writerow(header)
        w.writerows(rows)
    return len(rows)


def concat_slices(industry_safe, base="downloads"):
    """Concatenate an industry's downloaded slice CSVs into one file. No dedup --
    slice overlap (multi-location companies) stays in; dedup happens at DB insert."""
    paths = sorted(glob.glob(f"{base}/{industry_safe}*/*.csv"))
    rows, header = [], None
    for p in paths:
        with open(p, newline="", encoding="utf-8", errors="replace") as f:
            r = csv.reader(f)
            h = next(r, None)
            if not h:
                continue
            header = header or h
            rows.extend(r)
    out = f"{base}/{industry_safe}_ALL.csv"
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if header:
            w.writerow(header)
        w.writerows(rows)
    return len(paths), len(rows), out


# ---------------------------------------------------------------------------
# Geography config (per country). size/revenue bands are GLOBAL (below).
# To add a country: supply its admin-1 regions ("states"), major "cities", and
# optional per-city "postal" ZIP lists for cities dense enough to exceed 4,800.
# ---------------------------------------------------------------------------
from clay_geo import GEO  # noqa: E402  (kept in a separate data file, see clay_geo.py)

SIZE_CODES = ["1", "2", "10", "50", "200", "500", "1000", "5000", "10000"]
REVENUE_BANDS = ["0-500K", "500K-1M", "1M-5M", "5M-10M", "10M-25M", "25M-75M",
                 "75M-200M", "200M-500M", "500M-1B", "1B-10B", "10B-100B", "100B-1T"]

EXPORT_LIMIT = 5000    # Clay's hard export/pull ceiling; free count overestimates
MAX_DEPTH = 10          # actual pulls, so planning right at 5000 is safe


@dataclass
class Bucket:
    label: str
    predicate: dict
    value: object = None      # the dim value, so plan() can stop the chain early


@dataclass
class Dimension:
    name: str
    key: str
    values: list
    exclude_key: str | None = None
    parent_map: dict | None = None    # {parent_value: [child values]} -> scoped dim
    parent_key: str | None = None     # filter key holding the parent value(s)
    only_when_no: str | None = None   # skip this dim if this filter key is set
    stop_below: int = 0               # stop chaining once a bucket returns < this
    stop_min_buckets: int = 4         # ...but always try at least this many

    def resolve_values(self, filters):
        # Region-postal splits a state's city-EXCLUDE remainder (no city set), so
        # it must NOT fire on leaves that already have a city.
        if self.only_when_no and filters.get(self.only_when_no):
            return []
        # Scoped dims (city under state, postal under city/state) only enumerate
        # the children of the parent(s) currently in the filter -> no cross-product.
        if self.parent_map is not None:
            out = []
            for p in (filters.get(self.parent_key) or []):
                out += self.parent_map.get(p, [])
            return list(dict.fromkeys(out))   # dedup, keep order
        return self.values

    def buckets_for(self, filters):
        return [Bucket(f"{self.name}-{v}", {self.key: [v]})
                for v in self.resolve_values(filters)]


class ChainedDimension(Dimension):
    """description_keywords is the only splitter whose include+exclude is a COMPLETE
    partition (verified: include + exclude == cell total, no blanks -- unlike
    sizes/revenues). Bucket i = "contains kw_i but none of kw_1..kw_i-1", so the
    buckets are disjoint and the dim's exclude remainder sweeps up the rest.

    Excludes ACCUMULATE across rounds: a later round splits the previous round's
    "none of the above" remainder, so its buckets must keep carrying the earlier
    exclusions or they'd re-admit rows the parent already ruled out."""

    def _prev(self, filters):
        return list(filters.get(self.exclude_key) or [])

    def _new(self, filters):
        prev = self._prev(filters)
        return [v for v in self.values if v not in prev]

    def resolve_values(self, filters):
        # include is OR, so a cell already pinned to a keyword can't be split
        # further by another include -- let it fall through to size/revenue.
        if filters.get(self.key):
            return []
        return self._prev(filters) + self._new(filters)   # remainder excludes ALL

    def buckets_for(self, filters):
        if filters.get(self.key):
            return []
        prev, new = self._prev(filters), self._new(filters)
        return [Bucket(f"{self.name}-{v}", {self.key: [v], self.exclude_key: prev + new[:i]}, v)
                for i, v in enumerate(new)]


# Generic description words -- this dim runs for every country/industry, and only
# on cells still over the cap after geography. Each round chops the previous
# round's remainder; the last round is deliberately near-universal filler words.
KEYWORD_ROUNDS = [
    ["services", "ltd", "limited", "group", "solutions", "management",
     "company", "london", "design", "consulting", "systems", "trading"],
    ["building", "property", "engineering", "contractors", "homes", "projects",
     "developments", "maintenance", "installations", "roofing", "plumbing", "electrical"],
    ["uk", "north", "south", "east", "west", "city",
     "national", "international", "family", "quality", "professional", "specialist"],
    ["we", "our", "the", "and", "for", "with",
     "provide", "offer", "based", "established", "experience", "team"],
]

KEYWORD_DIMS = [ChainedDimension(f"kw{n}", "description_keywords", kws,
                                 exclude_key="description_keywords_exclude",
                                 stop_below=150)
                for n, kws in enumerate(KEYWORD_ROUNDS, 1)]

# Company type. No types_exclude exists (probed: types_exclude / company_types_exclude
# / derived_business_types_exclude all return the UNFILTERED total -- Clay ignores
# unknown filter keys, i.e. an unsupported filter fails OPEN). So it's lossy like
# size/revenue, but measured at only ~12% blank vs size's ~38%, and it splits cells
# the lossless dims have already run out of moves on.
TYPE_VALUES = ["Privately Held", "Public Company", "Partnership", "Self-Employed",
               "Self-Owned", "Nonprofit", "Educational", "Government Agency"]
TYPE = Dimension("type", "types", TYPE_VALUES)                # no exclude in Clay

SIZE = Dimension("size", "sizes", SIZE_CODES)                 # no exclude in Clay
REVENUE = Dimension("revenue", "annual_revenues", REVENUE_BANDS)  # no exclude

# Consolidate merges along these include keys, in this order.
DIM_INCLUDE_KEYS = ["location_states_include", "location_cities_include",
                    "location_postal_codes_include", "sizes", "annual_revenues"]


def build_dims(country):
    """Geography-first, scoped: state -> its cities -> that city's ZIPs, then
    size/revenue last. Geo dims are excludable so their remainders sweep up
    blank-location rows; scoping avoids the state x city x postal cross-product."""
    geo = GEO.get(country, {})
    dims = []
    states = geo.get("states")            # {state: [cities]}
    if states:
        dims.append(Dimension("state", "location_states_include",
                              list(states.keys()),
                              exclude_key="location_states_exclude"))
        dims.append(Dimension("city", "location_cities_include", [],
                              exclude_key="location_cities_exclude",
                              parent_map=states, parent_key="location_states_include"))
    cities = geo.get("cities")            # flat [city] list, no state parent (city-states)
    if cities:
        dims.append(Dimension("city", "location_cities_include", cities,
                              exclude_key="location_cities_exclude"))
    postal = geo.get("postal")            # {city: [zips]}
    if postal:
        dims.append(Dimension("postal", "location_postal_codes_include", [],
                              exclude_key="location_postal_codes_exclude",
                              parent_map=postal, parent_key="location_cities_include"))
    # Region-postal: split a state's city-exclude remainder by its suburb postals
    # (only fires when no city is set). Lets a dense region-remainder (e.g. the
    # Île-de-France long tail) be split geographically instead of leaking to size.
    state_postal = geo.get("state_postal")   # {state: [postal codes]}
    if state_postal:
        dims.append(Dimension("regionpostal", "location_postal_codes_include", [],
                              exclude_key="location_postal_codes_exclude",
                              parent_map=state_postal, parent_key="location_states_include",
                              only_when_no="location_cities_include"))
    # Fallback splitters (no exclude filter -> their blanks leak). Order them so
    # the LOWER-blank-rate dimension goes FIRST, since it splits every dense cell.
    # Default size-first (good for US). Countries where size data is sparse (e.g.
    # France, ~53% blank size) set "fallback": ["revenue", "size"] in clay_geo.
    # Counties via Clay's free-form `locations` filter -- verified complete
    # (Kent 4,697 + exclude 272,944 == England 277,641). Real geographic
    # granularity where admin-1 is thin (England is one state of 277k).
    # Chained: a location string can match several county names at once.
    counties = geo.get("counties")
    if counties and not os.getenv("CLAY_NO_COUNTIES"):
        dims.append(ChainedDimension("county", "locations", counties,
                                     exclude_key="locations_exclude"))   # no early-stop
    # Keywords BEFORE size/revenue: plan() records a no-exclude dim's remainder as
    # uncovered without recursing, so anything after size never gets a chance to
    # rescue those blanks. Only fires on cells still oversized after geography.
    dims += KEYWORD_DIMS
    fb = {"size": SIZE, "revenue": REVENUE}
    for name in geo.get("fallback", ["size", "revenue"]):
        dims.append(fb[name])
    # TYPE goes LAST, not before size/revenue. plan() records a no-exclude dim's
    # remainder as uncovered WITHOUT recursing, so an early lossy dim strands its
    # own blanks AND the later dims strand theirs -- measured: type-first turned
    # ~89.7k truncated rows into 275.9k unreachable ones. Here it only fires on
    # cells still oversized after everything else, where the alternative is a
    # slice that truncates at 5,000 anyway.
    # dims.append(TYPE)   # see TYPE_VALUES note -- measured net-negative, left off
    return dims


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------
@dataclass
class Leaf:
    filters: dict
    label: str
    count: int
    oversized: bool = False


@dataclass
class PlanStats:
    count_calls: int = 0
    leaves: list = field(default_factory=list)
    oversized: list = field(default_factory=list)
    uncovered: list = field(default_factory=list)   # (label, count) blank size/rev
    merged_from: int = 0


def _merge(base, pred):
    out = dict(base)
    out.update(pred)
    return out


def plan(base_filters, base_label, dims, count_fn, stats, depth=0, known_count=None):
    if known_count is None:
        stats.count_calls += 1
        total = count_fn(base_filters)
        if total is None:
            for retry_att in range(3):
                time.sleep(2 * (retry_att + 1))
                total = count_fn(base_filters)
                if total is not None:
                    break
    else:
        total = known_count

    if total is None:
        stats.uncovered.append((base_label + " [count-failed]", 0, dict(base_filters)))
        return
    if total == 0:
        return
    if total <= EXPORT_LIMIT:
        stats.leaves.append(Leaf(base_filters, base_label, total)); return
    if not dims or depth >= MAX_DEPTH:
        leaf = Leaf(base_filters, base_label, total, oversized=True)
        stats.leaves.append(leaf); stats.oversized.append(leaf); return

    dim, rest = dims[0], dims[1:]
    values = dim.resolve_values(base_filters)
    if not values:                     # dim has nothing to split here (e.g. postal
        plan(base_filters, base_label, rest, count_fn, stats, depth, total); return

    covered = 0
    used, c_prev = [], None                  # dim values actually turned into buckets
    buckets = dim.buckets_for(base_filters)
    b_filters = [_merge(base_filters, b.predicate) for b in buckets]
    if len(buckets) > 2:
        with ThreadPoolExecutor(max_workers=8) as ex:
            counts = list(ex.map(count_fn, b_filters))
    else:
        counts = [count_fn(f) for f in b_filters]

    for bucket, cf, c in zip(buckets, b_filters, counts):
        if (dim.stop_below and len(used) >= dim.stop_min_buckets
                and covered and c_prev is not None and c_prev < dim.stop_below):
            break
        stats.count_calls += 1
        c_prev = c
        if not c:
            continue
        used.append(bucket.value if bucket.value is not None else bucket.label)
        if depth == 0:                       # top level (e.g. each state)
            log(f"  {bucket.label}: {c:,} -> split | calls={stats.count_calls} "
                f"leaves={len(stats.leaves)} uncovered={len(stats.uncovered)}")
        covered += c
        plan(cf, f"{base_label}__{bucket.label}", rest, count_fn, stats,
             depth + 1, known_count=c)

    remainder = total - covered
    if remainder > 0:
        if dim.exclude_key is not None:
            prev_excl = list(base_filters.get(dim.exclude_key) or [])
            excl = (prev_excl + used) if dim.stop_below else list(values)
            uf = _merge(base_filters, {dim.exclude_key: excl})
            plan(uf, f"{base_label}__{dim.name}-other(excl)", rest, count_fn,
                 stats, depth + 1, known_count=remainder)
        else:
            # Blank size/revenue in this geo cell. No exclude filter exists, so the
            # blanks can't be isolated -- but the CELL itself is a valid filter, and
            # pulling it yields EXPORT_LIMIT ranked rows instead of nothing. Count
            # only what can actually be delivered, never the full remainder: that
            # over-claim is what made a truncating plan look like 96% when it wasn't.
            stats.uncovered.append(
                (f"{base_label}__{dim.name}-blank", remainder, dict(base_filters)))
            stats.leaves.append(Leaf(dict(base_filters), f"{base_label}__{dim.name}-sweep",
                                     min(remainder, EXPORT_LIMIT),
                                     oversized=remainder > EXPORT_LIMIT))


def _sig(filters, exclude_key):
    return tuple(sorted((k, tuple(v) if isinstance(v, list) else v)
                        for k, v in filters.items()
                        if k != exclude_key and v not in (None, [], "")))


def consolidate(leaves, cap=3500, max_items=5):
    """Merge sibling leaves (identical except one include-dimension) into single
    exports using multi-value filter arrays, safely bin-packed to <= cap and <= max_items."""
    leaves = list(leaves)
    for key in DIM_INCLUDE_KEYS:
        groups, passthrough = {}, []
        for l in leaves:
            vals = l.filters.get(key)
            if l.oversized or not vals:
                passthrough.append(l); continue
            groups.setdefault(_sig(l.filters, key), []).append(l)
        merged = list(passthrough)
        for _, group in groups.items():
            if len(group) == 1:
                merged.append(group[0]); continue
            group.sort(key=lambda l: -l.count)
            bins = []
            for l in group:
                for b in bins:
                    if b["total"] + l.count <= cap and len(b["vals"]) + len(l.filters[key]) <= max_items:
                        b["vals"].extend(l.filters[key]); b["total"] += l.count; break
                else:
                    bins.append({"vals": list(l.filters[key]), "total": l.count,
                                 "proto": l.filters})
            for b in bins:
                f = dict(b["proto"]); f[key] = b["vals"]
                merged.append(Leaf(f, "", b["total"]))
        leaves = merged
    return leaves


def run(industry, country, count_fn=None, merge=True):
    inner = count_fn or count
    base = {"industries": [industry], "country_names": [country]}
    label = slugify(f"{industry}_{country}")
    dims = build_dims(country)
    stats = PlanStats()

    def wrapped(f):                          # milestone logging every 250 counts
        r = inner(f)
        if stats.count_calls % 250 == 0:
            log(f"  ...{stats.count_calls} counts | {len(stats.leaves)} leaves "
                f"| {len(stats.uncovered)} uncovered")
        return r

    log(f"PLAN start: {industry} + {country} | dims={[d.name for d in dims]}")
    plan(base, label, dims, wrapped, stats)
    log(f"PLAN raw done: {len(stats.leaves)} leaves, {len(stats.oversized)} "
        f"oversized, {len(stats.uncovered)} uncovered, calls={stats.count_calls}")
    if merge:
        stats.merged_from = len(stats.leaves)
        stats.leaves = consolidate(stats.leaves)
        log(f"PLAN merged: {stats.merged_from} -> {len(stats.leaves)} slices")
    return stats, base
