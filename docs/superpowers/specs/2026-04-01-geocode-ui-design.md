# Geocode UI — Feature Spec

**Date:** 2026-04-01
**Status:** Draft
**Scope:** Add a web UI to trigger and monitor geocoding of leads that lack coordinates

---

## Problem

2,443 of 2,461 leads have no latitude/longitude. The map page shows this count but provides no way to fix it — the user must SSH in and run `python3 -m cli.main geocode`. There is no progress visibility, no way to know when it finishes, and no record of past geocoding runs.

## Solution

Add a "Geocode All" button to the map page that triggers geocoding via the API. Show live progress in a floating toast overlay on the map. Log geocoding runs alongside ETL runs on the pipeline page.

## Design Decision: Option B + Variant 3

**Map page (floating overlay):**
- **Idle state:** A small frosted-glass button floats in the top-right corner of the map tile: "2,443 leads unplotted · Geocode All". Low visual weight — the map stays dominant.
- **Running state:** A frosted-glass toast overlays the bottom of the map. Shows: icon, "Geocoding in progress" title, three big stat numbers (geocoded / failed / remaining), a progress bar with percentage, ETA, and a disabled "Running..." button. Header chips update to show live counts.
- **Completed state:** When `running` transitions to `false`, the toast shows a green "Geocoding complete — X leads geocoded" summary for 5 seconds (via Sonner toast notification, not the map overlay), then disappears. The map overlay returns to idle state if any leads still lack coordinates, or hides entirely if all are geocoded. Map and stats queries are invalidated immediately so new pins appear without a page refresh.

**Pipeline page (run history):**
- Geocoding jobs appear as rows in the unified run history timeline alongside ETL runs, with a distinguishing label/badge. Shows status (Running/Done/Failed), counts, and a mini progress bar for active jobs.

---

## Architecture

### New table: `geocode_runs`

```sql
CREATE TABLE IF NOT EXISTS geocode_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at      TEXT NOT NULL DEFAULT (datetime('now')),
    finished_at     TEXT,
    status          TEXT NOT NULL DEFAULT 'running',   -- running | completed | failed
    total           INTEGER NOT NULL DEFAULT 0,
    succeeded       INTEGER NOT NULL DEFAULT 0,
    failed          INTEGER NOT NULL DEFAULT 0,
    error_message   TEXT
);
```

Rationale: Separate from `pipeline_runs` because the column semantics differ. The pipeline page merges both tables client-side, sorted by timestamp.

### API Endpoints

#### `POST /api/geocode/run`

Starts a geocoding job in a background thread.

**Request:** No body required.

**Response (200):**
```json
{
  "message": "Geocoding started",
  "run_id": 1,
  "total": 2443
}
```

**Response (409 — already running):**
```json
{
  "detail": "Geocoding is already in progress"
}
```

**Behavior:**
1. Acquire `_geocode_lock` (threading.Lock). If already held, return 409.
2. Query `SELECT COUNT(*) FROM leads WHERE deleted_at IS NULL AND (latitude IS NULL OR longitude IS NULL)`.
3. Insert a `geocode_runs` row with `status='running'` and `total=count`.
4. Spawn a daemon thread that:
   - Fetches all un-geocoded leads.
   - Loops through them, calling `geocode_lead()` for each.
   - Respects Nominatim's 1.1s rate limit (already in `geocode_batch`).
   - After each lead: updates the lead row (`SET latitude=?, longitude=?`), increments `_geocode_state` counters.
   - On completion: updates the `geocode_runs` row with `status='completed'`, `finished_at`, final counts.
   - On unrecoverable error: sets `status='failed'`, `error_message`.
   - Releases `_geocode_lock`.
5. Return 200 immediately (non-blocking).

#### `GET /api/geocode/status`

Returns current geocoding state.

