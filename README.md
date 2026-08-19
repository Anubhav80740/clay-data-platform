# Clay Company-Data Extraction Pipeline

Pull complete company datasets out of Clay (name, domain, industry, size, type,
location, country, LinkedIn URL, description) for any **industry + country**,
working around Clay's **5,000-row export cap**.

> ⚠️ Uses Clay's **internal API** via your logged-in browser session. Runs on
> **your** Clay account and credits. Counting/planning is free; downloading costs
> ~1 credit per company row pulled.

**Requirements:** `python3` (3.9+) and `curl`. No pip installs, no venv.

**This package is scripts only.** No plans, no downloaded data, no country
ledgers, no session cookie. You generate all of that yourself from §3 onward.

---

## 0. The one-paragraph mental model

Clay will only export 5,000 rows per table. So you never export "an industry" —
you **split the industry into slices** that are each under 5,000, then export
each slice separately and concatenate. The splitting is done by
`generate_clicklist.py`, which recursively adds filters
(`state → city → postal → county → description-keyword → size → revenue`) until
every leaf is under 5,000. That list of leaves is the "clicklist" / **plan**
(`plans/clicklist_<Industry>_<Country>.json`). `clay_pipeline.py download` then
walks the plan, and for each slice: creates a Clay table → waits for it to
populate → exports → downloads the CSV → **deletes the table**. Everything is
resumable: a slice with a CSV on disk is skipped.

**Key fact that drives every decision:** a slice takes ~40–65 seconds *whether it
has 12 rows or 5,000 rows*. Wall-clock time is driven by the **number of
slices**, not the number of rows. Never split more finely than you need to.

---

## 1. What each script is for

### The ones you run

| Script | Purpose |
|---|---|
| `count_industries.py` | Counts every industry in an industry-list CSV for one country (free, resumable) → `<Country>_nontech_counts.csv`. **Run this first for a new country** — it's the input to `run_nontech.py`. |
| `run_nontech.py` | **The main driver.** Runs a whole country end to end: for every industry with count > 0, largest first — plan → download → concatenate → `delivery/`. Resumable, retries failed slices, writes a progress ledger and a low-coverage alerts file. This is what you'll use 90% of the time. |
| `generate_clicklist.py` | Plans ONE industry+country (free): recursively splits it into under-5,000 slices and writes `plans/clicklist_<prefix>.json` + a human-readable `.csv`. `run_nontech.py` calls this for you. |
| `clay_pipeline.py` | Downloads/merges/diagnoses ONE industry. Modes: `download`, `merge`, `combine`, `audit`, `diag`, `selftest`. `run_nontech.py` calls this for you. |
| `organize_delivery.py` | Copies finished per-industry CSVs into flat `delivery/<Country>/non-tech/` folders. Copies rather than moves, so resume state survives. Dry run by default; `--apply` to act. |
| `country_sheets.py` | Builds the per-country summary sheet: `industry, clay_count, rows_downloaded, coverage_pct, Status`, sorted by count with a TOTAL row. `rows_downloaded` is **unique companies**, not raw rows. |

### Libraries — don't run them, but you will edit them

| File | Purpose |
|---|---|
| `clay_lib.py` | The engine. Auth, count, table create/populate/export/download/delete, the recursive **planner**, unique-company keying, CSV concatenation. Tuning knobs live at the top: `EXPORT_LIMIT` (5000), `MAX_DEPTH`, `WORKSPACE_ID`, size/revenue bands, keyword rounds. |
| `clay_geo.py` | **Geography vocabulary** — each country's states mapped to their cities, plus UK counties and optional postcode lists. This is the file you edit to add a country (§5). Ships with US, UK and Canada geography already filled in. |

### Repair and optimisation tools — only when something's wrong (§8)

