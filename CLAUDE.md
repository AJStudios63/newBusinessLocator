# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ETL pipeline that discovers new businesses in Nashville/Middle Tennessee using Tavily search API, scores them for POS-system sales relevance, and loads into SQLite with a CLI interface for lead management.

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

# Manage scheduled weekly runs (launchd)
python -m cli.main schedule status
python -m cli.main schedule install
python -m cli.main schedule uninstall

# Run tests
pytest tests/

# Run a single test file
pytest tests/test_transform.py

# Run with verbose output
pytest tests/ -v
```

## Frontend Development

```bash
# Start both servers (recommended)
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

### Data Model

**`leads` table** — one row per unique business
- Dedup key: `fingerprint` = sha256(normalized_name + "|" + normalized_city)[:16]
- Stage workflow: New → Qualified → Contacted → Follow-up → Closed-Won/Closed-Lost

**Lead scoring (0-100):**
- Business type (max 50): restaurant=50, bar=48, retail=45, salon=40, etc.
- Source confidence (max 20): license_table=20, news_article=15, search_snippet=8
- Address completeness (max 15)
- Recency from license_date (max 15)

### Environment

- Requires `TAVILY_API_KEY` environment variable
- Database created at `data/leads.db` on first run
- Logs appended to `logs/pipeline.log`

## Testing

Tests use pytest and cover transform functions (classify, chain filter, article-title filter, scoring, dedup). Test files are in `tests/` and follow `test_*.py` naming.
