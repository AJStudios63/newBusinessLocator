"""Leads API endpoints."""

from __future__ import annotations

import csv
import io
import math
from typing import Annotated

from fastapi import APIRouter, Depends, Query, HTTPException, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import sqlite3

from api.dependencies import get_db
from db.queries import (
    get_leads,
    get_lead,
    update_stage,
    search_leads,
    get_leads_by_batch,
    update_lead_fields,
    soft_delete_leads,
    bulk_update_county,
    find_duplicates,
    get_duplicate_suggestions,
    get_duplicate_suggestion_count,
    update_duplicate_suggestion,
    merge_leads,
    count_leads,
    count_search_leads,
)

router = APIRouter(prefix="/api/leads", tags=["leads"])

VALID_STAGES = ["New", "Qualified", "Contacted", "Follow-up", "Closed-Won", "Closed-Lost"]
VALID_BUSINESS_TYPES = ["restaurant", "bar", "retail", "salon", "cafe", "bakery", "gym", "spa", "other"]


class LeadFieldUpdate(BaseModel):
    """Request body for updating lead fields."""
    business_name: str | None = None
    address: str | None = None
    city: str | None = None
    county: str | None = None
    zip_code: str | None = None
    business_type: str | None = None
    stage: str | None = None
    note: str | None = None


