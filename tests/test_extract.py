"""
Tests for etl/extract.py

Tests the extraction functions:
- run_extract: main extraction entry point
- _get_domain: extracts domain from URL
- _determine_source_type: classifies page by title
- _domain_matches: checks if domain matches a pattern list
- _validate_sources: validates sources.yaml configuration
"""

import pytest
from unittest.mock import MagicMock, patch

from etl.extract import (
    run_extract,
    _get_domain,
    _determine_source_type,
    _domain_matches,
    _validate_sources,
)


# ---------------------------------------------------------------------------
# Helper Function Tests
# ---------------------------------------------------------------------------


class TestGetDomain:
    """Tests for the _get_domain helper function."""

    def test_extracts_simple_domain(self):
        """Extracts domain from simple URL."""
        assert _get_domain("https://example.com/page") == "example.com"

    def test_strips_www_prefix(self):
        """Strips www. prefix from domain."""
        assert _get_domain("https://www.example.com/page") == "example.com"

    def test_handles_subdomain(self):
        """Preserves subdomains other than www."""
        assert _get_domain("https://news.example.com/article") == "news.example.com"

    def test_handles_http(self):
        """Handles http:// URLs."""
        assert _get_domain("http://example.com/page") == "example.com"

    def test_handles_no_path(self):
        """Handles URLs without path."""
        assert _get_domain("https://example.com") == "example.com"


class TestDetermineSourceType:
    """Tests for the _determine_source_type helper function."""

    def test_detects_license_table_from_title(self):
        """Detects license_table from 'new business license' in title."""
        assert _determine_source_type("New Business License Applications") == "license_table"

    def test_detects_license_table_plural(self):
        """Detects license_table from 'business licenses' in title."""
        assert _determine_source_type("Business Licenses - January 2026") == "license_table"

    def test_case_insensitive(self):
        """Detection is case-insensitive."""
        assert _determine_source_type("NEW BUSINESS LICENSE") == "license_table"

    def test_defaults_to_news_article(self):
        """Defaults to news_article for other titles."""
        assert _determine_source_type("New Restaurants Opening in Nashville") == "news_article"
        assert _determine_source_type("Grand Opening Announcement") == "news_article"


class TestDomainMatches:
    """Tests for the _domain_matches helper function."""

    def test_exact_match(self):
        """Matches exact domain."""
        domain_list = ["example.com", "test.com"]
        assert _domain_matches("example.com", domain_list) is True

    def test_subdomain_match(self):
        """Matches subdomains of listed domains."""
        domain_list = ["example.com"]
        assert _domain_matches("news.example.com", domain_list) is True

    def test_no_partial_match(self):
        """Does not match partial domain names."""
        domain_list = ["example.com"]
        # "notexample.com" should not match "example.com"
        assert _domain_matches("notexample.com", domain_list) is False

    def test_no_match_returns_false(self):
        """Returns False when no match found."""
        domain_list = ["example.com", "test.com"]
        assert _domain_matches("other.com", domain_list) is False

    def test_empty_list(self):
        """Returns False for empty domain list."""
        assert _domain_matches("example.com", []) is False


class TestValidateSources:
    """Tests for the _validate_sources helper function."""

    def test_valid_config_passes(self, sample_sources_config):
        """Valid configuration passes validation."""
        # Should not raise
        _validate_sources(sample_sources_config)

    def test_raises_on_missing_queries(self):
        """Raises ValueError when queries key is missing."""
        config = {
            "extractable_domains": [],
            "blocked_domains": [],
        }
        with pytest.raises(ValueError) as exc_info:
            _validate_sources(config)

        assert "queries" in str(exc_info.value)

    def test_raises_on_wrong_type(self):
        """Raises ValueError when key has wrong type."""
        config = {
            "queries": "not a list",  # Should be list
            "extractable_domains": [],
            "blocked_domains": [],
        }
        with pytest.raises(ValueError) as exc_info:
            _validate_sources(config)

        assert "should be list" in str(exc_info.value)


# ---------------------------------------------------------------------------
# run_extract Tests (with mocks)
# ---------------------------------------------------------------------------


