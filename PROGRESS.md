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

### Phase 1 — Foundation (sequential, must complete first)
- [ ] Create full directory structure + all `__init__.py` + `.gitkeep` files
- [ ] Write `requirements.txt` (requests, click, pyyaml)
- [ ] Write `config/settings.py` (env vars, paths)
- [ ] Run `pip install -r requirements.txt`

### Phase 2 — Core Modules (3 sub-agents IN PARALLEL — no interdependencies)

**Agent A — Database Layer**
- [ ] `db/schema.py` — all CREATE TABLE / CREATE INDEX statements
- [ ] `db/queries.py` — all named SQL functions (get_leads, get_seen_urls, insert_lead, update_stage, get_stats, get_stage_history, get_pipeline_runs)

**Agent B — Configuration Files**
- [ ] `config/sources.yaml` — county→city map, all Tier A/B/C queries, extractable/blocked domains
- [ ] `config/scoring.yaml` — type_scores, business_type_keywords (priority-ordered), source_scores, address_scores, recency_scores
- [ ] `config/chains.yaml` — seeded blocklist of 30+ national chains/franchises

**Agent C — Utility Layer**
- [ ] `utils/tavily_client.py` — TavilyClient class with `.search()` and `.extract()` methods
- [ ] `utils/parsers.py` — `parse_license_table()` (markdown pipe-table → BusinessRecord list) and `parse_news_article()` (## heading / *address* pattern → BusinessRecord list) and `parse_snippet()` (title + content → minimal BusinessRecord)
- [ ] `utils/dedup.py` — `generate_fingerprint(name, city)` with full normalization chain

### Phase 3 — ETL Modules (3 sub-agents IN PARALLEL — each is a self-contained module)
> Depends on Phase 2 completing. Each module imports from utils/ and config/ but does not call the others directly.

**Agent D — Extract**
- [ ] `etl/extract.py` — reads sources.yaml, calls TavilyClient.search() for each query group, filters URLs against blocked/seen/extractable lists, calls TavilyClient.extract() for qualifying URLs, determines source_type from page title, returns list[RawExtract]

**Agent E — Transform**
- [ ] `etl/transform.py` — routes RawExtract by source_type to the correct parser, runs classify → chain_filter → score → infer_county → deduplicate pipeline on resulting BusinessRecords, returns clean list[BusinessRecord]

**Agent F — Load**
- [ ] `etl/load.py` — opens SQLite via db/schema.py (auto-creates tables), INSERT OR IGNORE each BusinessRecord, inserts source URLs into seen_urls, updates pipeline_runs row with counts

### Phase 4 — Orchestrator (sequential, depends on Phase 3)
- [ ] `etl/pipeline.py` — imports extract/transform/load; wires them in order; creates pipeline_runs row; handles errors; writes to pipeline.log

### Phase 5 — CLI (sequential, depends on Phase 4)
- [ ] `cli/main.py` — all click commands: run, leads, lead, update, stats, history, export

### Phase 6 — Verification
- [ ] Smoke test: `python -m cli.main run --dry-run`
- [ ] Full run + `stats`
- [ ] Chain filter validation
- [ ] Dedup validation (run twice → 0 new second time)
- [ ] CLI command walkthrough
- [ ] CSV export test
- [ ] Scoring spot-check on 2–3 leads
