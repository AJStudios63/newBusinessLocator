# Frontend Dashboard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Next.js + FastAPI dashboard for managing POS leads with table, kanban, stats, and pipeline management views.

**Architecture:** FastAPI backend (port 8000) serves JSON API reusing existing `db/queries.py`. Next.js frontend (port 3000) with shadcn/ui components proxies API calls. Both share existing SQLite database.

**Tech Stack:** Python 3.12, FastAPI, uvicorn, Next.js 14, React 18, TypeScript, Tailwind CSS, shadcn/ui, @tanstack/react-query, @dnd-kit/core, recharts

---

## Phase 1: Backend API

### Task 1: Add FastAPI dependencies

**Files:**
- Modify: `requirements.txt`

**Step 1: Add FastAPI and uvicorn to requirements**

```txt
requests>=2.28.0
click>=8.0.0
pyyaml>=6.0
pytest>=7.0.0
pytest-mock>=3.10.0
fastapi>=0.109.0
uvicorn>=0.27.0
```

**Step 2: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: Successfully installed fastapi uvicorn (plus dependencies)

**Step 3: Commit**

```bash
git add requirements.txt
git commit -m "Add FastAPI and uvicorn dependencies"
```

---

### Task 2: Create FastAPI app skeleton

**Files:**
- Create: `api/__init__.py`
- Create: `api/main.py`
- Create: `api/dependencies.py`

**Step 1: Create api/__init__.py**

```python
"""FastAPI backend for New Business Locator dashboard."""
```

**Step 2: Create api/dependencies.py**

```python
"""Shared dependencies for FastAPI routes."""

from __future__ import annotations

from typing import Generator
import sqlite3

from config.settings import DB_PATH
from db.schema import init_db


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Yield a database connection, closing it after the request."""
    conn = init_db(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()
```

**Step 3: Create api/main.py**

```python
"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="New Business Locator API",
    description="API for managing POS sales leads",
    version="1.0.0",
)

# CORS for local development (Next.js on port 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
```

**Step 4: Test the server starts**

Run: `uvicorn api.main:app --reload --port 8000`
Expected: Server starts, visit http://localhost:8000/api/health returns `{"status":"ok"}`

**Step 5: Commit**

```bash
git add api/
git commit -m "Add FastAPI app skeleton with health check"
```

---

### Task 3: Create leads router with list endpoint

**Files:**
- Create: `api/routers/__init__.py`
- Create: `api/routers/leads.py`
- Modify: `api/main.py`

**Step 1: Create api/routers/__init__.py**

```python
"""API routers package."""
```

**Step 2: Create api/routers/leads.py**

```python
"""Leads API endpoints."""

from __future__ import annotations

import csv
import io
from typing import Annotated

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
import sqlite3

from api.dependencies import get_db
from db.queries import get_leads, get_lead, update_stage

router = APIRouter(prefix="/api/leads", tags=["leads"])

VALID_STAGES = ["New", "Qualified", "Contacted", "Follow-up", "Closed-Won", "Closed-Lost"]


@router.get("")
def list_leads(
    conn: Annotated[sqlite3.Connection, Depends(get_db)],
    stage: str | None = None,
    county: str | None = None,
    min_score: Annotated[int | None, Query(alias="minScore")] = None,
    sort: str = "pos_score",
    limit: int = 50,
):
    """List leads with optional filters."""
    try:
        rows = get_leads(conn, stage=stage, county=county, min_score=min_score, sort=sort, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"leads": rows, "count": len(rows)}


@router.get("/export")
def export_leads(
    conn: Annotated[sqlite3.Connection, Depends(get_db)],
    stage: str | None = None,
    county: str | None = None,
    min_score: Annotated[int | None, Query(alias="minScore")] = None,
):
    """Export filtered leads as CSV download."""
    rows = get_leads(conn, stage=stage, county=county, min_score=min_score, limit=10000)

    if not rows:
        raise HTTPException(status_code=404, detail="No leads match the filters")

    fieldnames = [
        "id", "fingerprint", "business_name", "business_type", "raw_type",
        "address", "city", "state", "zip_code", "county", "license_date",
        "pos_score", "stage", "source_url", "source_type", "notes",
        "created_at", "updated_at", "contacted_at", "closed_at",
    ]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads.csv"},
    )


@router.get("/{lead_id}")
def get_lead_detail(
    lead_id: int,
    conn: Annotated[sqlite3.Connection, Depends(get_db)],
):
    """Get a single lead by ID."""
    lead = get_lead(conn, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found")
    return lead


@router.patch("/{lead_id}")
def update_lead(
    lead_id: int,
    conn: Annotated[sqlite3.Connection, Depends(get_db)],
    stage: str | None = None,
    note: str | None = None,
):
    """Update a lead's stage and/or add a note."""
    if stage is not None and stage not in VALID_STAGES:
        raise HTTPException(status_code=400, detail=f"Invalid stage. Must be one of: {VALID_STAGES}")

    if stage is None and note is None:
        raise HTTPException(status_code=400, detail="Must provide stage or note")

    try:
        # If only note provided, we still need to call update_stage with current stage
        if stage is None:
            lead = get_lead(conn, lead_id)
            if lead is None:
                raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found")
            stage = lead["stage"]

        update_stage(conn, lead_id, stage, note)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return get_lead(conn, lead_id)


@router.patch("/{lead_id}/stage")
def quick_stage_update(
    lead_id: int,
    stage: str,
    conn: Annotated[sqlite3.Connection, Depends(get_db)],
):
    """Quick stage change (for kanban drag-drop)."""
    if stage not in VALID_STAGES:
        raise HTTPException(status_code=400, detail=f"Invalid stage. Must be one of: {VALID_STAGES}")

    try:
        update_stage(conn, lead_id, stage)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return {"id": lead_id, "stage": stage}


@router.post("/bulk")
def bulk_update_leads(
    conn: Annotated[sqlite3.Connection, Depends(get_db)],
    ids: list[int] = [],
    stage: str | None = None,
):
    """Bulk update stage for multiple leads."""
    if not ids:
        raise HTTPException(status_code=400, detail="Must provide at least one lead ID")

    if stage is None:
        raise HTTPException(status_code=400, detail="Must provide stage")

    if stage not in VALID_STAGES:
        raise HTTPException(status_code=400, detail=f"Invalid stage. Must be one of: {VALID_STAGES}")

    updated = []
    errors = []

    for lead_id in ids:
        try:
            update_stage(conn, lead_id, stage)
            updated.append(lead_id)
        except ValueError as exc:
            errors.append({"id": lead_id, "error": str(exc)})

    return {"updated": updated, "errors": errors}
```

