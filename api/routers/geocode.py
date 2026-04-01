"""Geocoding API endpoints — trigger, monitor, and list geocoding runs."""

from __future__ import annotations

import logging
import sqlite3
import threading
import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import get_db
from config.settings import DB_PATH
from db.queries import (
    insert_geocode_run,
    update_geocode_run,
    get_geocode_runs,
    cleanup_orphaned_geocode_runs,
)
from utils.geocoder import geocode_lead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/geocode", tags=["geocode"])

# Nominatim rate limit — 1.1s between requests.  Overridable in tests.
_MIN_INTERVAL = 1.1

# Mutex — prevents two simultaneous geocoding jobs.
# Acquired by the request handler; released by the background thread's finally.
_geocode_lock = threading.Lock()

# Separate lock protecting _geocode_state dict reads/writes (Bug 1).
# It is distinct from _geocode_lock so the background thread can update
# progress counters without any re-entrancy issues.
_state_lock = threading.Lock()

_geocode_state: dict = {
    "running": False,
    "run_id": None,
    "total": 0,
    "done": 0,
    "succeeded": 0,
    "failed": 0,
    "started_at": None,
}

# Stop event: set this to ask the background thread to cancel cleanly (Bug 8).
_stop_event = threading.Event()


def _state_update(**kwargs) -> None:
    """Thread-safe helper to update one or more fields of _geocode_state."""
    with _state_lock:
        _geocode_state.update(kwargs)


def _state_increment(field: str, amount: int = 1) -> None:
    """Thread-safe increment of a numeric field in _geocode_state."""
    with _state_lock:
        _geocode_state[field] += amount


def _reset_state() -> None:
    """Reset module-level state.  Used by tests to clean up between runs.

    Bug 2 fix: we never call _geocode_lock.release() from outside the thread
    that owns it.  Instead, we signal the thread to stop (via _stop_event),
    then wait for it to release _geocode_lock on its own by doing a blocking
    acquire-then-release.  This guarantees the lock is free before we return.
    """
    global _geocode_state
    _stop_event.set()  # ask any running thread to stop
    # Wait for the background thread to release the lock (it always does in its
    # finally block).  A 5-second timeout is more than enough for tests.
    acquired = _geocode_lock.acquire(timeout=5.0)
    if acquired:
        _geocode_lock.release()
    _stop_event.clear()
    with _state_lock:
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
    cancelled = False
    try:
        conn = sqlite3.connect(db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode = WAL")   # Bug 6: WAL mode for concurrent reads
        conn.execute("PRAGMA busy_timeout = 30000")
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            "SELECT id, address, city, state, zip_code FROM leads "
            "WHERE deleted_at IS NULL AND (latitude IS NULL OR longitude IS NULL);"
        ).fetchall()
        leads = [dict(r) for r in rows]

        actual_total = len(leads)

        # Bug 4: update total in both state and DB to the thread's own count.
        _state_update(total=actual_total)
        conn.execute(
            "UPDATE geocode_runs SET total = ? WHERE id = ?;",
            (actual_total, run_id),
        )
        conn.commit()

        last_request_time = 0.0

        # Bug 5: in-memory cache to avoid duplicate API calls for same address.
        from utils.geocoder import _build_query_string
        coord_cache: dict[str, tuple[float | None, float | None]] = {}

        for lead in leads:
            # Bug 8: honour cancellation request
            if _stop_event.is_set():
                cancelled = True
                break

            query = _build_query_string(lead)

            if query is not None and query in coord_cache:
                lat, lon = coord_cache[query]
            else:
                # Rate limit only applies to real API calls
                elapsed = time.monotonic() - last_request_time
                if elapsed < _MIN_INTERVAL:
                    time.sleep(_MIN_INTERVAL - elapsed)

                lat, lon = geocode_lead(lead)
                last_request_time = time.monotonic()

                if query is not None:
                    coord_cache[query] = (lat, lon)

            if lat is not None and lon is not None:
                conn.execute(
                    "UPDATE leads SET latitude = ?, longitude = ?, updated_at = datetime('now') WHERE id = ?;",
                    (lat, lon, lead["id"]),
                )
                conn.commit()
                _state_increment("succeeded")
            else:
                _state_increment("failed")

            _state_increment("done")

        if cancelled:
            update_geocode_run(
                conn,
                run_id=run_id,
                status="cancelled",
                succeeded=_geocode_state["succeeded"],
                failed=_geocode_state["failed"],
                error_message="Cancelled by user request",
            )
        else:
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
        # Mark job as no longer running, then release the run-mutex.
        _state_update(running=False)
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

    # Clear any previous stop signal so the new job runs to completion.
    _stop_event.clear()

    try:
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM leads "
            "WHERE deleted_at IS NULL AND (latitude IS NULL OR longitude IS NULL);"
        ).fetchone()
        total = row["cnt"] if row else 0

        run_id = insert_geocode_run(conn, total=total)

        # Bug 1: write _geocode_state under _state_lock
        _state_update(
            running=True,
            run_id=run_id,
            total=total,
            done=0,
            succeeded=0,
            failed=0,
        )

        run_row = conn.execute(
            "SELECT started_at FROM geocode_runs WHERE id = ?;", (run_id,)
        ).fetchone()
        if run_row:
            _state_update(started_at=run_row["started_at"])

        # Get the actual DB path from the connection (works for both prod and tests)
        db_list_row = conn.execute("PRAGMA database_list;").fetchone()
        actual_db_path = db_list_row[2] if db_list_row and db_list_row[2] else str(DB_PATH)

        thread = threading.Thread(
            target=_geocode_thread,
            args=(run_id, actual_db_path),
            daemon=True,
        )
        thread.start()
        # Note: _geocode_lock is intentionally NOT released here — the background
        # thread owns it for the duration of the job and releases it in its finally.

    except Exception:
        try:
            _geocode_lock.release()
        except RuntimeError:
            pass
        raise

    return {"message": "Geocoding started", "run_id": run_id, "total": total}


