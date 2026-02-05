# New Business Locator

A lead generation ETL pipeline that discovers new businesses opening in Nashville and Middle Tennessee, scores them for POS (Point-of-Sale) system sales relevance, and provides a CLI for managing the sales pipeline.

## Table of Contents

- [The Problem](#the-problem)
- [How It Works](#how-it-works)
- [Data Flow](#data-flow)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [CLI Reference](#cli-reference)
- [Database Schema](#database-schema)
- [Lead Scoring](#lead-scoring)
- [Testing](#testing)

---

## The Problem

New businesses opening in the Nashville metro area are prime prospects for POS system sales—they need payment processing from day one. The challenge is finding them before competitors do.

This pipeline automates lead discovery by:
1. Mining public business license records from county websites
2. Monitoring local news for "grand opening" announcements
3. Running targeted web searches for new business activity
4. Filtering out national chains (they have corporate POS contracts)
5. Scoring leads by business type relevance and data quality
6. Deduplicating across sources so the same business isn't contacted twice

---

## How It Works

### The Story of a Lead

**Discovery**: The pipeline runs (manually or on a weekly schedule) and queries multiple data sources:

1. **License Tables** (highest value): County websites like `davidsoncountysource.com` publish weekly lists of new business licenses in markdown table format. These contain the business name, license date, business type (e.g., "Restaurant", "Retail Sales"), and address.

2. **News Articles**: Local news sites (WSMV, Fox17, Tennessean) publish "what's opening" roundups. The pipeline extracts business names and addresses from these articles.

3. **Search Snippets**: Tavily web searches for queries like "new restaurant opening Nashville 2026" catch businesses that haven't appeared in other sources yet.

**Processing**: Each discovered business goes through:

1. **Parsing**: Content is routed to the appropriate parser based on source type. License tables are parsed by column headers; news articles are parsed by `##` headings; snippets extract the business name from the page title.

2. **Classification**: The business type is determined by matching keywords in the raw license type or business name (e.g., "grill" → restaurant, "salon" → salon).

3. **Chain Filtering**: Known national chains (McDonald's, Starbucks, etc.) are dropped—they already have corporate POS systems.

4. **Article Title Filtering**: Search snippets that are actually article titles ("10 Best New Restaurants in Nashville") rather than business names are filtered out.

5. **Scoring**: Each lead gets a 0-100 score based on business type, source quality, address completeness, and recency.

6. **County Inference**: If the county isn't known from the source, it's inferred from the city name.

7. **Deduplication**: A fingerprint is generated from the normalized business name + city. Duplicates within the batch keep only the higher-scored version. The database enforces uniqueness so the same business from different sources isn't inserted twice.

**Storage**: New leads are inserted into SQLite with stage "New". The pipeline records which URLs it has seen so they aren't re-processed on future runs.

**Management**: The CLI lets you list, filter, and update leads through the sales pipeline stages: New → Qualified → Contacted → Follow-up → Closed-Won/Closed-Lost.

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              EXTRACT PHASE                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐    │
│  │ Direct URLs      │     │ Search Queries   │     │ Tavily API       │    │
│  │ (license tables) │     │ (sources.yaml)   │     │                  │    │
│  └────────┬─────────┘     └────────┬─────────┘     └────────┬─────────┘    │
│           │                        │                        │              │
│           │    ┌───────────────────┴───────────────────┐    │              │
│           │    │                                       │    │              │
│           ▼    ▼                                       ▼    ▼              │
│  ┌──────────────────┐                         ┌──────────────────┐         │
│  │ Tavily Extract   │                         │ Tavily Search    │         │
│  │ (full page)      │                         │ (10 results)     │         │
│  └────────┬─────────┘                         └────────┬─────────┘         │
│           │                                            │                   │
│           │         ┌──────────────────────────────────┤                   │
│           │         │                                  │                   │
│           │         ▼                                  ▼                   │
│           │  ┌──────────────┐                 ┌──────────────┐             │
│           │  │ Blocked?     │───yes──────────▶│ (dropped)    │             │
│           │  │ (youtube,    │                 └──────────────┘             │
│           │  │  facebook…)  │                                              │
│           │  └──────┬───────┘                                              │
│           │         │ no                                                   │
│           │         ▼                                                      │
│           │  ┌──────────────┐                 ┌──────────────┐             │
│           │  │ Already      │───yes──────────▶│ (skipped)    │             │
│           │  │ seen URL?    │                 └──────────────┘             │
│           │  └──────┬───────┘                                              │
│           │         │ no                                                   │
│           │         ▼                                                      │
│           │  ┌──────────────┐     ┌──────────────────┐                     │
│           │  │ Extractable? │─yes─▶ Tavily Extract   │                     │
│           │  │ domain?      │     │ (full page)      │                     │
│           │  └──────┬───────┘     └────────┬─────────┘                     │
│           │         │ no                   │                               │
│           │         ▼                      │                               │
│           │  ┌──────────────┐              │                               │
│           │  │ Keep as      │              │                               │
│           │  │ snippet only │              │                               │
│           │  └──────┬───────┘              │                               │
│           │         │                      │                               │
│           └─────────┴──────────────────────┘                               │
│                     │                                                      │
│                     ▼                                                      │
│           ┌──────────────────┐                                             │
│           │ RawExtract[]     │                                             │
│           │ • raw_content    │                                             │
│           │ • source_url     │                                             │
│           │ • source_type    │                                             │
│           │ • county         │                                             │
│           │ • title          │                                             │
│           └────────┬─────────┘                                             │
└────────────────────┼────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             TRANSFORM PHASE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │                         ROUTE TO PARSER                          │      │
│  ├──────────────────┬───────────────────────┬───────────────────────┤      │
│  │ license_table    │ news_article          │ search_snippet        │      │
│  │                  │                       │                       │      │
│  │ parse_license_   │ parse_news_article()  │ parse_snippet()       │      │
│  │ table()          │                       │                       │      │
│  │                  │ Splits on ## headings │ Extracts name from    │      │
│  │ Parses markdown  │ Finds address lines   │ title, finds city     │      │
│  │ pipe tables      │ with italic markers   │ in text               │      │
│  │ Maps columns     │ or street numbers     │                       │      │
│  │ by header names  │                       │                       │      │
│  └────────┬─────────┴───────────┬───────────┴───────────┬───────────┘      │
│           │                     │                       │                  │
│           └─────────────────────┼───────────────────────┘                  │
│                                 ▼                                          │
│                      ┌──────────────────┐                                  │
│                      │ BusinessRecord[] │                                  │
│                      └────────┬─────────┘                                  │
│                               │                                            │
│                               ▼                                            │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                           CLASSIFY                                 │    │
│  │  Match raw_type OR business_name against keyword lists:            │    │
│  │  • "grill", "pizza", "sushi" → restaurant                          │    │
│  │  • "salon", "barber", "hair" → salon                               │    │
│  │  • "retail", "store", "shop" → retail                              │    │
│  │  • (no match) → other                                              │    │
│  └────────────────────────────────┬───────────────────────────────────┘    │
│                                   │                                        │
│                                   ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                         CHAIN FILTER                               │    │
│  │  Drop if business_name contains: McDonald's, Starbucks, Walmart…   │    │
│  └────────────────────────────────┬───────────────────────────────────┘    │
│                                   │                                        │
│                                   ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                     ARTICLE TITLE FILTER                           │    │
│  │  (search_snippet only)                                             │    │
│  │  Drop if name looks like article: "10 Best…", "What's Coming…"     │    │
│  └────────────────────────────────┬───────────────────────────────────┘    │
│                                   │                                        │
│                                   ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                            SCORE                                   │    │
│  │  pos_score = type_score + source_score + address_score + recency   │    │
│  │  (0-100, see Lead Scoring section)                                 │    │
│  └────────────────────────────────┬───────────────────────────────────┘    │
│                                   │                                        │
│                                   ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                        INFER COUNTY                                │    │
│  │  If county unknown, lookup city → county from sources.yaml         │    │
│  └────────────────────────────────┬───────────────────────────────────┘    │
│                                   │                                        │
│                                   ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                         DEDUPLICATE                                │    │
│  │  fingerprint = sha256(normalize(name) + "|" + normalize(city))     │    │
│  │  Keep higher-scored record on collision                            │    │
│  └────────────────────────────────┬───────────────────────────────────┘    │
│                                   │                                        │
│                                   ▼                                        │
│                      ┌──────────────────┐                                  │
│                      │ BusinessRecord[] │                                  │
│                      │ (cleaned, scored,│                                  │
│                      │  deduplicated)   │                                  │
│                      └────────┬─────────┘                                  │
└───────────────────────────────┼─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                               LOAD PHASE                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                    INSERT INTO seen_urls                           │    │
│  │  All source URLs from this run (prevents re-processing)            │    │
│  └────────────────────────────────┬───────────────────────────────────┘    │
│                                   │                                        │
│                                   ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                    INSERT OR IGNORE INTO leads                     │    │
│  │  UNIQUE constraint on fingerprint silently skips DB-level dupes    │    │
│  │  Track: new inserts vs duplicates                                  │    │
│  └────────────────────────────────┬───────────────────────────────────┘    │
│                                   │                                        │
│                                   ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                    UPDATE pipeline_runs                            │    │
│  │  Record: leads_found, leads_new, leads_dupes, status               │    │
│  └────────────────────────────────┬───────────────────────────────────┘    │
│                                   │                                        │
│                                   ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                    APPEND TO pipeline.log                          │    │
│  │  Human-readable run summary                                        │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Architecture

### Project Structure

```
newBusinessLocator/
├── cli/
│   └── main.py              # Click CLI: run, leads, lead, update, stats, export, rescore, schedule
├── config/
│   ├── settings.py          # Environment variables, file paths
│   ├── sources.yaml         # Search queries, domain lists, county→city mappings
│   ├── scoring.yaml         # Business type scores, keywords, scoring weights
│   └── chains.yaml          # Blocklist of national chain names
├── db/
│   ├── schema.py            # DDL statements, init_db()
│   └── queries.py           # Named SQL functions (get_leads, insert_lead, etc.)
├── etl/
│   ├── extract.py           # Tavily search/extract, URL filtering
│   ├── transform.py         # Parse, classify, filter, score, dedupe
│   ├── load.py              # Insert leads, update seen_urls, log runs
│   └── pipeline.py          # Orchestrator: extract→transform→load
├── utils/
│   ├── tavily_client.py     # HTTP client for Tavily API with rate limiting
│   ├── parsers.py           # parse_license_table, parse_news_article, parse_snippet
│   ├── dedup.py             # Fingerprint generation with name normalization
│   └── logging_config.py    # Structured logging setup
├── tests/                   # Pytest test suite
├── data/
│   └── leads.db             # SQLite database (created on first run)
├── logs/
│   └── pipeline.log         # Run history log
└── scripts/
    └── com.newbusinesslocator.weekly.plist  # macOS launchd template
```

### Key Design Decisions

**YAML Configuration**: All business rules (search queries, scoring weights, chain blocklist) are in YAML files. Tuning the pipeline requires no code changes.

**Three-Tier Source Strategy**:
- **Tier A (License Tables)**: Highest value—structured data directly from county government sources
- **Tier B (News Articles)**: Medium value—local news "what's opening" roundups
- **Tier C (Search Sweeps)**: Catch-all—broad searches for business types that might be missed

**Two-Level Deduplication**:
1. **In-batch**: Transform phase keeps the higher-scored record when fingerprints collide
2. **Cross-run**: Database UNIQUE constraint on fingerprint silently ignores duplicates

**Fingerprint Algorithm**: `sha256(normalized_name + "|" + normalized_city)[:32]`
- Name normalization: lowercase → strip legal suffixes (LLC, Inc) → remove punctuation except hyphens → remove common words (the, and, &)
- 128-bit hash prefix balances collision resistance with readability

---

## Installation

### Prerequisites

- Python 3.10+
- Tavily API key ([get one here](https://tavily.com))

### Setup

```bash
# Clone the repository
git clone <repo-url>
cd newBusinessLocator

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set your Tavily API key
export TAVILY_API_KEY="your-api-key-here"
```

The database (`data/leads.db`) is created automatically on first run.

---

## Configuration

### sources.yaml

**County mappings** — used to infer county from city name:
```yaml
counties:
  Davidson:
    - Nashville
    - Antioch
    - Madison
  Williamson:
    - Franklin
    - Brentwood
```

**Domain filtering**:
```yaml
extractable_domains:   # Full page extraction attempted
  - davidsoncountysource.com
  - nashvilleguru.com
  - tennessean.com

blocked_domains:       # Completely ignored
  - youtube.com
  - facebook.com
```

**Search queries** (Tier A/B/C):
```yaml
queries:
  - query: "site:davidsoncountysource.com new business licenses"
    county: Davidson
    tier: A
  - query: "new business opening Nashville 2026"
    county: Davidson
    tier: B
```

**Direct extract URLs** — license table pages that don't surface via search:
```yaml
direct_extract_urls:
  - url: "https://davidsoncountysource.com/davidson-county-new-business-licenses-for-feb-2-2026/"
    county: Davidson
```

### scoring.yaml

**Business type scores** (max 50 points):
```yaml
type_scores:
  restaurant: 50
  bar: 48
  cafe: 45
  retail: 45
  salon: 40
  other: 10
```

**Classification keywords** — first match wins:
```yaml
business_type_keywords:
  restaurant:
    - restaurant
    - grill
    - pizza
    - sushi
  salon:
    - salon
    - barber
    - hair
```

**Source confidence scores** (max 20 points):
```yaml
source_scores:
  license_table: 20
  news_article: 15
  search_snippet: 8
```

### chains.yaml

Blocklist of national chains (case-insensitive substring match):
```yaml
chains:
  - McDonald's
  - Starbucks
  - Walmart
  - Chick-fil-A
  # ... 45+ chains
```

---

## CLI Reference

All commands are run via `python -m cli.main <command>`.

### Pipeline Operations

```bash
# Run full ETL pipeline
python -m cli.main run

# Preview results without writing to database
python -m cli.main run --dry-run

# Re-classify and re-score all existing leads
# (useful after updating scoring.yaml keywords)
python -m cli.main rescore
```

### Lead Management

```bash
# List leads with filters
python -m cli.main leads
python -m cli.main leads --stage New --county Davidson --min-score 40
python -m cli.main leads --sort pos_score --limit 20

# View full details for a single lead
python -m cli.main lead 42

# Update lead stage and add notes
python -m cli.main update 42 --stage Qualified
python -m cli.main update 42 --stage Contacted --note "Left voicemail"

# View stage change history
python -m cli.main history 42
```

### Reporting

```bash
# Dashboard with counts by stage, county, type
python -m cli.main stats

# Export to CSV
python -m cli.main export --output leads.csv
python -m cli.main export --stage New --min-score 50 --output hot-leads.csv
```

### Scheduling (macOS only)

```bash
# Install weekly run (Sundays at 6 AM)
python -m cli.main schedule install

# Check status
python -m cli.main schedule status

# Remove scheduled job
python -m cli.main schedule uninstall
```

### Global Options

```bash
# Set log level (DEBUG, INFO, WARNING, ERROR)
python -m cli.main --log-level DEBUG run

# Also output logs to console
python -m cli.main --log-console run
```

---

## Database Schema

### leads

The main table—one row per unique business.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| fingerprint | TEXT | Unique dedup key (sha256 hash prefix) |
| business_name | TEXT | Business name |
| business_type | TEXT | Classified type (restaurant, salon, etc.) |
| raw_type | TEXT | Original type text from source |
| address | TEXT | Street address |
| city | TEXT | City name |
| state | TEXT | State (default: TN) |
| zip_code | TEXT | ZIP code |
| county | TEXT | County name |
| license_date | TEXT | License issue date (ISO format) |
| pos_score | INTEGER | Lead quality score (0-100) |
| stage | TEXT | Pipeline stage |
| source_url | TEXT | Where this lead was found |
| source_type | TEXT | license_table, news_article, or search_snippet |
| notes | TEXT | User-added notes |
| created_at | TEXT | When lead was inserted |
| updated_at | TEXT | Last modification time |
| contacted_at | TEXT | When stage first hit "Contacted" |
| closed_at | TEXT | When stage hit Closed-Won/Lost |

**Stage workflow**: New → Qualified → Contacted → Follow-up → Closed-Won / Closed-Lost

### pipeline_runs

Audit log of every ETL execution.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Run ID |
| run_started_at | TEXT | Start timestamp |
| run_finished_at | TEXT | End timestamp |
| status | TEXT | running, completed, or failed |
| leads_found | INTEGER | Total records after transform |
| leads_new | INTEGER | New inserts |
| leads_dupes | INTEGER | Duplicates skipped |
| error_message | TEXT | Error details if failed |
| sources_queried | TEXT | JSON array of processed URLs |

### seen_urls

Tracks URLs that have been processed to prevent re-extraction.

| Column | Type | Description |
|--------|------|-------------|
| url | TEXT | Primary key |
| first_seen_at | TEXT | When URL was first processed |
| county | TEXT | County associated with this URL |

### stage_history

Append-only audit trail of stage changes.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| lead_id | INTEGER | Foreign key to leads |
| old_stage | TEXT | Previous stage |
| new_stage | TEXT | New stage |
| changed_at | TEXT | Timestamp of change |

---

## Lead Scoring

Each lead receives a score from 0-100 based on four components:

### A. Business Type (max 50 points)

How likely is this business type to need a POS system?

| Type | Score | Rationale |
|------|-------|-----------|
| restaurant | 50 | High transaction volume, tips, kitchen tickets |
| bar | 48 | Tab management, age verification |
| cafe | 45 | Quick service, inventory |
| retail | 45 | Inventory, returns, loyalty programs |
| liquor | 42 | Inventory tracking, compliance |
| salon | 40 | Appointments + payments |
| bakery | 40 | Quick service retail |
| spa | 38 | Services + retail products |
| food_service | 35 | Catering, food trucks |
| automotive | 25 | Service tickets, parts |
| services | 20 | General service businesses |
| other | 10 | Unknown type |
| consulting | 5 | Typically invoicing, not POS |
| real_estate | 5 | No retail transactions |
| construction | 5 | Project-based billing |

### B. Source Confidence (max 20 points)

How reliable is the data source?

| Source | Score | Rationale |
|--------|-------|-----------|
| license_table | 20 | Official government records |
| news_article | 15 | Journalist-verified |
| search_snippet | 8 | May be outdated or misidentified |

### C. Address Completeness (max 15 points)

More complete addresses mean easier contact.

| Completeness | Score |
|--------------|-------|
| Street + City + ZIP | 15 |
| Street + City | 10 |
| City only | 5 |
| None | 0 |

### D. Recency (max 15 points)

How recently was the license issued? (License table sources only)

| Days Since License | Score |
|-------------------|-------|
| ≤ 7 days | 15 |
| ≤ 14 days | 10 |
| ≤ 30 days | 5 |
| > 30 days or unknown | 0 |

### Score Examples

**High-value lead (score 85)**:
- Restaurant (50) from license table (20) with full address (15) filed this week (15) = 100 (capped)

**Medium-value lead (score 53)**:
- Salon (40) from news article (15) with city only (5) = 60

**Low-value lead (score 23)**:
- Other (10) from search snippet (8) with city only (5) = 23

---

## Testing

Tests use pytest and cover the transform functions.

```bash
# Run all tests
pytest tests/

# Run a specific test file
pytest tests/test_transform.py

# Run with verbose output
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=etl --cov=utils
```

### Test Coverage

- `test_transform.py` — classify, is_chain, is_article_title, score_lead, infer_county, deduplicate
- `test_parsers.py` — parse_license_table, parse_news_article, parse_snippet
- `test_dedup.py` — fingerprint generation, name normalization
- `test_extract.py` — domain filtering, URL handling
- `test_load.py` — database insertion, duplicate handling
- `test_db.py` — schema initialization, query functions

---

## Target Geography

The pipeline focuses on Nashville and Middle Tennessee:

| County | Primary Cities |
|--------|----------------|
| Davidson | Nashville, Antioch, Madison, Hermitage |
| Williamson | Franklin, Brentwood, Nolensville, Spring Hill |
| Rutherford | Murfreesboro, Smyrna, La Vergne |
| Sumner | Gallatin, Hendersonville, Portland |
| Wilson | Lebanon, Mount Juliet |
| Robertson | Springfield, White House, Greenbrier |
| Maury | Columbia, Spring Hill, Mt. Pleasant |
| Dickson | Dickson, White Bluff |

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| TAVILY_API_KEY | Yes | API key for Tavily search/extract |
| LOG_LEVEL | No | Logging level (default: INFO) |

---

## Files Created

| Path | Description |
|------|-------------|
| `data/leads.db` | SQLite database |
| `logs/pipeline.log` | Run history (appended) |
| `logs/launchd_stdout.log` | Scheduled run output (if using schedule) |
| `logs/launchd_stderr.log` | Scheduled run errors (if using schedule) |

---

## License

Private repository.
