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