@router.delete("/run")
def cancel_geocode_run():
    """Cancel a running geocoding job (Bug 8).

    Sets the stop event; the background thread will finish its current lead,
    mark the run as cancelled in the DB, and exit cleanly.
    Returns 409 if no job is currently running.
    """
    with _state_lock:
        running = _geocode_state["running"]
    if not running:
        raise HTTPException(status_code=409, detail="No geocoding job is currently running")
    _stop_event.set()
    return {"message": "Cancellation requested"}


@router.get("/status")
def get_geocode_status():
    """Return current geocoding state."""
    # Bug 1: take a snapshot under _state_lock to avoid torn reads
    with _state_lock:
        snapshot = dict(_geocode_state)

    total = snapshot["total"]
    done = snapshot["done"]
    pct = round((done / total) * 100, 1) if total > 0 else 0.0

    remaining = total - done
    eta_seconds = round(remaining * _MIN_INTERVAL) if snapshot["running"] else None

    return {
        "running": snapshot["running"],
        "run_id": snapshot["run_id"],
        "total": total,
        "done": done,
        "succeeded": snapshot["succeeded"],
        "failed": snapshot["failed"],
        "pct": pct,
        "started_at": snapshot["started_at"],
        "eta_seconds": eta_seconds,
    }


@router.get("/runs")
def list_geocode_runs(
    conn: Annotated[sqlite3.Connection, Depends(get_db)],
    limit: int = Query(default=20, ge=1, le=100),  # Bug 7: bounded limit
):
    """Return past geocoding runs, newest first."""
    return get_geocode_runs(conn, limit=limit)


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


# Bug 3: _startup_cleanup() is NO LONGER called at module import time.
# It is called from the FastAPI lifespan handler in api/main.py instead.
