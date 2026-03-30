"""
Tests for etl/transform.py

Tests the transformation functions:
- classify: classifies business type from raw_type
- is_chain: checks if business is a known chain
- is_article_title: detects article titles masquerading as business names
- score_lead: computes lead quality score
- infer_county: infers county from city
- deduplicate: deduplicates records by fingerprint
"""

import pytest
from datetime import datetime, timedelta

from etl.transform import (
    classify,
    is_chain,
    is_article_title,
    score_lead,
    infer_county,
    deduplicate,
    run_transform,
    _parse_date,
    _build_city_to_county_map,
    _validate_scoring,
)


# ---------------------------------------------------------------------------
# classify Tests
# ---------------------------------------------------------------------------


class TestClassify:
    """Tests for the classify function."""

    @pytest.fixture
    def type_keywords(self):
        """Sample type keywords from scoring config."""
        return {
            "restaurant": ["restaurant", "grill", "pizza", "sushi"],
            "bar": ["bar", "tavern", "pub"],
            "cafe": ["cafe", "coffee", "tea"],
            "retail": ["retail", "store", "shop"],
            "salon": ["salon", "barber", "hair"],
        }

    def test_classifies_restaurant(self, type_keywords):
        """Classifies raw_type containing 'restaurant' as restaurant."""
        record = {"raw_type": "Restaurant"}
        result = classify(record, type_keywords)

        assert result["business_type"] == "restaurant"
        assert result is record  # Mutates in place

    def test_classifies_by_keyword_substring(self, type_keywords):
        """Classifies by keyword substring match."""
        record = {"raw_type": "Pizza Parlor"}
        classify(record, type_keywords)

        assert record["business_type"] == "restaurant"

    def test_classifies_hair_salon_as_salon(self, type_keywords):
        """Classifies hair salon as salon."""
        record = {"raw_type": "Hair Salon"}
        classify(record, type_keywords)

        assert record["business_type"] == "salon"

    def test_case_insensitive_match(self, type_keywords):
        """Classification is case-insensitive."""
        record = {"raw_type": "COFFEE SHOP"}
        classify(record, type_keywords)

        assert record["business_type"] == "cafe"

    def test_defaults_to_other_when_no_match(self, type_keywords):
        """Defaults to 'other' when no keyword matches."""
        record = {"raw_type": "Consulting Firm"}
        classify(record, type_keywords)

        assert record["business_type"] == "other"

    def test_defaults_to_other_when_raw_type_empty(self, type_keywords):
        """Defaults to 'other' when raw_type is empty string."""
        record = {"raw_type": ""}
        classify(record, type_keywords)

        assert record["business_type"] == "other"

    def test_defaults_to_other_when_raw_type_none(self, type_keywords):
        """Defaults to 'other' when raw_type is None and no business_name match."""
        record = {"raw_type": None}
        classify(record, type_keywords)

        assert record["business_type"] == "other"

    def test_fallback_to_business_name_when_raw_type_empty(self, type_keywords):
        """Falls back to business_name when raw_type is empty."""
        record = {"raw_type": "", "business_name": "Joe's Pizza Palace"}
        classify(record, type_keywords)

        assert record["business_type"] == "restaurant"

    def test_fallback_to_business_name_when_raw_type_none(self, type_keywords):
        """Falls back to business_name when raw_type is None."""
        record = {"raw_type": None, "business_name": "Downtown Hair Salon"}
        classify(record, type_keywords)

        assert record["business_type"] == "salon"

    def test_raw_type_takes_priority_over_business_name(self, type_keywords):
        """raw_type match takes priority over business_name match."""
        record = {"raw_type": "Coffee Shop", "business_name": "The Pizza Cafe"}
        classify(record, type_keywords)

        # Should match cafe from raw_type, not restaurant from business_name
        assert record["business_type"] == "cafe"

    def test_first_match_wins(self, type_keywords):
        """First matching keyword in order wins."""
        # If keywords had overlapping matches, first wins
        record = {"raw_type": "Restaurant Bar"}
        classify(record, type_keywords)

        # Restaurant comes before bar in the fixture
        assert record["business_type"] == "restaurant"


