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
