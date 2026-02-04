"""
Tests for etl/load.py

Tests the load functions:
- run_load: main load entry point
- log_pipeline_run: logs run results to file
"""

import pytest
from datetime import datetime

from etl.load import run_load, log_pipeline_run
from db.queries import get_leads, get_seen_urls, get_pipeline_runs


# ---------------------------------------------------------------------------
# run_load Tests
# ---------------------------------------------------------------------------


class TestRunLoad:
    """Tests for the run_load function."""

    @pytest.fixture
    def sample_business_records(self):
        """Sample business records to load."""
        return [
            {
                "fingerprint": "fp001",
                "business_name": "Test Restaurant",
                "business_type": "restaurant",
                "raw_type": "Restaurant",
                "address": "123 Main St",
                "city": "Nashville",
                "state": "TN",
                "zip_code": "37201",
                "county": "Davidson",
                "license_date": "2026-01-15",
                "pos_score": 85,
                "source_url": "https://example.com/1",
                "source_type": "license_table",
                "notes": None,
            },
            {
                "fingerprint": "fp002",
                "business_name": "Test Salon",
                "business_type": "salon",
                "raw_type": "Beauty Salon",
                "address": "456 Oak Ave",
                "city": "Franklin",
                "state": "TN",
                "zip_code": "37064",
                "county": "Williamson",
                "license_date": "2026-01-14",
                "pos_score": 65,
                "source_url": "https://example.com/2",
                "source_type": "news_article",
                "notes": None,
            },
        ]

    @pytest.fixture
    def sample_raw_extracts(self):
        """Sample raw extracts for URL tracking."""
        return [
            {
                "source_url": "https://example.com/1",
                "county": "Davidson",
            },
            {
                "source_url": "https://example.com/2",
                "county": "Williamson",
            },
        ]

    @pytest.fixture
    def run_id(self, memory_db):
        """Create a pipeline run and return its ID."""
        cursor = memory_db.execute(
            "INSERT INTO pipeline_runs (run_started_at, status) VALUES (?, 'running');",
            (datetime.now().isoformat(),),
        )
        memory_db.commit()
        return cursor.lastrowid

    def test_inserts_new_leads(self, memory_db, sample_business_records, sample_raw_extracts, run_id):
        """Inserts new leads into the database."""
        result = run_load(sample_business_records, sample_raw_extracts, run_id, conn=memory_db)

        assert result["leads_found"] == 2
        assert result["leads_new"] == 2
        assert result["leads_dupes"] == 0

        # Verify leads are in the database
        leads = get_leads(memory_db)
        assert len(leads) == 2
        business_names = [l["business_name"] for l in leads]
        assert "Test Restaurant" in business_names
        assert "Test Salon" in business_names

    def test_detects_duplicate_leads(self, memory_db, sample_business_records, sample_raw_extracts, run_id):
        """Detects duplicate leads on second run."""
        # First run
        run_load(sample_business_records, sample_raw_extracts, run_id, conn=memory_db)

        # Create a new run_id for second run
        cursor = memory_db.execute(
            "INSERT INTO pipeline_runs (run_started_at, status) VALUES (?, 'running');",
            (datetime.now().isoformat(),),
        )
        memory_db.commit()
        run_id_2 = cursor.lastrowid

        # Second run with same records
        result = run_load(sample_business_records, sample_raw_extracts, run_id_2, conn=memory_db)

        assert result["leads_found"] == 2
        assert result["leads_new"] == 0
        assert result["leads_dupes"] == 2

    def test_inserts_seen_urls(self, memory_db, sample_business_records, sample_raw_extracts, run_id):
        """Inserts source URLs into seen_urls table."""
        run_load(sample_business_records, sample_raw_extracts, run_id, conn=memory_db)

        seen_urls = get_seen_urls(memory_db)
        assert "https://example.com/1" in seen_urls
        assert "https://example.com/2" in seen_urls

    def test_updates_pipeline_run(self, memory_db, sample_business_records, sample_raw_extracts, run_id):
        """Updates pipeline run with results."""
        run_load(sample_business_records, sample_raw_extracts, run_id, conn=memory_db)

        runs = get_pipeline_runs(memory_db, limit=1)
        assert len(runs) == 1
        run = runs[0]

        assert run["status"] == "completed"
        assert run["leads_found"] == 2
        assert run["leads_new"] == 2
        assert run["leads_dupes"] == 0
        assert run["run_finished_at"] is not None

    def test_sets_default_stage_to_new(self, memory_db, sample_business_records, sample_raw_extracts, run_id):
        """Sets default stage to 'New' when not specified."""
        # Remove stage from records
        for record in sample_business_records:
            record.pop("stage", None)

        run_load(sample_business_records, sample_raw_extracts, run_id, conn=memory_db)

        leads = get_leads(memory_db)
        for lead in leads:
            assert lead["stage"] == "New"

    def test_handles_empty_records(self, memory_db, sample_raw_extracts, run_id):
        """Handles empty business records list."""
        result = run_load([], sample_raw_extracts, run_id, conn=memory_db)

        assert result["leads_found"] == 0
        assert result["leads_new"] == 0
        assert result["leads_dupes"] == 0

    def test_handles_records_without_source_urls(self, memory_db, sample_business_records, run_id):
        """Handles raw extracts with missing source_url."""
        raw_extracts_no_url = [
            {"county": "Davidson"},  # No source_url
            {"source_url": None, "county": "Davidson"},  # None source_url
        ]

        result = run_load(sample_business_records, raw_extracts_no_url, run_id, conn=memory_db)

        # Should still insert leads
        assert result["leads_found"] == 2
        assert result["leads_new"] == 2

    def test_deduplicates_seen_urls_in_same_batch(self, memory_db, sample_business_records, run_id):
        """Deduplicates URLs that appear multiple times in same batch."""
        # Same URL twice in raw_extracts
        raw_extracts_with_dupes = [
            {"source_url": "https://example.com/same", "county": "Davidson"},
            {"source_url": "https://example.com/same", "county": "Davidson"},
        ]

        run_load(sample_business_records, raw_extracts_with_dupes, run_id, conn=memory_db)

        seen_urls = get_seen_urls(memory_db)
        # Should only have one entry for the duplicate URL
        assert "https://example.com/same" in seen_urls

    def test_mixed_new_and_duplicate_leads(self, memory_db, run_id):
        """Handles a mix of new and duplicate leads."""
        # Insert one lead first
        initial_records = [
            {
                "fingerprint": "existing_fp",
                "business_name": "Existing Business",
                "business_type": "retail",
                "raw_type": "Store",
                "address": None,
                "city": "Nashville",
                "state": "TN",
                "zip_code": None,
                "county": "Davidson",
                "license_date": None,
                "pos_score": 50,
                "source_url": "https://example.com/old",
                "source_type": "search_snippet",
                "notes": None,
            },
        ]
        raw_extracts = [{"source_url": "https://example.com/old", "county": "Davidson"}]
        run_load(initial_records, raw_extracts, run_id, conn=memory_db)

        # Now run with mix of existing and new
        cursor = memory_db.execute(
            "INSERT INTO pipeline_runs (run_started_at, status) VALUES (?, 'running');",
            (datetime.now().isoformat(),),
        )
        memory_db.commit()
        run_id_2 = cursor.lastrowid

        mixed_records = [
            {
                "fingerprint": "existing_fp",  # Duplicate
                "business_name": "Existing Business",
                "business_type": "retail",
                "raw_type": "Store",
                "address": None,
                "city": "Nashville",
                "state": "TN",
                "zip_code": None,
                "county": "Davidson",
                "license_date": None,
                "pos_score": 50,
                "source_url": "https://example.com/old",
                "source_type": "search_snippet",
                "notes": None,
            },
            {
                "fingerprint": "new_fp",  # New
                "business_name": "New Business",
                "business_type": "cafe",
                "raw_type": "Coffee Shop",
                "address": "789 Pine St",
                "city": "Franklin",
                "state": "TN",
                "zip_code": "37064",
                "county": "Williamson",
                "license_date": "2026-01-20",
                "pos_score": 70,
                "source_url": "https://example.com/new",
                "source_type": "news_article",
                "notes": None,
            },
        ]
        raw_extracts_2 = [
            {"source_url": "https://example.com/old", "county": "Davidson"},
            {"source_url": "https://example.com/new", "county": "Williamson"},
        ]

        result = run_load(mixed_records, raw_extracts_2, run_id_2, conn=memory_db)

        assert result["leads_found"] == 2
        assert result["leads_new"] == 1
        assert result["leads_dupes"] == 1