**Step 3: Update api/main.py to include leads router**

```python
"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import leads

app = FastAPI(
    title="New Business Locator API",
    description="API for managing POS sales leads",
    version="1.0.0",
)

# CORS for local development (Next.js on port 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(leads.router)


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
```

**Step 4: Test leads endpoint**

Run: `uvicorn api.main:app --reload --port 8000`
Then: `curl http://localhost:8000/api/leads`
Expected: `{"leads":[...],"count":5}` (your 5 leads)

**Step 5: Commit**

```bash
git add api/
git commit -m "Add leads API router with list, detail, update, bulk, export endpoints"
```

---

### Task 4: Create stats router

**Files:**
- Create: `api/routers/stats.py`
- Modify: `api/main.py`

**Step 1: Create api/routers/stats.py**

```python
"""Stats API endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
import sqlite3

from api.dependencies import get_db
from db.queries import get_stats

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("")
def get_dashboard_stats(
    conn: Annotated[sqlite3.Connection, Depends(get_db)],
):
    """Get aggregated statistics for the dashboard."""
    stats = get_stats(conn)
    return stats
```

**Step 2: Update api/main.py**

Add import and include router:

```python
from api.routers import leads, stats
```

```python
app.include_router(stats.router)
```

**Step 3: Test stats endpoint**

Run: `curl http://localhost:8000/api/stats`
Expected: JSON with by_stage, by_county, by_type, avg_score, total_leads, last_run

**Step 4: Commit**

```bash
git add api/
git commit -m "Add stats API router"
```

---

### Task 5: Create pipeline router

**Files:**
- Create: `api/routers/pipeline.py`
- Modify: `api/main.py`

**Step 1: Create api/routers/pipeline.py**

```python
"""Pipeline API endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, BackgroundTasks
import sqlite3

from api.dependencies import get_db
from db.queries import get_pipeline_runs
from etl.pipeline import run_pipeline

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

# Track running pipeline status
_pipeline_status = {"running": False, "last_result": None}


@router.get("/runs")
def list_pipeline_runs(
    conn: Annotated[sqlite3.Connection, Depends(get_db)],
    limit: int = 10,
):
    """List recent pipeline runs."""
    runs = get_pipeline_runs(conn, limit=limit)
    return {"runs": runs}


@router.get("/status")
def get_pipeline_status():
    """Get current pipeline status."""
    return _pipeline_status


def _run_pipeline_task():
    """Background task to run the pipeline."""
    global _pipeline_status
    _pipeline_status["running"] = True
    _pipeline_status["last_result"] = None

    try:
        result = run_pipeline(dry_run=False)
        _pipeline_status["last_result"] = {
            "run_id": result["run_id"],
            "status": result["status"],
            "leads_found": result["leads_found"],
            "leads_new": result["leads_new"],
            "leads_dupes": result["leads_dupes"],
            "error": result["error"],
        }
    except Exception as exc:
        _pipeline_status["last_result"] = {
            "status": "failed",
            "error": str(exc),
        }
    finally:
        _pipeline_status["running"] = False


@router.post("/run")
def trigger_pipeline_run(background_tasks: BackgroundTasks):
    """Trigger a new pipeline run (async)."""
    if _pipeline_status["running"]:
        return {"message": "Pipeline already running", "running": True}

    background_tasks.add_task(_run_pipeline_task)
    return {"message": "Pipeline started", "running": True}
```

**Step 2: Update api/main.py**

Add import and include router:

```python
from api.routers import leads, stats, pipeline
```

```python
app.include_router(pipeline.router)
```

**Step 3: Test pipeline endpoints**

Run: `curl http://localhost:8000/api/pipeline/runs`
Expected: `{"runs":[...]}`

Run: `curl http://localhost:8000/api/pipeline/status`
Expected: `{"running":false,"last_result":null}`

**Step 4: Commit**

```bash
git add api/
git commit -m "Add pipeline API router with runs, status, and trigger endpoints"
```

---

### Task 6: Create kanban router

**Files:**
- Create: `api/routers/kanban.py`
- Modify: `api/main.py`

**Step 1: Create api/routers/kanban.py**

```python
"""Kanban API endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
import sqlite3

from api.dependencies import get_db
from db.queries import get_leads

router = APIRouter(prefix="/api/kanban", tags=["kanban"])

STAGES = ["New", "Qualified", "Contacted", "Follow-up", "Closed-Won", "Closed-Lost"]


@router.get("")
def get_kanban_board(
    conn: Annotated[sqlite3.Connection, Depends(get_db)],
    county: str | None = None,
    min_score: int | None = None,
):
    """Get leads grouped by stage for kanban view."""
    # Fetch all leads (high limit) and group by stage
    all_leads = get_leads(conn, county=county, min_score=min_score, limit=1000, sort="pos_score")

    # Initialize all stages (even empty ones)
    grouped = {stage: [] for stage in STAGES}

    for lead in all_leads:
        stage = lead.get("stage", "New")
        if stage in grouped:
            grouped[stage].append(lead)

    return {"stages": STAGES, "columns": grouped}
```

**Step 2: Update api/main.py**

Add import and include router:

```python
from api.routers import leads, stats, pipeline, kanban
```

```python
app.include_router(kanban.router)
```

**Step 3: Test kanban endpoint**

Run: `curl http://localhost:8000/api/kanban`
Expected: `{"stages":[...],"columns":{"New":[...],...}}`

**Step 4: Commit**

```bash
git add api/
git commit -m "Add kanban API router"
```

---

### Task 7: Add API tests

**Files:**
- Create: `tests/test_api.py`

**Step 1: Create tests/test_api.py**

