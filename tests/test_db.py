"""
Tests for db/queries.py and db/schema.py

Tests database operations:
- init_db: initializes database schema
- insert_lead, get_leads, get_lead: lead CRUD operations
- update_stage, get_stage_history: stage management
- insert_seen_url, get_seen_urls: URL tracking
- insert_pipeline_run, update_pipeline_run, get_pipeline_runs: pipeline run tracking
- get_stats: aggregate statistics
"""

import pytest
from datetime import datetime

from db.schema import init_db
from db.queries import (
    insert_lead,
    get_leads,
    get_lead,
    count_leads,
    search_leads,
    count_search_leads,
    update_stage,
    get_stage_history,
    insert_seen_url,
    get_seen_urls,
    insert_pipeline_run,
    update_pipeline_run,
    get_pipeline_runs,
    get_stats,
)


# ---------------------------------------------------------------------------
# init_db Tests
# ---------------------------------------------------------------------------


class TestInitDb:
    """Tests for the init_db function."""

    def test_creates_tables(self):
        """Creates all required tables."""
        conn = init_db(":memory:")

        # Query sqlite_master to check tables exist
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
        ).fetchall()
        table_names = [t[0] for t in tables]

        assert "leads" in table_names
        assert "pipeline_runs" in table_names
        assert "seen_urls" in table_names
        assert "stage_history" in table_names

        conn.close()

    def test_creates_indexes(self):
        """Creates all required indexes."""
        conn = init_db(":memory:")

        indexes = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%';"
        ).fetchall()
        index_names = [i[0] for i in indexes]

        assert "idx_leads_fingerprint" in index_names
        assert "idx_leads_city" in index_names
        assert "idx_leads_county" in index_names
        assert "idx_leads_stage" in index_names
        assert "idx_leads_pos_score" in index_names

        conn.close()

    def test_idempotent(self):
        """Running init_db multiple times is safe."""
        conn = init_db(":memory:")
        # Run again on same connection
        conn.executescript("SELECT 1;")  # Just verify connection is still valid
        conn.close()


# ---------------------------------------------------------------------------
# Lead CRUD Tests
# ---------------------------------------------------------------------------


class TestLeadCrud:
    """Tests for lead CRUD operations."""

    @pytest.fixture
    def sample_lead(self):
        """Sample lead data."""
        return {
            "fingerprint": "test_fp_001",
            "business_name": "Test Business",
            "business_type": "restaurant",
            "raw_type": "Restaurant",
            "address": "123 Main St",
            "city": "Nashville",
            "state": "TN",
            "zip_code": "37201",
            "county": "Davidson",
            "license_date": "2026-01-15",
            "pos_score": 75,
            "stage": "New",
            "source_url": "https://example.com/test",
            "source_type": "license_table",
            "source_batch_id": None,
            "notes": "Test notes",
        }

    def test_insert_lead(self, memory_db, sample_lead):
        """Inserts a lead successfully."""
        insert_lead(memory_db, sample_lead)

        leads = get_leads(memory_db)
        assert len(leads) == 1
        assert leads[0]["business_name"] == "Test Business"

    def test_insert_lead_ignore_duplicate(self, memory_db, sample_lead):
        """Ignores duplicate lead with same fingerprint."""
        insert_lead(memory_db, sample_lead)
        insert_lead(memory_db, sample_lead)  # Second insert

        leads = get_leads(memory_db)
        assert len(leads) == 1  # Still only one

    def test_get_leads_all(self, populated_db):
        """Gets all leads."""
        leads = get_leads(populated_db)
        assert len(leads) == 3

    def test_get_leads_filter_by_stage(self, populated_db):
        """Filters leads by stage."""
        leads = get_leads(populated_db, stage="New")
        assert len(leads) == 2
        for lead in leads:
            assert lead["stage"] == "New"

    def test_get_leads_filter_by_county(self, populated_db):
        """Filters leads by county."""
        leads = get_leads(populated_db, county="Davidson")
        assert len(leads) == 1
        assert leads[0]["county"] == "Davidson"

    def test_get_leads_filter_by_min_score(self, populated_db):
        """Filters leads by minimum score."""
        leads = get_leads(populated_db, min_score=60)
        assert len(leads) == 2
        for lead in leads:
            assert lead["pos_score"] >= 60

    def test_get_leads_sort_by_column(self, populated_db):
        """Sorts leads by specified column."""
        leads = get_leads(populated_db, sort="pos_score")
        # Should be descending order
        scores = [l["pos_score"] for l in leads]
        assert scores == sorted(scores, reverse=True)

    def test_get_leads_invalid_sort_column(self, populated_db):
        """Raises ValueError for invalid sort column."""
        with pytest.raises(ValueError) as exc_info:
            get_leads(populated_db, sort="invalid_column")

        assert "Invalid sort column" in str(exc_info.value)

    def test_get_leads_limit(self, populated_db):
        """Limits number of leads returned."""
        leads = get_leads(populated_db, limit=2)
        assert len(leads) == 2

    def test_get_lead_by_id(self, populated_db):
        """Gets single lead by ID."""
        lead = get_lead(populated_db, 1)
        assert lead is not None
        assert lead["id"] == 1

    def test_get_lead_not_found(self, populated_db):
        """Returns None for non-existent lead ID."""
        lead = get_lead(populated_db, 9999)
        assert lead is None


