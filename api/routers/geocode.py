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

        last_request_time = 0.0

        for lead in leads:
            # Rate limit
            elapsed = time.monotonic() - last_request_time
            if elapsed < _MIN_INTERVAL:
                time.sleep(_MIN_INTERVAL - elapsed)

            lat, lon = geocode_lead(lead)
            last_request_time = time.monotonic()

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
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM leads "
            "WHERE deleted_at IS NULL AND (latitude IS NULL OR longitude IS NULL);"
        ).fetchone()
        total = row["cnt"] if row else 0

        run_id = insert_geocode_run(conn, total=total)

        _geocode_state["running"] = True
        _geocode_state["run_id"] = run_id
        _geocode_state["total"] = total
        _geocode_state["done"] = 0
        _geocode_state["succeeded"] = 0
        _geocode_state["failed"] = 0

        run_row = conn.execute(
            "SELECT started_at FROM geocode_runs WHERE id = ?;", (run_id,)
        ).fetchone()
        if run_row:
            _geocode_state["started_at"] = run_row["started_at"]

        # Get the actual DB path from the connection (works for both prod and tests)
        db_list_row = conn.execute("PRAGMA database_list;").fetchone()
        actual_db_path = db_list_row[2] if db_list_row and db_list_row[2] else str(DB_PATH)

        thread = threading.Thread(
            target=_geocode_thread,
            args=(run_id, actual_db_path),
            daemon=True,
        )
        thread.start()

    except Exception:
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