@router.get("")
def list_leads(
    conn: Annotated[sqlite3.Connection, Depends(get_db)],
    q: str | None = None,
    stage: str | None = None,
    county: str | None = None,
    min_score: Annotated[int | None, Query(alias="minScore")] = None,
    max_score: Annotated[int | None, Query(alias="maxScore")] = None,
    sort: str = "pos_score",
    limit: int = 50,
    page: int = 1,
    page_size: Annotated[int | None, Query(alias="pageSize")] = None,
):
    """List leads with optional filters and pagination.

    Use q parameter for full-text search.
    Pagination: use page (1-indexed) and pageSize parameters.
    The limit parameter is supported for backwards compatibility but pageSize takes precedence.
    """
    # Validate pagination parameters
    if page < 1:
        raise HTTPException(status_code=400, detail="page must be >= 1")

    # Use pageSize if provided, otherwise fall back to limit
    effective_limit = page_size if page_size is not None else limit

    if effective_limit < 1:
        raise HTTPException(status_code=400, detail="pageSize must be >= 1")

    offset = (page - 1) * effective_limit

    try:
        if q and q.strip():
            # Full-text search mode
            rows = search_leads(conn, q, limit=effective_limit, offset=offset)
            total = count_search_leads(conn, q)
        else:
            # Regular filtered list
            rows = get_leads(
                conn,
                stage=stage,
                county=county,
                min_score=min_score,
                max_score=max_score,
                sort=sort,
                limit=effective_limit,
                offset=offset,
            )
            total = count_leads(
                conn,
                stage=stage,
                county=county,
                min_score=min_score,
                max_score=max_score,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    total_pages = max(1, math.ceil(total / effective_limit)) if effective_limit > 0 else 1

    return {
        "leads": rows,
        "count": len(rows),
        "total": total,
        "page": page,
        "pageSize": effective_limit,
        "totalPages": total_pages,
    }


@router.get("/export")
def export_leads(
    conn: Annotated[sqlite3.Connection, Depends(get_db)],
    stage: str | None = None,
    county: str | None = None,
    min_score: Annotated[int | None, Query(alias="minScore")] = None,
    max_score: Annotated[int | None, Query(alias="maxScore")] = None,
):
    """Export filtered leads as CSV download."""
    rows = get_leads(
        conn,
        stage=stage,
        county=county,
        min_score=min_score,
        max_score=max_score,
        limit=10000,
    )

    if not rows:
        raise HTTPException(status_code=404, detail="No leads match the filters")

    fieldnames = [
        "id", "fingerprint", "business_name", "business_type", "raw_type",
        "address", "city", "state", "zip_code", "county", "license_date",
        "pos_score", "stage", "source_url", "source_type", "source_batch_id",
        "notes", "created_at", "updated_at", "contacted_at", "closed_at",
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


@router.get("/batch/{batch_id}")
def get_batch_leads(
    batch_id: str,
    conn: Annotated[sqlite3.Connection, Depends(get_db)],
):
    """Get all leads from the same extraction batch."""
    rows = get_leads_by_batch(conn, batch_id)
    return {"leads": rows, "count": len(rows), "batch_id": batch_id}


# ---------------------------------------------------------------------------
# Duplicate Detection (must be before /{lead_id} to avoid route conflicts)
# ---------------------------------------------------------------------------


class MergeRequest(BaseModel):
    """Request body for merging leads."""
    keep_id: int
    merge_id: int
    field_choices: dict | None = None
    suggestion_id: int | None = None


@router.get("/duplicates/count")
def get_duplicates_count(
    conn: Annotated[sqlite3.Connection, Depends(get_db)],
    status: str = "pending",
):
    """Get count of duplicate suggestions."""
    count = get_duplicate_suggestion_count(conn, status)
    return {"count": count, "status": status}


@router.get("/duplicates")
def list_duplicates(
    conn: Annotated[sqlite3.Connection, Depends(get_db)],
    status: str = "pending",
    limit: int = 20,
):
    """List duplicate suggestions with full lead data."""
    suggestions = get_duplicate_suggestions(conn, status, limit)
    return {"suggestions": suggestions, "count": len(suggestions)}


@router.post("/duplicates/scan")
def scan_for_duplicates(
    conn: Annotated[sqlite3.Connection, Depends(get_db)],
    threshold: float = 0.7,
    limit: int = 100,
):
    """Scan for new duplicate suggestions."""
    count = find_duplicates(conn, threshold, limit)
    return {"new_suggestions": count, "threshold": threshold}


@router.patch("/duplicates/{suggestion_id}")
def update_suggestion_status(
    suggestion_id: int,
    status: str,
    conn: Annotated[sqlite3.Connection, Depends(get_db)],
):
    """Update a duplicate suggestion status (merged or dismissed)."""
    if status not in ("merged", "dismissed"):
        raise HTTPException(status_code=400, detail="Status must be 'merged' or 'dismissed'")

    success = update_duplicate_suggestion(conn, suggestion_id, status)
    if not success:
        raise HTTPException(status_code=404, detail=f"Suggestion {suggestion_id} not found")

    return {"id": suggestion_id, "status": status}


@router.post("/merge")
def merge_lead_pair(
    conn: Annotated[sqlite3.Connection, Depends(get_db)],
    request: MergeRequest = Body(...),
):
    """Merge two leads into one."""
    result = merge_leads(conn, request.keep_id, request.merge_id, request.field_choices)
    if result is None:
        raise HTTPException(status_code=404, detail="One or both leads not found")

    # Update suggestion status if provided
    if request.suggestion_id:
        update_duplicate_suggestion(conn, request.suggestion_id, "merged")

    return result


# ---------------------------------------------------------------------------
# Single Lead Operations (/{lead_id} must come after specific routes)
# ---------------------------------------------------------------------------


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
    body: LeadFieldUpdate = Body(default=None),
    stage: str | None = Query(default=None),
    note: str | None = Query(default=None),
):
    """Update a lead's fields, stage, and/or add a note.

    Supports both query params (for backwards compatibility) and JSON body.
    Editable fields: business_name, address, city, county, zip_code, business_type
    """
    # Merge query params with body if provided
    field_updates = {}
    stage_to_set = stage
    note_to_add = note

    if body:
        if body.business_name is not None:
            field_updates["business_name"] = body.business_name
        if body.address is not None:
            field_updates["address"] = body.address
        if body.city is not None:
            field_updates["city"] = body.city
        if body.county is not None:
            field_updates["county"] = body.county
        if body.zip_code is not None:
            field_updates["zip_code"] = body.zip_code
        if body.business_type is not None:
            if body.business_type not in VALID_BUSINESS_TYPES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid business_type. Must be one of: {VALID_BUSINESS_TYPES}"
                )
            field_updates["business_type"] = body.business_type
        if body.stage is not None:
            stage_to_set = body.stage
        if body.note is not None:
            note_to_add = body.note

    # Validate stage if provided
    if stage_to_set is not None and stage_to_set not in VALID_STAGES:
        raise HTTPException(status_code=400, detail=f"Invalid stage. Must be one of: {VALID_STAGES}")

    # Check lead exists
    lead = get_lead(conn, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found")

    # Apply field updates if any
    if field_updates:
        try:
            update_lead_fields(conn, lead_id, field_updates)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    # Apply stage/note updates if any
    if stage_to_set is not None or note_to_add is not None:
        try:
            effective_stage = stage_to_set if stage_to_set is not None else lead["stage"]
            update_stage(conn, lead_id, effective_stage, note_to_add)
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
    ids: Annotated[list[int], Query()] = [],
    stage: str | None = None,
    county: str | None = None,
):
    """Bulk update stage and/or county for multiple leads."""
    if not ids:
        raise HTTPException(status_code=400, detail="Must provide at least one lead ID")

    if stage is None and county is None:
        raise HTTPException(status_code=400, detail="Must provide stage or county")

    if stage is not None and stage not in VALID_STAGES:
        raise HTTPException(status_code=400, detail=f"Invalid stage. Must be one of: {VALID_STAGES}")

    updated = []
    errors = []

    # Handle stage updates
    if stage is not None:
        for lead_id in ids:
            try:
                update_stage(conn, lead_id, stage)
                updated.append(lead_id)
            except ValueError as exc:
                errors.append({"id": lead_id, "error": str(exc)})

    # Handle county updates
    if county is not None:
        try:
            county_updated = bulk_update_county(conn, ids, county)
            if not updated:  # Only set if stage didn't already populate
                updated = county_updated
        except Exception as exc:
            errors.append({"error": str(exc)})

    return {"updated": updated, "errors": errors}


@router.delete("/bulk")
def bulk_delete_leads(
    conn: Annotated[sqlite3.Connection, Depends(get_db)],
    ids: Annotated[list[int], Query()] = [],
):
    """Soft-delete multiple leads."""
    if not ids:
        raise HTTPException(status_code=400, detail="Must provide at least one lead ID")

    try:
        deleted = soft_delete_leads(conn, ids)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    errors = [{"id": lid, "error": "Not found or already deleted"} for lid in ids if lid not in deleted]

    return {"deleted": deleted, "errors": errors}
