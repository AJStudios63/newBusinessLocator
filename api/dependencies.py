"""Shared dependencies for FastAPI routes."""

from __future__ import annotations

from typing import Generator
import sqlite3

from config.settings import DB_PATH
from db.schema import init_db

_initialized = False


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Yield a database connection, closing it after the request."""
    global _initialized
    if not _initialized:
        init_conn = init_db(DB_PATH)
        init_conn.close()
        _initialized = True

    conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