class TestRunExtract:
    """Tests for the run_extract function with mocked dependencies."""

    @pytest.fixture
    def mock_client(self, mock_tavily_search_results):
        """Create a mock TavilyClient."""
        client = MagicMock()
        client.search.return_value = mock_tavily_search_results
        client.extract.return_value = {
            "url": "https://davidsoncountysource.com/licenses",
            "title": "New Business Licenses",
            "content": "| Date | Business | Type |\n|---|---|---|\n| 01/15 | Test | Restaurant |",
        }
        return client

    @pytest.fixture
    def mock_sources_yaml(self, sample_sources_config, tmp_path):
        """Create a temporary sources.yaml file."""
        import yaml

        sources_file = tmp_path / "sources.yaml"
        with open(sources_file, "w") as f:
            yaml.dump(sample_sources_config, f)
        return sources_file

    def test_returns_raw_extracts(self, mock_client, sample_sources_config):
        """Returns a list of RawExtract dicts."""
        with patch("etl.extract._load_sources", return_value=sample_sources_config):
            results = run_extract(client=mock_client, use_db=False)

        assert isinstance(results, list)
        # Should have processed some results
        assert len(results) > 0

    def test_filters_blocked_domains(self, mock_client, sample_sources_config):
        """Filters out results from blocked domains."""
        # Add a youtube result that should be filtered
        mock_client.search.return_value = [
            {
                "title": "Blocked Video",
                "url": "https://youtube.com/watch?v=abc",
                "content": "Video content",
            },
            {
                "title": "Valid Result",
                "url": "https://somesite.com/page",
                "content": "Page content",
            },
        ]

        with patch("etl.extract._load_sources", return_value=sample_sources_config):
            results = run_extract(client=mock_client, use_db=False)

        # YouTube result should be filtered out
        urls = [r["source_url"] for r in results]
        assert "https://youtube.com/watch?v=abc" not in urls

    def test_extracts_from_extractable_domains(self, mock_client, sample_sources_config):
        """Calls extract for URLs from extractable domains."""
        mock_client.search.return_value = [
            {
                "title": "License Table",
                "url": "https://davidsoncountysource.com/licenses",
                "content": "Search snippet",
            },
        ]
        mock_client.extract.return_value = {
            "title": "New Business Licenses",
            "content": "Full page content with tables",
        }

        with patch("etl.extract._load_sources", return_value=sample_sources_config):
            results = run_extract(client=mock_client, use_db=False)

        # Extract should have been called for the extractable domain
        mock_client.extract.assert_called()

    def test_creates_snippet_for_non_extractable(self, mock_client, sample_sources_config):
        """Creates search_snippet for non-extractable domains."""
        mock_client.search.return_value = [
            {
                "title": "Random Site",
                "url": "https://randomsite.com/page",
                "content": "Search result snippet content",
            },
        ]

        with patch("etl.extract._load_sources", return_value=sample_sources_config):
            results = run_extract(client=mock_client, use_db=False)

        # Should have a search_snippet result
        snippets = [r for r in results if r["source_type"] == "search_snippet"]
        assert len(snippets) > 0
        assert snippets[0]["raw_content"] == "Search result snippet content"

    def test_skips_seen_urls_from_db(self, mock_client, sample_sources_config, memory_db):
        """Skips URLs that are already in the seen_urls table."""
        # Add a URL to seen_urls
        memory_db.execute(
            "INSERT INTO seen_urls (url, county) VALUES (?, ?);",
            ("https://somesite.com/seen-page", "Davidson"),
        )
        memory_db.commit()

        mock_client.search.return_value = [
            {
                "title": "Already Seen",
                "url": "https://somesite.com/seen-page",
                "content": "This should be skipped",
            },
            {
                "title": "New Page",
                "url": "https://somesite.com/new-page",
                "content": "This should be included",
            },
        ]

        with patch("etl.extract._load_sources", return_value=sample_sources_config):
            results = run_extract(client=mock_client, conn=memory_db, use_db=True)

        urls = [r["source_url"] for r in results]
        assert "https://somesite.com/seen-page" not in urls
        assert "https://somesite.com/new-page" in urls

    def test_deduplicates_within_run(self, mock_client, sample_sources_config):
        """Deduplicates URLs encountered multiple times in the same run."""
        # Same URL returned by multiple queries
        mock_client.search.return_value = [
            {
                "title": "Duplicate Result",
                "url": "https://somesite.com/same-page",
                "content": "Content",
            },
        ]

        # Multiple queries will return the same URL
        sample_sources_config["queries"] = [
            {"query": "query 1", "county": "Davidson"},
            {"query": "query 2", "county": "Davidson"},
        ]

        with patch("etl.extract._load_sources", return_value=sample_sources_config):
            results = run_extract(client=mock_client, use_db=False)

        # Should only have one result even though it was returned twice
        assert len([r for r in results if r["source_url"] == "https://somesite.com/same-page"]) == 1

    def test_preserves_county_from_query(self, mock_client, sample_sources_config):
        """Preserves county from the query configuration."""
        mock_client.search.return_value = [
            {
                "title": "Result",
                "url": "https://somesite.com/page",
                "content": "Content",
            },
        ]

        # First query has Davidson county
        sample_sources_config["queries"] = [
            {"query": "test query", "county": "Davidson"},
        ]

        with patch("etl.extract._load_sources", return_value=sample_sources_config):
            results = run_extract(client=mock_client, use_db=False)

        assert results[0]["county"] == "Davidson"

    def test_handles_empty_search_results(self, mock_client, sample_sources_config):
        """Handles queries that return empty results."""
        mock_client.search.return_value = []

        with patch("etl.extract._load_sources", return_value=sample_sources_config):
            results = run_extract(client=mock_client, use_db=False)

        assert results == []

    def test_handles_failed_extraction(self, mock_client, sample_sources_config):
        """Handles failed extractions gracefully."""
        mock_client.search.return_value = [
            {
                "title": "Extractable Page",
                "url": "https://davidsoncountysource.com/page",
                "content": "Snippet",
            },
        ]
        mock_client.extract.return_value = None  # Extraction failed

        with patch("etl.extract._load_sources", return_value=sample_sources_config):
            results = run_extract(client=mock_client, use_db=False)

        # Should skip the failed extraction
        assert len(results) == 0