# ---------------------------------------------------------------------------
# is_chain Tests
# ---------------------------------------------------------------------------


class TestIsChain:
    """Tests for the is_chain function."""

    @pytest.fixture
    def chain_list(self):
        """Sample chain list."""
        return ["Starbucks", "McDonald's", "Subway", "Chick-fil-A", "Waffle House"]

    def test_identifies_exact_chain_name(self, chain_list):
        """Identifies exact chain name match."""
        assert is_chain("Starbucks", chain_list) is True

    def test_identifies_chain_as_substring(self, chain_list):
        """Identifies chain when it's a substring of business name."""
        assert is_chain("Starbucks Coffee #1234", chain_list) is True
        assert is_chain("McDonald's of Nashville", chain_list) is True

    def test_case_insensitive(self, chain_list):
        """Chain detection is case-insensitive."""
        assert is_chain("SUBWAY", chain_list) is True
        assert is_chain("waffle house", chain_list) is True

    def test_returns_false_for_non_chain(self, chain_list):
        """Returns False for non-chain business."""
        assert is_chain("Joe's Local Diner", chain_list) is False
        assert is_chain("Nashville Coffee Co", chain_list) is False

    def test_empty_business_name(self, chain_list):
        """Returns False for empty business name."""
        assert is_chain("", chain_list) is False

    def test_partial_match_that_isnt_chain(self, chain_list):
        """Doesn't false positive on partial matches."""
        # "Sub" is not Subway
        assert is_chain("Sub Shop", chain_list) is False


# ---------------------------------------------------------------------------
# is_article_title Tests
# ---------------------------------------------------------------------------


