"""Kanban API endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
import sqlite3

from api.dependencies import get_db

router = APIRouter(prefix="/api/kanban", tags=["kanban"])

STAGES = ["New", "Qualified", "Contacted", "Follow-up", "Closed-Won", "Closed-Lost"]

# Max leads per stage column to prevent memory issues
MAX_PER_STAGE = 100


@router.get("")
def get_kanban_board(
    conn: Annotated[sqlite3.Connection, Depends(get_db)],
    county: str | None = None,
    min_score: int | None = None,
):
    """Get leads grouped by stage for kanban view.

    Returns accurate counts per stage via SQL GROUP BY, plus up to
    MAX_PER_STAGE leads per column (sorted by pos_score DESC).
    """
    # Build filter clauses
    clauses = ["deleted_at IS NULL"]
    params: dict = {}
    if county:
        clauses.append("county = :county")
        params["county"] = county
    if min_score is not None:
        clauses.append("pos_score >= :min_score")
        params["min_score"] = min_score

    where = " AND ".join(clauses)

    # Get accurate counts per stage
    count_rows = conn.execute(
        f"SELECT stage, COUNT(*) as cnt FROM leads WHERE {where} GROUP BY stage;",
        params,
    ).fetchall()
    stage_counts = {row["stage"]: row["cnt"] for row in count_rows}

    # Initialize all stages
    grouped = {stage: [] for stage in STAGES}
    counts = {stage: stage_counts.get(stage, 0) for stage in STAGES}

    # Fetch top leads per stage
    for stage in STAGES:
        stage_params = {**params, "stage": stage, "limit": MAX_PER_STAGE}
        rows = conn.execute(
            f"SELECT * FROM leads WHERE {where} AND stage = :stage "
            f"ORDER BY pos_score DESC LIMIT :limit;",
            stage_params,
        ).fetchall()
        grouped[stage] = [dict(row) for row in rows]

    return {"stages": STAGES, "columns": grouped, "counts": counts}
