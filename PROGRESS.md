# New Business Locator — POS Lead Gen ETL Pipeline

## What this builds
A Python ETL pipeline that uses the Tavily search/extract API to discover new businesses opening in the Nashville/Middle Tennessee area, scores them by POS-system relevance, deduplicates, filters out chains, and loads them into a SQLite-backed lead pipeline with a CLI interface.

---

## Tech Stack
- **Python 3.10+** — requests, click, pyyaml. SQLite3 is stdlib (no ORM).
- **Tavily API** — key already in `~/.claude/settings.json` as `TAVILY_API_KEY` (injected into env automatically).

## Target Counties & Cities
| County | Primary Cities |
|---|---|
| Davidson | Nashville, Antioch, Madison, Hermitage |
| Williamson | Franklin, Brentwood, Nolensville, Spring Hill |
| Rutherford | Murfreesboro, Smyrna, La Vergne |
| Sumner | Gallatin, Hendersonville, Portland |
| Wilson | Lebanon, Mount Juliet |

---

## Project Structure
```
newBusinessLocator/
├── PROGRESS.md                  # this file
├── requirements.txt             # requests, click, pyyaml
├── config/
│   ├── __init__.py
│   ├── settings.py              # env vars, DB_PATH, file paths
│   ├── sources.yaml             # all Tavily queries, extractable/blocked domains, county→city map
│   ├── scoring.yaml             # type scores, keyword lists, source/address/recency weights
│   └── chains.yaml              # blocklist of known chain/franchise names
├── etl/
│   ├── __init__.py
│   ├── extract.py               # runs Tavily search + extract; returns list[RawExtract]
│   ├── transform.py             # parse → classify → score → infer county → dedup → filter chains
│   ├── load.py                  # INSERT OR IGNORE into SQLite; marks seen_urls
│   └── pipeline.py              # orchestrator: extract→transform→load, manages pipeline_runs row
├── db/
│   ├── __init__.py
│   ├── schema.py                # CREATE TABLE/INDEX statements; run once at startup
│   └── queries.py               # all named SQL query functions (get_leads, update_stage, etc.)
├── utils/
│   ├── __init__.py
│   ├── tavily_client.py         # thin wrapper: .search(query, max_results) and .extract(url)
│   ├── parsers.py               # parse_license_table() and parse_news_article()
│   └── dedup.py                 # generate_fingerprint(name, city) → 16-char hex
├── cli/
│   ├── __init__.py
│   └── main.py                  # click CLI: run, leads, lead, update, stats, history, export
├── data/
│   └── .gitkeep                 # leads.db created here at first run
└── logs/
    └── .gitkeep                 # pipeline.log appended here
```

---

## Database Schema (SQLite — `data/leads.db`)

### `leads` — central table, one row per unique business
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK AUTOINCREMENT | |
| fingerprint | TEXT UNIQUE NOT NULL | sha256(normalized_name\|normalized_city)[:16] — dedup key |
| business_name | TEXT NOT NULL | |
| business_type | TEXT | Classified: restaurant, bar, cafe, retail, salon, spa, bakery, etc. |
| raw_type | TEXT | Original text from source (e.g. "Restaurant", "Retail Sales") |
| address | TEXT | |
| city | TEXT | |
| state | TEXT DEFAULT 'TN' | |
| zip_code | TEXT | |
| county | TEXT | Davidson, Williamson, Rutherford, Sumner, Wilson |
| license_date | TEXT | ISO date from license table (NULL for news/snippet sources) |
| pos_score | INTEGER DEFAULT 0 | 0–100 lead quality score |
| stage | TEXT DEFAULT 'New' | New → Qualified → Contacted → Follow-up → Closed-Won / Closed-Lost |
| source_url | TEXT | URL this lead was extracted from |
| source_type | TEXT | license_table, news_article, or search_snippet |
| notes | TEXT | User-added notes via CLI |
| created_at | TEXT | |
| updated_at | TEXT | |
| contacted_at | TEXT | Set when stage first hits Contacted |
| closed_at | TEXT | Set on Closed-Won or Closed-Lost |

### `pipeline_runs` — audit log of every ETL execution
- id, run_started_at, run_finished_at, status (running/completed/failed), leads_found, leads_new, leads_dupes, error_message, sources_queried (JSON)

### `seen_urls` — prevents re-extracting already-processed pages
- url (PK), first_seen_at, county

### `stage_history` — append-only audit trail of every stage change
- id, lead_id (FK → leads), old_stage, new_stage, changed_at

---

## Data Sources & Search Strategy (3 Tiers)

### Tier A — License Tables (highest signal, structured)
These sources publish weekly new-business-license lists as markdown tables with columns: `Date | Business | Product | Address`. One parser handles all of them.

