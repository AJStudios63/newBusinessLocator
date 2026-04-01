# Geocode UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Geocode All" button to the map page that triggers geocoding via the API with live progress, and show geocoding runs in the pipeline history.

**Architecture:** New `geocode_runs` DB table, new `api/routers/geocode.py` router with 3 endpoints (POST /run, GET /status, GET /runs), and frontend changes to the map page (floating overlay + toast) and pipeline page (merged timeline). The background thread reuses the existing `utils/geocoder.py` module.

**Tech Stack:** Python/FastAPI (backend), SQLite (DB), Next.js 14 + React Query v5 + Tailwind + shadcn/ui (frontend), Sonner (toasts)

**Spec:** `docs/superpowers/specs/2026-04-01-geocode-ui-design.md`

---

## Phase 1: Backend — Database Schema

### Task 1: Add `geocode_runs` table to schema

**Files:**
- Modify: `db/schema.py:10-161` (add DDL constant) and `db/schema.py:188-223` (add to `init_db`)

- [ ] **Step 1: Add the DDL constant**

Open `db/schema.py`. After the `CREATE_DUPLICATE_SUGGESTIONS` constant (ends at line 94), add this new constant:

```python
CREATE_GEOCODE_RUNS = """
CREATE TABLE IF NOT EXISTS geocode_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at      TEXT NOT NULL DEFAULT (datetime('now')),
    finished_at     TEXT,
    status          TEXT NOT NULL DEFAULT 'running',
    total           INTEGER NOT NULL DEFAULT 0,
    succeeded       INTEGER NOT NULL DEFAULT 0,
    failed          INTEGER NOT NULL DEFAULT 0,
    error_message   TEXT
);
"""
```

- [ ] **Step 2: Include it in `DDL_SCRIPT`**

Find the `DDL_SCRIPT` concatenation at line 151. Add `+ CREATE_GEOCODE_RUNS` after `CREATE_DUPLICATE_SUGGESTIONS`:

Change:
```python
DDL_SCRIPT = (
    CREATE_LEADS
    + CREATE_PIPELINE_RUNS
    + CREATE_SEEN_URLS
    + CREATE_STAGE_HISTORY
    + CREATE_SEARCH_CACHE
    + CREATE_DUPLICATE_SUGGESTIONS
    + CREATE_INDEXES
    + CREATE_FTS
    + CREATE_FTS_TRIGGERS
)
```

To:
```python
DDL_SCRIPT = (
    CREATE_LEADS
    + CREATE_PIPELINE_RUNS
    + CREATE_SEEN_URLS
    + CREATE_STAGE_HISTORY
    + CREATE_SEARCH_CACHE
    + CREATE_DUPLICATE_SUGGESTIONS
    + CREATE_GEOCODE_RUNS
    + CREATE_INDEXES
    + CREATE_FTS
    + CREATE_FTS_TRIGGERS
)
```

- [ ] **Step 3: Verify schema creation works**

Run:
```bash
python3 -c "from db.schema import init_db; conn = init_db(':memory:'); print(conn.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name='geocode_runs'\").fetchone()[0])"
```

Expected output: `geocode_runs`

- [ ] **Step 4: Commit**

```bash
git add db/schema.py
git commit -m "feat(db): add geocode_runs table schema"
```

---

## Phase 2: Backend — Query Helpers

### Task 2: Add geocode_runs CRUD functions to db/queries.py

**Files:**
- Modify: `db/queries.py` (add after the `get_pipeline_runs` function which ends at line 765)
- Test: `tests/test_geocode.py` (new file)

- [ ] **Step 1: Write failing tests**

Create `tests/test_geocode.py`:

```python
"""Tests for geocode_runs query helpers and API endpoints."""

from __future__ import annotations

import sqlite3

import pytest

from db.schema import init_db
from db.queries import insert_geocode_run, update_geocode_run, get_geocode_runs


@pytest.fixture
def memory_db():
    """In-memory database with full schema."""
    conn = init_db(":memory:")
    yield conn
    conn.close()


class TestGeocodeRunQueries:
    """Tests for geocode_runs CRUD functions."""

    def test_insert_geocode_run_returns_id(self, memory_db):
        run_id = insert_geocode_run(memory_db, total=100)
        assert isinstance(run_id, int)
        assert run_id > 0

    def test_insert_geocode_run_creates_row(self, memory_db):
        run_id = insert_geocode_run(memory_db, total=250)
        row = memory_db.execute(
            "SELECT * FROM geocode_runs WHERE id = ?;", (run_id,)
        ).fetchone()
        assert row is not None
        assert row["total"] == 250
        assert row["status"] == "running"
        assert row["succeeded"] == 0
        assert row["failed"] == 0

    def test_update_geocode_run_sets_completed(self, memory_db):
        run_id = insert_geocode_run(memory_db, total=50)
        update_geocode_run(
            memory_db,
            run_id=run_id,
            status="completed",
            succeeded=45,
            failed=5,
        )
        row = memory_db.execute(
            "SELECT * FROM geocode_runs WHERE id = ?;", (run_id,)
        ).fetchone()
        assert row["status"] == "completed"
        assert row["succeeded"] == 45
        assert row["failed"] == 5
        assert row["finished_at"] is not None

    def test_update_geocode_run_sets_failed_with_message(self, memory_db):
        run_id = insert_geocode_run(memory_db, total=10)
        update_geocode_run(
            memory_db,
            run_id=run_id,
            status="failed",
            succeeded=3,
            failed=0,
            error_message="Connection lost",
        )
        row = memory_db.execute(
            "SELECT * FROM geocode_runs WHERE id = ?;", (run_id,)
        ).fetchone()
        assert row["status"] == "failed"
        assert row["error_message"] == "Connection lost"

    def test_get_geocode_runs_returns_newest_first(self, memory_db):
        insert_geocode_run(memory_db, total=10)
        insert_geocode_run(memory_db, total=20)
        insert_geocode_run(memory_db, total=30)
        runs = get_geocode_runs(memory_db, limit=10)
        assert len(runs) == 3
        assert runs[0]["total"] == 30  # newest first (highest id)

    def test_get_geocode_runs_respects_limit(self, memory_db):
        for i in range(5):
            insert_geocode_run(memory_db, total=i * 10)
        runs = get_geocode_runs(memory_db, limit=2)
        assert len(runs) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_geocode.py -v
```

