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
