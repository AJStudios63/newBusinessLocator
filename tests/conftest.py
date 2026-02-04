"""
Shared pytest fixtures for newBusinessLocator tests.

Provides:
- In-memory SQLite database fixtures
- Mock Tavily API response fixtures
- Sample YAML configuration fixtures
- Sample business record fixtures
"""

import sqlite3
from datetime import datetime, timedelta

import pytest

from db.schema import init_db


# ---------------------------------------------------------------------------
# Database Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def memory_db():
    """Create an in-memory SQLite database with schema initialized."""
    conn = init_db(":memory:")
    yield conn
    conn.close()


@pytest.fixture
def populated_db(memory_db):
    """In-memory database with sample data pre-populated."""
    # Insert a pipeline run
    memory_db.execute(
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
        memory_db.execute(
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

    # Insert some seen URLs
    memory_db.execute(
        "INSERT INTO seen_urls (url, county) VALUES (?, ?);",
        ("https://example.com/seen1", "Davidson"),
    )
    memory_db.execute(
        "INSERT INTO seen_urls (url, county) VALUES (?, ?);",
        ("https://example.com/seen2", "Williamson"),
    )

    memory_db.commit()
    yield memory_db


# ---------------------------------------------------------------------------
# Mock Tavily Response Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_tavily_search_results():
    """Sample Tavily search API response results."""
    return [
        {
            "title": "New Business License Applications - Davidson County",
            "url": "https://davidsoncountysource.com/new-business-licenses-jan-2026",
            "content": "New business licenses filed in Davidson County...",
        },
        {
            "title": "Joe's Italian Kitchen Opening in Nashville - News",
            "url": "https://wsmv.com/news/joes-italian-opening",
            "content": "Joe's Italian Kitchen announces grand opening in downtown Nashville...",
        },
        {
            "title": "The Coffee House - Franklin, TN",
            "url": "https://random-news.com/coffee-house-franklin",
            "content": "A new coffee shop is opening in Franklin next month...",
        },
        {
            "title": "Blocked Site Video - YouTube",
            "url": "https://youtube.com/watch?v=abc123",
            "content": "Video about new businesses...",
        },
    ]


@pytest.fixture
def mock_tavily_extract_license_table():
    """Sample Tavily extract response for a license table page."""
    return {
        "url": "https://davidsoncountysource.com/new-business-licenses-jan-2026",
        "title": "New Business Licenses - Davidson County",
        "content": """
# New Business Licenses - January 2026

The following businesses have filed new license applications in Davidson County.

| Date | Business Name | Product Type | Address |
|------|---------------|--------------|---------|
| 01/15/2026 | Nashville Noodles LLC | Restaurant | 789 Broadway, Nashville, TN 37203 |
| 01/14/2026 | Quick Clips Barber | Barber Shop | 456 Church St, Nashville, TN 37201 |
| 01/13/2026 | Tech Solutions Inc | Consulting | 123 Commerce Way, Nashville 37210 |

For more information, contact the clerk's office.
""",
    }


@pytest.fixture
def mock_tavily_extract_news_article():
    """Sample Tavily extract response for a news article page."""
    return {
        "url": "https://wsmv.com/news/new-restaurants-nashville",
        "title": "New Restaurants Opening in Nashville Area",
        "content": """
# New Restaurants Coming to Nashville

## Fire & Stone Pizza

*1234 West End Ave, Nashville, TN 37203*

This authentic Italian pizzeria is bringing wood-fired pizza to Nashville. Expected to open in February.

## The Taco Spot

*567 Nolensville Pike, Nashville*

A new taco restaurant featuring authentic Mexican cuisine is set to open next month in South Nashville.

## Sunrise Bakery

*890 Main St, Franklin, TN 37064*

Franklin residents can look forward to fresh pastries and artisan breads at this new bakery.
""",
    }


# ---------------------------------------------------------------------------
# Sample Configuration Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_sources_config():
    """Sample sources.yaml configuration as a dict."""
    return {
        "counties": {
            "Davidson": ["Nashville", "Antioch", "Madison", "Hermitage"],
            "Williamson": ["Franklin", "Brentwood", "Nolensville"],
            "Rutherford": ["Murfreesboro", "Smyrna", "La Vergne"],
        },
        "extractable_domains": [
            "davidsoncountysource.com",
            "wsmv.com",
            "tennessean.com",
        ],
        "blocked_domains": [
            "youtube.com",
            "facebook.com",
            "instagram.com",
        ],
        "queries": [
            {"query": "site:davidsoncountysource.com new business licenses", "county": "Davidson", "tier": "A"},
            {"query": "new business opening Nashville 2026", "county": "Davidson", "tier": "B"},
        ],
    }


@pytest.fixture
def sample_scoring_config():
    """Sample scoring.yaml configuration as a dict."""
    return {
        "type_scores": {
            "restaurant": 50,
            "bar": 48,
            "cafe": 45,
            "retail": 45,
            "salon": 40,
            "bakery": 40,
            "other": 10,
        },
        "business_type_keywords": {
            "restaurant": ["restaurant", "grill", "pizza", "sushi"],
            "bar": ["bar", "tavern", "pub"],
            "cafe": ["cafe", "coffee", "tea"],
            "retail": ["retail", "store", "shop", "boutique"],
            "salon": ["salon", "barber", "hair", "beauty"],
            "bakery": ["bakery", "pastry", "donut"],
        },
        "source_scores": {
            "license_table": 20,
            "news_article": 15,
            "search_snippet": 8,
        },
        "address_scores": {
            "street_city_zip": 15,
            "street_city": 10,
            "city_only": 5,
            "none": 0,
        },
        "recency_scores": [
            {"max_days": 7, "score": 15},
            {"max_days": 14, "score": 10},
            {"max_days": 30, "score": 5},
            {"max_days": None, "score": 0},
        ],
    }


@pytest.fixture
def sample_chains_config():
    """Sample chains.yaml configuration as a dict."""
    return {
        "chains": [
            "Starbucks",
            "McDonald's",
            "Subway",
            "Chick-fil-A",
            "Waffle House",
            "Cracker Barrel",
        ],
    }


# ---------------------------------------------------------------------------
# Sample Business Record Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_raw_extract_license():
    """Sample RawExtract dict from a license table source."""
    return {
        "raw_content": """
| Date | Business Name | Product Type | Address |
|------|---------------|--------------|---------|
| 01/15/2026 | Nashville Noodles LLC | Restaurant | 789 Broadway, Nashville, TN 37203 |
| 01/14/2026 | Quick Clips Barber | Barber Shop | 456 Church St, Nashville, TN 37201 |
""",
        "source_url": "https://davidsoncountysource.com/licenses",
        "county": "Davidson",
        "source_type": "license_table",
        "title": "New Business Licenses",
    }


@pytest.fixture
def sample_raw_extract_news():
    """Sample RawExtract dict from a news article source."""
    return {
        "raw_content": """
## Fire & Stone Pizza

*1234 West End Ave, Nashville, TN 37203*

This authentic Italian pizzeria is bringing wood-fired pizza to Nashville.

## The Taco Spot

*567 Nolensville Pike, Nashville*

A new taco restaurant is opening next month.
""",
        "source_url": "https://wsmv.com/news/restaurants",
        "county": "Davidson",
        "source_type": "news_article",
        "title": "New Restaurants Opening",
    }


@pytest.fixture
def sample_raw_extract_snippet():
    """Sample RawExtract dict from a search snippet."""
    return {
        "raw_content": "A new coffee shop is opening in Franklin next month...",
        "source_url": "https://news.com/coffee-shop",
        "county": "Williamson",
        "source_type": "search_snippet",
        "title": "The Coffee House - Franklin, TN",
    }


@pytest.fixture
def sample_business_record():
    """Sample BusinessRecord dict after parsing."""
    return {
        "business_name": "Nashville Noodles LLC",
        "business_type": None,
        "raw_type": "Restaurant",
        "address": "789 Broadway",
        "city": "Nashville",
        "state": "TN",
        "zip_code": "37203",
        "county": "Davidson",
        "license_date": "01/15/2026",
        "source_url": "https://davidsoncountysource.com/licenses",
        "source_type": "license_table",
        "notes": None,
    }


@pytest.fixture
def sample_business_record_scored():
    """Sample BusinessRecord dict after scoring."""
    return {
        "business_name": "Nashville Noodles LLC",
        "business_type": "restaurant",
        "raw_type": "Restaurant",
        "address": "789 Broadway",
        "city": "Nashville",
        "state": "TN",
        "zip_code": "37203",
        "county": "Davidson",
        "license_date": datetime.now().strftime("%Y-%m-%d"),
        "source_url": "https://davidsoncountysource.com/licenses",
        "source_type": "license_table",
        "notes": None,
        "pos_score": 100,  # 50 (type) + 20 (source) + 15 (addr) + 15 (recency)
        "fingerprint": "abc123",
        "stage": "New",
    }
