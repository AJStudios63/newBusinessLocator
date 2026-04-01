"""Tests for geocode_runs query helpers and API endpoints."""

from __future__ import annotations

import sqlite3
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from db.schema import init_db, DDL_SCRIPT
from db.queries import (
    insert_geocode_run,
    update_geocode_run,
    get_geocode_runs,
    cleanup_orphaned_geocode_runs,
)


@pytest.fixture
def memory_db():
    """In-memory database with full schema."""
    conn = init_db(":memory:")
    yield conn
    conn.close()


class TestGeocodeRunQueries:
    """Tests for geocode_runs CRUD functions."""

    def test_insert_geocode_run_returns_id(self, memory_db):
        run_id = insert_geocode_run(memory_db, total=100)
        assert isinstance(run_id, int)
        assert run_id > 0

    def test_insert_geocode_run_creates_row(self, memory_db):
        run_id = insert_geocode_run(memory_db, total=250)
        row = memory_db.execute(
            "SELECT * FROM geocode_runs WHERE id = ?;", (run_id,)
        ).fetchone()
        assert row is not None
        assert row["total"] == 250
        assert row["status"] == "running"
        assert row["succeeded"] == 0
        assert row["failed"] == 0

    def test_update_geocode_run_sets_completed(self, memory_db):
        run_id = insert_geocode_run(memory_db, total=50)
        update_geocode_run(
            memory_db,
            run_id=run_id,
            status="completed",
            succeeded=45,
            failed=5,
        )
        row = memory_db.execute(
            "SELECT * FROM geocode_runs WHERE id = ?;", (run_id,)
        ).fetchone()
        assert row["status"] == "completed"
        assert row["succeeded"] == 45
        assert row["failed"] == 5
        assert row["finished_at"] is not None

    def test_update_geocode_run_sets_failed_with_message(self, memory_db):
        run_id = insert_geocode_run(memory_db, total=10)
        update_geocode_run(
            memory_db,
            run_id=run_id,
            status="failed",
            succeeded=3,
            failed=0,
            error_message="Connection lost",
        )
        row = memory_db.execute(
            "SELECT * FROM geocode_runs WHERE id = ?;", (run_id,)
        ).fetchone()
        assert row["status"] == "failed"
        assert row["error_message"] == "Connection lost"

    def test_get_geocode_runs_returns_newest_first(self, memory_db):
        insert_geocode_run(memory_db, total=10)
        insert_geocode_run(memory_db, total=20)
        insert_geocode_run(memory_db, total=30)
        runs = get_geocode_runs(memory_db, limit=10)
        assert len(runs) == 3
        assert runs[0]["total"] == 30  # newest first (highest id)

    def test_get_geocode_runs_respects_limit(self, memory_db):
        for i in range(5):
            insert_geocode_run(memory_db, total=i * 10)
        runs = get_geocode_runs(memory_db, limit=2)
        assert len(runs) == 2

    def test_cleanup_orphaned_runs(self, memory_db):
        """Orphaned running rows get marked as failed on cleanup."""
        memory_db.execute(
            "INSERT INTO geocode_runs (status, total, succeeded, failed) VALUES ('running', 100, 50, 2);"
        )
        memory_db.execute(
            "INSERT INTO geocode_runs (status, total, succeeded, failed) VALUES ('completed', 200, 195, 5);"
        )
        memory_db.commit()

        cleaned = cleanup_orphaned_geocode_runs(memory_db)
        assert cleaned == 1

        rows = memory_db.execute(
            "SELECT status, error_message FROM geocode_runs ORDER BY id;"
        ).fetchall()
        assert rows[0]["status"] == "failed"
        assert "interrupted" in rows[0]["error_message"].lower()
        assert rows[1]["status"] == "completed"


@pytest.fixture
def test_db_path():
    """Create a temporary database file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)
    conn.executescript(DDL_SCRIPT)
    conn.row_factory = sqlite3.Row

    for i in range(3):
        conn.execute(
            "INSERT INTO leads (fingerprint, business_name, city, state, pos_score, stage) "
            "VALUES (?, ?, ?, 'TN', 50, 'New');",
            (f"fp_{i}", f"Business {i}", "Nashville"),
        )
    conn.commit()
    conn.close()

    yield db_path
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def api_client(test_db_path):
    """Test client with database dependency overridden."""
    from fastapi.testclient import TestClient

    from api.main import app
    from api.dependencies import get_db
    from api.routers.geocode import _reset_state

    def override_get_db():
        conn = sqlite3.connect(test_db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
    _reset_state()


class TestGeocodeAPI:
    """Tests for geocode API endpoints."""

    def test_get_status_when_idle(self, api_client):
        resp = api_client.get("/api/geocode/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["running"] is False
        assert data["run_id"] is None
        assert data["total"] == 0
        assert data["done"] == 0
        assert data["succeeded"] == 0
        assert data["failed"] == 0
        assert data["pct"] == 0.0

    @patch("api.routers.geocode.geocode_lead", return_value=(36.16, -86.78))
    @patch("api.routers.geocode._MIN_INTERVAL", 0)
    def test_post_run_starts_job(self, mock_geocode, api_client):
        resp = api_client.post("/api/geocode/run")
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Geocoding started"
        assert data["run_id"] >= 1
        assert data["total"] == 3

    @patch("api.routers.geocode.geocode_lead", return_value=(36.16, -86.78))
    @patch("api.routers.geocode._MIN_INTERVAL", 0)
    def test_post_run_returns_409_when_running(self, mock_geocode, api_client):
        resp1 = api_client.post("/api/geocode/run")
        assert resp1.status_code == 200

        resp2 = api_client.post("/api/geocode/run")
        assert resp2.status_code == 409
        assert "already" in resp2.json()["detail"].lower()

    @patch("api.routers.geocode.geocode_lead", return_value=(36.16, -86.78))
    @patch("api.routers.geocode._MIN_INTERVAL", 0)
    def test_job_completes_and_updates_leads(self, mock_geocode, api_client, test_db_path):
        resp = api_client.post("/api/geocode/run")
        assert resp.status_code == 200

        status = None
        for _ in range(50):
            time.sleep(0.1)
            status = api_client.get("/api/geocode/status").json()
            if not status["running"]:
                break

        assert status["running"] is False
        assert status["succeeded"] == 3
        assert status["failed"] == 0
        assert status["done"] == 3
        assert status["pct"] == 100.0

        conn = sqlite3.connect(test_db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT latitude, longitude FROM leads;").fetchall()
        conn.close()
        for row in rows:
            assert row["latitude"] == 36.16
            assert row["longitude"] == -86.78

    def test_get_runs_returns_list(self, api_client):
        resp = api_client.get("/api/geocode/runs")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    @patch("api.routers.geocode.geocode_lead", return_value=(36.16, -86.78))
    @patch("api.routers.geocode._MIN_INTERVAL", 0)
    def test_get_runs_shows_completed_run(self, mock_geocode, api_client):
        api_client.post("/api/geocode/run")
        for _ in range(50):
            time.sleep(0.1)
            status = api_client.get("/api/geocode/status").json()
            if not status["running"]:
                break

        runs = api_client.get("/api/geocode/runs").json()
        assert len(runs) >= 1
        assert runs[0]["status"] == "completed"
        assert runs[0]["total"] == 3
        assert runs[0]["succeeded"] == 3
