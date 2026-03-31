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
    latitude        REAL,
    longitude       REAL,
    county          TEXT,
    license_date    TEXT,
    pos_score       INTEGER DEFAULT 0,
    stage           TEXT    DEFAULT 'New',
    source_url      TEXT,
    source_type     TEXT,
    source_batch_id TEXT,
    notes           TEXT,
    created_at      TEXT    DEFAULT (datetime('now')),
    updated_at      TEXT    DEFAULT (datetime('now')),
    contacted_at    TEXT,
    closed_at       TEXT,
    deleted_at      TEXT
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
    credits_used     INTEGER DEFAULT 0,
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

CREATE_SEARCH_CACHE = """
CREATE TABLE IF NOT EXISTS search_cache (
    query_hash     TEXT PRIMARY KEY,
    query_text     TEXT NOT NULL,
    results_json   TEXT NOT NULL,
    cached_at      TEXT DEFAULT (datetime('now'))
);
"""

CREATE_DUPLICATE_SUGGESTIONS = """
CREATE TABLE IF NOT EXISTS duplicate_suggestions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id_a        INTEGER NOT NULL REFERENCES leads(id),
    lead_id_b        INTEGER NOT NULL REFERENCES leads(id),
    similarity_score REAL    NOT NULL,
    status           TEXT    DEFAULT 'pending',
    created_at       TEXT    DEFAULT (datetime('now')),
    resolved_at      TEXT,
    UNIQUE(lead_id_a, lead_id_b)
);
"""

# ---------------------------------------------------------------------------
# CREATE INDEX statements
# ---------------------------------------------------------------------------

CREATE_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_leads_fingerprint      ON leads(fingerprint);
CREATE INDEX IF NOT EXISTS idx_leads_city             ON leads(city);
CREATE INDEX IF NOT EXISTS idx_leads_county           ON leads(county);
CREATE INDEX IF NOT EXISTS idx_leads_stage            ON leads(stage);
CREATE INDEX IF NOT EXISTS idx_leads_pos_score        ON leads(pos_score);
CREATE INDEX IF NOT EXISTS idx_leads_source_batch_id  ON leads(source_batch_id);
CREATE INDEX IF NOT EXISTS idx_stage_history_lead     ON stage_history(lead_id);
CREATE INDEX IF NOT EXISTS idx_dupe_suggestions_status ON duplicate_suggestions(status);
CREATE INDEX IF NOT EXISTS idx_dupe_suggestions_lead_a ON duplicate_suggestions(lead_id_a);
CREATE INDEX IF NOT EXISTS idx_dupe_suggestions_lead_b ON duplicate_suggestions(lead_id_b);
CREATE INDEX IF NOT EXISTS idx_leads_active ON leads(deleted_at) WHERE deleted_at IS NULL;
"""

# ---------------------------------------------------------------------------
# FTS5 Full-Text Search
# ---------------------------------------------------------------------------

CREATE_FTS = """
CREATE VIRTUAL TABLE IF NOT EXISTS leads_fts USING fts5(
    business_name,
    city,
    address,
    content='leads',
    content_rowid='id'
);
"""

CREATE_FTS_TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS leads_fts_ai AFTER INSERT ON leads BEGIN
    INSERT INTO leads_fts(rowid, business_name, city, address)
    VALUES (new.id, new.business_name, new.city, new.address);
END;

CREATE TRIGGER IF NOT EXISTS leads_fts_ad AFTER DELETE ON leads BEGIN
    INSERT INTO leads_fts(leads_fts, rowid, business_name, city, address)
    VALUES ('delete', old.id, old.business_name, old.city, old.address);
END;

CREATE TRIGGER IF NOT EXISTS leads_fts_au AFTER UPDATE ON leads BEGIN
    INSERT INTO leads_fts(leads_fts, rowid, business_name, city, address)
    VALUES ('delete', old.id, old.business_name, old.city, old.address);
    INSERT INTO leads_fts(rowid, business_name, city, address)
    VALUES (new.id, new.business_name, new.city, new.address);
END;
"""

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

DDL_SCRIPT = (
    CREATE_LEADS
    + CREATE_PIPELINE_RUNS
    + CREATE_SEEN_URLS
    + CREATE_STAGE_HISTORY
    + CREATE_SEARCH_CACHE
    + CREATE_DUPLICATE_SUGGESTIONS
    + CREATE_INDEXES
    + CREATE_FTS
    + CREATE_FTS_TRIGGERS
)


def _migrate_add_column(
    conn: sqlite3.Connection,
    table: str,
    column: str,
    column_type: str,
) -> None:
    """Add a column to a table if it doesn't already exist.

    Parameters
    ----------
    conn        : open sqlite3 connection
    table       : table name
    column      : column name to add
    column_type : SQL column type (e.g., 'TEXT', 'INTEGER', 'REAL')
    """
    # Check if column exists
    cursor = conn.execute(f"PRAGMA table_info({table});")
    columns = [row[1] for row in cursor.fetchall()]

    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type};")
        conn.commit()


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
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.executescript(DDL_SCRIPT)

    # Migrations for existing databases
    _migrate_add_column(conn, "pipeline_runs", "credits_used", "INTEGER DEFAULT 0")

    conn.commit()
    conn.row_factory = sqlite3.Row

    # Run migrations for new columns
    _migrate_add_column(conn, "leads", "latitude", "REAL")
    _migrate_add_column(conn, "leads", "longitude", "REAL")

    # Create index on geocoded columns (after migration ensures columns exist)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_leads_geocoded "
        "ON leads(latitude, longitude) WHERE latitude IS NOT NULL;"
    )
    conn.commit()

    return conn
