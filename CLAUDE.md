# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ETL pipeline that discovers new businesses in Nashville/Middle Tennessee using Tavily search API, scores them for POS-system sales relevance, and loads into SQLite. Includes both CLI and web interfaces for lead management.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run full ETL pipeline
python -m cli.main run

# Dry run (no DB writes)
python -m cli.main run --dry-run

# List leads with filters
python -m cli.main leads --stage New --county Davidson --min-score 40 --sort pos_score --limit 20

# View single lead
python -m cli.main lead <ID>

# Update lead stage
python -m cli.main update <ID> --stage Qualified --note "Called owner"

# Show stats dashboard
python -m cli.main stats

# Export to CSV
python -m cli.main export --output /tmp/leads.csv

# Re-classify and re-score all existing leads
python -m cli.main rescore

# Run all tests
pytest tests/

# Run a single test file
pytest tests/test_transform.py

# Run a specific test by name
pytest tests/test_transform.py::TestClassify::test_classifies_restaurant_by_raw_type -v

# Run tests with coverage
pytest tests/ --cov=etl --cov=utils --cov=db
```

## Frontend Development

```bash
# Start both API and frontend servers (recommended)
./scripts/dev.sh

# Or start separately:
# Terminal 1: API server
uvicorn api.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev
```

Access:
- Dashboard: http://localhost:3000
- API Docs: http://localhost:8000/docs

## Architecture

### ETL Flow
```
sources.yaml queries → Tavily search → filter URLs → Tavily extract (extractable domains only)
    ↓
RawExtract dicts → route to parser (license_table | news_article | search_snippet)
    ↓
BusinessRecords → classify type → filter chains → score (0-100) → infer county → dedup
    ↓
INSERT OR IGNORE into leads table (fingerprint is UNIQUE)
```

### Key Components

**Config files (YAML, editable without code changes):**
- `config/sources.yaml` — search queries, county→city map, extractable/blocked domains
- `config/scoring.yaml` — type scores, keywords for classification, source/address/recency weights
- `config/chains.yaml` — blocklist of chain/franchise names to filter out

**ETL modules:**
- `etl/extract.py` — calls Tavily search/extract, returns `RawExtract` dicts
- `etl/transform.py` — parses, classifies, scores, deduplicates
- `etl/load.py` — inserts leads, updates seen_urls, logs runs
- `etl/pipeline.py` — orchestrator with dry_run support

**Parsers (`utils/parsers.py`):**
- `parse_license_table()` — parses markdown tables from countysource.com
- `parse_news_article()` — parses `##` headings from news sites
- `parse_snippet()` — extracts business name from search result title

### Web API

FastAPI backend at `api/` with routers:
- `api/routers/leads.py` — CRUD, search, pagination, bulk operations, duplicate detection/merge
- `api/routers/stats.py` — aggregate statistics
- `api/routers/kanban.py` — stage-based board view
- `api/routers/pipeline.py` — trigger ETL runs

Key API patterns:
- Pagination via `page` and `pageSize` query params (1-indexed)
- Filters: `stage`, `county`, `minScore`, `maxScore`, `q` (full-text search)
- Database connection via `Depends(get_db)` from `api/dependencies.py`

### Frontend

Next.js 14 app at `frontend/` using:
- React Query for data fetching (`@tanstack/react-query`)
- shadcn/ui components (`frontend/components/ui/`)
- Tailwind CSS for styling

Pages:
- `/` — Dashboard with stats cards and charts
- `/leads` — Paginated lead table with filters
- `/kanban` — Drag-drop stage management
- `/duplicates` — Duplicate detection and merge UI
- `/pipeline` — ETL run history and manual trigger
- `/batch/[id]` — View leads from a specific extraction batch

API client functions in `frontend/lib/api.ts`, types in `frontend/lib/types.ts`.

### Data Model

**`leads` table** — one row per unique business
- Dedup key: `fingerprint` = sha256(normalized_name + "|" + normalized_city)[:16]
- Stage workflow: New → Qualified → Contacted → Follow-up → Closed-Won/Closed-Lost
- Soft delete via `deleted_at` timestamp

**Lead scoring (0-100):**
- Business type (max 50): restaurant=50, bar=48, retail=45, salon=40, etc.
- Source confidence (max 20): license_table=20, news_article=15, search_snippet=8
- Address completeness (max 15)
- Recency from license_date (max 15)

### Database

**Tables:** `leads`, `stage_history`, `seen_urls`, `pipeline_runs`, `duplicate_suggestions`, `leads_fts` (FTS5 virtual table)

Query helpers in `db/queries.py`:
- `get_leads()`, `count_leads()` — filtered queries with pagination
- `search_leads()`, `count_search_leads()` — full-text search
- `_build_lead_filter_clauses()` — shared filter logic (DRY helper)

### Environment

- Requires `TAVILY_API_KEY` environment variable
- Database created at `data/leads.db` on first run
- Logs appended to `logs/pipeline.log`