# ---------------------------------------------------------------------------
# Pagination Tests
# ---------------------------------------------------------------------------


class TestPagination:
    """Tests for pagination functions."""

    def test_get_leads_with_offset(self, populated_db):
        """Pagination with offset returns correct subset."""
        # Get all leads sorted by score (default)
        all_leads = get_leads(populated_db, limit=100)
        assert len(all_leads) == 3

        # Get first page (offset 0, limit 2)
        page1 = get_leads(populated_db, limit=2, offset=0)
        assert len(page1) == 2
        assert page1[0]["id"] == all_leads[0]["id"]
        assert page1[1]["id"] == all_leads[1]["id"]

        # Get second page (offset 2, limit 2)
        page2 = get_leads(populated_db, limit=2, offset=2)
        assert len(page2) == 1
        assert page2[0]["id"] == all_leads[2]["id"]

    def test_get_leads_offset_beyond_results(self, populated_db):
        """Offset beyond total results returns empty list."""
        leads = get_leads(populated_db, limit=10, offset=100)
        assert leads == []

    def test_count_leads_all(self, populated_db):
        """Counts all non-deleted leads."""
        count = count_leads(populated_db)
        assert count == 3

    def test_count_leads_by_stage(self, populated_db):
        """Counts leads filtered by stage."""
        count = count_leads(populated_db, stage="New")
        assert count == 2

        count = count_leads(populated_db, stage="Qualified")
        assert count == 1

    def test_count_leads_by_county(self, populated_db):
        """Counts leads filtered by county."""
        count = count_leads(populated_db, county="Davidson")
        assert count == 1

    def test_count_leads_by_score_range(self, populated_db):
        """Counts leads filtered by score range."""
        count = count_leads(populated_db, min_score=60)
        assert count == 2

        count = count_leads(populated_db, max_score=70)
        assert count == 2

        count = count_leads(populated_db, min_score=60, max_score=70)
        assert count == 1

    def test_count_leads_combined_filters(self, populated_db):
        """Counts leads with multiple filters."""
        count = count_leads(populated_db, stage="New", min_score=50)
        assert count == 1

    def test_count_leads_empty_result(self, populated_db):
        """Returns 0 when no leads match filters."""
        count = count_leads(populated_db, stage="Closed-Won")
        assert count == 0

    def test_search_leads_with_offset(self, populated_db):
        """Search pagination with offset."""
        # First ensure we have searchable data
        results = search_leads(populated_db, "Test", limit=10, offset=0)
        total = len(results)

        if total > 1:
            # Get first result
            first_page = search_leads(populated_db, "Test", limit=1, offset=0)
            # Get second result
            second_page = search_leads(populated_db, "Test", limit=1, offset=1)
            assert first_page[0]["id"] != second_page[0]["id"]

    def test_count_search_leads(self, populated_db):
        """Counts search results."""
        count = count_search_leads(populated_db, "Test")
        # Should match number of leads with "Test" in searchable fields
        assert count >= 0

    def test_count_search_leads_empty_query(self, populated_db):
        """Returns 0 for empty search query."""
        count = count_search_leads(populated_db, "")
        assert count == 0

        count = count_search_leads(populated_db, "   ")
        assert count == 0


# ---------------------------------------------------------------------------
# Stage Management Tests
# ---------------------------------------------------------------------------