```python
"""Tests for FastAPI endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.dependencies import get_db


@pytest.fixture
def client(populated_db):
    """Test client with database dependency overridden."""
    def override_get_db():
        yield populated_db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


class TestHealthEndpoint:
    def test_health_check(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestLeadsEndpoints:
    def test_list_leads(self, client):
        response = client.get("/api/leads")
        assert response.status_code == 200
        data = response.json()
        assert "leads" in data
        assert "count" in data
        assert data["count"] == 3  # populated_db has 3 leads

    def test_list_leads_filter_by_stage(self, client):
        response = client.get("/api/leads?stage=New")
        assert response.status_code == 200
        data = response.json()
        for lead in data["leads"]:
            assert lead["stage"] == "New"

    def test_list_leads_filter_by_county(self, client):
        response = client.get("/api/leads?county=Davidson")
        assert response.status_code == 200
        data = response.json()
        for lead in data["leads"]:
            assert lead["county"] == "Davidson"

    def test_get_lead_detail(self, client):
        # First get the list to find an ID
        response = client.get("/api/leads")
        lead_id = response.json()["leads"][0]["id"]

        response = client.get(f"/api/leads/{lead_id}")
        assert response.status_code == 200
        assert response.json()["id"] == lead_id

    def test_get_lead_not_found(self, client):
        response = client.get("/api/leads/99999")
        assert response.status_code == 404

    def test_update_lead_stage(self, client):
        response = client.get("/api/leads")
        lead_id = response.json()["leads"][0]["id"]

        response = client.patch(f"/api/leads/{lead_id}?stage=Qualified")
        assert response.status_code == 200
        assert response.json()["stage"] == "Qualified"

    def test_update_lead_invalid_stage(self, client):
        response = client.get("/api/leads")
        lead_id = response.json()["leads"][0]["id"]

        response = client.patch(f"/api/leads/{lead_id}?stage=Invalid")
        assert response.status_code == 400

    def test_quick_stage_update(self, client):
        response = client.get("/api/leads")
        lead_id = response.json()["leads"][0]["id"]

        response = client.patch(f"/api/leads/{lead_id}/stage?stage=Contacted")
        assert response.status_code == 200
        assert response.json()["stage"] == "Contacted"


class TestStatsEndpoint:
    def test_get_stats(self, client):
        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert "by_stage" in data
        assert "by_county" in data
        assert "by_type" in data
        assert "avg_score" in data
        assert "total_leads" in data


class TestKanbanEndpoint:
    def test_get_kanban_board(self, client):
        response = client.get("/api/kanban")
        assert response.status_code == 200
        data = response.json()
        assert "stages" in data
        assert "columns" in data
        assert len(data["stages"]) == 6
        assert "New" in data["columns"]


class TestPipelineEndpoints:
    def test_get_pipeline_runs(self, client):
        response = client.get("/api/pipeline/runs")
        assert response.status_code == 200
        data = response.json()
        assert "runs" in data

    def test_get_pipeline_status(self, client):
        response = client.get("/api/pipeline/status")
        assert response.status_code == 200
        data = response.json()
        assert "running" in data
```

**Step 2: Run tests**

Run: `pytest tests/test_api.py -v`
Expected: All tests pass

**Step 3: Commit**

```bash
git add tests/test_api.py
git commit -m "Add API endpoint tests"
```

---

## Phase 2: Frontend Setup

### Task 8: Initialize Next.js project

**Files:**
- Create: `frontend/` directory with Next.js scaffold

**Step 1: Create Next.js project**

Run from project root:
```bash
cd /Users/rofoster/lab/newBusinessLocator
npx create-next-app@14 frontend --typescript --tailwind --eslint --app --src-dir=false --import-alias="@/*" --use-npm
```

Expected: Creates `frontend/` directory with Next.js 14 app

**Step 2: Verify it runs**

```bash
cd frontend && npm run dev
```

Expected: Server starts on http://localhost:3000

**Step 3: Commit**

```bash
cd /Users/rofoster/lab/newBusinessLocator
git add frontend/
git commit -m "Initialize Next.js 14 frontend project"
```

---

### Task 9: Configure API proxy and install dependencies

**Files:**
- Modify: `frontend/next.config.ts`
- Modify: `frontend/package.json`

**Step 1: Update next.config.ts for API proxy**

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
    ];
  },
};

export default nextConfig;
```

**Step 2: Install additional dependencies**

```bash
cd frontend
npm install @tanstack/react-query @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities recharts
```

**Step 3: Commit**

```bash
cd /Users/rofoster/lab/newBusinessLocator
git add frontend/
git commit -m "Configure API proxy and install frontend dependencies"
```

---

### Task 10: Initialize shadcn/ui

**Files:**
- Create: `frontend/components.json`
- Create: `frontend/components/ui/` (multiple files)

**Step 1: Initialize shadcn**

```bash
cd frontend
npx shadcn@latest init -d
```

Answer prompts:
- Style: Default
- Base color: Slate
- CSS variables: Yes

**Step 2: Add required components**

```bash
npx shadcn@latest add button card table dropdown-menu badge dialog sheet input select tabs toast sonner
```

**Step 3: Commit**

```bash
cd /Users/rofoster/lab/newBusinessLocator
git add frontend/
git commit -m "Initialize shadcn/ui with required components"
```

---

### Task 11: Create API client library

**Files:**
- Create: `frontend/lib/api.ts`
- Create: `frontend/lib/types.ts`

**Step 1: Create frontend/lib/types.ts**

```typescript
export interface Lead {
  id: number;
  fingerprint: string;
  business_name: string;
  business_type: string | null;
  raw_type: string | null;
  address: string | null;
  city: string | null;
  state: string;
  zip_code: string | null;
  county: string | null;
  license_date: string | null;
  pos_score: number;
  stage: Stage;
  source_url: string | null;
  source_type: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  contacted_at: string | null;
  closed_at: string | null;
}

export type Stage =
  | "New"
  | "Qualified"
  | "Contacted"
  | "Follow-up"
  | "Closed-Won"
  | "Closed-Lost";

export const STAGES: Stage[] = [
  "New",
  "Qualified",
  "Contacted",
  "Follow-up",
  "Closed-Won",
  "Closed-Lost",
];

export interface LeadsResponse {
  leads: Lead[];
  count: number;
}

export interface Stats {
  by_stage: Record<string, number>;
  by_county: Record<string, number>;
  by_type: Record<string, number>;
  avg_score: number;
  total_leads: number;
  last_run: PipelineRun | null;
}