Expected: All 6 tests FAIL with `ImportError: cannot import name 'insert_geocode_run'`

- [ ] **Step 3: Implement the query functions**

Add the following to `db/queries.py` after the `get_pipeline_runs` function (after line 765), before the `# Duplicate Detection` comment:

```python
# ---------------------------------------------------------------------------
# Geocode runs
# ---------------------------------------------------------------------------


def insert_geocode_run(conn: sqlite3.Connection, total: int) -> int:
    """Create a new geocode_runs row with status='running' and return its id."""
    cur = conn.execute(
        "INSERT INTO geocode_runs (status, total) VALUES ('running', ?);",
        (total,),
    )
    conn.commit()
    return cur.lastrowid


def update_geocode_run(
    conn: sqlite3.Connection,
    run_id: int,
    status: str,
    succeeded: int,
    failed: int,
    error_message: str | None = None,
) -> None:
    """Finalise a geocode run row with results and set finished_at to now."""
    conn.execute(
        "UPDATE geocode_runs SET "
        "finished_at     = datetime('now'), "
        "status          = ?, "
        "succeeded       = ?, "
        "failed          = ?, "
        "error_message   = ? "
        "WHERE id = ?;",
        (status, succeeded, failed, error_message, run_id),
    )
    conn.commit()


def get_geocode_runs(conn: sqlite3.Connection, limit: int = 10) -> list[dict]:
    """Return the most recent geocode runs, newest first."""
    rows = conn.execute(
        "SELECT * FROM geocode_runs ORDER BY started_at DESC LIMIT ?;",
        (limit,),
    ).fetchall()
    return _rows_to_dicts(rows)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_geocode.py -v
```

Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add db/queries.py tests/test_geocode.py
git commit -m "feat(db): add geocode_runs CRUD query helpers with tests"
```

---

## Phase 3: Backend — API Router

### Task 3: Create the geocode API router

**Files:**
- Create: `api/routers/geocode.py`
- Modify: `api/main.py:12,40-44` (add import and mount)
- Test: `tests/test_geocode.py` (append API tests)

- [ ] **Step 1: Write failing API tests**

Append the following to the bottom of `tests/test_geocode.py`:

```python
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.main import app
from api.dependencies import get_db
from db.schema import DDL_SCRIPT