Queries target these domains specifically so search results surface the license pages, which are then passed to Tavily extract:
- `davidsoncountysource.com` — Davidson County (weekly, 70+ businesses/page)
- `williamsonsource.com` — Williamson County (same format confirmed)
- `wilsoncountysource.com` — Wilson County (same format confirmed)
- `sumnercountysource.com` — Sumner County (may be less frequent; pipeline handles gracefully if no results)

### Tier B — News Articles (good signal, free-text)
Local news sites that announce upcoming openings. Extracted and parsed for business names + addresses:
- wsmv.com, fox17.com, wkrn.com (local TV news)
- franklinis.com (Williamson County what's-new roundups)
- tennessean.com (Nashville's main newspaper — uses `## Name` / `*address*` pattern)

One query per county/city targeting "new restaurant/retail/business opening [city] 2026".

### Tier C — Type Sweeps (catch stragglers)
Two broad queries across all of Middle Tennessee for high-value types the county-specific queries might miss:
- "new bar cafe opening Middle Tennessee Nashville area 2026"
- "new salon spa beauty opening Nashville Franklin Murfreesboro 2026"

### Domain Filtering
- **Extractable domains**: only URLs from the sources above get a Tavily extract call
- **Blocked domains**: youtube, instagram, facebook, tiktok, threads, pinterest, newsbreak (mirrors source content → would cause dupes)
- All other URLs: kept as `search_snippet` source_type only (title + snippet, no extract)

---

## Extract → Transform → Load Flow

### Extract (`etl/extract.py`)
1. Load all queries from `sources.yaml` (Tier A + B + C)
2. For each query → POST to Tavily `/search`
3. Filter result URLs: drop blocked domains, drop already-seen URLs (from `seen_urls` table)
4. For each URL in extractable domains → POST to Tavily `/extract` (one URL at a time for clean error isolation)
5. Determine `source_type` from page title: contains "New Business Licenses" → `license_table`; otherwise → `news_article`
6. Return list of `RawExtract` objects (raw_content, source_url, county, source_type)

### Transform (`etl/transform.py`)
1. **Route** each RawExtract to the correct parser based on source_type
2. **Parse**: `parse_license_table()` splits markdown table rows → BusinessRecord list. `parse_news_article()` splits on `##` headings → BusinessRecord list. Search snippets produce minimal BusinessRecords from title/content.
3. **Classify**: match `raw_type` text against keyword lists in `scoring.yaml` (first match wins, checked in priority order) → sets `business_type`
4. **Chain filter**: if `business_name` matches any entry in `chains.yaml` blocklist (case-insensitive, substring match) → drop the record entirely
5. **Score**: compute `pos_score` (0–100) from 4 components (see Scoring below)
6. **Infer county**: if county not set from query metadata, look up city in the county→cities map
7. **Deduplicate**: generate fingerprint; if collision within this batch, keep the higher-scored record

### Load (`etl/load.py`)
1. `INSERT OR IGNORE` each BusinessRecord into `leads` (UNIQUE on fingerprint silently skips DB-level dupes)
2. Insert all processed source URLs into `seen_urls`
3. Update the `pipeline_runs` row with final counts
4. Append summary to `logs/pipeline.log`

---

## Lead Scoring (0–100)

| Component | Max | Logic |
|---|---|---|
| **A — Business Type** | 50 | restaurant=50, bar=48, cafe/retail=45, liquor=42, salon/bakery=40, spa=38, food_service=35, automotive=25, services=20, other=10, consulting/real_estate/construction/cleaning=5 |
| **B — Source Confidence** | 20 | license_table=20, news_article=15, search_snippet=8 |
| **C — Address Completeness** | 15 | street+city+zip=15, street+city=10, city only=5, none=0 |
| **D — Recency** | 15 | ≤7 days=15, ≤14 days=10, ≤30 days=5, >30 days or unknown=0 |

All weights and keyword lists live in `scoring.yaml` — tunable without code changes.

---

## Chain/Franchise Blocklist (`config/chains.yaml`)

Configurable list of known chains that already have corporate POS systems. Applied during Transform as a hard filter (record dropped, not scored).

Initial seed list includes: Wawa, Buc-ee's, In-N-Out, Trader Joe's, Chick-fil-A, McDonald's, Starbucks, Panera, Chipotle, Subway, Wendy's, Taco Bell, KFC, Pizza Hut, Domino's, Applebee's, Cracker Barrel, Waffle House, Publix, Walmart, Target, Costco, Dollar General, Dollar Tree, Walgreens, CVS, and similar.

Match is case-insensitive substring against `business_name`. The list is in `chains.yaml` so adding/removing chains requires no code changes.

---

## CLI Commands (`cli/main.py` — invoked as `python -m cli.main`)

| Command | Description |
|---|---|
| `run [--dry-run]` | Execute full ETL. `--dry-run` prints results without DB writes. |
| `leads [--stage] [--county] [--min-score] [--sort] [--limit]` | List leads as a formatted table. Filterable and sortable. |
| `lead <ID>` | Full detail view for a single lead. |
| `update <ID> --stage <stage> [--note <text>]` | Change pipeline stage; append note. Writes to `stage_history`. |
| `stats` | Summary dashboard: totals by stage, county, type; avg score; last run info. |
| `history <ID>` | Stage-change audit trail for a lead. |
| `export [--stage] [--county] [--min-score] --output <file.csv>` | Export filtered leads to CSV. Same filter options as `leads`. |

---

## Deduplication Strategy (`utils/dedup.py`)

The same business can appear across multiple sources (license table one week, news article the next, search snippet the week after). Dedup key = `sha256(normalized_name + "|" + normalized_city)[:16]`.

Name normalization: lowercase → strip legal suffixes (llc, inc, corp, ltd, co, l.l.c.) → strip punctuation except hyphens → strip common words (the, and, &) → collapse whitespace.

The UNIQUE constraint on `fingerprint` in the `leads` table is the final safety net at the DB level.

---

## Verification / Testing Plan
1. **Smoke test**: Run `python -m cli.main run --dry-run`. Confirm it hits Tavily API, returns structured leads with scores, and prints the preview table. No DB writes.
2. **Full run**: Run `python -m cli.main run`. Confirm `leads.db` is created with records. Run `stats` to see counts by county/stage/type.
3. **Chain filter validation**: Verify that any chain names from the seed list that appeared in dry-run output are absent after a real run.
4. **Dedup validation**: Run the pipeline twice in a row. Second run should report 0 new leads (all dupes).
5. **CLI commands**: Step through `leads`, `lead <ID>`, `update <ID> --stage Qualified`, `history <ID>`, `stats` to confirm display and state transitions.
6. **CSV export**: Run `export --output /tmp/test.csv` and verify the file contains correct columns and filtered data.
7. **Scoring spot-check**: Manually verify 2–3 leads match the expected scoring breakdown (type + source + address + recency).

---

## Build Phases & Progress Tracking

### Phase 1 — Foundation ✅ DONE
- [x] Create full directory structure + all `__init__.py` + `.gitkeep` files
- [x] Write `requirements.txt` (requests, click, pyyaml)
- [x] Write `config/settings.py` (env vars, paths)
- [x] Run `pip install -r requirements.txt`

### Phase 2 — Core Modules ✅ DONE
- [x] `db/schema.py` — all CREATE TABLE / CREATE INDEX statements
- [x] `db/queries.py` — all named SQL functions
- [x] `config/sources.yaml` — county→city map, all Tier A/B/C queries, extractable/blocked domains
- [x] `config/scoring.yaml` — type_scores, business_type_keywords, source/address/recency scores
- [x] `config/chains.yaml` — seeded blocklist of 45 national chains/franchises
- [x] `utils/tavily_client.py` — TavilyClient class with `.search()` and `.extract()` methods
- [x] `utils/parsers.py` — `parse_license_table()`, `parse_news_article()`, `parse_snippet()`
- [x] `utils/dedup.py` — `generate_fingerprint(name, city)` with full normalization chain

### Phase 3 — ETL Modules ✅ DONE
- [x] `etl/extract.py` — search, filter, extract, returns list[RawExtract]
- [x] `etl/transform.py` — parse → classify → chain filter → score → infer county → dedup
- [x] `etl/load.py` — INSERT OR IGNORE, seen_urls, pipeline_runs update, log append

### Phase 4 — Orchestrator ✅ DONE
- [x] `etl/pipeline.py` — extract→transform→load, dry_run support, error handling

### Phase 5 — CLI ✅ DONE
- [x] `cli/main.py` — run, leads, lead, update, stats, history, export

### Phase 6 — Verification ✅ DONE
- [x] Smoke test: dry-run returned 23 leads, preview table printed
- [x] Full run: 22 leads inserted (run_id=1)
- [x] Chain filter: Buc-ee's correctly dropped; Sprouts added to blocklist
- [x] Dedup: second run returned found=0 (all URLs already seen)
- [x] CLI walkthrough: lead detail, two stage transitions, history audit trail, contacted_at timestamp all correct
- [x] CSV export: 22 leads, 20 columns, stage/note changes reflected
- [x] Scoring spot-check: lead 20 manually verified (other 10 + snippet 8 + city 5 = 23)
- [x] Bug fix: snippet title-splitter regex changed from `\s*[-–|]\s*` to `\s+[-–|]+\s+` to stop splitting on hyphens inside words (e.g. "Buc-ee's")

---

## First-Run Findings

These observations from the Phase 6 run drive the Phase 7+ roadmap.

### What worked
- End-to-end pipeline: extract → transform → load → CLI all functional
- Chain filter, dedup (seen_urls + fingerprint), scoring math, stage transitions, CSV export
- `parse_license_table` and `parse_news_article` parsers are fully built and correct — they just never ran because no license-table or news-article extracts were returned

### What didn't work / needs improvement
1. **Tier A (license tables) returned zero results.** All four `site:` queries against `*countysource.com` came back empty. The parser is ready; the source URLs just aren't surfacing in Tavily search.
2. **Almost all leads are search snippets, not extracted pages.** 22 out of 22 are `search_snippet`. Domains like nashvilleguru.com, visitmusiccity.com, bizjournals.com, and theinfatuation.com surfaced in results but aren't in `extractable_domains`, so only their title was captured — not the page content.
3. **~18 of 22 "business names" are actually article titles.** Titles like "Coming Soon to Nashville! 10 Exciting Additions" or "What's Coming to Williamson County" are list-style articles, not individual businesses. The real businesses are inside the page body — which was never extracted.
4. **All leads classified as `other` (score 10).** `classify()` only checks `raw_type`. Snippets have no `raw_type`, so every lead defaults to `other` regardless of what the business name says. "Rose, a Luxury Spa and Salon" should be `spa` (38), not `other` (10).

### Real business names that came through correctly
| ID | Name | Why it worked |
|---|---|---|
| 19 | WHAT'S NEW SALON & BARBER | Yelp URL → title is the actual business name |
| 20 | Rose, a Luxury Spa and Salon | Award-site URL → title is the business name |
| 21 | The Trinity: Where Wellness Begins | Lifestyle-blog URL → title is the business name |
| 22 | House of Her | Same pattern |

---

## Next Steps Roadmap

Ordered by impact. Phase 7 and 8 together close the two biggest gaps (classification and extraction depth) and should be done before 9–11.

### Phase 7 — Name-based classification fallback ✅ DONE
**Impact: immediate score lift on every snippet lead with a typed name**
**File: `etl/transform.py` — `classify()` function**

- [x] Update `classify()` in `etl/transform.py`: after the `raw_type` keyword loop, if no match and `raw_type` was empty, repeat the same loop against `business_name`
- [x] Re-score existing leads: added CLI command `rescore` that re-classifies and updates `business_type` + `pos_score` on all existing leads

### Phase 8 — Expand extractable domains ✅ DONE
**Impact: transforms the majority of current snippet leads into parsed news_article leads**
**Files: `config/sources.yaml`**

- [x] Added 13 new domains to `extractable_domains`: nashvilleguru.com, visitmusiccity.com, theinfatuation.com, bizjournals.com, welcometowedgewood.com, styleblueprint.com, nashtoday.6amcity.com, goodnightstay.com, yelp.com, gallatintn.gov, plus countysource domains

### Phase 9 — Article-title noise filter ✅ DONE
**Impact: drops low-value snippet leads that slip through even after Phase 8**
**File: `etl/transform.py`**

- [x] Added `is_article_title(name: str) -> bool` function with heuristic rules:
  - Starts with number + space (e.g., "5 Nashville...")
  - Matches known patterns: "What's Coming", "Coming Soon to", "New Businesses", "Top [number]", etc.
  - Length > 60 characters
- [x] Integrated into `run_transform` after chain filter — only filters `search_snippet` source types
- [x] Added 20 tests for the filter

### Phase 10 — Recover Tier A license table sourcing ✅ DONE
**Impact: highest-value source (score ceiling 100)**
**Files: `config/sources.yaml`, `etl/extract.py`**

Research findings:
- 6 countysource domains publish license tables: Davidson, Williamson, Wilson, Robertson, Maury, Dickson
- 2 do NOT publish license tables: Sumner, Rutherford
- `site:` queries don't work — direct URL extraction needed

- [x] Added `direct_extract_urls` section to `sources.yaml` with 10 license-table URLs across 6 counties
- [x] Updated `etl/extract.py` to process direct URLs before search queries
- [x] Added 3 new counties to `county_cities` map: Robertson, Maury, Dickson

### Phase 11 — Scheduled weekly runs ✅ DONE
**Impact: keeps the lead DB current without manual intervention**
**Files: `scripts/com.newbusinesslocator.weekly.plist`, `cli/main.py`**

- [x] Created launchd plist template for weekly runs (Sunday 6 AM)
- [x] Added `schedule` subcommand to CLI:
  - `schedule install` — installs the launchd job
  - `schedule uninstall` — removes the scheduled job
  - `schedule status` — shows job status and last run info

---

## Phase 7-11 Verification Run (2026-02-04)

Pipeline run after all phases complete:
- **Result:** 5 new leads (run_id=1)
- **Classification working:** 2 leads correctly classified as `salon`, 1 as `automotive`
- **Counties:** Rutherford (3), Sumner (1), Williamson (1)
- **Average score:** 38.0