class TestIsArticleTitle:
    """Tests for the is_article_title function."""

    # -------------------------------------------------------------------------
    # Rule 1: Starts with number followed by space
    # -------------------------------------------------------------------------

    def test_starts_with_number_and_space(self):
        """Detects titles starting with number + space."""
        assert is_article_title("5 Nashville Restaurants Opening This Month") is True
        assert is_article_title("10 anticipated new places to eat") is True
        assert is_article_title("12 New Businesses Coming to Franklin") is True

    def test_number_without_space_not_filtered(self):
        """Does not filter names where number is part of the name."""
        assert is_article_title("7-Eleven") is False
        assert is_article_title("3rd & Lindsley") is False
        assert is_article_title("21c Museum Hotel") is False

    # -------------------------------------------------------------------------
    # Rule 2: Known article-title patterns
    # -------------------------------------------------------------------------

    def test_whats_coming_pattern(self):
        """Detects 'What's Coming' pattern."""
        assert is_article_title("What's Coming to Nashville in 2026") is True
        assert is_article_title("Whats Coming to Williamson County") is True

    def test_coming_soon_to_pattern(self):
        """Detects 'Coming Soon to' pattern."""
        assert is_article_title("Coming Soon to Nashville! 10 Exciting Additions") is True
        assert is_article_title("Coming Soon to Franklin") is True

    def test_new_businesses_bare_pattern(self):
        """Detects bare 'New Businesses' without specific name."""
        assert is_article_title("New Businesses") is True
        assert is_article_title("New Business") is True
        # Should NOT match if there's more to the name
        assert is_article_title("New Business Solutions LLC") is False

    def test_economic_development_pattern(self):
        """Detects 'Economic Development' pattern."""
        assert is_article_title("Davidson County Economic Development Report") is True
        assert is_article_title("Economic Development News") is True

    def test_calendar_pattern(self):
        """Detects 'Calendar' pattern."""
        assert is_article_title("Business Events Calendar - Nashville") is True
        assert is_article_title("2026 Calendar of Openings") is True

    def test_new_in_city_pattern(self):
        """Detects 'New in [City]' pattern."""
        assert is_article_title("New in Nashville This Week") is True
        assert is_article_title("New in Franklin: Restaurant Roundup") is True

    def test_best_new_pattern(self):
        """Detects 'Best New' pattern."""
        assert is_article_title("Best New Restaurants in Nashville") is True
        assert is_article_title("The Best New Bars of 2026") is True

    def test_top_number_pattern(self):
        """Detects 'Top [number]' pattern."""
        assert is_article_title("Top 10 New Restaurants") is True
        assert is_article_title("Top 5 Places to Eat") is True

    def test_opening_soon_pattern(self):
        """Detects 'Opening Soon' pattern."""
        assert is_article_title("Restaurants Opening Soon in Nashville") is True
        assert is_article_title("Opening Soon: New Retail Complex") is True

    def test_grand_opening_pattern(self):
        """Detects 'Grand Opening' pattern."""
        assert is_article_title("Grand Opening Celebrations This Weekend") is True
        assert is_article_title("Nashville Grand Opening Events") is True

    def test_exciting_additions_pattern(self):
        """Detects 'Exciting Additions' pattern."""
        assert is_article_title("10 Exciting Additions to Nashville's Food Scene") is True
        assert is_article_title("Exciting Addition to Downtown") is True

    # -------------------------------------------------------------------------
    # Rule 3: Name too long (> 60 characters)
    # -------------------------------------------------------------------------

    def test_name_over_60_characters(self):
        """Detects names longer than 60 characters."""
        long_name = "A" * 61
        assert is_article_title(long_name) is True

    def test_name_exactly_60_characters(self):
        """Does not filter names exactly 60 characters."""
        name_60 = "A" * 60
        assert is_article_title(name_60) is False

    def test_name_under_60_characters(self):
        """Does not filter normal-length names."""
        assert is_article_title("Rose, a Luxury Spa and Salon") is False
        assert is_article_title("The Trinity: Where Wellness Begins") is False

    # -------------------------------------------------------------------------
    # Valid business names (should NOT be filtered)
    # -------------------------------------------------------------------------

    def test_valid_business_names_not_filtered(self):
        """Real business names should not be filtered."""
        valid_names = [
            "WHAT'S NEW SALON & BARBER",  # Contains "what's" but it's the name
            "Rose, a Luxury Spa and Salon",
            "The Trinity: Where Wellness Begins",
            "House of Her",
            "Joe's Pizza Palace",
            "Downtown Hair Salon",
            "Nashville Coffee Co",
            "Biscuit Love",
            "Hattie B's Hot Chicken",
            "The Pharmacy Burger Parlor",
        ]
        for name in valid_names:
            assert is_article_title(name) is False, f"'{name}' should not be filtered"

    # -------------------------------------------------------------------------
    # Edge cases
    # -------------------------------------------------------------------------

    def test_empty_name(self):
        """Returns False for empty name."""
        assert is_article_title("") is False

    def test_none_name(self):
        """Returns False for None name."""
        assert is_article_title(None) is False

    def test_whitespace_only_name(self):
        """Returns False for whitespace-only name."""
        assert is_article_title("   ") is False


# ---------------------------------------------------------------------------
# score_lead Tests
# ---------------------------------------------------------------------------