export interface PipelineRun {
  id: number;
  run_started_at: string;
  run_finished_at: string | null;
  status: string;
  leads_found: number;
  leads_new: number;
  leads_dupes: number;
  error_message: string | null;
  sources_queried: string | null;
}

export interface PipelineStatus {
  running: boolean;
  last_result: {
    run_id?: number;
    status: string;
    leads_found?: number;
    leads_new?: number;
    leads_dupes?: number;
    error?: string | null;
  } | null;
}

export interface KanbanData {
  stages: Stage[];
  columns: Record<Stage, Lead[]>;
}

export interface LeadFilters {
  stage?: string;
  county?: string;
  minScore?: number;
  sort?: string;
  limit?: number;
}
```

**Step 2: Create frontend/lib/api.ts**

```typescript
import type {
  Lead,
  LeadsResponse,
  Stats,
  PipelineRun,
  PipelineStatus,
  KanbanData,
  LeadFilters,
} from "./types";

const API_BASE = "/api";

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

// Leads
export async function getLeads(filters: LeadFilters = {}): Promise<LeadsResponse> {
  const params = new URLSearchParams();
  if (filters.stage) params.set("stage", filters.stage);
  if (filters.county) params.set("county", filters.county);
  if (filters.minScore) params.set("minScore", filters.minScore.toString());
  if (filters.sort) params.set("sort", filters.sort);
  if (filters.limit) params.set("limit", filters.limit.toString());

  const query = params.toString();
  return fetchJson<LeadsResponse>(`${API_BASE}/leads${query ? `?${query}` : ""}`);
}

export async function getLead(id: number): Promise<Lead> {
  return fetchJson<Lead>(`${API_BASE}/leads/${id}`);
}

export async function updateLead(
  id: number,
  data: { stage?: string; note?: string }
): Promise<Lead> {
  const params = new URLSearchParams();
  if (data.stage) params.set("stage", data.stage);
  if (data.note) params.set("note", data.note);

  return fetchJson<Lead>(`${API_BASE}/leads/${id}?${params.toString()}`, {
    method: "PATCH",
  });
}

export async function updateLeadStage(id: number, stage: string): Promise<{ id: number; stage: string }> {
  return fetchJson(`${API_BASE}/leads/${id}/stage?stage=${encodeURIComponent(stage)}`, {
    method: "PATCH",
  });
}

export async function bulkUpdateLeads(
  ids: number[],
  stage: string
): Promise<{ updated: number[]; errors: Array<{ id: number; error: string }> }> {
  const params = new URLSearchParams();
  params.set("stage", stage);
  ids.forEach((id) => params.append("ids", id.toString()));

  return fetchJson(`${API_BASE}/leads/bulk?${params.toString()}`, {
    method: "POST",
  });
}

export function getExportUrl(filters: LeadFilters = {}): string {
  const params = new URLSearchParams();
  if (filters.stage) params.set("stage", filters.stage);
  if (filters.county) params.set("county", filters.county);
  if (filters.minScore) params.set("minScore", filters.minScore.toString());

  const query = params.toString();
  return `${API_BASE}/leads/export${query ? `?${query}` : ""}`;
}

// Stats
export async function getStats(): Promise<Stats> {
  return fetchJson<Stats>(`${API_BASE}/stats`);
}

// Pipeline
export async function getPipelineRuns(limit = 10): Promise<{ runs: PipelineRun[] }> {
  return fetchJson(`${API_BASE}/pipeline/runs?limit=${limit}`);
}

export async function getPipelineStatus(): Promise<PipelineStatus> {
  return fetchJson<PipelineStatus>(`${API_BASE}/pipeline/status`);
}

export async function triggerPipelineRun(): Promise<{ message: string; running: boolean }> {
  return fetchJson(`${API_BASE}/pipeline/run`, { method: "POST" });
}

// Kanban
export async function getKanbanData(filters: LeadFilters = {}): Promise<KanbanData> {
  const params = new URLSearchParams();
  if (filters.county) params.set("county", filters.county);
  if (filters.minScore) params.set("min_score", filters.minScore.toString());

  const query = params.toString();
  return fetchJson<KanbanData>(`${API_BASE}/kanban${query ? `?${query}` : ""}`);
}
```

**Step 3: Commit**

```bash
cd /Users/rofoster/lab/newBusinessLocator
git add frontend/lib/
git commit -m "Add API client library and TypeScript types"
```

---

### Task 12: Create React Query provider

**Files:**
- Create: `frontend/components/providers.tsx`
- Modify: `frontend/app/layout.tsx`

**Step 1: Create frontend/components/providers.tsx**

```typescript
"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { Toaster } from "@/components/ui/sonner";

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 5 * 1000, // 5 seconds
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <Toaster position="top-right" />
    </QueryClientProvider>
  );
}
```

**Step 2: Update frontend/app/layout.tsx**

```typescript
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "New Business Locator",
  description: "POS lead generation dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

**Step 3: Commit**

```bash
cd /Users/rofoster/lab/newBusinessLocator
git add frontend/
git commit -m "Add React Query provider and Toaster"
```

---

## Phase 3: Frontend Components & Pages

### Task 13: Create app shell with navigation

**Files:**
- Create: `frontend/components/nav-sidebar.tsx`
- Create: `frontend/components/app-shell.tsx`

**Step 1: Create frontend/components/nav-sidebar.tsx**

```typescript
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Users,
  Columns3,
  Play,
} from "lucide-react";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/leads", label: "Leads", icon: Users },
  { href: "/kanban", label: "Kanban", icon: Columns3 },
  { href: "/pipeline", label: "Pipeline", icon: Play },
];

export function NavSidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 border-r bg-muted/40 p-4">
      <div className="mb-8">
        <h1 className="text-xl font-bold">New Business Locator</h1>
        <p className="text-sm text-muted-foreground">POS Lead Generation</p>
      </div>
      <nav className="space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "hover:bg-muted"
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
```

**Step 2: Create frontend/components/app-shell.tsx**

```typescript
import type { ReactNode } from "react";
import { NavSidebar } from "./nav-sidebar";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-screen">
      <NavSidebar />
      <main className="flex-1 overflow-auto p-6">{children}</main>
    </div>
  );
}
```

**Step 3: Install lucide-react icons**

```bash
cd frontend && npm install lucide-react
```

**Step 4: Commit**