| Script | Purpose |
|---|---|
| `refresh_oversized.py` | Rebuilds an `oversized_slices.csv` report from **live** Clay counts — which slices are still hitting the 5,000 cap and how far behind they are. Run this to find out where you're losing data. |
| `split_minimal.py` | Splits oversized cells using the **minimal-slice** technique (§8.2) — samples downloaded rows to size each city bucket, then bin-packs to produce `ceil(N/5000)` slices instead of hundreds. **Use this one first.** |
| `split_oversized.py` | Older brute-force enumeration splitter. Slower, produces far more slices. Fallback only. |
| `harvest_cities.py` | Mines real city names out of already-downloaded rows and adds the missing ones to `clay_geo.py`. **The single highest-leverage fix** in the toolkit — this is what closes oversized slices when nothing else works. |
| `trim_cities.py` | Keeps only the top-N cities per state. Run after `harvest_cities.py` if the planner got slow from oversized city lists. |
| `compact_plan.py` | Merges redundant slices in an existing plan (suffix-collapse + OR-merge), verifying each merge against a live count first. Fewer slices = less wall time. |
| `repair_truncated.py` | Finds slices that came back short and re-pulls them. `--verify` live-counts each candidate first so you don't spend credits re-pulling complete slices. |
| `rebuild_ledger.py` | Rebuilds a country's progress CSV from what's actually on disk. Use if the ledger is lost or corrupted. |
| `fix_slugs.py` | Detects and repairs slug collisions in a plan (§8.4). |
| `clay_maxpull.py` | Optional multi-pass union across 6 slice orderings. ~3× the credits for ~+5% data. Only where completeness genuinely justifies it. |
| `map_industries.py` | Older industry-sizing tool. Superseded by `count_industries.py`; kept because `audit` references its target list. |
| `london_split.py`, `split_uk_counties.py`, `merge_uk_cities.py`, `migrate_slugs.py` | One-off jobs from the UK run. Kept as worked examples of custom splitting — not part of the normal flow. |

### Directories the scripts create

| Dir | Contents |
|---|---|
| `plans/` | `clicklist_*.json` (read by the downloader) + `.csv` (readable). Written by `generate_clicklist.py`. |
| `downloads/` | One dir per slice, plus `<prefix>_ALL.csv` per industry. |
| `delivery/` | Final per-industry CSVs. |
| `logs/` | Per-industry planner logs. |

### What you need to supply

- `.clay_cookie.txt` — your Clay session cookie (§2). Not included; make your own.
- An industry-list CSV — one `Industry` column, names spelled exactly as Clay
  spells them. Feed it to `count_industries.py`. Ask me for the non-tech list if
  you want the one I used.

---

## 2. FIRST THING: set up the session cookie

**Do this before anything else, and again whenever things start failing.** The
cookie expires every few days and is the most common cause of failure.

Symptoms of expiry: counts return empty/`None`, HTTP 401/403, "PLAN FAILED"
everywhere, every slice erroring at once.

1. Log in to **app.clay.com** in Chrome.
2. DevTools (`Cmd+Opt+I`) → **Network** tab → filter **Fetch/XHR**.
3. Click anything in Clay so a request to `api.clay.com` appears.
4. Right-click that request → **Copy → Copy as cURL**.
5. From what you copied, take the value after **`-b '`** up to the closing `'`
   (the whole cookie string; the part that matters is `claysession=`).
6. Paste it as **one single line** into `.clay_cookie.txt`, replacing everything
   in it. See `.clay_cookie.txt.example`.
7. Test: `python3 clay_pipeline.py audit "Accounting" "Canada"` — if it prints
   counts, you're good.

**If counts work but downloads fail**, the table-creation params also went stale.
From a fresh `create-cpj-table` request (Copy as cURL again) update in
`clay_lib.py`: `WORKSPACE_ID` (also visible in the URL
`app.clay.com/workspaces/<ID>`), `FRONTEND_VERSION` (`x-clay-frontend-version`
header), `CONVERSATION_ID` (a body field).

**A different Clay account** needs its own cookie **and** its own `WORKSPACE_ID`
and `CONVERSATION_ID`. The cookie alone is not enough.

---

## 3. The main job: download a whole country

```bash
# Step 1 — count every industry for the country (free, ~30-60 min, resumable)
python3 count_industries.py "Germany"
#   -> Germany_nontech_counts.csv   (Industry, Count)
#   Checkpoints as it goes. If it dies, re-run it — it resumes.

# Step 2 — run it. Plans and downloads every industry with count > 0,
#          largest first, and delivers to delivery/.
nohup python3 run_nontech.py "Germany" > germany.out 2>&1 &

# Step 3 — watch it
tail -f germany.out
```

Fully resumable — kill it and re-run the identical command. It skips any industry
that already has a file in `delivery/`, and within an industry skips any slice
that already has a CSV.

### Flags

```bash
python3 run_nontech.py "Germany" --min 10000 --max 30000     # only this count band
python3 run_nontech.py "Germany" --only "Retail|Restaurants" # just these (pipe-separated)
python3 run_nontech.py "Germany" --shard 0/3                 # shard 0 of 3
```

