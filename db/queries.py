"""Named SQL query helpers for newBusinessLocator."""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from typing import Sequence

from utils.dedup import normalize_name

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Leads – write
# ---------------------------------------------------------------------------

_INSERT_LEAD_COLUMNS = (
    "fingerprint",
    "business_name",
    "business_type",
    "raw_type",
    "address",
    "city",
    "state",
    "zip_code",
    "county",
    "latitude",
    "longitude",
    "license_date",
    "pos_score",
    "stage",
    "source_url",
    "source_type",
    "source_batch_id",
    "notes",
)

_INSERT_LEAD_SQL = (
    "INSERT OR IGNORE INTO leads ("
    + ", ".join(_INSERT_LEAD_COLUMNS)
    + ") VALUES ("
    + ", ".join(f":{col}" for col in _INSERT_LEAD_COLUMNS)
    + ");"
)


def insert_lead(conn: sqlite3.Connection, lead: dict, commit: bool = True) -> None:
    """Insert a single lead row; silently ignored if fingerprint already exists."""
    conn.execute(_INSERT_LEAD_SQL, lead)
    if commit:
        conn.commit()


# ---------------------------------------------------------------------------
# Leads – read
# ---------------------------------------------------------------------------


def _rows_to_dicts(rows: Sequence[sqlite3.Row]) -> list[dict]:
    """Convert a list of sqlite3.Row objects to plain dicts."""
    return [dict(row) for row in rows]


def _build_lead_filter_clauses(
    stage: str | None = None,
    county: str | None = None,
    min_score: int | None = None,
    max_score: int | None = None,
    business_type: str | None = None,
) -> tuple[list[str], dict]:
    """Build WHERE clause components for lead filtering.

    Returns
    -------
    tuple of (clauses, params) where:
        clauses : list of SQL WHERE clause conditions
        params  : dict of named parameters for the query
    """
    clauses: list[str] = ["deleted_at IS NULL"]
    params: dict = {}

    if stage is not None:
        clauses.append("stage = :stage")
        params["stage"] = stage
    if county is not None:
        clauses.append("county = :county")
        params["county"] = county
    if min_score is not None:
        clauses.append("pos_score >= :min_score")
        params["min_score"] = min_score
    if max_score is not None:
        clauses.append("pos_score <= :max_score")
        params["max_score"] = max_score
    if business_type is not None:
        clauses.append("business_type = :business_type")
        params["business_type"] = business_type

    return clauses, params