```bash
cd /Users/rofoster/lab/newBusinessLocator
git add frontend/
git commit -m "Add navigation sidebar and app shell"
```

---

### Task 14: Create Dashboard page

**Files:**
- Modify: `frontend/app/page.tsx`
- Create: `frontend/components/stats-cards.tsx`
- Create: `frontend/components/charts.tsx`

**Step 1: Create frontend/components/stats-cards.tsx**

```typescript
"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Stats } from "@/lib/types";

interface StatsCardsProps {
  stats: Stats;
}

export function StatsCards({ stats }: StatsCardsProps) {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total Leads</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.total_leads}</div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Avg Score</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.avg_score.toFixed(1)}</div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">New Leads</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.by_stage["New"] || 0}</div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Qualified</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.by_stage["Qualified"] || 0}</div>
        </CardContent>
      </Card>
    </div>
  );
}
```

**Step 2: Create frontend/components/charts.tsx**

```typescript
"use client";

import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const COLORS = ["#0088FE", "#00C49F", "#FFBB28", "#FF8042", "#8884d8", "#82ca9d"];

interface ChartData {
  name: string;
  value: number;
}

interface TypeChartProps {
  data: Record<string, number>;
}

export function TypePieChart({ data }: TypeChartProps) {
  const chartData: ChartData[] = Object.entries(data).map(([name, value]) => ({
    name: name || "other",
    value,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Leads by Type</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={250}>
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={({ name, percent }) =>
                `${name} (${(percent * 100).toFixed(0)}%)`
              }
              outerRadius={80}
              fill="#8884d8"
              dataKey="value"
            >
              {chartData.map((_, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

export function CountyBarChart({ data }: TypeChartProps) {
  const chartData: ChartData[] = Object.entries(data)
    .map(([name, value]) => ({ name: name || "Unknown", value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 8);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Leads by County</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={chartData}>
            <XAxis dataKey="name" tick={{ fontSize: 12 }} />
            <YAxis />
            <Tooltip />
            <Bar dataKey="value" fill="#0088FE" />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
```

**Step 3: Update frontend/app/page.tsx**

```typescript
"use client";

import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { StatsCards } from "@/components/stats-cards";
import { TypePieChart, CountyBarChart } from "@/components/charts";
import { getStats, triggerPipelineRun, getPipelineStatus } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import { Loader2, Play } from "lucide-react";

export default function DashboardPage() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ["stats"],
    queryFn: getStats,
  });

  const { data: pipelineStatus, refetch: refetchStatus } = useQuery({
    queryKey: ["pipelineStatus"],
    queryFn: getPipelineStatus,
    refetchInterval: (query) => {
      // Poll while pipeline is running
      return query.state.data?.running ? 2000 : false;
    },
  });

  const handleRunPipeline = async () => {
    try {
      await triggerPipelineRun();
      toast.success("Pipeline started");
      refetchStatus();
    } catch (error) {
      toast.error("Failed to start pipeline");
    }
  };

  if (isLoading || !stats) {
    return (
      <AppShell>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin" />
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <Button
            onClick={handleRunPipeline}
            disabled={pipelineStatus?.running}
          >
            {pipelineStatus?.running ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Running...
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" />
                Run Pipeline
              </>
            )}
          </Button>
        </div>

        <StatsCards stats={stats} />

        <div className="grid gap-4 md:grid-cols-2">
          <TypePieChart data={stats.by_type} />
          <CountyBarChart data={stats.by_county} />
        </div>

        {stats.last_run && (
          <Card>
            <CardHeader>
              <CardTitle>Last Pipeline Run</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground">Started</p>
                  <p className="font-medium">
                    {new Date(stats.last_run.run_started_at).toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-muted-foreground">Status</p>
                  <p className="font-medium capitalize">{stats.last_run.status}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Found</p>
                  <p className="font-medium">{stats.last_run.leads_found}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">New</p>
                  <p className="font-medium">{stats.last_run.leads_new}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </AppShell>
  );
}
```

**Step 4: Commit**

```bash
cd /Users/rofoster/lab/newBusinessLocator
git add frontend/
git commit -m "Add Dashboard page with stats cards and charts"
```

---

### Task 15: Create Leads table page

**Files:**
- Create: `frontend/app/leads/page.tsx`
- Create: `frontend/components/lead-table.tsx`
- Create: `frontend/components/lead-filters.tsx`
- Create: `frontend/components/lead-detail-panel.tsx`

**Step 1: Create frontend/components/lead-filters.tsx**

```typescript
"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { STAGES, type LeadFilters } from "@/lib/types";
import { Download } from "lucide-react";
import { getExportUrl } from "@/lib/api";

interface LeadFiltersProps {
  filters: LeadFilters;
  onFilterChange: (filters: LeadFilters) => void;
  counties: string[];
}

export function LeadFiltersBar({ filters, onFilterChange, counties }: LeadFiltersProps) {
  return (
    <div className="flex flex-wrap gap-4 items-center">
      <Select
        value={filters.stage || "all"}
        onValueChange={(value) =>
          onFilterChange({ ...filters, stage: value === "all" ? undefined : value })
        }
      >
        <SelectTrigger className="w-[150px]">
          <SelectValue placeholder="All Stages" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Stages</SelectItem>
          {STAGES.map((stage) => (
            <SelectItem key={stage} value={stage}>
              {stage}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={filters.county || "all"}
        onValueChange={(value) =>
          onFilterChange({ ...filters, county: value === "all" ? undefined : value })
        }
      >
        <SelectTrigger className="w-[150px]">
          <SelectValue placeholder="All Counties" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Counties</SelectItem>
          {counties.map((county) => (
            <SelectItem key={county} value={county}>
              {county}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Input
        type="number"
        placeholder="Min Score"
        className="w-[120px]"
        value={filters.minScore || ""}
        onChange={(e) =>
          onFilterChange({
            ...filters,
            minScore: e.target.value ? parseInt(e.target.value) : undefined,
          })
        }
      />

      <Button variant="outline" asChild>
        <a href={getExportUrl(filters)} download>
          <Download className="mr-2 h-4 w-4" />
          Export CSV
        </a>
      </Button>
    </div>
  );
}
```

**Step 2: Create frontend/components/lead-detail-panel.tsx**