> ⚠️ **Run ONE at a time.** `--shard` works, but running 3 concurrently got table
> creation throttled on Clay's side and slices started failing. One shard is
> slower and reliable.

### What it does per industry

1. Plans it (or reuses an existing plan in `plans/`).
2. Discards and re-plans if the plan came back empty — a transient count failure
   can produce an empty plan that would otherwise claim 100% coverage.
3. Downloads every slice, retrying failed slices up to 3 times.
4. Concatenates slices into `downloads/<prefix>_ALL.csv` — **no dedup**, by
   design; slice overlap is expected and dedup happens at DB insert.
5. Copies to `delivery/<Country> Data [Clay] -<Industry>.csv`.
6. Appends to `<Country>_nontech_progress.csv`.
7. Writes to `alerts_<Country>.csv` if coverage < 95%.

### After the run

```bash
python3 organize_delivery.py --apply   # collect into delivery/<Country>/non-tech/
python3 country_sheets.py              # build summary sheets
cat alerts_Germany.csv                 # anything below 95% and why
```

---

## 4. Doing ONE industry by hand

```bash
python3 clay_pipeline.py audit "Retail" "United States"     # free: totals, blank-%, overlap-%
python3 generate_clicklist.py "Retail" "United States"      # plan (free, 5-40 min)
python3 clay_pipeline.py download Retail_United_States 5 asc  # cheap 5-slice smoke test
python3 clay_pipeline.py download Retail_United_States        # full run (resumable)
python3 clay_pipeline.py merge Retail_United_States           # -> _ALL.csv
```

`<prefix>` is always `slugify(Industry_Country)` — the clicklist filename stem.
Industry names must match Clay's taxonomy **exactly**
(`"IT Services and IT Consulting"`, not `"IT Services"`).

---

## 5. Adding a new country

Size and revenue bands are global; only **geography** is country-specific, and it
lives in `GEO` in `clay_geo.py`.

```python
"Germany": {
    "states": {
        "Bavaria":                ["Munich", "Nuremberg", "Augsburg", ...],
        "North Rhine-Westphalia": ["Cologne", "Düsseldorf", "Dortmund", ...],
        "Bremen": [],        # [] = no cities; splits by size/revenue only
    },
    # "postal": {"Berlin": ["10115", "10117", ...]},   # optional, see below
},
```

1. `states` = the country's admin-1 divisions **exactly as Clay names them**,
   each mapped to its major cities. Top ~50–75 by business density is plenty to
   start; you'll harvest more later (§8.3).
2. Cities are **scoped to their state**, so adding cities under a state only
   costs count-calls when that state actually needs splitting. Cheap to extend.
3. The country name must match Clay's `country_names` value exactly.
4. A country with **no `GEO` entry still runs**, but falls back to size/revenue
   only → much lower coverage. Always add geography.
5. Run one plan and check the printed **`still oversized`** count. 0 means done.

**Verify your state names are real Clay values before trusting a plan.** An
unsupported filter value **fails open** — Clay silently ignores it and returns
the unfiltered set, which looks like success while silently duplicating data:

```bash
python3 -c "import clay_lib as cl; print(cl.count({'industries':['Retail'],'country_names':['Germany'],'location_states_include':['Bavaria']}))"
```

If that matches the unfiltered count, the value is wrong.

### Postal codes — optional

Only needed for a *single city* dense enough to exceed 5,000 in one industry (SF,
NYC, London). Add `"postal": {"Berlin": ["10115", ...]}`, re-plan, and the
oversized slice splits by postcode. Skip it and that city splits by size/revenue
instead, losing a little — the rest of the country is unaffected.

---

## 6. Understanding coverage (read once — it explains every design choice)

### Which filters can partition completely

A filter can **completely** partition a set only if it has a working `_exclude`
twin — that's how the planner captures the "everything else, including blanks"
remainder.

| Filter | Has exclude? | Complete partition? |
|---|---|---|
| `location_states_include` | ✅ | yes |
| `location_cities_include` | ✅ | yes |
| `location_postal_codes_include` | ✅ | yes |
| `locations` (counties) | ✅ | yes |
| `description_keywords` | ✅ | yes |
| `sizes` | ❌ | **no** — blank-size rows unreachable |
| `annual_revenues` | ❌ | **no** — blank-revenue rows unreachable |
| `types` | ❌ | **no** |

Companies with blank size **and** blank revenue **and** no geographic match are a
hard floor you cannot reach. That's most of the missing few percent.

### The critical trade-off

> **An oversized slice still delivers 5,000 rows. An uncovered bucket delivers
> zero.**

