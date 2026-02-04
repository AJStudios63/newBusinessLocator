"""Named SQL query helpers for newBusinessLocator."""

import sqlite3


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
    "license_date",
    "pos_score",
    "stage",
    "source_url",
    "source_type",
    "notes",
)

_INSERT_LEAD_SQL = (
    "INSERT OR IGNORE INTO leads ("
    + ", ".join(_INSERT_LEAD_COLUMNS)
    + ") VALUES ("
    + ", ".join(f":{col}" for col in _INSERT_LEAD_COLUMNS)
    + ");"
)


def insert_lead(conn: sqlite3.Connection, lead: dict) -> None:
    """Insert a single lead row; silently ignored if fingerprint already exists."""
    conn.execute(_INSERT_LEAD_SQL, lead)
    conn.commit()


# ---------------------------------------------------------------------------
# Leads – read
# ---------------------------------------------------------------------------


def _rows_to_dicts(rows) -> list[dict]:
    """Convert a list of sqlite3.Row objects to plain dicts."""
    return [dict(row) for row in rows]


def get_leads(
    conn: sqlite3.Connection,
    stage: str | None = None,
    county: str | None = None,
    min_score: int | None = None,
    sort: str = "pos_score",
    limit: int = 100,
) -> list[dict]:
    """Return leads, optionally filtered, ordered by *sort* DESC.

    Parameters
    ----------
    conn       : open sqlite3 connection
    stage      : filter by stage value (optional)
    county     : filter by county value (optional)
    min_score  : minimum pos_score, inclusive (optional)
    sort       : column name to ORDER BY (default 'pos_score')
    limit      : maximum number of rows returned (default 100)
    """
    conn.row_factory = sqlite3.Row

    clauses: list[str] = []
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

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""

    # Guard *sort* against SQL injection – only allow identifiers that exist
    # in the leads table column list.
    _ALLOWED_SORT_COLUMNS = {
        "id", "fingerprint", "business_name", "business_type", "raw_type",
        "address", "city", "state", "zip_code", "county", "license_date",
        "pos_score", "stage", "source_url", "source_type", "notes",
        "created_at", "updated_at", "contacted_at", "closed_at",
    }
    if sort not in _ALLOWED_SORT_COLUMNS:
        raise ValueError(f"Invalid sort column: {sort}")

    sql = f"SELECT * FROM leads{where} ORDER BY {sort} DESC LIMIT :limit;"
    params["limit"] = limit

    rows = conn.execute(sql, params).fetchall()
    return _rows_to_dicts(rows)


def get_lead(conn: sqlite3.Connection, lead_id: int) -> dict | None:
    """Return a single lead as a dict, or None if not found."""
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM leads WHERE id = ?;", (lead_id,)).fetchone()
    return dict(row) if row else None


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
    conn.row_factory = sqlite3.Row

    # -- current stage ---------------------------------------------------
    row = conn.execute(
        "SELECT stage FROM leads WHERE id = ?;", (lead_id,)
    ).fetchone()
    if row is None:
        raise ValueError(f"No lead with id={lead_id}")

    old_stage: str | None = row["stage"]
    if old_stage == new_stage:
        return  # nothing to do

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


def get_stage_history(conn: sqlite3.Connection, lead_id: int) -> list[dict]:
    """Return all stage-change records for *lead_id*, oldest first."""
    conn.row_factory = sqlite3.Row
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
    conn.row_factory = sqlite3.Row

    # by_stage
    by_stage = {
        row["stage"]: row["cnt"]
        for row in conn.execute(
            "SELECT stage, COUNT(*) AS cnt FROM leads GROUP BY stage;"
        ).fetchall()
    }

    # by_county
    by_county = {
        row["county"]: row["cnt"]
        for row in conn.execute(
            "SELECT county, COUNT(*) AS cnt FROM leads GROUP BY county;"
        ).fetchall()
    }

    # by_type
    by_type = {
        row["business_type"]: row["cnt"]
        for row in conn.execute(
            "SELECT business_type, COUNT(*) AS cnt FROM leads GROUP BY business_type;"
        ).fetchall()
    }

    # avg_score
    avg_row = conn.execute(
        "SELECT COALESCE(AVG(pos_score), 0.0) AS avg FROM leads;"
    ).fetchone()
    avg_score: float = float(avg_row["avg"])

    # total_leads
    total_row = conn.execute("SELECT COUNT(*) AS cnt FROM leads;").fetchone()
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


def insert_seen_url(conn: sqlite3.Connection, url: str, county: str | None = None) -> None:
    """Insert a URL into seen_urls; silently ignored if already present."""
    conn.execute(
        "INSERT OR IGNORE INTO seen_urls (url, county) VALUES (?, ?);",
        (url, county),
    )
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
) -> None:
    """Finalise a pipeline run row with results and set run_finished_at to now."""
    conn.execute(
        "UPDATE pipeline_runs SET "
        "run_finished_at   = datetime('now'), "
        "status            = ?, "
        "leads_found       = ?, "
        "leads_new         = ?, "
        "leads_dupes       = ?, "
        "error_message     = ?, "
        "sources_queried   = ? "
        "WHERE id = ?;",
        (status, leads_found, leads_new, leads_dupes, error_message, sources_queried, run_id),
    )
    conn.commit()


def get_pipeline_runs(conn: sqlite3.Connection, limit: int = 10) -> list[dict]:
    """Return the most recent pipeline runs, newest first."""
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM pipeline_runs ORDER BY run_started_at DESC LIMIT ?;",
        (limit,),
    ).fetchall()
    return _rows_to_dicts(rows)