```typescript
"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { updateLead } from "@/lib/api";
import { STAGES, type Lead, type Stage } from "@/lib/types";

interface LeadDetailPanelProps {
  lead: Lead | null;
  open: boolean;
  onClose: () => void;
}

export function LeadDetailPanel({ lead, open, onClose }: LeadDetailPanelProps) {
  const [newStage, setNewStage] = useState<Stage | null>(null);
  const [note, setNote] = useState("");
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () =>
      updateLead(lead!.id, {
        stage: newStage || undefined,
        note: note || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      queryClient.invalidateQueries({ queryKey: ["kanban"] });
      toast.success("Lead updated");
      setNewStage(null);
      setNote("");
      onClose();
    },
    onError: () => {
      toast.error("Failed to update lead");
    },
  });

  if (!lead) return null;

  return (
    <Sheet open={open} onOpenChange={(o) => !o && onClose()}>
      <SheetContent className="w-[500px] sm:max-w-[500px] overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{lead.business_name}</SheetTitle>
        </SheetHeader>

        <div className="mt-6 space-y-6">
          <div className="flex items-center gap-2">
            <Badge variant="outline">{lead.business_type || "other"}</Badge>
            <Badge>{lead.stage}</Badge>
            <Badge variant="secondary">Score: {lead.pos_score}</Badge>
          </div>

          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground">Address</p>
              <p>{lead.address || "—"}</p>
            </div>
            <div>
              <p className="text-muted-foreground">City</p>
              <p>{lead.city || "—"}</p>
            </div>
            <div>
              <p className="text-muted-foreground">County</p>
              <p>{lead.county || "—"}</p>
            </div>
            <div>
              <p className="text-muted-foreground">ZIP</p>
              <p>{lead.zip_code || "—"}</p>
            </div>
            <div>
              <p className="text-muted-foreground">License Date</p>
              <p>{lead.license_date || "—"}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Source</p>
              <p>{lead.source_type || "—"}</p>
            </div>
          </div>

          {lead.source_url && (
            <div>
              <p className="text-sm text-muted-foreground">Source URL</p>
              <a
                href={lead.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-blue-600 hover:underline break-all"
              >
                {lead.source_url}
              </a>
            </div>
          )}

          {lead.notes && (
            <div>
              <p className="text-sm text-muted-foreground">Notes</p>
              <p className="text-sm whitespace-pre-wrap">{lead.notes}</p>
            </div>
          )}

          <hr />

          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">Update Stage</label>
              <Select
                value={newStage || lead.stage}
                onValueChange={(v) => setNewStage(v as Stage)}
              >
                <SelectTrigger className="mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {STAGES.map((stage) => (
                    <SelectItem key={stage} value={stage}>
                      {stage}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="text-sm font-medium">Add Note</label>
              <Textarea
                className="mt-1"
                placeholder="Enter a note..."
                value={note}
                onChange={(e) => setNote(e.target.value)}
              />
            </div>

            <Button
              onClick={() => mutation.mutate()}
              disabled={mutation.isPending || (!newStage && !note)}
              className="w-full"
            >
              {mutation.isPending ? "Saving..." : "Save Changes"}
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
```

**Step 3: Add Textarea component**

```bash
cd frontend && npx shadcn@latest add textarea
```

**Step 4: Create frontend/components/lead-table.tsx**

```typescript
"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";
import { bulkUpdateLeads } from "@/lib/api";
import { STAGES, type Lead, type Stage } from "@/lib/types";

interface LeadTableProps {
  leads: Lead[];
  onRowClick: (lead: Lead) => void;
}

export function LeadTable({ leads, onRowClick }: LeadTableProps) {
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [bulkStage, setBulkStage] = useState<Stage | "">("");
  const queryClient = useQueryClient();

  const bulkMutation = useMutation({
    mutationFn: () => bulkUpdateLeads(Array.from(selectedIds), bulkStage as string),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      queryClient.invalidateQueries({ queryKey: ["kanban"] });
      toast.success(`Updated ${data.updated.length} leads`);
      setSelectedIds(new Set());
      setBulkStage("");
    },
    onError: () => {
      toast.error("Failed to update leads");
    },
  });

  const toggleAll = () => {
    if (selectedIds.size === leads.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(leads.map((l) => l.id)));
    }
  };

  const toggleOne = (id: number) => {
    const next = new Set(selectedIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setSelectedIds(next);
  };

  return (
    <div className="space-y-4">
      {selectedIds.size > 0 && (
        <div className="flex items-center gap-4 p-3 bg-muted rounded-md">
          <span className="text-sm font-medium">
            {selectedIds.size} selected
          </span>
          <Select
            value={bulkStage}
            onValueChange={(v) => setBulkStage(v as Stage)}
          >
            <SelectTrigger className="w-[150px]">
              <SelectValue placeholder="Move to..." />
            </SelectTrigger>
            <SelectContent>
              {STAGES.map((stage) => (
                <SelectItem key={stage} value={stage}>
                  {stage}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            size="sm"
            onClick={() => bulkMutation.mutate()}
            disabled={!bulkStage || bulkMutation.isPending}
          >
            Apply
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setSelectedIds(new Set())}
          >
            Clear
          </Button>
        </div>
      )}

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[40px]">
                <Checkbox
                  checked={selectedIds.size === leads.length && leads.length > 0}
                  onCheckedChange={toggleAll}
                />
              </TableHead>
              <TableHead>Business Name</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>City</TableHead>
              <TableHead>County</TableHead>
              <TableHead className="text-right">Score</TableHead>
              <TableHead>Stage</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {leads.map((lead) => (
              <TableRow
                key={lead.id}
                className="cursor-pointer hover:bg-muted/50"
                onClick={() => onRowClick(lead)}
              >
                <TableCell onClick={(e) => e.stopPropagation()}>
                  <Checkbox
                    checked={selectedIds.has(lead.id)}
                    onCheckedChange={() => toggleOne(lead.id)}
                  />
                </TableCell>
                <TableCell className="font-medium">{lead.business_name}</TableCell>
                <TableCell>
                  <Badge variant="outline">{lead.business_type || "other"}</Badge>
                </TableCell>
                <TableCell>{lead.city || "—"}</TableCell>
                <TableCell>{lead.county || "—"}</TableCell>
                <TableCell className="text-right">{lead.pos_score}</TableCell>
                <TableCell>
                  <Badge>{lead.stage}</Badge>
                </TableCell>
              </TableRow>
            ))}
            {leads.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                  No leads found
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
```

