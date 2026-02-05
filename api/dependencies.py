"""Shared dependencies for FastAPI routes."""

from __future__ import annotations

from typing import Generator
import sqlite3

from config.settings import DB_PATH
from db.schema import init_db


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Yield a database connection, closing it after the request."""
    conn = init_db(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()
