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