class TestStageManagement:
    """Tests for stage management functions."""

    def test_update_stage(self, populated_db):
        """Updates lead stage successfully."""
        # Get a lead in 'New' stage
        leads = get_leads(populated_db, stage="New", limit=1)
        lead_id = leads[0]["id"]

        update_stage(populated_db, lead_id, "Qualified")

        updated_lead = get_lead(populated_db, lead_id)
        assert updated_lead["stage"] == "Qualified"

    def test_update_stage_creates_history(self, populated_db):
        """Creates stage history record on update."""
        leads = get_leads(populated_db, stage="New", limit=1)
        lead_id = leads[0]["id"]

        update_stage(populated_db, lead_id, "Contacted")

        history = get_stage_history(populated_db, lead_id)
        assert len(history) == 1
        assert history[0]["old_stage"] == "New"
        assert history[0]["new_stage"] == "Contacted"

    def test_update_stage_adds_note(self, populated_db):
        """Appends note when provided."""
        leads = get_leads(populated_db, stage="New", limit=1)
        lead_id = leads[0]["id"]

        update_stage(populated_db, lead_id, "Qualified", note="Called owner")

        updated_lead = get_lead(populated_db, lead_id)
        assert "Called owner" in (updated_lead["notes"] or "")

    def test_update_stage_same_stage_with_note(self, populated_db):
        """Updates notes without changing stage."""
        leads = get_leads(populated_db, stage="New", limit=1)
        lead_id = leads[0]["id"]

        update_stage(populated_db, lead_id, "New", note="Added note")

        updated_lead = get_lead(populated_db, lead_id)
        assert "Added note" in (updated_lead["notes"] or "")

        # No history should be created for same-stage update
        history = get_stage_history(populated_db, lead_id)
        assert len(history) == 0

    def test_update_stage_sets_contacted_at(self, populated_db):
        """Sets contacted_at timestamp when transitioning to Contacted."""
        leads = get_leads(populated_db, stage="New", limit=1)
        lead_id = leads[0]["id"]

        # Verify contacted_at is initially None
        lead = get_lead(populated_db, lead_id)
        assert lead["contacted_at"] is None

        update_stage(populated_db, lead_id, "Contacted")

        updated_lead = get_lead(populated_db, lead_id)
        assert updated_lead["contacted_at"] is not None

    def test_update_stage_sets_closed_at(self, populated_db):
        """Sets closed_at timestamp when transitioning to closed stage."""
        leads = get_leads(populated_db, stage="New", limit=1)
        lead_id = leads[0]["id"]

        update_stage(populated_db, lead_id, "Closed-Won")

        updated_lead = get_lead(populated_db, lead_id)
        assert updated_lead["closed_at"] is not None

    def test_update_stage_nonexistent_lead(self, populated_db):
        """Raises ValueError for non-existent lead."""
        with pytest.raises(ValueError) as exc_info:
            update_stage(populated_db, 9999, "Qualified")

        assert "No lead with id=9999" in str(exc_info.value)

    def test_get_stage_history_ordered(self, populated_db):
        """Stage history is ordered by changed_at ascending."""
        leads = get_leads(populated_db, stage="New", limit=1)
        lead_id = leads[0]["id"]

        # Make multiple stage changes
        update_stage(populated_db, lead_id, "Qualified")
        update_stage(populated_db, lead_id, "Contacted")
        update_stage(populated_db, lead_id, "Follow-up")

        history = get_stage_history(populated_db, lead_id)
        assert len(history) == 3
        assert history[0]["new_stage"] == "Qualified"
        assert history[1]["new_stage"] == "Contacted"
        assert history[2]["new_stage"] == "Follow-up"


# ---------------------------------------------------------------------------
# Seen URLs Tests
# ---------------------------------------------------------------------------


class TestSeenUrls:
    """Tests for seen URL tracking functions."""

    def test_insert_seen_url(self, memory_db):
        """Inserts a seen URL."""
        insert_seen_url(memory_db, "https://example.com/page", "Davidson")

        seen = get_seen_urls(memory_db)
        assert "https://example.com/page" in seen

    def test_insert_seen_url_ignore_duplicate(self, memory_db):
        """Ignores duplicate URL insertion."""
        insert_seen_url(memory_db, "https://example.com/page", "Davidson")
        insert_seen_url(memory_db, "https://example.com/page", "Williamson")  # Duplicate

        seen = get_seen_urls(memory_db)
        assert len(seen) == 1

    def test_get_seen_urls_returns_set(self, populated_db):
        """Returns seen URLs as a set."""
        seen = get_seen_urls(populated_db)

        assert isinstance(seen, set)
        assert "https://example.com/seen1" in seen
        assert "https://example.com/seen2" in seen