**Response (200):**
```json
{
  "running": true,
  "run_id": 1,
  "total": 2443,
  "done": 834,
  "succeeded": 801,
  "failed": 33,
  "pct": 34.1,
  "started_at": "2026-04-01T14:30:00",
  "eta_seconds": 1568
}
```

When no job has ever run, returns `{ "running": false, "run_id": null, ... }` with zero counts.

**State source:** Module-level `_geocode_state` dict, updated by the background thread on every iteration. This is cheap to read and doesn't touch the database.

#### `GET /api/geocode/runs`

Returns past geocoding runs for the pipeline history page.

**Response (200):**
```json
[
  {
    "id": 1,
    "started_at": "2026-04-01T14:30:00",
    "finished_at": "2026-04-01T15:12:34",
    "status": "completed",
    "total": 2443,
    "succeeded": 2101,
    "failed": 342
  }
]
```

### Backend Files

| File | Change |
|------|--------|
| `db/schema.py` | Add `geocode_runs` table DDL in `init_db()` |
| `db/queries.py` | Add `insert_geocode_run()`, `update_geocode_run()`, `get_geocode_runs()` |
| `api/routers/geocode.py` | New file — `POST /run`, `GET /status`, `GET /runs` |
| `api/main.py` | Mount geocode router at `/api/geocode` |

### Frontend Types

```typescript
// frontend/lib/types.ts

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

### Frontend API Functions

```typescript
// frontend/lib/api.ts

