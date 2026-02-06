# New Business Locator

A lead generation ETL pipeline that discovers new businesses opening in Nashville and Middle Tennessee, scores them for POS (Point-of-Sale) system sales relevance, and provides both CLI and web interfaces for managing the sales pipeline.

## Table of Contents

- [The Problem](#the-problem)
- [How It Works](#how-it-works)
- [Data Flow](#data-flow)
- [Architecture](#architecture)
- [Installation](#installation)
- [Web Interface](#web-interface)
- [Configuration](#configuration)
- [CLI Reference](#cli-reference)
- [API Reference](#api-reference)
- [Database Schema](#database-schema)
- [Lead Scoring](#lead-scoring)
- [Target Geography](#target-geography)
- [Environment Variables](#environment-variables)
- [Files Created](#files-created)
- [Development](#development)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

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

3. **Chain Filtering**: Known national chains (McDonald's, Starbucks, etc.) are dropped—they already have corporate POS systems. The blocklist contains 58 chain/franchise names.

4. **Article Title Filtering**: Search snippets that are actually article titles ("10 Best New Restaurants in Nashville") rather than business names are filtered out.

5. **Scoring**: Each lead gets a 0-100 score based on business type, source quality, address completeness, and recency.

6. **County Inference**: If the county isn't known from the source, it's inferred from the city name using the county→city mapping in `sources.yaml`.

7. **Deduplication**: A fingerprint is generated from the normalized business name + city. Duplicates within the batch keep only the higher-scored version. The database enforces uniqueness so the same business from different sources isn't inserted twice.

**Storage**: New leads are inserted into SQLite with stage "New". The pipeline records which URLs it has seen so they aren't re-processed on future runs.

**Management**: The CLI and web dashboard let you list, filter, and update leads through the sales pipeline stages: New → Qualified → Contacted → Follow-up → Closed-Won/Closed-Lost.

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
├── api/                     # FastAPI backend
│   ├── main.py              # App entry point, CORS, router mounting
│   ├── dependencies.py      # Database connection injection (per-request)
│   └── routers/
│       ├── leads.py         # Lead CRUD, search, bulk ops, duplicate detection/merge
│       ├── stats.py         # Aggregate statistics
│       ├── kanban.py        # Stage-based board data
│       └── pipeline.py      # Trigger ETL runs, run history, status
├── frontend/                # Next.js 14 web dashboard
│   ├── app/
│   │   ├── layout.tsx       # Root layout with AppShell, providers
│   │   ├── globals.css      # Glassmorphism design system, theme tokens
│   │   ├── page.tsx         # Dashboard with stats cards and charts
│   │   ├── leads/page.tsx   # Paginated lead table with filters
│   │   ├── kanban/page.tsx  # Drag-drop stage management
│   │   ├── duplicates/page.tsx  # Duplicate detection and merge UI
│   │   ├── pipeline/page.tsx    # ETL run history and trigger
│   │   └── batch/[id]/page.tsx  # Leads from specific extraction batch
│   ├── components/          # React components
│   │   ├── ui/              # shadcn/ui primitives (Button, Card, Dialog, Select, etc.)
│   │   ├── lead-table.tsx   # Sortable table with selection and pagination
│   │   ├── lead-detail-panel.tsx  # Full lead editor panel
│   │   ├── lead-filters.tsx # Filter UI controls
│   │   ├── filter-presets.tsx   # Saved/quick filter presets
│   │   ├── kanban-board.tsx # Drag-drop stage columns
│   │   ├── kanban-card.tsx  # Individual kanban card
│   │   ├── score-badge.tsx  # Visual score indicator
│   │   ├── stats-cards.tsx  # Summary stat cards
│   │   ├── charts.tsx       # Recharts visualizations
│   │   ├── nav-sidebar.tsx  # Navigation sidebar
│   │   ├── app-shell.tsx    # Shell wrapper
│   │   └── providers.tsx    # QueryClient provider
│   └── lib/
│       ├── api.ts           # API client functions (getLeads, updateLead, mergeLeads, etc.)
│       ├── types.ts         # TypeScript interfaces (Lead, Stats, PipelineRun, etc.)
│       └── utils.ts         # Utility functions
├── cli/
│   └── main.py              # Click CLI: run, leads, lead, update, stats, export, rescore, history, schedule
├── config/
│   ├── settings.py          # Environment variables, file paths
│   ├── sources.yaml         # Search queries, domain lists, county→city mappings
│   ├── scoring.yaml         # Business type scores, keywords, scoring weights
│   └── chains.yaml          # Blocklist of 58 national chain names
├── db/
│   ├── schema.py            # DDL statements, init_db(), FTS5 triggers
│   └── queries.py           # Named SQL functions (get_leads, insert_lead, search_leads, etc.)
├── etl/
│   ├── extract.py           # Tavily search/extract, URL filtering, domain classification
│   ├── transform.py         # Parse, classify, filter, score, county inference, dedupe
│   ├── load.py              # Insert leads, update seen_urls, log runs (atomic transactions)
│   └── pipeline.py          # Orchestrator: extract→transform→load with dry_run support
├── utils/
│   ├── tavily_client.py     # HTTP client for Tavily API with rate limiting and retry
│   ├── parsers.py           # parse_license_table, parse_news_article, parse_snippet
│   ├── dedup.py             # Fingerprint generation with name normalization
│   └── logging_config.py    # Structured logging setup with file/console handlers
├── tests/                   # Pytest test suite (unit, integration, UAT)
│   ├── conftest.py          # Fixtures (temp DB, sample configs, mock leads)
│   ├── test_parsers.py      # Parser tests for all three source types
│   ├── test_transform.py    # Classify, score, filter, deduplicate tests
│   ├── test_extract.py      # Extract phase with Tavily mocking
│   ├── test_load.py         # Insert, dedup tracking, audit trail tests
│   ├── test_db.py           # Schema, CRUD, FTS, stats aggregation tests
│   ├── test_dedup.py        # Fingerprint and normalization tests
│   ├── test_api.py          # API endpoint integration tests
│   └── uat_playwright_test.py  # Browser-based UAT with Playwright
├── scripts/
│   ├── dev.sh               # Start API + frontend servers together
│   └── com.newbusinesslocator.weekly.plist  # macOS LaunchAgent template
├── data/
│   └── leads.db             # SQLite database (created on first run)
├── logs/
│   └── pipeline.log         # Run history log (appended)
├── requirements.txt         # Python dependencies
└── pytest.ini               # Test configuration
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
- Name normalization: lowercase → strip legal suffixes (LLC, Inc, Corp, Ltd, Co) → remove punctuation except hyphens → remove common words (the, and, &)
- 128-bit hash prefix balances collision resistance with readability

**No ORM**: Raw SQL with bound parameters in `db/queries.py` for full control over queries and performance.

**Per-Request Database Connections**: FastAPI dependency injection (`Depends(get_db)`) provides one SQLite connection per request, automatically closed after response.

**Async Pipeline Execution**: Pipeline runs triggered via the API execute as FastAPI `BackgroundTasks` so the HTTP response returns immediately.

---

## Installation

### Prerequisites

- Python 3.10+
- Node.js 18+ (for the web frontend)
- Tavily API key ([get one here](https://tavily.com))

### macOS Setup

```bash
# Clone the repository
git clone <repo-url>
cd newBusinessLocator

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Set your Tavily API key (add to ~/.zshrc to persist across sessions)
export TAVILY_API_KEY="your-api-key-here"

# Install frontend dependencies
cd frontend && npm install && cd ..

# Initialize the database (created automatically on first run)
python -m cli.main stats

# Start both API and frontend servers
./scripts/dev.sh
```

**Scheduling (macOS only):** The pipeline can run weekly via a macOS LaunchAgent:

```bash
python -m cli.main schedule install    # Installs Sunday 6 AM weekly job
python -m cli.main schedule status     # Check job status
python -m cli.main schedule uninstall  # Remove scheduled job
```

### Windows Setup

```powershell
# Clone the repository
git clone <repo-url>
cd newBusinessLocator

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Set your Tavily API key (for current session)
$env:TAVILY_API_KEY = "your-api-key-here"

# To persist across sessions, set it as a system environment variable:
# Settings > System > About > Advanced system settings > Environment Variables
# Or via PowerShell (requires admin):
# [System.Environment]::SetEnvironmentVariable("TAVILY_API_KEY", "your-api-key-here", "User")

# Install frontend dependencies
cd frontend
npm install
cd ..

# Initialize the database (created automatically on first run)
python -m cli.main stats
```

**Starting the servers on Windows** (run in two separate terminals):

```powershell
# Terminal 1: API server
.venv\Scripts\activate
uvicorn api.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
```

> **Note:** The `scripts/dev.sh` helper script is bash-only (macOS/Linux). On Windows, start the API and frontend in separate terminals as shown above.

**Scheduling (Windows):** Use Task Scheduler to run the pipeline on a recurring basis:

1. Open Task Scheduler (`taskschd.msc`)
2. Create a new task with a trigger (e.g., weekly)
3. Set the action to run: `<path-to-project>\.venv\Scripts\python.exe -m cli.main run`
4. Set "Start in" to the project directory

### Python Dependencies

| Package | Purpose |
|---------|---------|
| `requests` | HTTP client for Tavily API |
| `click` | CLI framework |
| `pyyaml` | YAML config parsing |
| `fastapi` | Web API framework |
| `uvicorn` | ASGI server |
| `python-dotenv` | Load `.env` file variables |
| `pytest` | Testing framework |
| `pytest-mock` | Mock fixtures for testing |

The database (`data/leads.db`) is created automatically on first run.

---

## Web Interface

The application includes a full-featured web dashboard built with Next.js and FastAPI.

### Quick Start

```bash
# Start both API and frontend servers
./scripts/dev.sh

# Or start separately:
# Terminal 1: API server
uvicorn api.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev
```

The `dev.sh` script starts both servers, handles cleanup on Ctrl+C, and displays access URLs.

**Access:**
- Dashboard: http://localhost:3000
- API Documentation: http://localhost:8000/docs (interactive Swagger UI)

### Dashboard Features

| Page | URL | Description |
|------|-----|-------------|
| **Dashboard** | `/` | Stats cards showing leads by stage, county, and type. Charts for score distribution and recent activity. |
| **Leads** | `/leads` | Paginated table with filters (stage, county, score range, full-text search). Click any row to view/edit details. |
| **Kanban** | `/kanban` | Drag-and-drop board organized by pipeline stage. Quick stage changes without opening lead details. |
| **Duplicates** | `/duplicates` | Review potential duplicate leads detected by fuzzy matching. Merge or dismiss suggestions. |
| **Pipeline** | `/pipeline` | View ETL run history. Trigger new runs manually. See leads discovered in each batch. |
| **Batch** | `/batch/[id]` | View all leads discovered in a specific extraction batch. |

### Frontend Stack

| Library | Version | Purpose |
|---------|---------|---------|
| Next.js | 14.2.35 | React framework with App Router |
| React | 18 | UI library |
| TypeScript | 5 | Type safety |
| @tanstack/react-query | 5.90.20 | Server state management (staleTime: 5s) |
| shadcn/ui | — | Accessible components built on Radix UI primitives |
| Tailwind CSS | 3.4.1 | Utility-first styling |
| @dnd-kit | 6.3.1 / 10.0.0 | Kanban drag-and-drop |
| Recharts | 3.7.0 | Data visualization |
| next-themes | 0.4.6 | Dark/light mode (dark default) |
| Sonner | 2.0.7 | Toast notifications |
| Lucide React | 0.563.0 | Icon library |

### Design System

The UI uses a **glassmorphism** design language with blue-indigo accent gradients. Key CSS utility classes are defined in `globals.css`:

| Class | Effect |
|-------|--------|
| `.glass` | Standard backdrop-blur panel |
| `.glass-strong` | Higher intensity blur/opacity |
| `.glass-subtle` | Lower intensity, more transparent |
| `.bg-mesh` | Radial gradient mesh background (adapts to dark/light) |
| `.bg-accent-gradient` | Blue-to-purple gradient fill |
| `.text-gradient` | Gradient text effect |
| `.glow-hover` | Cards emit subtle glow on hover |
| `.custom-scrollbar` | Thin styled scrollbar |

Design tokens use HSL CSS custom properties. Both light and dark modes define `--glass-bg`, `--glass-border`, `--glass-blur`, and `--glass-shadow` tokens. The `Card` component applies glass effects by default.

Theme toggle in the sidebar uses `next-themes` with a `mounted` guard to avoid hydration mismatch.

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

**Address completeness scores** (max 15 points):
```yaml
address_scores:
  street_city_zip: 15
  street_city: 10
  city_only: 5
```

**Recency scores** (max 15 points):
```yaml
recency_scores:
  within_7_days: 15
  within_14_days: 10
  within_30_days: 5
```

### chains.yaml

Blocklist of 58 national chains (case-insensitive substring match):
```yaml
chains:
  - McDonald's
  - Starbucks
  - Walmart
  - Chick-fil-A
  - Chipotle
  - Wawa
  # ... 52 more chains
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

### Scheduling

**macOS** — uses a LaunchAgent (`com.newbusinesslocator.weekly.plist`):

```bash
# Install weekly run (Sundays at 6 AM)
python -m cli.main schedule install

# Check status
python -m cli.main schedule status

# Remove scheduled job
python -m cli.main schedule uninstall
```

**Windows** — use Task Scheduler (`taskschd.msc`):

1. Open Task Scheduler and click "Create Basic Task"
2. Set trigger to Weekly (e.g., Sunday 6:00 AM)
3. Action: Start a program
   - Program: `<project-path>\.venv\Scripts\python.exe`
   - Arguments: `-m cli.main run`
   - Start in: `<project-path>`
4. Ensure "Run whether user is logged on or not" is checked

### Global Options

```bash
# Set log level (DEBUG, INFO, WARNING, ERROR)
python -m cli.main --log-level DEBUG run

# Also output logs to console
python -m cli.main --log-console run
```

---

## API Reference

The FastAPI backend provides a RESTful API for all lead operations. Full interactive documentation is available at http://localhost:8000/docs when the server is running.

### Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| **Leads** | | |
| `GET` | `/api/leads` | List leads with filters and pagination |
| `GET` | `/api/leads/export` | Download filtered leads as CSV |
| `GET` | `/api/leads/batch/{batch_id}` | Get leads from specific extraction batch |
| `GET` | `/api/leads/{id}` | Get single lead details |
| `PATCH` | `/api/leads/{id}` | Update lead fields, stage, or add notes |
| `PATCH` | `/api/leads/{id}/stage` | Quick stage change (for kanban drag-drop) |
| `POST` | `/api/leads/bulk` | Bulk update stage/county for multiple leads |
| `DELETE` | `/api/leads/bulk` | Soft-delete multiple leads |
| **Duplicates** | | |
| `GET` | `/api/leads/duplicates/count` | Count pending duplicate suggestions |
| `GET` | `/api/leads/duplicates` | List duplicate suggestions with full lead data |
| `POST` | `/api/leads/duplicates/scan` | Trigger duplicate detection scan |
| `PATCH` | `/api/leads/duplicates/{id}` | Update suggestion status (merged/dismissed) |
| `POST` | `/api/leads/merge` | Merge two leads into one |
| **Stats & Kanban** | | |
| `GET` | `/api/stats` | Aggregate statistics |
| `GET` | `/api/kanban` | Leads grouped by stage for board view |
| **Pipeline** | | |
| `GET` | `/api/pipeline/runs` | List pipeline run history |
| `GET` | `/api/pipeline/status` | Current pipeline status (running/idle) |
| `POST` | `/api/pipeline/run` | Trigger ETL pipeline run (async background task) |

### Pagination

List endpoints support pagination via query parameters:

```
GET /api/leads?page=1&pageSize=50&stage=New&county=Davidson&minScore=40
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number (1-indexed) |
| `pageSize` | int | 50 | Results per page |
| `stage` | string | — | Filter by pipeline stage |
| `county` | string | — | Filter by county |
| `minScore` | int | — | Minimum pos_score (inclusive) |
| `maxScore` | int | — | Maximum pos_score (inclusive) |
| `q` | string | — | Full-text search on business name, city, address |
| `sort` | string | pos_score | Column to sort by (descending) |

Response includes pagination metadata:

```json
{
  "leads": [...],
  "count": 50,
  "total": 150,
  "page": 1,
  "pageSize": 50,
  "totalPages": 3
}
```

### Lead Update

The `PATCH /api/leads/{id}` endpoint supports both query parameters and JSON body:

```json
{
  "business_name": "Updated Name",
  "address": "123 Main St",
  "city": "Nashville",
  "county": "Davidson",
  "zip_code": "37201",
  "business_type": "restaurant",
  "stage": "Qualified",
  "note": "Spoke with owner"
}
```

Valid stages: `New`, `Qualified`, `Contacted`, `Follow-up`, `Closed-Won`, `Closed-Lost`

Valid business types: `restaurant`, `bar`, `retail`, `salon`, `cafe`, `bakery`, `gym`, `spa`, `other`

### Merge Request

The `POST /api/leads/merge` endpoint merges two leads:

```json
{
  "keep_id": 42,
  "merge_id": 87,
  "field_choices": {"address": 87, "city": 42},
  "suggestion_id": 5
}
```

The `field_choices` dict maps field names to the lead ID whose value should be kept. The merged lead is soft-deleted.

---

## Database Schema

### leads

The main table — one row per unique business.

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| id | INTEGER | auto | Primary key |
| fingerprint | TEXT | — | Unique dedup key (sha256 hash prefix, 32 hex chars) |
| business_name | TEXT | — | Business name (NOT NULL) |
| business_type | TEXT | — | Classified type (restaurant, salon, etc.) |
| raw_type | TEXT | — | Original type text from source |
| address | TEXT | — | Street address |
| city | TEXT | — | City name |
| state | TEXT | `'TN'` | State |
| zip_code | TEXT | — | ZIP code |
| county | TEXT | — | County name |
| license_date | TEXT | — | License issue date (ISO format) |
| pos_score | INTEGER | `0` | Lead quality score (0-100) |
| stage | TEXT | `'New'` | Pipeline stage |
| source_url | TEXT | — | Where this lead was found |
| source_type | TEXT | — | license_table, news_article, or search_snippet |
| source_batch_id | TEXT | — | Groups leads from same pipeline run |
| notes | TEXT | — | User-added notes |
| created_at | TEXT | `datetime('now')` | When lead was inserted |
| updated_at | TEXT | `datetime('now')` | Last modification time |
| contacted_at | TEXT | — | When stage first hit "Contacted" |
| closed_at | TEXT | — | When stage hit Closed-Won/Lost |
| deleted_at | TEXT | — | Soft delete timestamp |

**Indexes**: fingerprint, city, county, stage, pos_score, source_batch_id

**Stage workflow**: New → Qualified → Contacted → Follow-up → Closed-Won / Closed-Lost

### pipeline_runs

Audit log of every ETL execution.

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| id | INTEGER | auto | Run ID |
| run_started_at | TEXT | — | Start timestamp |
| run_finished_at | TEXT | — | End timestamp |
| status | TEXT | `'running'` | running, completed, or failed |
| leads_found | INTEGER | `0` | Total records after transform |
| leads_new | INTEGER | `0` | New inserts |
| leads_dupes | INTEGER | `0` | Duplicates skipped |
| error_message | TEXT | — | Error details if failed |
| sources_queried | TEXT | — | JSON array of processed URLs |

### seen_urls

Tracks URLs that have been processed to prevent re-extraction.

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| url | TEXT | — | Primary key |
| first_seen_at | TEXT | `datetime('now')` | When URL was first processed |
| county | TEXT | — | County associated with this URL |

### stage_history

Append-only audit trail of stage changes.

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| id | INTEGER | auto | Primary key |
| lead_id | INTEGER | — | Foreign key to leads |
| old_stage | TEXT | — | Previous stage |
| new_stage | TEXT | — | New stage |
| changed_at | TEXT | `datetime('now')` | Timestamp of change |

**Index**: lead_id

### duplicate_suggestions

Potential duplicates detected by fuzzy matching.

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| id | INTEGER | auto | Primary key |
| lead_id_a | INTEGER | — | First lead in pair (FK to leads) |
| lead_id_b | INTEGER | — | Second lead in pair (FK to leads) |
| similarity_score | REAL | — | Match confidence (0.0-1.0) |
| status | TEXT | `'pending'` | pending, merged, or dismissed |
| created_at | TEXT | `datetime('now')` | When suggestion was created |
| resolved_at | TEXT | — | When suggestion was resolved |

**Constraints**: UNIQUE(lead_id_a, lead_id_b)

**Indexes**: status, lead_id_a, lead_id_b

### leads_fts

FTS5 virtual table for full-text search on `business_name`, `city`, and `address`. Kept in sync via SQLite triggers on insert, update, and delete.

### Database Configuration

- **Busy timeout**: 30 seconds (`PRAGMA busy_timeout = 30000`)
- **Row factory**: `sqlite3.Row` for dict-like column access
- **FTS sync**: Automatic via three triggers (`leads_fts_ai`, `leads_fts_ad`, `leads_fts_au`)

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

**High-value lead (score 100)**:
- Restaurant (50) from license table (20) with full address (15) filed this week (15) = 100

**Medium-value lead (score 60)**:
- Salon (40) from news article (15) with city only (5) = 60

**Low-value lead (score 23)**:
- Other (10) from search snippet (8) with city only (5) = 23

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

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TAVILY_API_KEY` | Yes | — | API key for Tavily search/extract |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

---

## Files Created

| Path | Description |
|------|-------------|
| `data/leads.db` | SQLite database (created on first run) |
| `logs/pipeline.log` | Run history (appended each run) |
| `logs/launchd_stdout.log` | Scheduled run output (if using macOS schedule) |
| `logs/launchd_stderr.log` | Scheduled run errors (if using macOS schedule) |

---

## Development

### Running the API

```bash
# Start with auto-reload
uvicorn api.main:app --reload --port 8000

# Interactive API docs at http://localhost:8000/docs
```

**CORS**: The API allows requests from `http://localhost:3000` only (hardcoded in `api/main.py`).

### Frontend Development

```bash
cd frontend

# Install dependencies (first time only)
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Run linter
npm run lint
```

### Utility Modules

**`utils/tavily_client.py`** — HTTP wrapper around the Tavily API:
- `search()` — Perform web search, returns results array
- `extract()` — Extract full page content from URLs
- Rate limiting with 0.5s delay between requests
- Exponential backoff on HTTP 429 (rate limit exceeded)
- 3 max retries with 1.0s initial backoff

**`utils/parsers.py`** — Content parsers for each source type:
- `parse_license_table()` — Parses markdown pipe tables, maps columns by header names
- `parse_news_article()` — Splits on `##` headings, finds addresses via italic markers or street number patterns
- `parse_snippet()` — Extracts business name from search result title, finds city in text
- Helpers: `_split_address_parts()`, `_map_header_to_field()`, `_empty_record()`

**`utils/dedup.py`** — Fingerprint generation:
- `normalize_name()` — Lowercase, strip legal suffixes, remove punctuation except hyphens, remove common words
- `normalize_city()` — Lowercase and strip whitespace
- `generate_fingerprint()` — SHA256(normalized_name|normalized_city)[:32]

**`utils/logging_config.py`** — Structured logging:
- `setup_logging()` — Configure root logger with file and optional console handlers
- `get_logger()` — Get module-specific logger
- Log format: `%(asctime)s | %(name)s | %(levelname)s | %(message)s`

---

## Testing

### Test Configuration

Tests are configured via `pytest.ini`:
- Test paths: `tests/`
- Test file pattern: `test_*.py`
- Test class pattern: `Test*`
- Default options: `-v --tb=short`

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_transform.py

# Run specific test by name
pytest tests/test_transform.py::TestClassify::test_classifies_restaurant_by_raw_type -v

# Run with coverage
pytest tests/ --cov=etl --cov=utils --cov=db
```

### Test Suite

| File | Lines | Coverage |
|------|-------|----------|
| `conftest.py` | ~390 | Fixtures: temp DB, sample YAML configs, mock lead data |
| `test_parsers.py` | ~750 | License table parsing, news article parsing, snippet extraction, address splitting |
| `test_transform.py` | ~710 | Classification, chain detection, article title filtering, scoring, county inference, deduplication |
| `test_extract.py` | ~330 | Extract phase with mocked Tavily responses |
| `test_load.py` | ~350 | Lead insertion, duplicate tracking, seen_url recording, pipeline run audit |
| `test_db.py` | ~550 | Schema creation, CRUD operations, FTS search, stats aggregation, stage history |
| `test_dedup.py` | ~180 | Fingerprint generation, name normalization, edge cases |
| `test_api.py` | ~230 | API endpoint integration tests with test client |
| `uat_playwright_test.py` | ~690 | Browser-based user acceptance tests with Playwright (screenshots saved to `tests/screenshots/`) |

### UAT Tests

The `uat_playwright_test.py` file contains browser-based acceptance tests using Playwright. These test the full frontend-to-API flow including navigation, filtering, kanban interactions, and visual regression (screenshots).

---

## Troubleshooting

### Frontend shows "missing required error components, refreshing..."

**Symptom:** The browser shows a blank page with the text "missing required error components, refreshing..." and the console logs repeated 404 errors for `http://localhost:3000/`. All routes return 404.

**Cause:** The Next.js development cache (`frontend/.next/`) has become corrupted. This can happen after switching branches, interrupted builds, or stale dev server state. The code itself is fine — a production build (`npm run build`) will succeed even when this occurs.

**Fix (macOS/Linux):**

```bash
# 1. Stop the frontend dev server (Ctrl+C, or kill the process)
kill $(lsof -ti :3000)

# 2. Delete the corrupted cache
rm -rf frontend/.next

# 3. Restart the dev server
cd frontend && npm run dev
```

**Fix (Windows — PowerShell):**

```powershell
# 1. Stop the frontend dev server (Ctrl+C in its terminal, or kill the process)
Stop-Process -Id (Get-NetTCPConnection -LocalPort 3000).OwningProcess -Force

# 2. Delete the corrupted cache
Remove-Item -Recurse -Force frontend\.next

# 3. Restart the dev server
cd frontend; npm run dev
```

### API server fails to start (port already in use)

**Symptom:** `uvicorn` fails with "Address already in use" on port 8000.

**Fix (macOS/Linux):**

```bash
kill $(lsof -ti :8000)
uvicorn api.main:app --reload --port 8000
```

**Fix (Windows — PowerShell):**

```powershell
Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess -Force
uvicorn api.main:app --reload --port 8000
```

### Frontend dev server fails to start (port already in use)

**Symptom:** `npm run dev` fails because port 3000 is taken.

**Fix (macOS/Linux):**

```bash
kill $(lsof -ti :3000)
cd frontend && npm run dev
```

**Fix (Windows — PowerShell):**

```powershell
Stop-Process -Id (Get-NetTCPConnection -LocalPort 3000).OwningProcess -Force
cd frontend; npm run dev
```

### Frontend loads but shows no data (spinner forever)

**Symptom:** Pages render the layout and sidebar but data never loads — the loading spinner stays indefinitely.

**Cause:** The API server on port 8000 is not running, or CORS is blocking requests.

**Fix:** Ensure the API server is running first:

```bash
# macOS/Linux
uvicorn api.main:app --reload --port 8000

# Windows (PowerShell)
uvicorn api.main:app --reload --port 8000
```

Then refresh the frontend at `http://localhost:3000`. The frontend proxies API requests to `http://localhost:8000` — both servers must be running.

### `npm install` fails in `frontend/`

**Symptom:** Dependency installation fails with errors about node version or packages.

**Fix:** Ensure you are running Node.js 18+:

```bash
node --version   # Should be v18.x or higher
```

If using `nvm`:

```bash
nvm install 18
nvm use 18
cd frontend && rm -rf node_modules && npm install
```

### Database errors or missing tables

**Symptom:** API returns 500 errors about missing tables or columns.

**Fix:** The database is auto-created on first use. Delete and reinitialize:

```bash
# macOS/Linux
rm -f data/leads.db
python -m cli.main stats   # Recreates the database

# Windows (PowerShell)
Remove-Item data\leads.db -ErrorAction SilentlyContinue
python -m cli.main stats
```

### `TAVILY_API_KEY` not found

**Symptom:** Pipeline run fails with an error about missing API key.

**Fix (macOS/Linux):** Set the environment variable before running:

```bash
export TAVILY_API_KEY="your-api-key-here"

# To persist, add to your shell profile:
echo 'export TAVILY_API_KEY="your-api-key-here"' >> ~/.zshrc
source ~/.zshrc
```

**Fix (Windows — PowerShell):**

```powershell
# Current session only
$env:TAVILY_API_KEY = "your-api-key-here"

# Persist across sessions (run once)
[System.Environment]::SetEnvironmentVariable("TAVILY_API_KEY", "your-api-key-here", "User")
```

### Clean start checklist

If you are setting up on a new machine and want to verify everything works:

1. **Clone and install dependencies:**

   ```bash
   git clone <repo-url>
   cd newBusinessLocator
   python3 -m venv .venv               # python on Windows
   source .venv/bin/activate            # .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   cd frontend && npm install && cd ..
   ```

2. **Set environment variable:**

   ```bash
   export TAVILY_API_KEY="your-key"    # $env:TAVILY_API_KEY = "your-key" on Windows
   ```

3. **Start both servers:**

   ```bash
   # macOS/Linux (single command)
   ./scripts/dev.sh

   # Windows (two terminals)
   # Terminal 1:
   .venv\Scripts\activate
   uvicorn api.main:app --reload --port 8000

   # Terminal 2:
   cd frontend
   npm run dev
   ```

4. **Verify in browser:**
   - http://localhost:3000 — Dashboard should load with charts
   - http://localhost:3000/leads — Lead table should appear
   - http://localhost:3000/kanban — Kanban board with stage columns
   - http://localhost:3000/duplicates — Duplicate detection page
   - http://localhost:3000/pipeline — Pipeline run history
   - http://localhost:8000/docs — Swagger API documentation

5. **If any page shows "missing required error components":**
   - Stop the frontend server
   - Delete `frontend/.next/` directory
   - Restart `npm run dev`

---

## License

Private repository.