**Step 5: Add Checkbox component**

```bash
cd frontend && npx shadcn@latest add checkbox
```

**Step 6: Create frontend/app/leads/page.tsx**

```typescript
"use client";

import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { LeadTable } from "@/components/lead-table";
import { LeadFiltersBar } from "@/components/lead-filters";
import { LeadDetailPanel } from "@/components/lead-detail-panel";
import { getLeads, getStats } from "@/lib/api";
import { Loader2 } from "lucide-react";
import type { Lead, LeadFilters } from "@/lib/types";

export default function LeadsPage() {
  const [filters, setFilters] = useState<LeadFilters>({ limit: 100 });
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["leads", filters],
    queryFn: () => getLeads(filters),
  });

  const { data: stats } = useQuery({
    queryKey: ["stats"],
    queryFn: getStats,
  });

  const counties = useMemo(() => {
    if (!stats) return [];
    return Object.keys(stats.by_county).filter(Boolean).sort();
  }, [stats]);

  return (
    <AppShell>
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">Leads</h1>

        <LeadFiltersBar
          filters={filters}
          onFilterChange={setFilters}
          counties={counties}
        />

        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="h-8 w-8 animate-spin" />
          </div>
        ) : (
          <LeadTable
            leads={data?.leads || []}
            onRowClick={setSelectedLead}
          />
        )}

        <LeadDetailPanel
          lead={selectedLead}
          open={!!selectedLead}
          onClose={() => setSelectedLead(null)}
        />
      </div>
    </AppShell>
  );
}
```

**Step 7: Commit**

```bash
cd /Users/rofoster/lab/newBusinessLocator
git add frontend/
git commit -m "Add Leads page with table, filters, bulk actions, and detail panel"
```

---

### Task 16: Create Kanban page

**Files:**
- Create: `frontend/app/kanban/page.tsx`
- Create: `frontend/components/kanban-board.tsx`
- Create: `frontend/components/kanban-card.tsx`

**Step 1: Create frontend/components/kanban-card.tsx**

```typescript
"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Lead } from "@/lib/types";

interface KanbanCardProps {
  lead: Lead;
  onClick: () => void;
}

export function KanbanCard({ lead, onClick }: KanbanCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: lead.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <Card
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className="cursor-grab active:cursor-grabbing"
      onClick={onClick}
    >
      <CardContent className="p-3 space-y-2">
        <p className="font-medium text-sm line-clamp-2">{lead.business_name}</p>
        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant="outline" className="text-xs">
            {lead.business_type || "other"}
          </Badge>
          <Badge variant="secondary" className="text-xs">
            {lead.pos_score}
          </Badge>
        </div>
        <p className="text-xs text-muted-foreground">{lead.city || "Unknown"}</p>
      </CardContent>
    </Card>
  );
}
```

**Step 2: Create frontend/components/kanban-board.tsx**

```typescript
"use client";

import { useState } from "react";
import {
  DndContext,
  DragOverlay,
  closestCorners,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { KanbanCard } from "./kanban-card";
import { Card, CardContent } from "@/components/ui/card";
import { updateLeadStage } from "@/lib/api";
import { STAGES, type Lead, type Stage, type KanbanData } from "@/lib/types";

interface KanbanBoardProps {
  data: KanbanData;
  onCardClick: (lead: Lead) => void;
}

export function KanbanBoard({ data, onCardClick }: KanbanBoardProps) {
  const [activeId, setActiveId] = useState<number | null>(null);
  const queryClient = useQueryClient();

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 8 },
    })
  );

  const mutation = useMutation({
    mutationFn: ({ id, stage }: { id: number; stage: string }) =>
      updateLeadStage(id, stage),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["kanban"] });
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      queryClient.invalidateQueries({ queryKey: ["stats"] });
    },
    onError: () => {
      toast.error("Failed to move lead");
    },
  });

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as number);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveId(null);

    if (!over) return;

    const leadId = active.id as number;
    const targetStage = over.id as Stage;

    // Find current stage of the lead
    let currentStage: Stage | null = null;
    for (const stage of STAGES) {
      if (data.columns[stage].some((l) => l.id === leadId)) {
        currentStage = stage;
        break;
      }
    }

    if (currentStage && currentStage !== targetStage && STAGES.includes(targetStage)) {
      mutation.mutate({ id: leadId, stage: targetStage });
    }
  };

  const activeLead = activeId
    ? STAGES.flatMap((s) => data.columns[s]).find((l) => l.id === activeId)
    : null;

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="flex gap-4 overflow-x-auto pb-4">
        {STAGES.map((stage) => (
          <div
            key={stage}
            id={stage}
            className="flex-shrink-0 w-72 bg-muted/50 rounded-lg p-3"
          >
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-sm">{stage}</h3>
              <span className="text-xs text-muted-foreground">
                {data.columns[stage].length}
              </span>
            </div>
            <SortableContext
              id={stage}
              items={data.columns[stage].map((l) => l.id)}
              strategy={verticalListSortingStrategy}
            >
              <div className="space-y-2 min-h-[100px]">
                {data.columns[stage].map((lead) => (
                  <KanbanCard
                    key={lead.id}
                    lead={lead}
                    onClick={() => onCardClick(lead)}
                  />
                ))}
              </div>
            </SortableContext>
          </div>
        ))}
      </div>
      <DragOverlay>
        {activeLead && (
          <Card className="w-72 opacity-80">
            <CardContent className="p-3">
              <p className="font-medium text-sm">{activeLead.business_name}</p>
            </CardContent>
          </Card>
        )}
      </DragOverlay>
    </DndContext>
  );
}
```

**Step 3: Create frontend/app/kanban/page.tsx**

```typescript
"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { KanbanBoard } from "@/components/kanban-board";
import { LeadDetailPanel } from "@/components/lead-detail-panel";
import { getKanbanData } from "@/lib/api";
import { Loader2 } from "lucide-react";
import type { Lead } from "@/lib/types";

export default function KanbanPage() {
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["kanban"],
    queryFn: () => getKanbanData(),
  });

  return (
    <AppShell>
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">Kanban Board</h1>

        {isLoading || !data ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="h-8 w-8 animate-spin" />
          </div>
        ) : (
          <KanbanBoard data={data} onCardClick={setSelectedLead} />
        )}

        <LeadDetailPanel
          lead={selectedLead}
          open={!!selectedLead}
          onClose={() => setSelectedLead(null)}
        />
      </div>
    </AppShell>
  );
}
```