# ---------------------------------------------------------------------------
# log_pipeline_run Tests
# ---------------------------------------------------------------------------


class TestLogPipelineRun:
    """Tests for the log_pipeline_run function."""

    def test_creates_log_line_format(self, tmp_path, monkeypatch):
        """Creates log line in expected format."""
        from config import settings

        # Override LOG_PATH to use temp directory
        log_file = tmp_path / "logs" / "pipeline.log"
        monkeypatch.setattr(settings, "LOG_PATH", log_file)

        # Also need to patch the import in load.py
        import etl.load
        monkeypatch.setattr(etl.load, "LOG_PATH", log_file)

        log_pipeline_run(
            run_id=42,
            leads_found=10,
            leads_new=8,
            leads_dupes=2,
        )

        assert log_file.exists()
        content = log_file.read_text()

        assert "run_id=42" in content
        assert "status=completed" in content
        assert "found=10" in content
        assert "new=8" in content
        assert "dupes=2" in content
        assert "error=none" in content

    def test_logs_error_message(self, tmp_path, monkeypatch):
        """Logs error message when provided."""
        from config import settings

        log_file = tmp_path / "logs" / "pipeline.log"
        monkeypatch.setattr(settings, "LOG_PATH", log_file)

        import etl.load
        monkeypatch.setattr(etl.load, "LOG_PATH", log_file)

        log_pipeline_run(
            run_id=1,
            leads_found=0,
            leads_new=0,
            leads_dupes=0,
            status="failed",
            error="Connection timeout",
        )

        content = log_file.read_text()
        assert "status=failed" in content
        assert "error=Connection timeout" in content

    def test_appends_to_existing_log(self, tmp_path, monkeypatch):
        """Appends to existing log file."""
        from config import settings

        log_file = tmp_path / "logs" / "pipeline.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_file.write_text("Existing log content\n")

        monkeypatch.setattr(settings, "LOG_PATH", log_file)

        import etl.load
        monkeypatch.setattr(etl.load, "LOG_PATH", log_file)

        log_pipeline_run(run_id=1, leads_found=5, leads_new=5, leads_dupes=0)

        content = log_file.read_text()
        assert "Existing log content" in content
        assert "run_id=1" in content
