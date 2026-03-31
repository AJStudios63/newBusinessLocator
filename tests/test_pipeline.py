"""
Tests for etl/pipeline.py

Tests the pipeline orchestrator:
- Dry run mode (no DB writes)
- Full run with mocked extract/transform/load
- Error handling and recording
- source_batch_id stamping
"""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from etl.pipeline import run_pipeline


@pytest.fixture
def mock_extract():
    """Mock run_extract to return sample raw extracts."""
    raw_extracts = [
        {
            "raw_content": "| Date | Business Name | Product Type | Address |\n|---|---|---|---|\n| 01/15/2026 | Test Biz | Restaurant | 123 Main |",
            "source_url": "https://example.com/1",
            "county": "Davidson",
            "source_type": "license_table",
            "title": "New Business Licenses",
        },
    ]
    with patch("etl.pipeline.run_extract", return_value=(raw_extracts, 3)) as m:
        yield m


@pytest.fixture
def mock_transform():
    """Mock run_transform to return sample business records."""
    records = [
        {
            "business_name": "Test Biz",
            "business_type": "restaurant",
            "raw_type": "Restaurant",
            "address": "123 Main",
            "city": "Nashville",
            "state": "TN",
            "zip_code": "37201",
            "county": "Davidson",
            "license_date": "2026-01-15",
            "pos_score": 85,
            "source_url": "https://example.com/1",
            "source_type": "license_table",
            "fingerprint": "abc123",
            "notes": None,
            "stage": "New",
        },
    ]
    with patch("etl.pipeline.run_transform", return_value=records) as m:
        yield m


@pytest.fixture
def mock_load():
    """Mock run_load to return counts."""
    result = {"leads_found": 1, "leads_new": 1, "leads_dupes": 0}
    with patch("etl.pipeline.run_load", return_value=result) as m:
        yield m


@pytest.fixture
def mock_db():
    """Mock init_db and pipeline run DB calls."""
    mock_conn = MagicMock()
    with patch("etl.pipeline.init_db", return_value=mock_conn) as m_init, \
         patch("etl.pipeline.insert_pipeline_run", return_value=1) as m_insert, \
         patch("etl.pipeline.update_pipeline_run") as m_update:
        yield {
            "conn": mock_conn,
            "init_db": m_init,
            "insert_pipeline_run": m_insert,
            "update_pipeline_run": m_update,
        }


class TestDryRun:
    """Tests for dry_run mode."""

    def test_dry_run_returns_completed_status(self, mock_extract, mock_transform):
        """Dry run returns status=completed."""
        result = run_pipeline(dry_run=True)

        assert result["status"] == "completed"
        assert result["run_id"] is None
        assert result["error"] is None

    def test_dry_run_does_not_write_db(self, mock_extract, mock_transform):
        """Dry run does not open DB or insert pipeline run."""
        with patch("etl.pipeline.init_db") as m_init:
            run_pipeline(dry_run=True)
            m_init.assert_not_called()

    def test_dry_run_reports_leads_found(self, mock_extract, mock_transform):
        """Dry run reports the number of leads found."""
        result = run_pipeline(dry_run=True)

        assert result["leads_found"] == len(mock_transform.return_value)
        assert result["leads_new"] == 0
        assert result["leads_dupes"] == 0

    def test_dry_run_includes_business_records(self, mock_extract, mock_transform):
        """Dry run result includes the business records for inspection."""
        result = run_pipeline(dry_run=True)

        assert len(result["business_records"]) == 1
        assert result["business_records"][0]["business_name"] == "Test Biz"

    def test_dry_run_includes_raw_extracts(self, mock_extract, mock_transform):
        """Dry run result includes raw extracts."""
        result = run_pipeline(dry_run=True)

        assert len(result["raw_extracts"]) == 1


class TestFullRun:
    """Tests for full pipeline execution."""

    def test_full_run_returns_completed(self, mock_db, mock_extract, mock_transform, mock_load):
        """Full run returns status=completed with counts."""
        result = run_pipeline(dry_run=False)

        assert result["status"] == "completed"
        assert result["run_id"] == 1
        assert result["leads_found"] == 1
        assert result["leads_new"] == 1
        assert result["leads_dupes"] == 0
        assert result["error"] is None

    def test_full_run_creates_pipeline_run(self, mock_db, mock_extract, mock_transform, mock_load):
        """Full run creates a pipeline_runs row."""
        run_pipeline(dry_run=False)

        mock_db["insert_pipeline_run"].assert_called_once()

    def test_full_run_stamps_batch_id(self, mock_db, mock_extract, mock_transform, mock_load):
        """Full run stamps source_batch_id on each record."""
        result = run_pipeline(dry_run=False)

        for rec in result["business_records"]:
            assert rec["source_batch_id"] == 1

    def test_full_run_calls_load(self, mock_db, mock_extract, mock_transform, mock_load):
        """Full run calls run_load with records and run_id."""
        run_pipeline(dry_run=False)

        mock_load.assert_called_once()
        args = mock_load.call_args
        assert args[0][2] == 1  # run_id


class TestErrorHandling:
    """Tests for error handling in the pipeline."""

    def test_extract_failure_returns_failed(self, mock_db):
        """Pipeline returns failed status when extract raises."""
        with patch("etl.pipeline.run_extract", side_effect=RuntimeError("Tavily down")):
            result = run_pipeline(dry_run=False)

        assert result["status"] == "failed"
        assert "Tavily down" in result["error"]

    def test_transform_failure_returns_failed(self, mock_db, mock_extract):
        """Pipeline returns failed status when transform raises."""
        with patch("etl.pipeline.run_transform", side_effect=ValueError("Bad config")):
            result = run_pipeline(dry_run=False)

        assert result["status"] == "failed"
        assert "Bad config" in result["error"]

    def test_failure_records_error_in_db(self, mock_db):
        """Pipeline records error in pipeline_runs on failure."""
        with patch("etl.pipeline.run_extract", side_effect=RuntimeError("fail")):
            run_pipeline(dry_run=False)

        mock_db["update_pipeline_run"].assert_called_once()
        call_kwargs = mock_db["update_pipeline_run"].call_args
        assert call_kwargs[1].get("status") == "failed" or call_kwargs[0][2] == "failed"

    def test_failure_closes_connection(self, mock_db):
        """Pipeline closes DB connection even on failure."""
        with patch("etl.pipeline.run_extract", side_effect=RuntimeError("fail")):
            run_pipeline(dry_run=False)

        mock_db["conn"].close.assert_called_once()

    def test_dry_run_extract_failure(self):
        """Dry run also reports failure if extract raises."""
        with patch("etl.pipeline.run_extract", side_effect=RuntimeError("API error")):
            result = run_pipeline(dry_run=True)

        assert result["status"] == "failed"
        assert "API error" in result["error"]
