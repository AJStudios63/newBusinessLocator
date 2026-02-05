# Frontend Dashboard Design

**Date:** 2026-02-04
**Status:** Approved

## Overview

Web dashboard for managing the New Business Locator pipeline. Provides visual interface for sales team lead management and admin pipeline control.

## Decisions

| Decision | Choice |
|----------|--------|
| Users | Sales + Admin (lead management + pipeline control) |
| Deployment | Local only (localhost) |
| Tech stack | FastAPI backend + Next.js with shadcn/ui |
| Features | Full-featured (table, kanban, stats, bulk actions, export) |
| Auth | None (trusted local network) |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Next.js SPA                               │
│  (localhost:3000)                                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │Dashboard │ │Leads List│ │ Kanban   │ │ Pipeline │            │
│  │  (stats) │ │ (table)  │ │  Board   │ │   Runs   │            │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘            │
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTP/JSON
┌─────────────────────────▼───────────────────────────────────────┐
│                     FastAPI Backend                              │
│  (localhost:8000)                                                │
│  /api/leads, /api/leads/{id}, /api/stats, /api/pipeline/run     │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│              Existing SQLite (data/leads.db)                     │
│              Reuses db/queries.py functions                      │
└─────────────────────────────────────────────────────────────────┘
```

## API Endpoints

### Leads

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/leads` | List leads with query params: `?stage=New&county=Davidson&min_score=40&sort=pos_score&limit=50` |
| GET | `/api/leads/{id}` | Single lead detail |
| PATCH | `/api/leads/{id}` | Update stage and/or append note: `{"stage": "Qualified", "note": "Called owner"}` |
| POST | `/api/leads/bulk` | Bulk update: `{"ids": [1,2,3], "stage": "Contacted"}` |
| GET | `/api/leads/export` | Returns CSV download with same filters as list |

### Dashboard & Pipeline

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stats` | Aggregated stats (by_stage, by_county, by_type, avg_score, total) |
| GET | `/api/pipeline/runs` | List recent pipeline runs |
| POST | `/api/pipeline/run` | Trigger a new pipeline run (calls existing `run_pipeline()`) |

### Kanban

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/kanban` | Leads grouped by stage: `{New: [...], Qualified: [...], ...}` |
| PATCH | `/api/leads/{id}/stage` | Quick stage change for drag-drop |

## Frontend Pages

```
/                    → Dashboard (stats, charts, quick actions)
/leads               → Leads table with filters, bulk actions
/leads/[id]          → Lead detail page (or modal from table)
/kanban              → Kanban board view
/pipeline            → Pipeline run history + "Run Now" button
```

### Dashboard Page
- Stat cards: Total leads, avg score, leads by stage (mini bar)
- Pie chart: Leads by business type
- Bar chart: Leads by county
- Recent activity: Last 5 stage changes
- Quick action: "Run Pipeline" button with status indicator

### Leads Table Page
- Filters row: Stage dropdown, County dropdown, Min score input, Search box
- Data table (shadcn): Sortable columns, row selection checkboxes
- Bulk action bar: Appears when rows selected — "Move to stage" dropdown
- Row click → opens slide-out panel with full lead detail + edit form
- Export button in header

### Kanban Page
- 6 columns: New → Qualified → Contacted → Follow-up → Closed-Won → Closed-Lost
- Cards show: Business name, type badge, score, city
- Drag-drop to change stage (PATCH on drop)
- Click card → same detail panel as table view

### Pipeline Page
- "Run Pipeline Now" button (shows spinner while running)
- Results table: run_id, started, finished, status, found/new/dupes

## Project Structure

```
newBusinessLocator/
├── api/                          # FastAPI backend
│   ├── __init__.py
│   ├── main.py                   # FastAPI app, CORS, mounts routers
│   ├── routers/
│   │   ├── leads.py              # /api/leads endpoints
│   │   ├── stats.py              # /api/stats endpoint
│   │   ├── pipeline.py           # /api/pipeline/* endpoints
│   │   └── kanban.py             # /api/kanban endpoint
│   └── dependencies.py           # DB connection helper
│
├── frontend/                     # Next.js app
│   ├── package.json
│   ├── next.config.js            # Proxy /api to localhost:8000
│   ├── app/
│   │   ├── layout.tsx            # Root layout, nav sidebar
│   │   ├── page.tsx              # Dashboard
│   │   ├── leads/
│   │   │   └── page.tsx          # Leads table
│   │   ├── kanban/
│   │   │   └── page.tsx          # Kanban board
│   │   └── pipeline/
│   │       └── page.tsx          # Pipeline runs
│   ├── components/
│   │   ├── ui/                   # shadcn components (auto-generated)
│   │   ├── lead-table.tsx
│   │   ├── lead-detail-panel.tsx
│   │   ├── kanban-board.tsx
│   │   ├── kanban-card.tsx
│   │   ├── stats-cards.tsx
│   │   └── filters.tsx
│   └── lib/
│       └── api.ts                # Fetch helpers for backend calls
│
├── cli/                          # EXISTING (unchanged)
├── config/                       # EXISTING (unchanged)
├── db/                           # EXISTING (unchanged)
├── etl/                          # EXISTING (unchanged)
├── data/leads.db                 # EXISTING (shared)
└── scripts/
    └── dev.sh                    # Starts both servers
```

## Dependencies

### Backend (add to requirements.txt)
```
fastapi>=0.109.0
uvicorn>=0.27.0
```

### Frontend (package.json)
```
next@14
react@18
typescript
tailwindcss
@tanstack/react-query
@dnd-kit/core
recharts
```

shadcn/ui components: button, card, table, dropdown-menu, badge, dialog, sheet, input, select, tabs, toast, chart

## Dev Workflow

```bash
# Terminal 1: API server
uvicorn api.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev

# Or single command:
./scripts/dev.sh
```

Access at `http://localhost:3000`, API docs at `http://localhost:8000/docs`
