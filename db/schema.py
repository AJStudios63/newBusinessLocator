"""DDL statements and database initialisation for newBusinessLocator."""

from __future__ import annotations

import sqlite3
from pathlib import Path

# ---------------------------------------------------------------------------
# CREATE TABLE statements
# ---------------------------------------------------------------------------

CREATE_LEADS = """
CREATE TABLE IF NOT EXISTS leads (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint     TEXT    UNIQUE NOT NULL,
    business_name   TEXT    NOT NULL,
    business_type   TEXT,
    raw_type        TEXT,
    address         TEXT,
    city            TEXT,
    state           TEXT    DEFAULT 'TN',
    zip_code        TEXT,
    county          TEXT,
    license_date    TEXT,
    pos_score       INTEGER DEFAULT 0,
    stage           TEXT    DEFAULT 'New',
    source_url      TEXT,
    source_type     TEXT,
    notes           TEXT,
    created_at      TEXT    DEFAULT (datetime('now')),
    updated_at      TEXT    DEFAULT (datetime('now')),
    contacted_at    TEXT,
    closed_at       TEXT
);
"""

CREATE_PIPELINE_RUNS = """
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    run_started_at   TEXT,
    run_finished_at  TEXT,
    status           TEXT    DEFAULT 'running',
    leads_found      INTEGER DEFAULT 0,
    leads_new        INTEGER DEFAULT 0,
    leads_dupes      INTEGER DEFAULT 0,
    error_message    TEXT,
    sources_queried  TEXT
);
"""

CREATE_SEEN_URLS = """
CREATE TABLE IF NOT EXISTS seen_urls (
    url            TEXT PRIMARY KEY,
    first_seen_at  TEXT DEFAULT (datetime('now')),
    county         TEXT
);
"""

CREATE_STAGE_HISTORY = """
CREATE TABLE IF NOT EXISTS stage_history (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id    INTEGER NOT NULL REFERENCES leads(id),
    old_stage  TEXT,
    new_stage  TEXT,
    changed_at TEXT DEFAULT (datetime('now'))
);
"""

# ---------------------------------------------------------------------------
# CREATE INDEX statements
# ---------------------------------------------------------------------------

CREATE_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_leads_fingerprint   ON leads(fingerprint);
CREATE INDEX IF NOT EXISTS idx_leads_city          ON leads(city);
CREATE INDEX IF NOT EXISTS idx_leads_county        ON leads(county);
CREATE INDEX IF NOT EXISTS idx_leads_stage         ON leads(stage);
CREATE INDEX IF NOT EXISTS idx_leads_pos_score     ON leads(pos_score);
CREATE INDEX IF NOT EXISTS idx_stage_history_lead  ON stage_history(lead_id);
"""

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

DDL_SCRIPT = (
    CREATE_LEADS
    + CREATE_PIPELINE_RUNS
    + CREATE_SEEN_URLS
    + CREATE_STAGE_HISTORY
    + CREATE_INDEXES
)


def init_db(db_path: str | Path) -> sqlite3.Connection:
    """Open (or create) the SQLite database, apply all DDL, and return the connection.

    Parameters
    ----------
    db_path : str or Path
        File-system path to the SQLite database file.

    Returns
    -------
    sqlite3.Connection
        An open connection to the initialised database.
    """
    conn = sqlite3.connect(str(db_path), timeout=30.0)
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.executescript(DDL_SCRIPT)
    conn.commit()
    conn.row_factory = sqlite3.Row
    return conn