**Step 4: Commit**

```bash
cd /Users/rofoster/lab/newBusinessLocator
git add frontend/
git commit -m "Add Kanban page with drag-drop stage changes"
```

---

### Task 17: Create Pipeline page

**Files:**
- Create: `frontend/app/pipeline/page.tsx`

**Step 1: Create frontend/app/pipeline/page.tsx**

```typescript
"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { toast } from "sonner";
import { getPipelineRuns, getPipelineStatus, triggerPipelineRun } from "@/lib/api";
import { Loader2, Play, CheckCircle, XCircle, Clock } from "lucide-react";

export default function PipelinePage() {
  const queryClient = useQueryClient();

  const { data: runs, isLoading } = useQuery({
    queryKey: ["pipelineRuns"],
    queryFn: () => getPipelineRuns(20),
  });

  const { data: status, refetch: refetchStatus } = useQuery({
    queryKey: ["pipelineStatus"],
    queryFn: getPipelineStatus,
    refetchInterval: (query) => {
      return query.state.data?.running ? 2000 : false;
    },
  });

  const mutation = useMutation({
    mutationFn: triggerPipelineRun,
    onSuccess: () => {
      toast.success("Pipeline started");
      refetchStatus();
    },
    onError: () => {
      toast.error("Failed to start pipeline");
    },
  });

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "—";
    return new Date(dateStr).toLocaleString();
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case "failed":
        return <XCircle className="h-4 w-4 text-red-500" />;
      case "running":
        return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />;
      default:
        return <Clock className="h-4 w-4 text-muted-foreground" />;
    }
  };

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold">Pipeline</h1>
          <Button
            onClick={() => mutation.mutate()}
            disabled={status?.running || mutation.isPending}
            size="lg"
          >
            {status?.running ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Running...
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" />
                Run Pipeline Now
              </>
            )}
          </Button>
        </div>

        {status?.last_result && (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Latest Result</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Status</p>
                  <div className="flex items-center gap-2">
                    {getStatusIcon(status.last_result.status)}
                    <span className="font-medium capitalize">
                      {status.last_result.status}
                    </span>
                  </div>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Run ID</p>
                  <p className="font-medium">{status.last_result.run_id || "—"}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Found</p>
                  <p className="font-medium">{status.last_result.leads_found ?? "—"}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">New</p>
                  <p className="font-medium">{status.last_result.leads_new ?? "—"}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Duplicates</p>
                  <p className="font-medium">{status.last_result.leads_dupes ?? "—"}</p>
                </div>
              </div>
              {status.last_result.error && (
                <p className="mt-4 text-sm text-red-500">
                  Error: {status.last_result.error}
                </p>
              )}
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Run History</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex justify-center py-8">
                <Loader2 className="h-8 w-8 animate-spin" />
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>Started</TableHead>
                    <TableHead>Finished</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Found</TableHead>
                    <TableHead className="text-right">New</TableHead>
                    <TableHead className="text-right">Dupes</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {runs?.runs.map((run) => (
                    <TableRow key={run.id}>
                      <TableCell>{run.id}</TableCell>
                      <TableCell>{formatDate(run.run_started_at)}</TableCell>
                      <TableCell>{formatDate(run.run_finished_at)}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {getStatusIcon(run.status)}
                          <Badge
                            variant={
                              run.status === "completed"
                                ? "default"
                                : run.status === "failed"
                                ? "destructive"
                                : "secondary"
                            }
                          >
                            {run.status}
                          </Badge>
                        </div>
                      </TableCell>
                      <TableCell className="text-right">{run.leads_found}</TableCell>
                      <TableCell className="text-right">{run.leads_new}</TableCell>
                      <TableCell className="text-right">{run.leads_dupes}</TableCell>
                    </TableRow>
                  ))}
                  {(!runs?.runs || runs.runs.length === 0) && (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                        No pipeline runs yet
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
```

**Step 2: Commit**

```bash
cd /Users/rofoster/lab/newBusinessLocator
git add frontend/
git commit -m "Add Pipeline page with run history and trigger button"
```

---

### Task 18: Create dev script

**Files:**
- Create: `scripts/dev.sh`

**Step 1: Create scripts/dev.sh**

```bash
#!/bin/bash
# Start both backend and frontend for development

set -e

# Kill background jobs on exit
trap 'kill 0' EXIT

echo "Starting New Business Locator development servers..."
echo ""

# Start FastAPI backend
echo "[Backend] Starting uvicorn on port 8000..."
uvicorn api.main:app --reload --port 8000 &

# Wait for backend to start
sleep 2

# Start Next.js frontend
echo "[Frontend] Starting Next.js on port 3000..."
cd frontend && npm run dev &

echo ""
echo "=========================================="
echo "  Dashboard: http://localhost:3000"
echo "  API Docs:  http://localhost:8000/docs"
echo "=========================================="
echo ""
echo "Press Ctrl+C to stop all servers"

# Wait for all background jobs
wait
```

**Step 2: Make executable**

```bash
chmod +x scripts/dev.sh
```

**Step 3: Commit**

```bash
git add scripts/dev.sh
git commit -m "Add dev script to start both servers"
```

---

### Task 19: Update CLAUDE.md with frontend commands

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Add frontend section to CLAUDE.md**

Add after the existing Commands section:

```markdown
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
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "Update CLAUDE.md with frontend development commands"
```

---

### Task 20: Final verification

**Step 1: Run the backend tests**

```bash
pytest tests/test_api.py -v
```

Expected: All tests pass

**Step 2: Start both servers**

```bash
./scripts/dev.sh
```

**Step 3: Verify all pages work**

Open http://localhost:3000 and verify:
- Dashboard loads with stats and charts
- Leads page shows table with filters
- Kanban board shows leads in columns, drag-drop works
- Pipeline page shows run history, Run Pipeline button works

**Step 4: Final commit**

```bash
git add -A
git commit -m "Complete frontend dashboard implementation"
```
