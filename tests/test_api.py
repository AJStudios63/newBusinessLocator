"""Tests for FastAPI endpoints."""

from __future__ import annotations

import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.dependencies import get_db
from db.schema import DDL_SCRIPT


@pytest.fixture
def test_db_path():
    """Create a temporary database file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    # Initialize the database with schema and test data
    conn = sqlite3.connect(db_path)
    conn.executescript(DDL_SCRIPT)
    conn.row_factory = sqlite3.Row

    # Insert a pipeline run
    conn.execute(
        "INSERT INTO pipeline_runs (run_started_at, status) VALUES (?, 'running');",
        (datetime.now().isoformat(),),
    )

    # Insert some sample leads
    sample_leads = [
        {
            "fingerprint": "abc123def456",
            "business_name": "Test Restaurant LLC",
            "business_type": "restaurant",
            "raw_type": "Restaurant",
            "address": "123 Main St",
            "city": "Nashville",
            "state": "TN",
            "zip_code": "37201",
            "county": "Davidson",
            "license_date": datetime.now().strftime("%Y-%m-%d"),
            "pos_score": 85,
            "stage": "New",
            "source_url": "https://example.com/1",
            "source_type": "license_table",
            "notes": None,
        },
        {
            "fingerprint": "xyz789ghi012",
            "business_name": "Franklin Salon",
            "business_type": "salon",
            "raw_type": "Beauty Salon",
            "address": "456 Oak Ave",
            "city": "Franklin",
            "state": "TN",
            "zip_code": "37064",
            "county": "Williamson",
            "license_date": (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d"),
            "pos_score": 65,
            "stage": "Qualified",
            "source_url": "https://example.com/2",
            "source_type": "news_article",
            "notes": "Great prospect",
        },
        {
            "fingerprint": "mno345pqr678",
            "business_name": "Murfreesboro Coffee",
            "business_type": "cafe",
            "raw_type": None,
            "address": None,
            "city": "Murfreesboro",
            "state": "TN",
            "zip_code": None,
            "county": "Rutherford",
            "license_date": None,
            "pos_score": 40,
            "stage": "New",
            "source_url": "https://example.com/3",
            "source_type": "search_snippet",
            "notes": None,
        },
    ]

    for lead in sample_leads:
        conn.execute(
            """
            INSERT INTO leads (
                fingerprint, business_name, business_type, raw_type,
                address, city, state, zip_code, county, license_date,
                pos_score, stage, source_url, source_type, notes
            ) VALUES (
                :fingerprint, :business_name, :business_type, :raw_type,
                :address, :city, :state, :zip_code, :county, :license_date,
                :pos_score, :stage, :source_url, :source_type, :notes
            );
            """,
            lead,
        )

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def client(test_db_path):
    """Test client with database dependency overridden."""
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


class TestHealthEndpoint:
    def test_health_check(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestLeadsEndpoints:
    def test_list_leads(self, client):
        response = client.get("/api/leads")
        assert response.status_code == 200
        data = response.json()
        assert "leads" in data
        assert "count" in data
        assert data["count"] == 3  # populated_db has 3 leads

    def test_list_leads_filter_by_stage(self, client):
        response = client.get("/api/leads?stage=New")
        assert response.status_code == 200
        data = response.json()
        for lead in data["leads"]:
            assert lead["stage"] == "New"

    def test_list_leads_filter_by_county(self, client):
        response = client.get("/api/leads?county=Davidson")
        assert response.status_code == 200
        data = response.json()
        for lead in data["leads"]:
            assert lead["county"] == "Davidson"

    def test_get_lead_detail(self, client):
        # First get the list to find an ID
        response = client.get("/api/leads")
        lead_id = response.json()["leads"][0]["id"]

        response = client.get(f"/api/leads/{lead_id}")
        assert response.status_code == 200
        assert response.json()["id"] == lead_id

    def test_get_lead_not_found(self, client):
        response = client.get("/api/leads/99999")
        assert response.status_code == 404

    def test_update_lead_stage(self, client):
        response = client.get("/api/leads")
        lead_id = response.json()["leads"][0]["id"]

        response = client.patch(f"/api/leads/{lead_id}?stage=Qualified")
        assert response.status_code == 200
        assert response.json()["stage"] == "Qualified"

    def test_update_lead_invalid_stage(self, client):
        response = client.get("/api/leads")
        lead_id = response.json()["leads"][0]["id"]

        response = client.patch(f"/api/leads/{lead_id}?stage=Invalid")
        assert response.status_code == 400

    def test_quick_stage_update(self, client):
        response = client.get("/api/leads")
        lead_id = response.json()["leads"][0]["id"]

        response = client.patch(f"/api/leads/{lead_id}/stage?stage=Contacted")
        assert response.status_code == 200
        assert response.json()["stage"] == "Contacted"


class TestStatsEndpoint:
    def test_get_stats(self, client):
        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert "by_stage" in data
        assert "by_county" in data
        assert "by_type" in data
        assert "avg_score" in data
        assert "total_leads" in data


class TestKanbanEndpoint:
    def test_get_kanban_board(self, client):
        response = client.get("/api/kanban")
        assert response.status_code == 200
        data = response.json()
        assert "stages" in data
        assert "columns" in data
        assert len(data["stages"]) == 6
        assert "New" in data["columns"]


class TestPipelineEndpoints:
    def test_get_pipeline_runs(self, client):
        response = client.get("/api/pipeline/runs")
        assert response.status_code == 200
        data = response.json()
        assert "runs" in data

    def test_get_pipeline_status(self, client):
        response = client.get("/api/pipeline/status")
        assert response.status_code == 200
        data = response.json()
        assert "running" in data