class TestScoreLead:
    """Tests for the score_lead function."""

    @pytest.fixture
    def scoring_config(self):
        """Sample scoring configuration."""
        return {
            "type_scores": {
                "restaurant": 50,
                "bar": 48,
                "cafe": 45,
                "salon": 40,
                "other": 10,
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

    def test_max_score_for_perfect_lead(self, scoring_config):
        """Perfect lead with all components maxed out scores 100."""
        record = {
            "business_type": "restaurant",  # 50 points
            "source_type": "license_table",  # 20 points
            "address": "123 Main St",  # }
            "city": "Nashville",  # } 15 points
            "zip_code": "37201",  # }
            "license_date": datetime.now().strftime("%Y-%m-%d"),  # 15 points
        }
        score = score_lead(record, scoring_config)

        assert score == 100
        assert record["pos_score"] == 100

    def test_type_score_component(self, scoring_config):
        """Type score component is correctly applied."""
        record = {
            "business_type": "cafe",  # 45 points
            "source_type": "search_snippet",  # 8 points
        }
        score = score_lead(record, scoring_config)

        # 45 + 8 + 0 (no address) + 0 (no date) = 53
        assert score == 53

    def test_defaults_to_other_type_score(self, scoring_config):
        """Uses 'other' type score when business_type is unknown."""
        record = {
            "business_type": "unknown_type",
            "source_type": "search_snippet",
        }
        score = score_lead(record, scoring_config)

        # 10 (other default) + 8 = 18
        assert score == 18

    def test_address_completeness_street_city_zip(self, scoring_config):
        """Full address with street, city, zip gets max address score."""
        record = {
            "business_type": "other",
            "source_type": "search_snippet",
            "address": "123 Main St",
            "city": "Nashville",
            "zip_code": "37201",
        }
        score = score_lead(record, scoring_config)

        # 10 + 8 + 15 = 33
        assert score == 33

    def test_address_completeness_street_city(self, scoring_config):
        """Street and city without zip gets partial address score."""
        record = {
            "business_type": "other",
            "source_type": "search_snippet",
            "address": "123 Main St",
            "city": "Nashville",
        }
        score = score_lead(record, scoring_config)

        # 10 + 8 + 10 = 28
        assert score == 28

    def test_address_completeness_city_only(self, scoring_config):
        """City only gets minimal address score."""
        record = {
            "business_type": "other",
            "source_type": "search_snippet",
            "city": "Nashville",
        }
        score = score_lead(record, scoring_config)

        # 10 + 8 + 5 = 23
        assert score == 23

    def test_recency_within_7_days(self, scoring_config):
        """License date within 7 days gets max recency score."""
        record = {
            "business_type": "other",
            "source_type": "search_snippet",
            "license_date": datetime.now().strftime("%Y-%m-%d"),
        }
        score = score_lead(record, scoring_config)

        # 10 + 8 + 0 + 15 = 33
        assert score == 33

    def test_recency_8_to_14_days(self, scoring_config):
        """License date 8-14 days old gets medium recency score."""
        date_10_days_ago = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
        record = {
            "business_type": "other",
            "source_type": "search_snippet",
            "license_date": date_10_days_ago,
        }
        score = score_lead(record, scoring_config)

        # 10 + 8 + 0 + 10 = 28
        assert score == 28

    def test_recency_15_to_30_days(self, scoring_config):
        """License date 15-30 days old gets low recency score."""
        date_20_days_ago = (datetime.now() - timedelta(days=20)).strftime("%Y-%m-%d")
        record = {
            "business_type": "other",
            "source_type": "search_snippet",
            "license_date": date_20_days_ago,
        }
        score = score_lead(record, scoring_config)

        # 10 + 8 + 0 + 5 = 23
        assert score == 23

    def test_recency_over_30_days(self, scoring_config):
        """License date over 30 days old gets zero recency score."""
        date_60_days_ago = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
        record = {
            "business_type": "other",
            "source_type": "search_snippet",
            "license_date": date_60_days_ago,
        }
        score = score_lead(record, scoring_config)

        # 10 + 8 + 0 + 0 = 18
        assert score == 18

    def test_future_dated_license_gets_zero_recency(self, scoring_config):
        """Future-dated license gets zero recency score."""
        future_date = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        record = {
            "business_type": "other",
            "source_type": "search_snippet",
            "license_date": future_date,
        }
        score = score_lead(record, scoring_config)

        # 10 + 8 + 0 + 0 (future date) = 18
        assert score == 18

    def test_score_clamped_to_100(self, scoring_config):
        """Score is clamped to maximum of 100."""
        # Artificially inflate type score
        scoring_config["type_scores"]["restaurant"] = 200
        record = {
            "business_type": "restaurant",
            "source_type": "license_table",
            "address": "123 Main St",
            "city": "Nashville",
            "zip_code": "37201",
            "license_date": datetime.now().strftime("%Y-%m-%d"),
        }
        score = score_lead(record, scoring_config)

        assert score == 100


# ---------------------------------------------------------------------------
# _parse_date Tests
# ---------------------------------------------------------------------------


class TestParseDate:
    """Tests for the _parse_date helper function."""

    def test_parses_iso_format(self):
        """Parses YYYY-MM-DD format."""
        result = _parse_date("2026-01-15")
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 15

    def test_parses_us_slash_format(self):
        """Parses MM/DD/YYYY format."""
        result = _parse_date("01/15/2026")
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 15

    def test_parses_us_dash_format(self):
        """Parses MM-DD-YYYY format."""
        result = _parse_date("01-15-2026")
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 15

    def test_parses_long_format(self):
        """Parses 'Month DD, YYYY' format."""
        result = _parse_date("January 15, 2026")
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 15

    def test_returns_none_for_invalid_date(self):
        """Returns None for unrecognized date format."""
        assert _parse_date("not a date") is None
        assert _parse_date("") is None


# ---------------------------------------------------------------------------
# infer_county Tests
# ---------------------------------------------------------------------------


class TestInferCounty:
    """Tests for the infer_county function."""

    @pytest.fixture
    def city_to_county(self):
        """Sample city to county mapping."""
        return {
            "nashville": "Davidson",
            "antioch": "Davidson",
            "franklin": "Williamson",
            "brentwood": "Williamson",
            "murfreesboro": "Rutherford",
        }

    def test_infers_county_from_city(self, city_to_county):
        """Infers county from city name."""
        record = {"city": "Nashville", "county": None}
        result = infer_county(record, city_to_county)

        assert result["county"] == "Davidson"
        assert result is record  # Mutates in place

    def test_case_insensitive_city_lookup(self, city_to_county):
        """City lookup is case-insensitive."""
        record = {"city": "FRANKLIN", "county": None}
        infer_county(record, city_to_county)

        assert record["county"] == "Williamson"

    def test_preserves_existing_county(self, city_to_county):
        """Does not overwrite existing county value."""
        record = {"city": "Nashville", "county": "Existing County"}
        infer_county(record, city_to_county)

        assert record["county"] == "Existing County"

    def test_no_county_when_city_not_found(self, city_to_county):
        """Does not set county when city is not in mapping."""
        record = {"city": "Unknown City", "county": None}
        infer_county(record, city_to_county)

        assert record["county"] is None

    def test_no_county_when_city_is_none(self, city_to_county):
        """Does not set county when city is None."""
        record = {"city": None, "county": None}
        infer_county(record, city_to_county)

        assert record["county"] is None


# ---------------------------------------------------------------------------
# _build_city_to_county_map Tests
# ---------------------------------------------------------------------------


class TestBuildCityToCountyMap:
    """Tests for the _build_city_to_county_map helper."""

    def test_builds_reverse_map(self):
        """Builds reverse map from county -> cities to city -> county."""
        sources = {
            "counties": {
                "Davidson": ["Nashville", "Antioch"],
                "Williamson": ["Franklin", "Brentwood"],
            }
        }
        result = _build_city_to_county_map(sources)

        assert result["nashville"] == "Davidson"
        assert result["antioch"] == "Davidson"
        assert result["franklin"] == "Williamson"
        assert result["brentwood"] == "Williamson"

    def test_empty_when_no_counties(self):
        """Returns empty dict when no counties in config."""
        sources = {}
        result = _build_city_to_county_map(sources)

        assert result == {}


# ---------------------------------------------------------------------------
# deduplicate Tests
# ---------------------------------------------------------------------------


class TestDeduplicate:
    """Tests for the deduplicate function."""

    def test_removes_duplicate_fingerprints(self):
        """Removes records with duplicate fingerprints."""
        records = [
            {"business_name": "Test Cafe", "city": "Nashville", "pos_score": 50},
            {"business_name": "Test Cafe", "city": "Nashville", "pos_score": 60},
            {"business_name": "Other Shop", "city": "Franklin", "pos_score": 40},
        ]
        result = deduplicate(records)

        assert len(result) == 2
        # All records should have fingerprints
        for r in result:
            assert "fingerprint" in r

    def test_keeps_higher_score_on_collision(self):
        """Keeps the record with higher pos_score when fingerprints collide."""
        records = [
            {"business_name": "Test Cafe", "city": "Nashville", "pos_score": 50},
            {"business_name": "Test Cafe", "city": "Nashville", "pos_score": 80},
            {"business_name": "Test Cafe", "city": "Nashville", "pos_score": 60},
        ]
        result = deduplicate(records)

        assert len(result) == 1
        assert result[0]["pos_score"] == 80

    def test_generates_fingerprints(self):
        """Generates fingerprint for each record."""
        records = [
            {"business_name": "Test Cafe", "city": "Nashville", "pos_score": 50},
        ]
        result = deduplicate(records)

        assert len(result[0]["fingerprint"]) == 32  # SHA-256 truncated to 32 hex chars

    def test_empty_input_returns_empty(self):
        """Returns empty list for empty input."""
        result = deduplicate([])

        assert result == []


# ---------------------------------------------------------------------------
# _validate_scoring Tests
# ---------------------------------------------------------------------------


class TestValidateScoring:
    """Tests for the _validate_scoring helper."""

    def test_valid_config_passes(self, sample_scoring_config):
        """Valid configuration passes validation."""
        # Should not raise
        _validate_scoring(sample_scoring_config)

    def test_raises_on_missing_key(self):
        """Raises ValueError when required key is missing."""
        incomplete_config = {
            "type_scores": {},
            "business_type_keywords": {},
            # Missing: source_scores, address_scores, recency_scores
        }
        with pytest.raises(ValueError) as exc_info:
            _validate_scoring(incomplete_config)

        assert "Missing required keys" in str(exc_info.value)

    def test_raises_on_wrong_type(self):
        """Raises ValueError when key has wrong type."""
        wrong_type_config = {
            "type_scores": [],  # Should be dict
            "business_type_keywords": {},
            "source_scores": {},
            "address_scores": {},
            "recency_scores": [],
        }
        with pytest.raises(ValueError) as exc_info:
            _validate_scoring(wrong_type_config)

        assert "should be dict" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Parser Routing Tests
# ---------------------------------------------------------------------------


class TestParserRouting:
    """Tests for run_transform parser routing logic."""

    def test_routes_clerk_table_to_parse_clerk_table(self):
        """Verifies that clerk_table source_type routes to parse_clerk_table."""
        from unittest.mock import patch

        # Sample clerk_rows data (mimics ClerkScraper output)
        # Use today's date to ensure recency score is max (15 points)
        today = datetime.now().strftime("%Y-%m-%d")
        clerk_rows = [
            {
                "business_name": "Joe's Coffee Shop",
                "product": "Cafe",
                "address": "123 MAIN ST  NASHVILLE TN 37201",
                "owner": "Joe Smith",
                "date": today,
            },
        ]

        # Raw extract with clerk_table source_type
        raw_extracts = [
            {
                "source_type": "clerk_table",
                "source_url": "https://secure.tncountyclerk.com/businesslist/19",
                "county": "Davidson",
                "clerk_rows": clerk_rows,
                "raw_content": "",  # Not used for clerk_table
                "title": "",
            },
        ]

        # Mock YAML configs
        mock_scoring = {
            "type_scores": {"cafe": 40, "other": 10},
            "business_type_keywords": {"cafe": ["cafe", "coffee"]},
            "source_scores": {"clerk_table": 20, "search_snippet": 8},
            "address_scores": {"full": 15, "partial": 10, "city_only": 5, "none": 0},
            "recency_scores": [
                {"max_days": 7, "score": 15},
                {"max_days": 14, "score": 10},
                {"max_days": 30, "score": 5},
            ],
        }
        mock_chains = {"chains": []}
        mock_sources = {"counties": {"Davidson": ["Nashville"]}}

        def mock_load_yaml(path):
            if "scoring.yaml" in str(path):
                return mock_scoring
            elif "chains.yaml" in str(path):
                return mock_chains
            elif "sources.yaml" in str(path):
                return mock_sources
            return {}

        with patch("etl.transform._load_yaml", side_effect=mock_load_yaml):
            result = run_transform(raw_extracts)

        # Verify we got a record
        assert len(result) == 1
        record = result[0]

        # Verify it parsed the clerk data correctly
        assert record["business_name"] == "Joe's Coffee Shop"
        assert record["business_type"] == "cafe"
        assert record["raw_type"] == "Cafe"
        assert record["source_type"] == "clerk_table"
        assert record["address"] == "123 MAIN ST"
        assert record["city"] == "NASHVILLE"
        assert record["state"] == "TN"
        assert record["zip_code"] == "37201"
        assert record["county"] == "Davidson"
        assert record["license_date"] == today

        # Verify it was scored correctly (cafe=40 + clerk_table=20 + full_address=15 + recency=15 = 90)
        assert record["pos_score"] == 90