def get_leads(
    conn: sqlite3.Connection,
    stage: str | None = None,
    county: str | None = None,
    min_score: int | None = None,
    max_score: int | None = None,
    sort: str = "pos_score",
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """Return leads, optionally filtered, ordered by *sort* DESC.

    Parameters
    ----------
    conn       : open sqlite3 connection
    stage      : filter by stage value (optional)
    county     : filter by county value (optional)
    min_score  : minimum pos_score, inclusive (optional)
    max_score  : maximum pos_score, inclusive (optional)
    sort       : column name to ORDER BY (default 'pos_score')
    limit      : maximum number of rows returned (default 100)
    offset     : number of rows to skip for pagination (default 0)
    """
    clauses, params = _build_lead_filter_clauses(stage, county, min_score, max_score)

    where = " WHERE " + " AND ".join(clauses)

    # Guard *sort* against SQL injection – only allow identifiers that exist
    # in the leads table column list.
    _ALLOWED_SORT_COLUMNS = {
        "id", "fingerprint", "business_name", "business_type", "raw_type",
        "address", "city", "state", "zip_code", "county", "license_date",
        "pos_score", "stage", "source_url", "source_type", "source_batch_id",
        "notes", "created_at", "updated_at", "contacted_at", "closed_at",
        "latitude", "longitude",
    }
    if sort not in _ALLOWED_SORT_COLUMNS:
        raise ValueError(f"Invalid sort column: {sort}")

    sql = f"SELECT * FROM leads{where} ORDER BY {sort} DESC LIMIT :limit OFFSET :offset;"
    params["limit"] = limit
    params["offset"] = offset

    rows = conn.execute(sql, params).fetchall()
    return _rows_to_dicts(rows)


def count_leads(
    conn: sqlite3.Connection,
    stage: str | None = None,
    county: str | None = None,
    min_score: int | None = None,
    max_score: int | None = None,
) -> int:
    """Return the count of leads matching the filters.

    Parameters
    ----------
    conn       : open sqlite3 connection
    stage      : filter by stage value (optional)
    county     : filter by county value (optional)
    min_score  : minimum pos_score, inclusive (optional)
    max_score  : maximum pos_score, inclusive (optional)
    """
    clauses, params = _build_lead_filter_clauses(stage, county, min_score, max_score)

    where = " WHERE " + " AND ".join(clauses)

    sql = f"SELECT COUNT(*) AS cnt FROM leads{where};"
    row = conn.execute(sql, params).fetchone()
    return row["cnt"] if row else 0


def get_lead(conn: sqlite3.Connection, lead_id: int) -> dict | None:
    """Return a single lead as a dict, or None if not found."""
    row = conn.execute("SELECT * FROM leads WHERE id = ? AND deleted_at IS NULL;", (lead_id,)).fetchone()
    return dict(row) if row else None


def _sanitize_fts_query(query: str) -> str:
    """Sanitize a user query for safe use in an FTS5 MATCH expression.

    Strips characters that have special meaning in FTS5 syntax
    (parentheses, braces, colons, asterisks, carets, plus, tilde) and
    escapes double quotes by doubling them.  The cleaned tokens are
    wrapped in a quoted phrase with a trailing prefix-match wildcard.

    Returns an empty string if no usable tokens remain.
    """
    stripped = query.strip()
    if not stripped:
        return ""
    # Remove FTS5 special characters
    cleaned = ""
    for ch in stripped:
        if ch in '(){}*:^~+':
            cleaned += " "
        elif ch == '"':
            cleaned += '""'
        else:
            cleaned += ch
    cleaned = " ".join(cleaned.split())  # collapse whitespace
    if not cleaned:
        return ""
    return f'"{cleaned}"*'


def search_leads(
    conn: sqlite3.Connection,
    query: str,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Full-text search on business_name, city, address using FTS5.

    Parameters
    ----------
    conn   : open sqlite3 connection
    query  : search query string
    limit  : maximum number of rows returned (default 50)
    offset : number of rows to skip for pagination (default 0)

    Returns
    -------
    list of leads matching the search query, ordered by relevance
    """
    if not query or not query.strip():
        return []

    fts_query = _sanitize_fts_query(query)
    if not fts_query:
        return []

    sql = """
        SELECT leads.*
        FROM leads_fts
        JOIN leads ON leads_fts.rowid = leads.id
        WHERE leads_fts MATCH :query
          AND leads.deleted_at IS NULL
        ORDER BY rank
        LIMIT :limit OFFSET :offset;
    """
    rows = conn.execute(sql, {"query": fts_query, "limit": limit, "offset": offset}).fetchall()
    return _rows_to_dicts(rows)


def count_search_leads(
    conn: sqlite3.Connection,
    query: str,
) -> int:
    """Count results from full-text search on business_name, city, address using FTS5.

    Parameters
    ----------
    conn  : open sqlite3 connection
    query : search query string

    Returns
    -------
    count of leads matching the search query
    """
    if not query or not query.strip():
        return 0

    fts_query = _sanitize_fts_query(query)
    if not fts_query:
        return 0

    sql = """
        SELECT COUNT(*) AS cnt
        FROM leads_fts
        JOIN leads ON leads_fts.rowid = leads.id
        WHERE leads_fts MATCH :query
          AND leads.deleted_at IS NULL;
    """
    row = conn.execute(sql, {"query": fts_query}).fetchone()
    return row["cnt"] if row else 0


def get_leads_by_batch(conn: sqlite3.Connection, batch_id: str) -> list[dict]:
    """Return all leads that share the same source_batch_id."""
    if not batch_id:
        return []
    rows = conn.execute(
        "SELECT * FROM leads WHERE source_batch_id = ? AND deleted_at IS NULL ORDER BY id;",
        (batch_id,),
    ).fetchall()
    return _rows_to_dicts(rows)


def get_map_leads(
    conn: sqlite3.Connection,
    stage: str | None = None,
    county: str | None = None,
    min_score: int | None = None,
    max_score: int | None = None,
    business_type: str | None = None,
    limit: int = 2000,
) -> dict:
    """Return geocoded leads for map display with lightweight columns.

    Parameters
    ----------
    conn          : open sqlite3 connection
    stage         : filter by stage value (optional)
    county        : filter by county value (optional)
    min_score     : minimum pos_score, inclusive (optional)
    max_score     : maximum pos_score, inclusive (optional)
    business_type : filter by business_type value (optional)
    limit         : maximum number of leads returned (default 2000)

    Returns
    -------
    dict with keys:
        leads                 : list of geocoded lead dicts with lightweight columns
        total_geocoded        : count of leads WITH coordinates matching filters
        total_without_coords  : count of leads WITHOUT coordinates matching filters
    """
    # Build filter clauses
    clauses, params = _build_lead_filter_clauses(
        stage=stage,
        county=county,
        min_score=min_score,
        max_score=max_score,
        business_type=business_type,
    )

    # Count geocoded leads
    geocoded_clauses = clauses + ["latitude IS NOT NULL", "longitude IS NOT NULL"]
    geocoded_where = " WHERE " + " AND ".join(geocoded_clauses)
    geocoded_sql = f"SELECT COUNT(*) AS cnt FROM leads{geocoded_where};"
    geocoded_row = conn.execute(geocoded_sql, params).fetchone()
    total_geocoded = geocoded_row["cnt"] if geocoded_row else 0

    # Count leads without coordinates
    non_geocoded_clauses = clauses + ["(latitude IS NULL OR longitude IS NULL)"]
    non_geocoded_where = " WHERE " + " AND ".join(non_geocoded_clauses)
    non_geocoded_sql = f"SELECT COUNT(*) AS cnt FROM leads{non_geocoded_where};"
    non_geocoded_row = conn.execute(non_geocoded_sql, params).fetchone()
    total_without_coords = non_geocoded_row["cnt"] if non_geocoded_row else 0

    # Fetch geocoded leads with lightweight columns
    params["limit"] = limit
    fetch_clauses = clauses + ["latitude IS NOT NULL", "longitude IS NOT NULL"]
    fetch_where = " WHERE " + " AND ".join(fetch_clauses)
    fetch_sql = f"""
        SELECT
            id,
            business_name,
            business_type,
            city,
            county,
            pos_score,
            stage,
            latitude,
            longitude
        FROM leads{fetch_where}
        ORDER BY pos_score DESC
        LIMIT :limit;
    """
    rows = conn.execute(fetch_sql, params).fetchall()
    leads = _rows_to_dicts(rows)

    return {
        "leads": leads,
        "total_geocoded": total_geocoded,
        "total_without_coords": total_without_coords,
    }


# ---------------------------------------------------------------------------
# Lead field editing
# ---------------------------------------------------------------------------


_EDITABLE_FIELDS = {
    "business_name",
    "address",
    "city",
    "county",
    "zip_code",
    "business_type",
}


def update_lead_fields(
    conn: sqlite3.Connection,
    lead_id: int,
    fields: dict,
) -> dict | None:
    """Update editable fields on a lead and return the updated lead.

    Parameters
    ----------
    conn    : open sqlite3 connection
    lead_id : ID of the lead to update
    fields  : dict of field_name -> new_value (only editable fields allowed)

    Returns
    -------
    The updated lead as a dict, or None if lead not found
    """
    # Filter to only allowed fields
    updates = {k: v for k, v in fields.items() if k in _EDITABLE_FIELDS}
    if not updates:
        return get_lead(conn, lead_id)

    set_clauses = [f"{col} = :{col}" for col in updates]
    set_clauses.append("updated_at = datetime('now')")
    updates["lead_id"] = lead_id

    sql = f"UPDATE leads SET {', '.join(set_clauses)} WHERE id = :lead_id AND deleted_at IS NULL;"

    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(sql, updates)
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    return get_lead(conn, lead_id)


# ---------------------------------------------------------------------------
# Bulk operations
# ---------------------------------------------------------------------------


def soft_delete_leads(conn: sqlite3.Connection, ids: list[int]) -> list[int]:
    """Soft-delete leads by setting deleted_at timestamp.

    Returns list of IDs that were actually deleted.
    """
    if not ids:
        return []

    deleted = []
    try:
        conn.execute("BEGIN IMMEDIATE")
        for lead_id in ids:
            cur = conn.execute(
                "UPDATE leads SET deleted_at = datetime('now'), updated_at = datetime('now') "
                "WHERE id = ? AND deleted_at IS NULL;",
                (lead_id,),
            )
            if cur.rowcount > 0:
                deleted.append(lead_id)
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    return deleted


def bulk_update_county(conn: sqlite3.Connection, ids: list[int], county: str) -> list[int]:
    """Update county for multiple leads.

    Returns list of IDs that were actually updated.
    """
    if not ids:
        return []

    updated = []
    try:
        conn.execute("BEGIN IMMEDIATE")
        for lead_id in ids:
            cur = conn.execute(
                "UPDATE leads SET county = ?, updated_at = datetime('now') "
                "WHERE id = ? AND deleted_at IS NULL;",
                (county, lead_id),
            )
            if cur.rowcount > 0:
                updated.append(lead_id)
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    return updated


# ---------------------------------------------------------------------------
# Stage management
# ---------------------------------------------------------------------------


def update_stage(
    conn: sqlite3.Connection,
    lead_id: int,
    new_stage: str,
    note: str | None = None,
) -> None:
    """Transition a lead to *new_stage*, record history, and optionally append a note.

    * If the lead is already in *new_stage* the function returns immediately.
    * Inserts a row into stage_history.
    * Sets contacted_at / closed_at timestamps where appropriate.
    * Appends *note* (separated by a newline) to the existing notes field when provided.
    * Commits the transaction.
    """
    # -- current stage ---------------------------------------------------
    row = conn.execute(
        "SELECT stage FROM leads WHERE id = ?;", (lead_id,)
    ).fetchone()
    if row is None:
        raise ValueError(f"No lead with id={lead_id}")

    old_stage: str | None = row["stage"]
    if old_stage == new_stage:
        if note is None:
            return  # nothing to do
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "UPDATE leads SET "
                "notes = COALESCE(notes || char(10), '') || ?, "
                "updated_at = datetime('now') "
                "WHERE id = ?;",
                (note, lead_id),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        return

    try:
        conn.execute("BEGIN IMMEDIATE")

        # -- history record --------------------------------------------------
        conn.execute(
            "INSERT INTO stage_history (lead_id, old_stage, new_stage) VALUES (?, ?, ?);",
            (lead_id, old_stage, new_stage),
        )

        # -- main UPDATE -----------------------------------------------------
        conn.execute(
            "UPDATE leads SET stage = ?, updated_at = datetime('now') WHERE id = ?;",
            (new_stage, lead_id),
        )

        # contacted_at – set only on first transition to 'Contacted'
        if new_stage == "Contacted":
            conn.execute(
                "UPDATE leads SET contacted_at = datetime('now') "
                "WHERE id = ? AND contacted_at IS NULL;",
                (lead_id,),
            )

        # closed_at – set only on first transition to a closed stage
        if new_stage in ("Closed-Won", "Closed-Lost"):
            conn.execute(
                "UPDATE leads SET closed_at = datetime('now') "
                "WHERE id = ? AND closed_at IS NULL;",
                (lead_id,),
            )

        # -- optional note ---------------------------------------------------
        if note is not None:
            conn.execute(
                "UPDATE leads SET "
                "notes = COALESCE(notes || char(10), '') || ?, "
                "updated_at = datetime('now') "
                "WHERE id = ?;",
                (note, lead_id),
            )

        conn.commit()
    except Exception:
        conn.rollback()
        raise


def get_stage_history(conn: sqlite3.Connection, lead_id: int) -> list[dict]:
    """Return all stage-change records for *lead_id*, oldest first."""
    rows = conn.execute(
        "SELECT * FROM stage_history WHERE lead_id = ? ORDER BY changed_at ASC;",
        (lead_id,),
    ).fetchall()
    return _rows_to_dicts(rows)


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


def get_stats(conn: sqlite3.Connection) -> dict:
    """Aggregate statistics across the leads and pipeline_runs tables.

    Returns
    -------
    dict with keys:
        by_stage   : dict[str, int]  – stage -> row count
        by_county  : dict[str, int]  – county -> row count
        by_type    : dict[str, int]  – business_type -> row count
        avg_score  : float           – average pos_score (0.0 when no leads)
        total_leads: int
        last_run   : dict | None     – most recent pipeline_runs row as a dict
    """
    # by_stage (exclude deleted)
    by_stage = {
        row["stage"]: row["cnt"]
        for row in conn.execute(
            "SELECT stage, COUNT(*) AS cnt FROM leads WHERE deleted_at IS NULL GROUP BY stage;"
        ).fetchall()
    }

    # by_county (exclude deleted)
    by_county = {
        row["county"]: row["cnt"]
        for row in conn.execute(
            "SELECT county, COUNT(*) AS cnt FROM leads WHERE deleted_at IS NULL GROUP BY county;"
        ).fetchall()
    }

    # by_type (exclude deleted)
    by_type = {
        row["business_type"]: row["cnt"]
        for row in conn.execute(
            "SELECT business_type, COUNT(*) AS cnt FROM leads WHERE deleted_at IS NULL GROUP BY business_type;"
        ).fetchall()
    }

    # avg_score (exclude deleted)
    avg_row = conn.execute(
        "SELECT COALESCE(AVG(pos_score), 0.0) AS avg FROM leads WHERE deleted_at IS NULL;"
    ).fetchone()
    avg_score: float = float(avg_row["avg"])

    # total_leads (exclude deleted)
    total_row = conn.execute("SELECT COUNT(*) AS cnt FROM leads WHERE deleted_at IS NULL;").fetchone()
    total_leads: int = int(total_row["cnt"])

    # last_run
    last_run_row = conn.execute(
        "SELECT * FROM pipeline_runs ORDER BY run_started_at DESC LIMIT 1;"
    ).fetchone()
    last_run: dict | None = dict(last_run_row) if last_run_row else None

    return {
        "by_stage": by_stage,
        "by_county": by_county,
        "by_type": by_type,
        "avg_score": avg_score,
        "total_leads": total_leads,
        "last_run": last_run,
    }


# ---------------------------------------------------------------------------
# Seen URLs
# ---------------------------------------------------------------------------


def get_seen_urls(conn: sqlite3.Connection) -> set[str]:
    """Return every URL in seen_urls as a plain set of strings."""
    rows = conn.execute("SELECT url FROM seen_urls;").fetchall()
    return {row[0] for row in rows}


def insert_seen_url(
    conn: sqlite3.Connection,
    url: str,
    county: str | None = None,
    commit: bool = True,
) -> None:
    """Insert a URL into seen_urls; silently ignored if already present."""
    conn.execute(
        "INSERT OR IGNORE INTO seen_urls (url, county) VALUES (?, ?);",
        (url, county),
    )
    if commit:
        conn.commit()


# ---------------------------------------------------------------------------
# Search cache
# ---------------------------------------------------------------------------


def get_cached_search(
    conn: sqlite3.Connection,
    query: str,
    ttl_hours: int = 24,
) -> list[dict] | None:
    """Return cached search results if fresh enough, else None."""
    query_hash = hashlib.sha256(query.encode("utf-8")).hexdigest()[:32]
    row = conn.execute(
        "SELECT results_json, cached_at FROM search_cache "
        "WHERE query_hash = ? AND cached_at > datetime('now', ?);",
        (query_hash, f"-{ttl_hours} hours"),
    ).fetchone()
    if row:
        try:
            return json.loads(row["results_json"])
        except (json.JSONDecodeError, TypeError):
            return None
    return None


def set_cached_search(
    conn: sqlite3.Connection,
    query: str,
    results: list[dict],
    commit: bool = True,
) -> None:
    """Store search results in cache."""
    query_hash = hashlib.sha256(query.encode("utf-8")).hexdigest()[:32]
    conn.execute(
        "INSERT OR REPLACE INTO search_cache (query_hash, query_text, results_json) "
        "VALUES (?, ?, ?);",
        (query_hash, query, json.dumps(results)),
    )
    if commit:
        conn.commit()


# ---------------------------------------------------------------------------
# Pipeline runs
# ---------------------------------------------------------------------------


def insert_pipeline_run(conn: sqlite3.Connection, run_started_at: str) -> int:
    """Create a new pipeline_runs row with status='running' and return its id."""
    cur = conn.execute(
        "INSERT INTO pipeline_runs (run_started_at, status) VALUES (?, 'running');",
        (run_started_at,),
    )
    conn.commit()
    return cur.lastrowid


def update_pipeline_run(
    conn: sqlite3.Connection,
    run_id: int,
    status: str,
    leads_found: int,
    leads_new: int,
    leads_dupes: int,
    error_message: str | None = None,
    sources_queried: str | None = None,
    credits_used: int = 0,
    commit: bool = True,
) -> None:
    """Finalise a pipeline run row with results and set run_finished_at to now."""
    conn.execute(
        "UPDATE pipeline_runs SET "
        "run_finished_at   = datetime('now'), "
        "status            = ?, "
        "leads_found       = ?, "
        "leads_new         = ?, "
        "leads_dupes       = ?, "
        "credits_used      = ?, "
        "error_message     = ?, "
        "sources_queried   = ? "
        "WHERE id = ?;",
        (status, leads_found, leads_new, leads_dupes, credits_used, error_message, sources_queried, run_id),
    )
    if commit:
        conn.commit()


def get_pipeline_runs(conn: sqlite3.Connection, limit: int = 10) -> list[dict]:
    """Return the most recent pipeline runs, newest first."""
    rows = conn.execute(
        "SELECT * FROM pipeline_runs ORDER BY run_started_at DESC LIMIT ?;",
        (limit,),
    ).fetchall()
    return _rows_to_dicts(rows)


# ---------------------------------------------------------------------------
# Duplicate Detection
# ---------------------------------------------------------------------------


def _normalize_name(name: str | None) -> str:
    """Normalize a business name for comparison."""
    if not name:
        return ""
    return normalize_name(name)


def _levenshtein_distance(s1: str, s2: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def _compute_similarity(lead_a: dict, lead_b: dict) -> float:
    """Compute similarity score between two leads (0-1)."""
    name_a = _normalize_name(lead_a.get("business_name"))
    name_b = _normalize_name(lead_b.get("business_name"))

    if not name_a or not name_b:
        return 0.0

    max_len = max(len(name_a), len(name_b))
    if max_len == 0:
        return 0.0

    distance = _levenshtein_distance(name_a, name_b)
    name_sim = 1 - (distance / max_len)

    city_a = (lead_a.get("city") or "").lower().strip()
    city_b = (lead_b.get("city") or "").lower().strip()
    city_match = 1.0 if city_a and city_a == city_b else 0.0

    # Weighted: 70% name, 30% city
    return (name_sim * 0.7) + (city_match * 0.3)


def find_duplicates(
    conn: sqlite3.Connection,
    threshold: float = 0.7,
    limit: int = 100,
) -> int:
    """Scan for duplicate leads and insert suggestions.

    Parameters
    ----------
    conn      : open sqlite3 connection
    threshold : minimum similarity score to consider a duplicate (default 0.7)
    limit     : max number of new suggestions to create per run (default 100)

    Returns
    -------
    Number of new suggestions created.
    """
    # Get active leads
    rows = conn.execute(
        "SELECT id, business_name, city FROM leads WHERE deleted_at IS NULL ORDER BY id;"
    ).fetchall()
    leads = _rows_to_dicts(rows)

    # Get existing suggestions to avoid re-checking
    existing = set()
    for row in conn.execute(
        "SELECT lead_id_a, lead_id_b FROM duplicate_suggestions;"
    ).fetchall():
        existing.add((row[0], row[1]))
        existing.add((row[1], row[0]))

    suggestions = []
    for i, lead_a in enumerate(leads):
        for lead_b in leads[i + 1 :]:
            # Skip if already suggested
            if (lead_a["id"], lead_b["id"]) in existing:
                continue

            similarity = _compute_similarity(lead_a, lead_b)
            if similarity >= threshold:
                # Ensure consistent ordering (lower id first)
                id_a, id_b = min(lead_a["id"], lead_b["id"]), max(lead_a["id"], lead_b["id"])
                suggestions.append((id_a, id_b, similarity))

                if len(suggestions) >= limit:
                    break
        if len(suggestions) >= limit:
            break

    # Insert suggestions
    inserted = 0
    for id_a, id_b, score in suggestions:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO duplicate_suggestions (lead_id_a, lead_id_b, similarity_score) "
                "VALUES (?, ?, ?);",
                (id_a, id_b, score),
            )
            inserted += 1
        except Exception as exc:
            logger.warning(f"Failed to insert duplicate suggestion ({id_a}, {id_b}): {exc}")

    conn.commit()
    return inserted


def get_duplicate_suggestions(
    conn: sqlite3.Connection,
    status: str = "pending",
    limit: int = 20,
) -> list[dict]:
    """Get duplicate suggestions with full lead data via a single JOIN query.

    Returns list of dicts with keys: id, lead_a, lead_b, similarity_score, status, created_at
    """
    rows = conn.execute(
        """
        SELECT
            ds.id           AS ds_id,
            ds.similarity_score,
            ds.status       AS ds_status,
            ds.created_at   AS ds_created_at,
            la.*,
            lb.id           AS lb_id,
            lb.fingerprint  AS lb_fingerprint,
            lb.business_name AS lb_business_name,
            lb.business_type AS lb_business_type,
            lb.raw_type     AS lb_raw_type,
            lb.address      AS lb_address,
            lb.city         AS lb_city,
            lb.state        AS lb_state,
            lb.zip_code     AS lb_zip_code,
            lb.county       AS lb_county,
            lb.license_date AS lb_license_date,
            lb.pos_score    AS lb_pos_score,
            lb.stage        AS lb_stage,
            lb.source_url   AS lb_source_url,
            lb.source_type  AS lb_source_type,
            lb.source_batch_id AS lb_source_batch_id,
            lb.notes        AS lb_notes,
            lb.created_at   AS lb_created_at,
            lb.updated_at   AS lb_updated_at,
            lb.contacted_at AS lb_contacted_at,
            lb.closed_at    AS lb_closed_at,
            lb.deleted_at   AS lb_deleted_at
        FROM duplicate_suggestions ds
        JOIN leads la ON ds.lead_id_a = la.id AND la.deleted_at IS NULL
        JOIN leads lb ON ds.lead_id_b = lb.id AND lb.deleted_at IS NULL
        WHERE ds.status = ?
        ORDER BY ds.similarity_score DESC
        LIMIT ?;
        """,
        (status, limit),
    ).fetchall()

    _LEAD_COLS = [
        "id", "fingerprint", "business_name", "business_type", "raw_type",
        "address", "city", "state", "zip_code", "county", "license_date",
        "pos_score", "stage", "source_url", "source_type", "source_batch_id",
        "notes", "created_at", "updated_at", "contacted_at", "closed_at", "deleted_at",
    ]

    suggestions = []
    for row in rows:
        row_dict = dict(row)
        # lead_a comes from la.* (unprefixed columns)
        lead_a = {col: row_dict.get(col) for col in _LEAD_COLS}
        # lead_b comes from lb_ prefixed columns
        lead_b = {col: row_dict.get(f"lb_{col}") for col in _LEAD_COLS}

        suggestions.append({
            "id": row_dict["ds_id"],
            "lead_a": lead_a,
            "lead_b": lead_b,
            "similarity_score": row_dict["similarity_score"],
            "status": row_dict["ds_status"],
            "created_at": row_dict["ds_created_at"],
        })

    return suggestions


def get_duplicate_suggestion_count(conn: sqlite3.Connection, status: str = "pending") -> int:
    """Get count of duplicate suggestions with given status."""
    row = conn.execute(
        """
        SELECT COUNT(*) as cnt
        FROM duplicate_suggestions ds
        JOIN leads la ON ds.lead_id_a = la.id AND la.deleted_at IS NULL
        JOIN leads lb ON ds.lead_id_b = lb.id AND lb.deleted_at IS NULL
        WHERE ds.status = ?;
        """,
        (status,),
    ).fetchone()
    return row["cnt"] if row else 0


def update_duplicate_suggestion(
    conn: sqlite3.Connection,
    suggestion_id: int,
    status: str,
) -> bool:
    """Update the status of a duplicate suggestion.

    Parameters
    ----------
    conn          : open sqlite3 connection
    suggestion_id : ID of the suggestion to update
    status        : new status ('merged' or 'dismissed')

    Returns
    -------
    True if updated, False if not found.
    """
    cur = conn.execute(
        "UPDATE duplicate_suggestions SET status = ?, resolved_at = datetime('now') "
        "WHERE id = ?;",
        (status, suggestion_id),
    )
    conn.commit()
    return cur.rowcount > 0


def merge_leads(
    conn: sqlite3.Connection,
    keep_id: int,
    merge_id: int,
    field_choices: dict | None = None,
) -> dict | None:
    """Merge two leads, keeping one and soft-deleting the other.

    Parameters
    ----------
    conn          : open sqlite3 connection
    keep_id       : ID of the lead to keep
    merge_id      : ID of the lead to merge (will be soft-deleted)
    field_choices : optional dict of field names -> values to apply to kept lead

    Returns
    -------
    The merged lead as a dict, or None if either lead not found.
    """
    keep_lead = get_lead(conn, keep_id)
    merge_lead = get_lead(conn, merge_id)

    if not keep_lead or not merge_lead:
        return None

    try:
        conn.execute("BEGIN IMMEDIATE")

        # Apply field choices if provided
        if field_choices:
            updates = {k: v for k, v in field_choices.items() if k in _EDITABLE_FIELDS}
            if updates:
                set_clauses = [f"{col} = :{col}" for col in updates]
                set_clauses.append("updated_at = datetime('now')")
                updates["lead_id"] = keep_id
                sql = f"UPDATE leads SET {', '.join(set_clauses)} WHERE id = :lead_id;"
                conn.execute(sql, updates)

        # Merge notes
        if merge_lead.get("notes"):
            merge_notes = merge_lead["notes"]
            note_addition = f"\n--- Merged from lead #{merge_id} ---\n{merge_notes}"
            conn.execute(
                "UPDATE leads SET notes = COALESCE(notes, '') || ?, updated_at = datetime('now') "
                "WHERE id = ?;",
                (note_addition, keep_id),
            )

        # Soft-delete the merged lead
        conn.execute(
            "UPDATE leads SET deleted_at = datetime('now'), updated_at = datetime('now') "
            "WHERE id = ?;",
            (merge_id,),
        )

        # Update any duplicate suggestions involving the merged lead
        conn.execute(
            "UPDATE duplicate_suggestions SET status = 'merged', resolved_at = datetime('now') "
            "WHERE (lead_id_a = ? OR lead_id_b = ?) AND status = 'pending';",
            (merge_id, merge_id),
        )

        conn.commit()
    except Exception:
        conn.rollback()
        raise

    return get_lead(conn, keep_id)