Splitting harder on a filter with no exclude (size, revenue, type) converts a
*partial* loss into a *total* one. Measured: pushing size/revenue splitting
harder took one industry from **85% → 66.5%**. Don't do it.

### Already measured and ruled out — don't re-spend credits on these

| Idea | Result |
|---|---|
| Company `type` filter | +1,859 rows out of 345,013. Median 0.2–0.3% of rows are typed at all. Dimension is commented out in `clay_lib.py`. |
| ZIP-prefix splitting | Unsupported by the API, and the remainders have no ZIP anyway. |
| More keyword rounds (>4) | Remainder companies have no description text at all. |
| Deeper size/revenue splitting | 85% → 66.5%. Actively harmful. |
| English regions/counties as *states* | Not in Clay's state vocabulary — fails open. |
| London postcodes | Too sparse in Clay's data to split on. |
| `has_resolved_domain` | Silently ignored (unsupported filters fail open). |

### What actually worked

1. **Harvesting real city names from downloaded rows** (§8.3) — by far the
   biggest win; it's what drives oversized slice counts to zero.
2. `description_keywords` as a chained dimension with accumulating excludes.
3. Counties via the `locations` filter.

### Unique-company counting

`rows_downloaded` in the summary sheets counts **unique companies**, keyed on
**LinkedIn URL first, Domain as fallback**. The order matters: domain-first
collapses genuinely distinct entities that share a website — university
departments, hotel franchises, broker networks. Domain-first keying made one
industry read as 68% when it was really 98%.

The delivered CSVs contain **more raw rows** than that unique count, because
slices overlap and merge is a plain concatenation. Intentional.

---

## 7. Diagnostics

```bash
python3 clay_pipeline.py audit "<Industry>" "<Country>"  # free: totals, blank-%, overlap-%
python3 clay_pipeline.py selftest        # planner logic on mock data, no credits
python3 clay_pipeline.py diag <prefix>   # stated-vs-pulled shortfall per slice
python3 clay_pipeline.py merge <prefix>  # concatenate slices -> _ALL.csv
python3 clay_pipeline.py combine <out.csv> <in1.csv> <in2.csv> ...
python3 refresh_oversized.py             # rebuild oversized report from live counts
```

| Question | Where to look |
|---|---|
| Is it running? | `ps -eo pid,ppid,command \| grep -E 'run_nontech\|clay_pipeline'` |
| What's it doing now? | `tail -f <your>.out` |
| Which industries under-delivered? | `alerts_<Country>.csv` |
| What's finished? | `<Country>_nontech_progress.csv` |
| Where am I losing data? | `oversized_slices.csv` after `refresh_oversized.py` |
| Why did a plan look wrong? | `logs/plan_<slug>.out` |

---

## 8. Troubleshooting — what to do in what case

### 8.1 Common failures

| Symptom | Cause | Fix |
|---|---|---|
| Counts empty/`None`, 401/403 | Cookie expired | Refresh `.clay_cookie.txt` (§2) |
| Counts work, downloads fail | Stale table params | Update `WORKSPACE_ID`/`FRONTEND_VERSION`/`CONVERSATION_ID` (§2) |
| `EXPORT FAILED` but status `FINISHED`, valid URL, ~120-byte file, `totalRecordsInViewCount: 0` | **Clay's 15M workspace row ceiling** — source populates, view stays empty | Delete old tables in the Clay UI to free rows. The pipeline auto-deletes after each export, but orphans from crashed runs accumulate. |
| `CREATE FAILED` on several slices | Clay throttling table creation | Stop concurrent shards. Re-run — those slices retry. |
| A slice sits at 0 records | Table never populates | Handled: gives up after 20 zero-polls (~60s). If it genuinely hangs, kill and restart — resumable. |
| An industry delivered exactly 1 row | Populate-wait accepted a plateau at n=1 | Fixed (90%-of-expected rule). If seen again, delete the delivery file and re-run with `--only`. |
| Reports 100% but the file is empty | Empty plan from a transient count failure | Handled — empty plans are discarded and re-planned. Delete any 0-row delivery file. |
| Whole country's coverage low | Missing `GEO` entry, or state names Clay doesn't recognise | §5, and run the fail-open check |

### 8.2 A slice is oversized (hitting the 5,000 cap)

```bash
python3 refresh_oversized.py                 # current list, live counts
python3 split_minimal.py "<Country>"         # dry run
python3 split_minimal.py "<Country>" --apply
```