@pytest.fixture
def test_db_path():
    """Create a temporary database file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)
    conn.executescript(DDL_SCRIPT)
    conn.row_factory = sqlite3.Row

    # Insert 3 leads without coordinates so geocoding has work to do
    for i in range(3):
        conn.execute(
            "INSERT INTO leads (fingerprint, business_name, city, state, pos_score, stage) "
            "VALUES (?, ?, ?, 'TN', 50, 'New');",
            (f"fp_{i}", f"Business {i}", "Nashville"),
        )
    conn.commit()
    conn.close()

    yield db_path
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def api_client(test_db_path):
    """Test client with database dependency overridden."""
    def override_get_db():
        conn = sqlite3.connect(test_db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

    # Reset the module-level geocode state after each test
    from api.routers.geocode import _reset_state
    _reset_state()


class TestGeocodeAPI:
    """Tests for geocode API endpoints."""

    def test_get_status_when_idle(self, api_client):
        resp = api_client.get("/api/geocode/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["running"] is False
        assert data["run_id"] is None
        assert data["total"] == 0
        assert data["done"] == 0
        assert data["succeeded"] == 0
        assert data["failed"] == 0
        assert data["pct"] == 0.0

    @patch("api.routers.geocode.geocode_lead", return_value=(36.16, -86.78))
    @patch("api.routers.geocode._MIN_INTERVAL", 0)
    def test_post_run_starts_job(self, mock_geocode, api_client):
        resp = api_client.post("/api/geocode/run")
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Geocoding started"
        assert data["run_id"] >= 1
        assert data["total"] == 3

    @patch("api.routers.geocode.geocode_lead", return_value=(36.16, -86.78))
    @patch("api.routers.geocode._MIN_INTERVAL", 0)
    def test_post_run_returns_409_when_running(self, mock_geocode, api_client):
        resp1 = api_client.post("/api/geocode/run")
        assert resp1.status_code == 200

        # Immediately try again — should get 409
        resp2 = api_client.post("/api/geocode/run")
        assert resp2.status_code == 409
        assert "already" in resp2.json()["detail"].lower()

    @patch("api.routers.geocode.geocode_lead", return_value=(36.16, -86.78))
    @patch("api.routers.geocode._MIN_INTERVAL", 0)
    def test_job_completes_and_updates_leads(self, mock_geocode, api_client, test_db_path):
        resp = api_client.post("/api/geocode/run")
        assert resp.status_code == 200

        # Wait for the background thread to finish (3 leads, no rate limit)
        for _ in range(50):
            time.sleep(0.1)
            status = api_client.get("/api/geocode/status").json()
            if not status["running"]:
                break

        assert status["running"] is False
        assert status["succeeded"] == 3
        assert status["failed"] == 0
        assert status["done"] == 3
        assert status["pct"] == 100.0

        # Verify leads were updated in the database
        conn = sqlite3.connect(test_db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT latitude, longitude FROM leads;").fetchall()
        conn.close()
        for row in rows:
            assert row["latitude"] == 36.16
            assert row["longitude"] == -86.78

    def test_get_runs_returns_list(self, api_client):
        resp = api_client.get("/api/geocode/runs")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    @patch("api.routers.geocode.geocode_lead", return_value=(36.16, -86.78))
    @patch("api.routers.geocode._MIN_INTERVAL", 0)
    def test_get_runs_shows_completed_run(self, mock_geocode, api_client):
        api_client.post("/api/geocode/run")
        # Wait for completion
        for _ in range(50):
            time.sleep(0.1)
            status = api_client.get("/api/geocode/status").json()
            if not status["running"]:
                break

        runs = api_client.get("/api/geocode/runs").json()
        assert len(runs) >= 1
        assert runs[0]["status"] == "completed"
        assert runs[0]["total"] == 3
        assert runs[0]["succeeded"] == 3
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_geocode.py::TestGeocodeAPI -v
```

Expected: FAIL with `ModuleNotFoundError` or route 404 (router doesn't exist yet)

- [ ] **Step 3: Create `api/routers/geocode.py`**

Create the file `api/routers/geocode.py`:

```python
"""Geocoding API endpoints — trigger, monitor, and list geocoding runs."""

from __future__ import annotations

import logging
import sqlite3
import threading
import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_db
from config.settings import DB_PATH
from db.queries import insert_geocode_run, update_geocode_run, get_geocode_runs
from utils.geocoder import geocode_lead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/geocode", tags=["geocode"])

# Nominatim rate limit — 1.1s between requests.  Overridable in tests.
_MIN_INTERVAL = 1.1

# Module-level state — read by GET /status, written by background thread.
_geocode_lock = threading.Lock()
_geocode_state: dict = {
    "running": False,
    "run_id": None,
    "total": 0,
    "done": 0,
    "succeeded": 0,
    "failed": 0,
    "started_at": None,
}


def _reset_state() -> None:
    """Reset module-level state.  Used by tests to clean up between runs."""
    global _geocode_state
    # If a lock is held, release it (best-effort for tests)
    try:
        _geocode_lock.release()
    except RuntimeError:
        pass
    _geocode_state = {
        "running": False,
        "run_id": None,
        "total": 0,
        "done": 0,
        "succeeded": 0,
        "failed": 0,
        "started_at": None,
    }


def _geocode_thread(run_id: int, db_path: str) -> None:
    """Background thread that geocodes all un-geocoded leads."""
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(db_path, timeout=30.0)
        conn.execute("PRAGMA busy_timeout = 30000")
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            "SELECT id, address, city, state, zip_code FROM leads "
            "WHERE deleted_at IS NULL AND (latitude IS NULL OR longitude IS NULL);"
        ).fetchall()
        leads = [dict(r) for r in rows]

        _geocode_state["total"] = len(leads)

        cache: dict[str, tuple[float | None, float | None]] = {}
        last_request_time = 0.0

        for lead in leads:
            # Build a cache key from the geocoder's query string
            from utils.geocoder import _build_query_string

            query = _build_query_string(lead)

            if query and query in cache:
                lat, lon = cache[query]
            elif query:
                # Rate limit
                elapsed = time.monotonic() - last_request_time
                if elapsed < _MIN_INTERVAL:
                    time.sleep(_MIN_INTERVAL - elapsed)

                lat, lon = geocode_lead(lead)
                last_request_time = time.monotonic()
                cache[query] = (lat, lon)
            else:
                lat, lon = None, None

            # Update lead row
            if lat is not None and lon is not None:
                conn.execute(
                    "UPDATE leads SET latitude = ?, longitude = ?, updated_at = datetime('now') WHERE id = ?;",
                    (lat, lon, lead["id"]),
                )
                conn.commit()
                _geocode_state["succeeded"] += 1
            else:
                _geocode_state["failed"] += 1

            _geocode_state["done"] += 1

        # Mark run as completed
        update_geocode_run(
            conn,
            run_id=run_id,
            status="completed",
            succeeded=_geocode_state["succeeded"],
            failed=_geocode_state["failed"],
        )

    except Exception as exc:
        logger.exception("Geocode thread failed: %s", exc)
        if conn:
            try:
                update_geocode_run(
                    conn,
                    run_id=run_id,
                    status="failed",
                    succeeded=_geocode_state["succeeded"],
                    failed=_geocode_state["failed"],
                    error_message=str(exc),
                )
            except Exception:
                pass
    finally:
        if conn:
            conn.close()
        _geocode_state["running"] = False
        try:
            _geocode_lock.release()
        except RuntimeError:
            pass


@router.post("/run")
def start_geocode_run(
    conn: Annotated[sqlite3.Connection, Depends(get_db)],
):
    """Start a geocoding job in a background thread.

    Returns 409 if a job is already running.
    """
    acquired = _geocode_lock.acquire(blocking=False)
    if not acquired:
        raise HTTPException(status_code=409, detail="Geocoding is already in progress")

    try:
        # Count un-geocoded leads
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM leads "
            "WHERE deleted_at IS NULL AND (latitude IS NULL OR longitude IS NULL);"
        ).fetchone()
        total = row["cnt"] if row else 0

        # Insert run record
        run_id = insert_geocode_run(conn, total=total)

        # Update module state
        _geocode_state["running"] = True
        _geocode_state["run_id"] = run_id
        _geocode_state["total"] = total
        _geocode_state["done"] = 0
        _geocode_state["succeeded"] = 0
        _geocode_state["failed"] = 0
        _geocode_state["started_at"] = None  # Will be set from DB row

        # Read back the started_at value
        run_row = conn.execute(
            "SELECT started_at FROM geocode_runs WHERE id = ?;", (run_id,)
        ).fetchone()
        if run_row:
            _geocode_state["started_at"] = run_row["started_at"]

        # Spawn daemon thread
        thread = threading.Thread(
            target=_geocode_thread,
            args=(run_id, str(DB_PATH)),
            daemon=True,
        )
        thread.start()

    except Exception:
        # Release lock if we fail before spawning the thread
        try:
            _geocode_lock.release()
        except RuntimeError:
            pass
        raise

    return {"message": "Geocoding started", "run_id": run_id, "total": total}


@router.get("/status")
def get_geocode_status():
    """Return current geocoding state."""
    total = _geocode_state["total"]
    done = _geocode_state["done"]
    pct = round((done / total) * 100, 1) if total > 0 else 0.0

    # Estimate remaining time: each lead takes ~1.1s
    remaining = total - done
    eta_seconds = round(remaining * _MIN_INTERVAL) if _geocode_state["running"] else None

    return {
        "running": _geocode_state["running"],
        "run_id": _geocode_state["run_id"],
        "total": total,
        "done": done,
        "succeeded": _geocode_state["succeeded"],
        "failed": _geocode_state["failed"],
        "pct": pct,
        "started_at": _geocode_state["started_at"],
        "eta_seconds": eta_seconds,
    }


@router.get("/runs")
def list_geocode_runs(
    conn: Annotated[sqlite3.Connection, Depends(get_db)],
    limit: int = 10,
):
    """Return past geocoding runs, newest first."""
    return get_geocode_runs(conn, limit=limit)
```

- [ ] **Step 4: Mount the router in `api/main.py`**

In `api/main.py`, add the import. Change line 12:

```python
from api.routers import leads, stats, pipeline, kanban, map as map_router
```

To:

```python
from api.routers import leads, stats, pipeline, kanban, map as map_router, geocode
```

Then add after line 44 (`app.include_router(map_router.router)`):

```python
app.include_router(geocode.router)
```

- [ ] **Step 5: Run all geocode tests**

```bash
pytest tests/test_geocode.py -v
```

Expected: All 12 tests PASS (6 query tests + 6 API tests)

- [ ] **Step 6: Run the full test suite to check for regressions**

```bash
pytest tests/ -v --ignore=tests/uat_playwright_test.py --ignore=tests/test_clerk_scraper.py
```

Expected: All existing tests still pass

- [ ] **Step 7: Commit**

```bash
git add api/routers/geocode.py api/main.py tests/test_geocode.py
git commit -m "feat(api): add geocode router with POST /run, GET /status, GET /runs"
```

---

## Phase 4: Frontend — Types and API Client

### Task 4: Add TypeScript types and API functions

**Files:**
- Modify: `frontend/lib/types.ts:191` (append after `MapFilters` interface)
- Modify: `frontend/lib/api.ts:202` (append after `getMapLeads` function)

- [ ] **Step 1: Add types to `frontend/lib/types.ts`**

Append at the end of the file (after line 191):

```typescript

export interface GeocodeStatus {
  running: boolean;
  run_id: number | null;
  total: number;
  done: number;
  succeeded: number;
  failed: number;
  pct: number;
  started_at: string | null;
  eta_seconds: number | null;
}

export interface GeocodeRun {
  id: number;
  started_at: string;
  finished_at: string | null;
  status: string;
  total: number;
  succeeded: number;
  failed: number;
}
```

- [ ] **Step 2: Add API functions to `frontend/lib/api.ts`**

First, update the import at the top of `frontend/lib/api.ts` (line 1-15). Add `GeocodeStatus` and `GeocodeRun` to the import:

Change line 1-15 from:
```typescript
import type {
  Lead,
  LeadsResponse,
  LeadsBatchResponse,
  Stats,
  PipelineRun,
  PipelineStatus,
  KanbanData,
  LeadFilters,
  LeadFieldUpdate,
  DuplicatesResponse,
  MergeRequest,
  MapLeadsResponse,
  MapFilters,
} from "./types";
```

To:
```typescript
import type {
  Lead,
  LeadsResponse,
  LeadsBatchResponse,
  Stats,
  PipelineRun,
  PipelineStatus,
  KanbanData,
  LeadFilters,
  LeadFieldUpdate,
  DuplicatesResponse,
  MergeRequest,
  MapLeadsResponse,
  MapFilters,
  GeocodeStatus,
  GeocodeRun,
} from "./types";
```

Then append at the end of the file (after the `getMapLeads` function):

```typescript

// Geocode
export async function startGeocode(): Promise<{ message: string; run_id: number; total: number }> {
  return fetchJson(`${API_BASE}/geocode/run`, { method: "POST" });
}

export async function getGeocodeStatus(): Promise<GeocodeStatus> {
  return fetchJson<GeocodeStatus>(`${API_BASE}/geocode/status`);
}

export async function getGeocodeRuns(): Promise<GeocodeRun[]> {
  return fetchJson<GeocodeRun[]>(`${API_BASE}/geocode/runs`);
}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: No new errors related to `GeocodeStatus`, `GeocodeRun`, `startGeocode`, `getGeocodeStatus`, or `getGeocodeRuns`

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/types.ts frontend/lib/api.ts
git commit -m "feat(frontend): add GeocodeStatus/GeocodeRun types and API functions"
```

---

## Phase 5: Frontend — Map Page Geocode Overlay

### Task 5: Add idle overlay and running toast to the map page

**Files:**
- Modify: `frontend/app/map/page.tsx` (add geocode status query, pass to map)
- Modify: `frontend/components/lead-map.tsx` (add overlay and toast components)

- [ ] **Step 1: Update `frontend/app/map/page.tsx` to fetch geocode status and expose controls**

Replace the full contents of `frontend/app/map/page.tsx` with:

```typescript
"use client";

import { useState, useRef, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import { AppShell } from "@/components/app-shell";
import { LeadDetailPanel } from "@/components/lead-detail-panel";
import { MapFiltersBar } from "@/components/map-filters";
import { getMapLeads, getLead, getGeocodeStatus, startGeocode } from "@/lib/api";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import type { Lead, MapFilters } from "@/lib/types";

const LeadMap = dynamic(() => import("@/components/lead-map"), { ssr: false });

export default function MapPage() {
  const queryClient = useQueryClient();
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [filters, setFilters] = useState<MapFilters>({});
  const prevRunningRef = useRef<boolean | undefined>(undefined);

  const { data, isLoading } = useQuery({
    queryKey: ["map-leads", filters],
    queryFn: () => getMapLeads(filters),
  });

  const { data: geocodeStatus } = useQuery({
    queryKey: ["geocodeStatus"],
    queryFn: getGeocodeStatus,
    refetchInterval: (query) => {
      return query.state.data?.running ? 2000 : false;
    },
  });

  // When geocoding finishes, invalidate map data and show toast
  useEffect(() => {
    if (prevRunningRef.current === true && geocodeStatus?.running === false) {
      queryClient.invalidateQueries({ queryKey: ["map-leads"] });
      queryClient.invalidateQueries({ queryKey: ["stats"] });
      if (geocodeStatus.succeeded > 0) {
        toast.success(
          `Geocoding complete — ${geocodeStatus.succeeded} leads geocoded`
        );
      }
    }
    prevRunningRef.current = geocodeStatus?.running;
  }, [geocodeStatus?.running]);

  const geocodeMutation = useMutation({
    mutationFn: startGeocode,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["geocodeStatus"] });
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to start geocoding");
    },
  });

  const handleLeadClick = async (leadId: number) => {
    try {
      const fullLead = await getLead(leadId);
      setSelectedLead(fullLead);
    } catch {
      const mapLead = data?.leads.find((l) => l.id === leadId);
      if (mapLead) {
        setSelectedLead({
          ...mapLead,
          fingerprint: "",
          raw_type: null,
          address: null,
          state: "TN",
          zip_code: null,
          license_date: null,
          source_url: null,
          source_type: null,
          source_batch_id: null,
          notes: null,
          created_at: "",
          updated_at: "",
          contacted_at: null,
          closed_at: null,
        } as Lead);
      }
    }
  };

  return (
    <AppShell>
      <div className="-m-8 h-[calc(100vh)] relative">
        {isLoading || !data ? (
          <div className="flex items-center justify-center h-full">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : (
          <>
            <LeadMap
              leads={data.leads}
              onLeadClick={handleLeadClick}
              geocodeStatus={geocodeStatus ?? null}
              totalWithoutCoords={data.total_without_coords}
              onStartGeocode={() => geocodeMutation.mutate()}
              isStarting={geocodeMutation.isPending}
            />
            <MapFiltersBar
              filters={filters}
              onFilterChange={setFilters}
              totalGeocoded={data.total_geocoded}
              totalWithoutCoords={data.total_without_coords}
            />
          </>
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

- [ ] **Step 2: Update `frontend/components/lead-map.tsx` with overlay and toast**

Replace the full contents of `frontend/components/lead-map.tsx` with:

```typescript
"use client";

import { MapContainer, TileLayer, Marker, Tooltip } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { MapLead, Stage, GeocodeStatus } from "@/lib/types";

interface LeadMapProps {
  leads: MapLead[];
  onLeadClick: (leadId: number) => void;
  geocodeStatus: GeocodeStatus | null;
  totalWithoutCoords: number;
  onStartGeocode: () => void;
  isStarting: boolean;
}

const STAGE_COLORS: Record<Stage, string> = {
  New: "#4f7cf6",
  Qualified: "#8b5cf6",
  Contacted: "#14b8a6",
  "Follow-up": "#f59e0b",
  "Closed-Won": "#22c55e",
  "Closed-Lost": "#6b7280",
};

function createMarkerIcon(stage: Stage): L.DivIcon {
  const color = STAGE_COLORS[stage];
  return L.divIcon({
    html: `<div style="
      width: 12px;
      height: 12px;
      background-color: ${color};
      border: 2px solid white;
      border-radius: 50%;
      box-shadow: 0 2px 4px rgba(0,0,0,0.3);
    "></div>`,
    className: "",
    iconSize: [12, 12],
    iconAnchor: [6, 6],
  });
}

function formatEta(seconds: number | null): string {
  if (seconds === null || seconds <= 0) return "";
  const mins = Math.ceil(seconds / 60);
  if (mins < 2) return "~1 min";
  return `~${mins} min`;
}

export default function LeadMap({
  leads,
  onLeadClick,
  geocodeStatus,
  totalWithoutCoords,
  onStartGeocode,
  isStarting,
}: LeadMapProps) {
  const isRunning = geocodeStatus?.running === true;
  const showIdleOverlay = !isRunning && totalWithoutCoords > 0;
  const estimatedMinutes = Math.ceil(totalWithoutCoords * 1.1 / 60);

  return (
    <MapContainer
      center={[36.1627, -86.7816]}
      zoom={9}
      className="h-full w-full z-0"
      style={{ height: "100%", width: "100%" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {leads.map((lead) => (
        <Marker
          key={lead.id}
          position={[lead.latitude, lead.longitude]}
          icon={createMarkerIcon(lead.stage)}
          eventHandlers={{
            click: () => onLeadClick(lead.id),
          }}
        >
          <Tooltip>
            <div className="text-xs">
              <div className="font-semibold">{lead.business_name}</div>
              <div className="text-muted-foreground">
                {lead.business_type || "other"} • Score: {lead.pos_score}
              </div>
            </div>
          </Tooltip>
        </Marker>
      ))}

      {/* Idle overlay — top-right floating button */}
      {showIdleOverlay && (
        <div
          className="absolute top-16 right-4 z-[1000]"
          style={{
            background: "rgba(8, 13, 26, 0.88)",
            border: "1px solid rgba(99, 102, 241, 0.35)",
            borderRadius: "8px",
            padding: "8px 14px",
            backdropFilter: "blur(16px)",
            boxShadow: "0 4px 16px rgba(0,0,0,0.4)",
            display: "flex",
            alignItems: "center",
            gap: "10px",
          }}
        >
          <div>
            <div style={{ fontSize: "11px", color: "#c7d2fe", fontWeight: 600 }}>
              {totalWithoutCoords.toLocaleString()} leads unplotted
            </div>
            <div style={{ fontSize: "10px", color: "#4f46e5", marginTop: "1px" }}>
              OpenStreetMap · free · ~{estimatedMinutes} min
            </div>
          </div>
          <div style={{ width: "1px", height: "24px", background: "rgba(255,255,255,0.08)" }} />
          <button
            onClick={onStartGeocode}
            disabled={isStarting}
            style={{
              fontSize: "11px",
              fontWeight: 700,
              padding: "6px 14px",
              borderRadius: "6px",
              border: "none",
              background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
              color: "#fff",
              cursor: isStarting ? "not-allowed" : "pointer",
              opacity: isStarting ? 0.6 : 1,
              boxShadow: "0 2px 8px rgba(99,102,241,0.4)",
              whiteSpace: "nowrap",
            }}
          >
            {isStarting ? "Starting..." : "Geocode All"}
          </button>
        </div>
      )}

      {/* Running toast — bottom floating overlay */}
      {isRunning && geocodeStatus && (
        <div
          className="absolute bottom-4 left-4 right-4 z-[1000]"
          style={{
            background: "rgba(8, 13, 26, 0.92)",
            border: "1px solid rgba(16, 185, 129, 0.3)",
            borderRadius: "10px",
            padding: "14px 16px",
            backdropFilter: "blur(20px)",
            boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
          }}
        >
          {/* Top row: icon, title, stats, button */}
          <div style={{ display: "flex", alignItems: "flex-start", gap: "12px", marginBottom: "10px" }}>
            <div
              style={{
                width: "32px",
                height: "32px",
                borderRadius: "8px",
                background: "rgba(16, 185, 129, 0.12)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "15px",
                flexShrink: 0,
                marginTop: "1px",
              }}
            >
              ⏳
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: "12px", fontWeight: 700, color: "#6ee7b7" }}>
                Geocoding in progress
              </div>
              <div style={{ fontSize: "10px", color: "#059669", marginTop: "2px" }}>
                OpenStreetMap · 1 req/sec · new pins appear as leads resolve
              </div>
              {/* Stat numbers */}
              <div style={{ display: "flex", gap: "18px", marginTop: "8px" }}>
                <div>
                  <div style={{ fontSize: "18px", fontWeight: 800, color: "#34d399", lineHeight: 1 }}>
                    {geocodeStatus.succeeded.toLocaleString()}
                  </div>
                  <div style={{ fontSize: "9px", textTransform: "uppercase", letterSpacing: "0.08em", color: "#334155", marginTop: "2px" }}>
                    Geocoded
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: "18px", fontWeight: 800, color: "#f87171", lineHeight: 1 }}>
                    {geocodeStatus.failed.toLocaleString()}
                  </div>
                  <div style={{ fontSize: "9px", textTransform: "uppercase", letterSpacing: "0.08em", color: "#334155", marginTop: "2px" }}>
                    Failed
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: "18px", fontWeight: 800, color: "#64748b", lineHeight: 1 }}>
                    {(geocodeStatus.total - geocodeStatus.done).toLocaleString()}
                  </div>
                  <div style={{ fontSize: "9px", textTransform: "uppercase", letterSpacing: "0.08em", color: "#334155", marginTop: "2px" }}>
                    Remaining
                  </div>
                </div>
              </div>
            </div>
            <button
              disabled
              style={{
                fontSize: "10px",
                fontWeight: 600,
                padding: "6px 12px",
                borderRadius: "6px",
                border: "1px solid rgba(255,255,255,0.08)",
                background: "rgba(255,255,255,0.05)",
                color: "#64748b",
                cursor: "not-allowed",
                whiteSpace: "nowrap",
                alignSelf: "flex-start",
              }}
            >
              Running...
            </button>
          </div>

          {/* Progress bar */}
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "5px" }}>
              <span style={{ fontSize: "10px", color: "#475569" }}>
                {geocodeStatus.done.toLocaleString()} / {geocodeStatus.total.toLocaleString()}
              </span>
              <span style={{ fontSize: "11px", fontWeight: 800, color: "#34d399" }}>
                {geocodeStatus.pct}%
              </span>
            </div>
            <div
              style={{
                height: "6px",
                background: "rgba(255,255,255,0.06)",
                borderRadius: "3px",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  height: "100%",
                  width: `${geocodeStatus.pct}%`,
                  borderRadius: "3px",
                  background: "linear-gradient(90deg, #059669, #10b981, #34d399)",
                  boxShadow: "0 0 8px rgba(16,185,129,0.4)",
                  transition: "width 0.5s ease",
                }}
              />
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: "4px" }}>
              <span style={{ fontSize: "9px", color: "#334155" }}>
                {geocodeStatus.started_at ? `Started ${geocodeStatus.started_at}` : ""}
              </span>
              <span style={{ fontSize: "9px", color: "#334155" }}>
                {geocodeStatus.eta_seconds !== null && (
                  <>{formatEta(geocodeStatus.eta_seconds)} remaining</>
                )}
              </span>
            </div>
          </div>
        </div>
      )}
    </MapContainer>
  );
}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: No new type errors

- [ ] **Step 4: Manual smoke test**

Start both servers:
```bash
./scripts/dev.sh
```

1. Navigate to `http://localhost:3000/map`
2. Verify the frosted-glass "X leads unplotted · Geocode All" button appears in the top-right area of the map
3. Click "Geocode All" — the idle overlay should disappear and the running toast should appear at the bottom
4. Verify the progress bar updates every 2 seconds
5. When complete, a Sonner toast should say "Geocoding complete — X leads geocoded" and new pins should appear on the map

- [ ] **Step 5: Commit**

```bash
git add frontend/app/map/page.tsx frontend/components/lead-map.tsx
git commit -m "feat(frontend): add geocode overlay + running toast to map page"
```

---

## Phase 6: Frontend — Pipeline Page Integration

### Task 6: Show geocode runs in the pipeline history timeline

**Files:**
- Modify: `frontend/app/pipeline/page.tsx`

- [ ] **Step 1: Update `frontend/app/pipeline/page.tsx`**

Replace the full contents of the file with:

```typescript
"use client";

import { useMemo, useEffect } from "react";
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
import {
  getPipelineRuns,
  getPipelineStatus,
  triggerPipelineRun,
  getGeocodeRuns,
  getGeocodeStatus,
} from "@/lib/api";
import { Loader2, Play, CheckCircle, XCircle, Clock, MapPin } from "lucide-react";
import { formatLocalDateTime } from "@/lib/utils";

interface TimelineRow {
  id: string;
  job_type: "etl" | "geocode";
  started_at: string;
  finished_at: string | null;
  status: string;
  label: string;
  detail: string;
}

export default function PipelinePage() {
  const queryClient = useQueryClient();

  const { data: runs, isLoading } = useQuery({
    queryKey: ["pipelineRuns"],
    queryFn: () => getPipelineRuns(20),
  });

  const { data: geocodeRuns } = useQuery({
    queryKey: ["geocodeRuns"],
    queryFn: getGeocodeRuns,
  });

  const { data: status, refetch: refetchStatus } = useQuery({
    queryKey: ["pipelineStatus"],
    queryFn: getPipelineStatus,
    refetchInterval: (query) => {
      return query.state.data?.running ? 2000 : false;
    },
  });

  const { data: geocodeStatus } = useQuery({
    queryKey: ["geocodeStatus"],
    queryFn: getGeocodeStatus,
    refetchInterval: (query) => {
      return query.state.data?.running ? 2000 : false;
    },
  });

  useEffect(() => {
    if (status && !status.running) {
      queryClient.invalidateQueries({ queryKey: ["pipelineRuns"] });
    }
  }, [status?.running]);

  useEffect(() => {
    if (geocodeStatus && !geocodeStatus.running) {
      queryClient.invalidateQueries({ queryKey: ["geocodeRuns"] });
    }
  }, [geocodeStatus?.running]);

  const mutation = useMutation({
    mutationFn: triggerPipelineRun,
    onSuccess: () => {
      toast.success("Pipeline started");
      refetchStatus();
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to start pipeline");
    },
  });

  // Merge ETL and geocode runs into a unified timeline sorted by started_at desc
  const timeline = useMemo<TimelineRow[]>(() => {
    const rows: TimelineRow[] = [];

    if (runs?.runs) {
      for (const r of runs.runs) {
        rows.push({
          id: `etl-${r.id}`,
          job_type: "etl",
          started_at: r.run_started_at,
          finished_at: r.run_finished_at,
          status: r.status,
          label: "ETL Pipeline",
          detail: `${r.leads_new} new · ${r.leads_dupes} dupes · ${r.leads_found} found`,
        });
      }
    }

    if (geocodeRuns) {
      for (const g of geocodeRuns) {
        rows.push({
          id: `geo-${g.id}`,
          job_type: "geocode",
          started_at: g.started_at,
          finished_at: g.finished_at,
          status: g.status,
          label: "Geocode",
          detail: `${g.succeeded} geocoded · ${g.failed} failed · ${g.total} total`,
        });
      }
    }

    rows.sort((a, b) => (b.started_at ?? "").localeCompare(a.started_at ?? ""));
    return rows;
  }, [runs, geocodeRuns]);

  const formatDate = (dateStr: string | null) => {
    return formatLocalDateTime(dateStr) || "—";
  };

  const getStatusIcon = (rowStatus: string) => {
    switch (rowStatus) {
      case "completed":
        return <CheckCircle className="h-4 w-4 text-emerald-400" />;
      case "failed":
        return <XCircle className="h-4 w-4 text-red-400" />;
      case "running":
        return <Loader2 className="h-4 w-4 animate-spin text-primary" />;
      default:
        return <Clock className="h-4 w-4 text-muted-foreground" />;
    }
  };

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Pipeline</h1>
            <p className="text-muted-foreground mt-1">
              ETL pipeline runs and execution history
            </p>
          </div>
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
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Latest Result</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                <div>
                  <p className="text-xs uppercase tracking-wider text-muted-foreground mb-1">Status</p>
                  <div className="flex items-center gap-2">
                    {getStatusIcon(status.last_result.status)}
                    <span className="font-medium capitalize">
                      {status.last_result.status}
                    </span>
                  </div>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wider text-muted-foreground mb-1">Run ID</p>
                  <p className="font-medium font-mono text-sm">{status.last_result.run_id || "—"}</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wider text-muted-foreground mb-1">Found</p>
                  <p className="font-medium text-lg">{status.last_result.leads_found ?? "—"}</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wider text-muted-foreground mb-1">New</p>
                  <p className="font-medium text-lg">{status.last_result.leads_new ?? "—"}</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wider text-muted-foreground mb-1">Duplicates</p>
                  <p className="font-medium text-lg">{status.last_result.leads_dupes ?? "—"}</p>
                </div>
              </div>
              {status.last_result.error && (
                <p className="mt-4 text-sm text-destructive glass-subtle rounded-lg p-3">
                  Error: {status.last_result.error}
                </p>
              )}
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Run History</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex justify-center py-8">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
              </div>
            ) : (
              <div className="rounded-lg overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow className="border-b border-border/50 hover:bg-transparent">
                      <TableHead className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">Type</TableHead>
                      <TableHead className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">Started</TableHead>
                      <TableHead className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">Finished</TableHead>
                      <TableHead className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">Status</TableHead>
                      <TableHead className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">Details</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {timeline.map((row) => (
                      <TableRow key={row.id} className="border-b border-border/30 hover:bg-accent/5 transition-colors">
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {row.job_type === "geocode" ? (
                              <MapPin className="h-4 w-4 text-indigo-400" />
                            ) : (
                              <Play className="h-3.5 w-3.5 text-muted-foreground" />
                            )}
                            <span className="text-sm font-medium">{row.label}</span>
                          </div>
                        </TableCell>
                        <TableCell className="text-muted-foreground">{formatDate(row.started_at)}</TableCell>
                        <TableCell className="text-muted-foreground">{formatDate(row.finished_at)}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {getStatusIcon(row.status)}
                            <Badge
                              variant={
                                row.status === "completed"
                                  ? "success"
                                  : row.status === "failed"
                                  ? "destructive"
                                  : "secondary"
                              }
                              className="text-xs"
                            >
                              {row.status}
                            </Badge>
                          </div>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">{row.detail}</TableCell>
                      </TableRow>
                    ))}
                    {timeline.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={5} className="text-center py-12 text-muted-foreground">
                          No runs yet
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: No new type errors

- [ ] **Step 3: Manual smoke test**

1. Navigate to `http://localhost:3000/pipeline`
2. Verify existing ETL runs still show in the table
3. Trigger a geocode job from the map page
4. Return to the pipeline page — verify the geocode run appears in the timeline with a MapPin icon and "Geocode" label
5. Once complete, verify it shows status "completed" with correct counts

- [ ] **Step 4: Commit**

```bash
git add frontend/app/pipeline/page.tsx
git commit -m "feat(frontend): show geocode runs in pipeline history timeline"
```

---

## Phase 7: Backend — Orphaned Run Cleanup

### Task 7: Clean up orphaned geocode runs on startup

**Files:**
- Modify: `db/queries.py` (add cleanup function)
- Modify: `api/routers/geocode.py` (call cleanup on module load)
- Test: `tests/test_geocode.py` (add cleanup test)

- [ ] **Step 1: Write failing test**

Add to `tests/test_geocode.py` inside `TestGeocodeRunQueries`:

```python
    def test_cleanup_orphaned_runs(self, memory_db):
        """Orphaned running rows get marked as failed on cleanup."""
        from db.queries import cleanup_orphaned_geocode_runs

        # Insert an orphaned "running" row
        memory_db.execute(
            "INSERT INTO geocode_runs (status, total, succeeded, failed) VALUES ('running', 100, 50, 2);"
        )
        # Insert a completed row (should not be touched)
        memory_db.execute(
            "INSERT INTO geocode_runs (status, total, succeeded, failed) VALUES ('completed', 200, 195, 5);"
        )
        memory_db.commit()

        cleaned = cleanup_orphaned_geocode_runs(memory_db)
        assert cleaned == 1

        rows = memory_db.execute(
            "SELECT status, error_message FROM geocode_runs ORDER BY id;"
        ).fetchall()
        assert rows[0]["status"] == "failed"
        assert "interrupted" in rows[0]["error_message"].lower()
        assert rows[1]["status"] == "completed"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_geocode.py::TestGeocodeRunQueries::test_cleanup_orphaned_runs -v
```

Expected: FAIL with `ImportError: cannot import name 'cleanup_orphaned_geocode_runs'`

- [ ] **Step 3: Implement cleanup function**

Add to `db/queries.py`, after the `get_geocode_runs` function:

```python
def cleanup_orphaned_geocode_runs(conn: sqlite3.Connection) -> int:
    """Mark any 'running' geocode_runs as 'failed' (server restart cleanup).

    Returns the number of rows cleaned up.
    """
    cur = conn.execute(
        "UPDATE geocode_runs SET "
        "status = 'failed', "
        "finished_at = datetime('now'), "
        "error_message = 'Interrupted — server restarted before job completed' "
        "WHERE status = 'running';"
    )
    conn.commit()
    return cur.rowcount
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_geocode.py::TestGeocodeRunQueries::test_cleanup_orphaned_runs -v
```

Expected: PASS

- [ ] **Step 5: Call cleanup on router module load**

In `api/routers/geocode.py`, add at the bottom of the file (after all route definitions), add a startup cleanup call. Add this import at the top with the other db imports:

```python
from db.queries import insert_geocode_run, update_geocode_run, get_geocode_runs, cleanup_orphaned_geocode_runs
```

(Update the existing import line — add `cleanup_orphaned_geocode_runs` to it.)

Then add at the very bottom of the file:

```python
def _startup_cleanup() -> None:
    """Clean up orphaned geocode runs from a previous server crash."""
    import sqlite3 as _sqlite3
    try:
        conn = _sqlite3.connect(str(DB_PATH), timeout=5.0)
        conn.row_factory = _sqlite3.Row
        cleaned = cleanup_orphaned_geocode_runs(conn)
        if cleaned:
            logger.info("Cleaned up %d orphaned geocode run(s)", cleaned)
        conn.close()
    except Exception as exc:
        logger.warning("Startup cleanup failed: %s", exc)


_startup_cleanup()
```

- [ ] **Step 6: Run all tests**

```bash
pytest tests/test_geocode.py -v
```

Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add db/queries.py api/routers/geocode.py tests/test_geocode.py
git commit -m "feat(api): clean up orphaned geocode runs on startup"
```

---

## Phase 8: Final Verification

### Task 8: Full integration test

- [ ] **Step 1: Run the full backend test suite**

```bash
pytest tests/ -v --ignore=tests/uat_playwright_test.py --ignore=tests/test_clerk_scraper.py
```

Expected: All tests PASS with no regressions

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: Zero errors

- [ ] **Step 3: End-to-end manual test**

Start both servers:
```bash
./scripts/dev.sh
```

Verify:
1. `/map` — idle overlay shows "X leads unplotted" with "Geocode All" button
2. Click "Geocode All" — running toast appears with stats and progress bar
3. Progress bar updates every 2s, showing pct%, done/total, ETA
4. When complete, Sonner toast says "Geocoding complete — X leads geocoded"
5. New pins appear on the map without page refresh
6. `/pipeline` — geocode run shows in the unified timeline with a MapPin icon
7. API docs at `/docs` show the 3 new geocode endpoints

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: add geocode UI with map overlay, live progress, and pipeline history

- POST /api/geocode/run — triggers background geocoding job
- GET /api/geocode/status — polls live progress (running, done, pct, ETA)
- GET /api/geocode/runs — lists past geocode runs for pipeline history
- Map page: floating 'Geocode All' button + frosted-glass progress toast
- Pipeline page: unified timeline merging ETL and geocode runs
- Orphaned run cleanup on server startup
- New geocode_runs DB table with full CRUD helpers and tests"
```