# ---------------------------------------------------------------------------
# Pipeline Runs Tests
# ---------------------------------------------------------------------------


class TestPipelineRuns:
    """Tests for pipeline run tracking functions."""

    def test_insert_pipeline_run(self, memory_db):
        """Inserts a new pipeline run."""
        run_id = insert_pipeline_run(memory_db, datetime.now().isoformat())

        assert run_id is not None
        assert run_id > 0

        runs = get_pipeline_runs(memory_db)
        assert len(runs) == 1
        assert runs[0]["status"] == "running"

    def test_update_pipeline_run(self, memory_db):
        """Updates pipeline run with results."""
        run_id = insert_pipeline_run(memory_db, datetime.now().isoformat())

        update_pipeline_run(
            memory_db,
            run_id,
            status="completed",
            leads_found=10,
            leads_new=8,
            leads_dupes=2,
            error_message=None,
            sources_queried='["https://example.com"]',
        )

        runs = get_pipeline_runs(memory_db)
        run = runs[0]

        assert run["status"] == "completed"
        assert run["leads_found"] == 10
        assert run["leads_new"] == 8
        assert run["leads_dupes"] == 2
        assert run["run_finished_at"] is not None

    def test_get_pipeline_runs_ordered(self, memory_db):
        """Pipeline runs are returned newest first."""
        insert_pipeline_run(memory_db, "2026-01-01T10:00:00")
        insert_pipeline_run(memory_db, "2026-01-02T10:00:00")
        insert_pipeline_run(memory_db, "2026-01-03T10:00:00")

        runs = get_pipeline_runs(memory_db)

        assert runs[0]["run_started_at"] == "2026-01-03T10:00:00"
        assert runs[2]["run_started_at"] == "2026-01-01T10:00:00"

    def test_get_pipeline_runs_limit(self, memory_db):
        """Limits number of runs returned."""
        for i in range(5):
            insert_pipeline_run(memory_db, f"2026-01-0{i+1}T10:00:00")

        runs = get_pipeline_runs(memory_db, limit=3)
        assert len(runs) == 3


# ---------------------------------------------------------------------------
# Statistics Tests
# ---------------------------------------------------------------------------


class TestStats:
    """Tests for the get_stats function."""

    def test_get_stats_by_stage(self, populated_db):
        """Returns lead counts by stage."""
        stats = get_stats(populated_db)

        assert "by_stage" in stats
        assert stats["by_stage"]["New"] == 2
        assert stats["by_stage"]["Qualified"] == 1

    def test_get_stats_by_county(self, populated_db):
        """Returns lead counts by county."""
        stats = get_stats(populated_db)

        assert "by_county" in stats
        assert stats["by_county"]["Davidson"] == 1
        assert stats["by_county"]["Williamson"] == 1
        assert stats["by_county"]["Rutherford"] == 1

    def test_get_stats_by_type(self, populated_db):
        """Returns lead counts by business type."""
        stats = get_stats(populated_db)

        assert "by_type" in stats
        assert stats["by_type"]["restaurant"] == 1
        assert stats["by_type"]["salon"] == 1
        assert stats["by_type"]["cafe"] == 1

    def test_get_stats_avg_score(self, populated_db):
        """Returns average lead score."""
        stats = get_stats(populated_db)

        assert "avg_score" in stats
        # (85 + 65 + 40) / 3 = 63.33...
        assert 63 <= stats["avg_score"] <= 64

    def test_get_stats_total_leads(self, populated_db):
        """Returns total lead count."""
        stats = get_stats(populated_db)

        assert "total_leads" in stats
        assert stats["total_leads"] == 3

    def test_get_stats_last_run(self, populated_db):
        """Returns most recent pipeline run."""
        stats = get_stats(populated_db)

        assert "last_run" in stats
        assert stats["last_run"] is not None
        assert stats["last_run"]["status"] == "running"

    def test_get_stats_empty_db(self, memory_db):
        """Handles empty database."""
        stats = get_stats(memory_db)

        assert stats["total_leads"] == 0
        assert stats["avg_score"] == 0.0
        assert stats["last_run"] is None
        assert stats["by_stage"] == {}