**The minimal-slice technique** — don't brute-force enumerate every filter value.
If a cell is 5,129, it's only **129 over the cap**, so you only need *one* filter
value that peels off ≥129 rows. That's two clean slices instead of forty.
`split_minimal.py` samples the downloaded rows to estimate each city bucket's
size, then bin-packs buckets to sum just under the cap.

Before splitting, ask whether the cell is **splittable at all**: check whether the
downloaded rows have more than one distinct value on the axis you're splitting.
If all 5,000 sampled rows share one city, no city split exists.

⚠️ `split_oversized.py` will rewrite a city-pinned cell's city (turning
`city=London` into `city=Croydon`), which is semantically wrong. There's a guard
now, but prefer `split_minimal.py`.

### 8.3 Coverage is low and you're out of ideas → harvest cities

Highest-leverage fix in the toolkit. Reads the cities that actually appear in
your downloaded rows and adds the missing ones to `clay_geo.py`:

```bash
python3 harvest_cities.py               # dry run
python3 harvest_cities.py --apply
python3 trim_cities.py 60 --apply       # optional, if planning got slow
```

Then re-plan and re-download only the affected industries with `--only`.

### 8.4 Slug collisions (rare, nasty — know the signature)

Two different filter sets can slugify identically (e.g. `..._cityX37_rest` for
both New York and Ohio, both having 37 cities). The second slice **overwrites the
first**, filing one state's rows under another's. This happened once: 26 slugs,
65 slices, ~87K rows misfiled. Slugs now include a hash of the full filter set,
so it shouldn't recur.

```bash
python3 fix_slugs.py "<Country>"           # dry run, reports collisions
python3 fix_slugs.py "<Country>" --apply
```

### 8.5 Killing a run — DO THIS PROPERLY

Killing the driver but leaving its children alive has cost real money.

```bash
ps -eo pid,ppid,command | grep -E 'run_nontech|clay_pipeline|generate_clicklist'
```

Anything with **PPID 1** is an orphan — kill it explicitly before restarting.
Restarting on top of live orphans causes duplicate downloads (once: 2.5 hours of
wasted credits).

### 8.6 Slices came back short

```bash
python3 repair_truncated.py "<Country>" --verify           # dry run
python3 repair_truncated.py "<Country>" --verify --apply
```

`--verify` re-counts each candidate against Clay before re-pulling, so you don't
pay to re-pull slices that were already complete.

### 8.7 The run is too slow

Wall time = slice count × ~50s. Reduce **slices**, not rows.

```bash
python3 compact_plan.py <prefix>           # dry run
python3 compact_plan.py <prefix> --apply   # merge redundant slices, live-verified
```

Also `trim_cities.py N --apply` if `harvest_cities.py` made the city lists huge
and planning slowed down.

### 8.8 Ledger corrupted or lost

```bash
python3 rebuild_ledger.py "<Country>"   # rebuild progress CSV from disk
```

---

## 9. Credits and cost

- **Free:** counting, planning, `audit`, `diag`, `selftest`, every dry run.
- **Costs credits:** downloading, ~1 credit per row pulled.
- A large industry in a big market runs to the low hundreds of thousands of rows.
  A whole country runs to millions. Budget before you start.
- **Always run a small `asc` test batch first** and check your balance.
- Every slice creates a table; the pipeline deletes it after a successful export.
  A run that dies mid-way leaves orphan tables that push you toward the 15M
  workspace row ceiling — check the Clay UI after any crash.

---

## 10. Filter vocabulary reference

**`sizes`:** `1` (self-employed) · `2` (2-10) · `10` (11-50) · `50` (51-200) ·
`200` (201-500) · `500` (501-1k) · `1000` (1k-5k) · `5000` (5k-10k) ·
`10000` (10k+)

**`annual_revenues`:** `0-500K` · `500K-1M` · `1M-5M` · `5M-10M` · `10M-25M` ·
`25M-75M` · `75M-200M` · `200M-500M` · `500M-1B` · `1B-10B` · `10B-100B` ·
`100B-1T`

**Geographic:** `location_states_include` / `_exclude`,
`location_cities_include` / `_exclude`, `location_postal_codes_include` /
`_exclude`, `locations` / `locations_exclude` (counties)

**Other:** `description_keywords` / `_exclude`, `industries`, `country_names`

> Remember: an **unsupported filter name or value fails open** — Clay ignores it
> and returns the unfiltered set. Sanity-check any new filter with a `count` call
> before trusting a plan built on it.