export async function startGeocode(): Promise<{ message: string; run_id: number; total: number }> {
  const res = await fetch(`${API}/geocode/run`, { method: "POST" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getGeocodeStatus(): Promise<GeocodeStatus> {
  const res = await fetch(`${API}/geocode/status`);
  if (!res.ok) throw new Error("Failed to fetch geocode status");
  return res.json();
}

export async function getGeocodeRuns(): Promise<GeocodeRun[]> {
  const res = await fetch(`${API}/geocode/runs`);
  if (!res.ok) throw new Error("Failed to fetch geocode runs");
  return res.json();
}
```

### Frontend Components

#### Map page — `frontend/components/lead-map.tsx`

**Idle overlay (top-right of map tile):**
- Frosted glass (`backdrop-filter: blur(16px)`, dark semi-transparent bg)
- Shows: "X leads unplotted" + "OpenStreetMap · free · ~Y min" + "Geocode All" button
- Only visible when `geocodeStatus.running === false` AND there are un-geocoded leads

**Running toast (bottom of map tile):**
- Frosted glass overlay spanning full width of map, pinned to bottom
- Left: icon + title "Geocoding in progress" + subtitle with rate info
- Center: three stat numbers — Geocoded (green), Failed (red), Remaining (muted)
- Bottom: progress bar with `pct%` label, "X / Y" count, ETA
- Right: disabled "Running..." button
- Visible when `geocodeStatus.running === true`

**Polling:** `useQuery("geocodeStatus", getGeocodeStatus, { refetchInterval: status?.running ? 2000 : false })`

**On completion:** Invalidate `["map"]` query so new pins render, invalidate `["stats"]` query, briefly show a completion toast via Sonner.

#### Pipeline page — `frontend/app/pipeline/page.tsx`

- Fetch `getGeocodeRuns()` alongside existing `getPipelineRuns()`
- Merge both arrays into a single timeline sorted by `started_at` descending
- Each row shows: colored dot (indigo for running, green for done), job name ("Geocode" vs "ETL Pipeline"), metadata line, status badge
- Running geocode jobs get a mini progress bar in the metadata line

---

## Data Flow

```
User clicks "Geocode All"
  → POST /api/geocode/run
  → 409? Show toast: "Geocoding already in progress"
  → 200? Show running toast, start polling

Background thread (server-side):
  → Query leads WHERE latitude IS NULL AND longitude IS NULL AND deleted_at IS NULL
  → For each lead:
      1. Build query string from address + city + state + zip
      2. Call Nominatim API (1.1s rate limit)
      3. UPDATE leads SET latitude=?, longitude=? WHERE id=?
      4. Increment _geocode_state.done, .succeeded or .failed
  → On finish: UPDATE geocode_runs SET status='completed', finished_at=now()
  → Release _geocode_lock

Frontend polling (every 2s):
  → GET /api/geocode/status
  → Update toast: stats, progress bar, pct, ETA
  → When running → false:
      → queryClient.invalidateQueries(["map"])
      → queryClient.invalidateQueries(["stats"])
      → toast.success("Geocoding complete — X leads geocoded")
      → Idle overlay reappears (if remaining > 0) or hides (if all done)
```

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Nominatim returns no results for a lead | `failed` counter increments, lead keeps NULL coords, job continues |
| Nominatim rate-limits or times out | `geocode_lead()` catches the exception, returns (None, None), `failed` increments, job continues |
| Network error mid-job | Same as above — individual failures don't abort the batch |
| User clicks "Geocode All" while job running | `POST /run` returns 409, frontend shows "already running" info (toast is already visible) |
| CLI `geocode` command runs concurrently with API job | Soft guard: API checks for `status='running'` row in `geocode_runs` before starting. CLI doesn't check (existing behavior unchanged). Worst case: two processes both geocode, Nominatim may throttle. Acceptable for single-user tool. |
| Server restarts mid-job | In-memory state lost. On next startup, detect orphaned `geocode_runs` rows with `status='running'` and mark them `status='failed'`. Leads already geocoded retain their coordinates. |
| Zero leads need geocoding | `POST /run` returns 200 with `total: 0`, job completes immediately |

---

## Concurrency Guard

```python
# api/routers/geocode.py

_geocode_lock = threading.Lock()
_geocode_state = {
    "running": False,
    "run_id": None,
    "total": 0,
    "done": 0,
    "succeeded": 0,
    "failed": 0,
    "started_at": None,
}
```

The lock is acquired non-blocking (`_geocode_lock.acquire(blocking=False)`). If it fails, return 409. The background thread releases the lock in a `finally` block, guaranteeing cleanup even on exceptions.

---

## Testing

| Test | Type | Description |
|------|------|-------------|
| `POST /api/geocode/run` returns 200 | Unit | Start a job, verify response shape and `geocode_runs` row created |
| `POST /api/geocode/run` returns 409 when running | Unit | Start a job, immediately POST again, verify 409 |
| `GET /api/geocode/status` shape | Unit | Verify all fields present and correctly typed |
| Geocoding updates lead coordinates | Integration | Mock `geocode_lead` to return (36.16, -86.78), run job, verify lead row updated |
| Job sets status=completed on finish | Integration | Run job with mocked geocoder, verify `geocode_runs` row has `status='completed'` |
| Job sets status=failed on exception | Integration | Mock geocoder to raise, verify `geocode_runs` row has `status='failed'` and `error_message` |
| Orphaned run cleanup on startup | Unit | Insert a `status='running'` row, call cleanup function, verify it becomes `status='failed'` |

---

## Files Changed (Summary)

**New files:**
- `api/routers/geocode.py`

**Modified files:**
- `db/schema.py` — add `geocode_runs` table
- `db/queries.py` — add geocode run CRUD helpers
- `api/main.py` — mount geocode router
- `frontend/lib/types.ts` — add `GeocodeStatus`, `GeocodeRun`
- `frontend/lib/api.ts` — add `startGeocode()`, `getGeocodeStatus()`, `getGeocodeRuns()`
- `frontend/components/lead-map.tsx` — idle overlay + running toast
- `frontend/app/pipeline/page.tsx` — merge geocode runs into history timeline

**Not changed:**
- `utils/geocoder.py` — reused as-is
- `cli/main.py` — existing CLI command unchanged
- `frontend/components/kanban-*.tsx`, `charts.tsx`, etc. — untouched
