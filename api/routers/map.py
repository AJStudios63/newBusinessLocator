"""Map API endpoint — serves geocoded leads for the map view."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
import sqlite3

from api.dependencies import get_db
from db.queries import get_map_leads

router = APIRouter(prefix="/api/map", tags=["map"])


@router.get("")
def get_map_data(
    conn: Annotated[sqlite3.Connection, Depends(get_db)],
    stage: str | None = None,
    county: str | None = None,
    min_score: Annotated[int | None, Query(alias="minScore")] = None,
    max_score: Annotated[int | None, Query(alias="maxScore")] = None,
    business_type: Annotated[str | None, Query(alias="businessType")] = None,
):
    """Return geocoded leads for map display."""
    return get_map_leads(
        conn,
        stage=stage,
        county=county,
        min_score=min_score,
        max_score=max_score,
        business_type=business_type,
    )
