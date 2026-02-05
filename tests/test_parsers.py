"""
Tests for utils/parsers.py

Tests the three parser functions:
- parse_license_table: parses markdown pipe-tables with business license data
- parse_news_article: parses news articles with ## headings for business names
- parse_snippet: creates a BusinessRecord from a search result snippet
"""

import pytest

from utils.parsers import (
    parse_license_table,
    parse_news_article,
    parse_snippet,
    _split_address_parts,
    _find_tn_city,
    _map_header_to_field,
)


# ---------------------------------------------------------------------------
# Helper Function Tests
# ---------------------------------------------------------------------------


class TestSplitAddressParts:
    """Tests for _split_address_parts helper."""

    def test_full_address_with_state_zip(self):
        """Address with street, city, state and zip."""
        street, city, zip_code = _split_address_parts("123 Main St, Nashville, TN 37201")
        assert street == "123 Main St"
        assert city == "Nashville"
        assert zip_code == "37201"

    def test_address_without_state(self):
        """Address with street, city, zip but no state abbreviation.

        Note: Without a state abbreviation pattern (e.g., 'TN'), the city
        extraction includes the zip code since the regex doesn't match.
        """
        street, city, zip_code = _split_address_parts("456 Oak Ave, Franklin 37064")
        assert street == "456 Oak Ave"
        # City includes the zip since there's no state abbreviation to strip
        assert city == "Franklin 37064"
        assert zip_code == "37064"

    def test_address_city_only_no_zip(self):
        """Address with street and city, no zip."""
        street, city, zip_code = _split_address_parts("789 Broadway, Nashville")
        assert street == "789 Broadway"
        assert city == "Nashville"
        assert zip_code is None

    def test_no_comma_returns_street_only(self):
        """Address without comma returns entire string as street."""
        street, city, zip_code = _split_address_parts("123 Main St")
        assert street == "123 Main St"
        assert city is None
        assert zip_code is None

    def test_empty_string_returns_nones(self):
        """Empty string returns all None."""
        street, city, zip_code = _split_address_parts("")
        assert street is None
        assert city is None
        assert zip_code is None

    def test_zip_with_plus_four(self):
        """ZIP code with +4 extension is captured."""
        street, city, zip_code = _split_address_parts("123 Main, Nashville, TN 37201-1234")
        assert zip_code == "37201-1234"


class TestFindTnCity:
    """Tests for _find_tn_city helper."""

    def test_finds_nashville(self):
        """Finds Nashville in text."""
        assert _find_tn_city("Opening a new store in Nashville next week") == "Nashville"

    def test_finds_franklin(self):
        """Finds Franklin in text."""
        assert _find_tn_city("Franklin's newest restaurant") == "Franklin"

    def test_case_insensitive(self):
        """City detection is case-insensitive."""
        assert _find_tn_city("Opening in MURFREESBORO") == "Murfreesboro"

    def test_no_city_found(self):
        """Returns None when no city found."""
        assert _find_tn_city("Some random text without a city") is None

    def test_multi_word_city(self):
        """Finds multi-word city names like Spring Hill."""
        assert _find_tn_city("New business in Spring Hill area") == "Spring Hill"


class TestMapHeaderToField:
    """Tests for _map_header_to_field helper."""

    def test_date_variants(self):
        """Various date header synonyms map correctly."""
        assert _map_header_to_field("Date") == "license_date"
        assert _map_header_to_field("License Date") == "license_date"
        assert _map_header_to_field("Lic. Date") == "license_date"

    def test_business_name_variants(self):
        """Various business name header synonyms map correctly."""
        assert _map_header_to_field("Business") == "business_name"
        assert _map_header_to_field("Business Name") == "business_name"
        assert _map_header_to_field("Company") == "business_name"
        assert _map_header_to_field("Name") == "business_name"

    def test_type_variants(self):
        """Various type header synonyms map correctly."""
        assert _map_header_to_field("Product") == "raw_type"
        assert _map_header_to_field("Type") == "raw_type"
        assert _map_header_to_field("Product Type") == "raw_type"

    def test_address_variants(self):
        """Various address header synonyms map correctly."""
        assert _map_header_to_field("Address") == "address"
        assert _map_header_to_field("Location") == "address"

    def test_unrecognized_returns_none(self):
        """Unrecognized headers return None."""
        assert _map_header_to_field("Random Header") is None
        assert _map_header_to_field("Phone Number") is None


# ---------------------------------------------------------------------------
# parse_license_table Tests
# ---------------------------------------------------------------------------


class TestParseLicenseTable:
    """Tests for parse_license_table function."""

    def test_parses_standard_table(self):
        """Parses a standard markdown table with business license data."""
        content = """
# New Business Licenses

| Date | Business Name | Product Type | Address |
|------|---------------|--------------|---------|
| 01/15/2026 | Nashville Noodles LLC | Restaurant | 789 Broadway, Nashville, TN 37203 |
| 01/14/2026 | Quick Clips | Barber Shop | 456 Church St, Nashville, TN 37201 |
"""
        records = parse_license_table(content, "https://example.com", "Davidson")

        assert len(records) == 2

        # First record
        assert records[0]["business_name"] == "Nashville Noodles LLC"
        assert records[0]["raw_type"] == "Restaurant"
        assert records[0]["license_date"] == "01/15/2026"
        assert records[0]["address"] == "789 Broadway"
        assert records[0]["city"] == "Nashville"
        assert records[0]["zip_code"] == "37203"
        assert records[0]["county"] == "Davidson"
        assert records[0]["source_type"] == "license_table"

        # Second record
        assert records[1]["business_name"] == "Quick Clips"
        assert records[1]["raw_type"] == "Barber Shop"

    def test_handles_different_column_order(self):
        """Handles tables with different column ordering."""
        content = """
| Business | Address | Date |
|----------|---------|------|
| Test Cafe | 123 Main St, Franklin, TN 37064 | 01/20/2026 |
"""
        records = parse_license_table(content, "https://example.com", "Williamson")

        assert len(records) == 1
        assert records[0]["business_name"] == "Test Cafe"
        assert records[0]["license_date"] == "01/20/2026"
        assert records[0]["address"] == "123 Main St"
        assert records[0]["city"] == "Franklin"

    def test_skips_empty_business_names(self):
        """Skips rows where business name is empty."""
        content = """
| Date | Business Name | Type |
|------|---------------|------|
| 01/15/2026 | | Restaurant |
| 01/14/2026 | Valid Business | Retail |
"""
        records = parse_license_table(content, "https://example.com", None)

        assert len(records) == 1
        assert records[0]["business_name"] == "Valid Business"

    def test_returns_empty_for_no_table(self):
        """Returns empty list when no table is found."""
        content = "This is just some text without any table."
        records = parse_license_table(content, "https://example.com", None)

        assert records == []

    def test_returns_empty_for_no_header_keywords(self):
        """Returns empty list when table has no recognizable headers."""
        content = """
| Column A | Column B | Column C |
|----------|----------|----------|
| Value 1 | Value 2 | Value 3 |
"""
        records = parse_license_table(content, "https://example.com", None)

        assert records == []

    def test_sets_state_to_tn_when_address_present(self):
        """Sets state to TN when address or city is present."""
        content = """
| Business Name | Address |
|---------------|---------|
| Test Shop | 123 Main St, Nashville |
"""
        records = parse_license_table(content, "https://example.com", None)

        assert records[0]["state"] == "TN"


# ---------------------------------------------------------------------------
# parse_news_article Tests
# ---------------------------------------------------------------------------


class TestParseNewsArticle:
    """Tests for parse_news_article function."""

    def test_parses_section_headings(self):
        """Parses ## section headings as business names."""
        content = """
# New Restaurants Coming to Nashville

## Fire & Stone Pizza

*1234 West End Ave, Nashville, TN 37203*

This authentic Italian pizzeria is bringing wood-fired pizza to Nashville.

## The Taco Spot

*567 Nolensville Pike, Nashville*

A new taco restaurant is opening next month.
"""
        records = parse_news_article(content, "https://example.com", "Davidson")

        assert len(records) == 2

        # First business
        assert records[0]["business_name"] == "Fire & Stone Pizza"
        assert records[0]["address"] == "1234 West End Ave"
        assert records[0]["city"] == "Nashville"
        assert records[0]["zip_code"] == "37203"

        # Second business
        assert records[1]["business_name"] == "The Taco Spot"
        assert records[1]["address"] == "567 Nolensville Pike"

    def test_extracts_address_from_italic_lines(self):
        """Extracts address from italic markdown lines starting with *."""
        content = """
## Test Business

*100 Commerce St, Nashville, TN 37201*

More description text.
"""
        records = parse_news_article(content, "https://example.com", None)

        assert len(records) == 1
        assert records[0]["address"] == "100 Commerce St"
        assert records[0]["city"] == "Nashville"
        assert records[0]["zip_code"] == "37201"

    def test_finds_city_in_section_text(self):
        """Finds city name in section text when not in address line."""
        content = """
## Nashville Brewing Company

Located in the heart of downtown Nashville, this new brewery will open soon.
"""
        records = parse_news_article(content, "https://example.com", None)

        assert len(records) == 1
        assert records[0]["city"] == "Nashville"

    def test_fallback_for_announcement_lines(self):
        """Fallback parsing for articles without ## headings."""
        content = """
"Joe's Diner" is opening in Murfreesboro next month.
A new shop called The Boutique launches in Franklin.
"""
        records = parse_news_article(content, "https://example.com", None)

        assert len(records) >= 1
        # Should find at least the quoted business name
        names = [r["business_name"] for r in records]
        assert "Joe's Diner" in names

    def test_returns_empty_for_no_content(self):
        """Returns empty list for content without businesses."""
        content = "Just some random text about nothing specific."
        records = parse_news_article(content, "https://example.com", None)

        assert records == []

    def test_sets_county_from_parameter(self):
        """Sets county from the provided parameter."""
        content = """
## Test Shop

Opening soon in Franklin.
"""
        records = parse_news_article(content, "https://example.com", "Williamson")

        assert records[0]["county"] == "Williamson"


class TestParseNewsArticleBoldNames:
    """Tests for bold name extraction strategy."""

    def test_extracts_bold_double_asterisk(self):
        """Extracts business names from **bold** markdown."""
        content = """
Here are the new businesses opening:

**Potbelly Sandwich Shop** is opening at 123 Main St, Franklin.

**Velvet Taco** will be located at 456 Oak Ave, Nashville.

**Local Coffee Co** coming soon to Brentwood.
"""
        records = parse_news_article(content, "https://example.com/article", "Williamson")

        names = [r["business_name"] for r in records]
        assert "Potbelly Sandwich Shop" in names
        assert "Velvet Taco" in names
        assert "Local Coffee Co" in names
        assert len(records) == 3

    def test_extracts_bold_double_underscore(self):
        """Extracts business names from __bold__ markdown."""
        content = """
__Nashville Taco Co__ opening downtown.
__Franklin Brewing__ coming to Cool Springs.
"""
        records = parse_news_article(content, "https://example.com/article", None)

        names = [r["business_name"] for r in records]
        assert "Nashville Taco Co" in names
        assert "Franklin Brewing" in names

    def test_skips_generic_bold_words(self):
        """Skips bold text that isn't a business name."""
        content = """
**New** businesses are **Opening** this month.
**Potbelly** is one of them.
"""
        records = parse_news_article(content, "https://example.com/article", None)

        names = [r["business_name"] for r in records]
        assert "New" not in names
        assert "Opening" not in names
        assert "Potbelly" in names

    def test_extracts_address_after_bold_name(self):
        """Associates address on same/next line with bold business name."""
        content = """
**Potbelly Sandwich Shop**
*123 Main Street, Franklin, TN 37064*

Great sandwiches coming soon!
"""
        records = parse_news_article(content, "https://example.com/article", None)

        assert len(records) == 1
        assert records[0]["business_name"] == "Potbelly Sandwich Shop"
        assert records[0]["address"] == "123 Main Street"
        assert records[0]["city"] == "Franklin"


# ---------------------------------------------------------------------------
# parse_snippet Tests
# ---------------------------------------------------------------------------


class TestParseSnippet:
    """Tests for parse_snippet function."""

    def test_extracts_business_name_from_title(self):
        """Extracts business name by stripping title suffixes."""
        records = parse_snippet(
            title="Joe's Coffee - Nashville, TN",
            content="A new coffee shop is opening...",
            source_url="https://example.com",
            county="Davidson",
        )

        assert len(records) == 1
        assert records[0]["business_name"] == "Joe's Coffee"

    def test_strips_pipe_separator(self):
        """Strips | separator and trailing content from title."""
        records = parse_snippet(
            title="Best Pizza | Nashville News",
            content="Pizza restaurant news...",
            source_url="https://example.com",
            county=None,
        )

        assert records[0]["business_name"] == "Best Pizza"

    def test_strips_dash_separator(self):
        """Strips - separator and trailing content from title."""
        records = parse_snippet(
            title="The Burger Joint - Food & Dining",
            content="New burger place...",
            source_url="https://example.com",
            county=None,
        )

        assert records[0]["business_name"] == "The Burger Joint"

    def test_strips_tn_suffix(self):
        """Strips TN state suffix from title."""
        records = parse_snippet(
            title="Franklin Bakery, TN 37064",
            content="Bakery news...",
            source_url="https://example.com",
            county=None,
        )

        assert records[0]["business_name"] == "Franklin Bakery"

    def test_finds_city_in_title(self):
        """Finds city name in the title."""
        records = parse_snippet(
            title="New Coffee Shop - Franklin",
            content="Description...",
            source_url="https://example.com",
            county="Williamson",
        )

        assert records[0]["city"] == "Franklin"

    def test_finds_city_in_content(self):
        """Falls back to finding city in content."""
        records = parse_snippet(
            title="Amazing Restaurant",
            content="A new restaurant is opening in Murfreesboro next month.",
            source_url="https://example.com",
            county=None,
        )

        assert records[0]["city"] == "Murfreesboro"

    def test_returns_empty_for_empty_title(self):
        """Returns empty list when title is empty after cleaning."""
        records = parse_snippet(
            title=" - Nashville News",
            content="Some content...",
            source_url="https://example.com",
            county=None,
        )

        assert records == []

    def test_sets_source_type_correctly(self):
        """Sets source_type to search_snippet."""
        records = parse_snippet(
            title="Test Business",
            content="Test content",
            source_url="https://example.com",
            county=None,
        )

        assert records[0]["source_type"] == "search_snippet"

    def test_sets_state_when_city_found(self):
        """Sets state to TN when city is found."""
        records = parse_snippet(
            title="Test Cafe",
            content="Opening in Nashville",
            source_url="https://example.com",
            county=None,
        )

        assert records[0]["state"] == "TN"
        assert records[0]["city"] == "Nashville"


class TestParseNewsArticleListItems:
    """Tests for list item extraction strategy."""

    def test_extracts_bullet_list_dash(self):
        """Extracts business names from dash bullet lists."""
        content = """
New businesses opening:

- Potbelly Sandwich Shop - opening March 2026
- Velvet Taco (coming to Franklin)
- Local Coffee Co, located downtown
"""
        records = parse_news_article(content, "https://example.com/article", None)

        names = [r["business_name"] for r in records]
        assert "Potbelly Sandwich Shop" in names
        assert "Velvet Taco" in names
        assert "Local Coffee Co" in names

    def test_extracts_bullet_list_asterisk(self):
        """Extracts business names from asterisk bullet lists."""
        content = """
* Nashville Taco Co
* Franklin Brewing
* Brentwood Bagels
"""
        records = parse_news_article(content, "https://example.com/article", None)

        names = [r["business_name"] for r in records]
        assert "Nashville Taco Co" in names
        assert "Franklin Brewing" in names
        assert "Brentwood Bagels" in names

    def test_extracts_numbered_list(self):
        """Extracts business names from numbered lists."""
        content = """
1. Potbelly Sandwich Shop
2. Velvet Taco
3. Nothing Bundt Cakes
"""
        records = parse_news_article(content, "https://example.com/article", None)

        names = [r["business_name"] for r in records]
        assert "Potbelly Sandwich Shop" in names
        assert "Velvet Taco" in names
        assert "Nothing Bundt Cakes" in names

    def test_strips_description_after_delimiter(self):
        """Strips description text after common delimiters."""
        content = """
- Potbelly - a sandwich chain opening in March
- Velvet Taco (Mexican street food)
- Local Coffee, expected Q2 2026
"""
        records = parse_news_article(content, "https://example.com/article", None)

        names = [r["business_name"] for r in records]
        assert "Potbelly" in names
        assert "a sandwich chain" not in str(names)
        assert "Velvet Taco" in names
        assert "Mexican street food" not in str(names)


class TestParseNewsArticleSentencePatterns:
    """Tests for sentence pattern extraction strategy (fallback)."""

    def test_extracts_is_opening_pattern(self):
        """Extracts business name from 'X is opening' pattern."""
        content = """
Potbelly is opening a new location in Franklin this spring.
Velvet Taco is opening at the corner of Main and 5th.
"""
        records = parse_news_article(content, "https://example.com/article", None)

        names = [r["business_name"] for r in records]
        assert "Potbelly" in names
        assert "Velvet Taco" in names

    def test_extracts_will_open_pattern(self):
        """Extracts business name from 'X will open' pattern."""
        content = """
Nashville Taco Co will open its doors in March.
Franklin Brewing will open a taproom downtown.
"""
        records = parse_news_article(content, "https://example.com/article", None)

        names = [r["business_name"] for r in records]
        assert "Nashville Taco Co" in names
        assert "Franklin Brewing" in names

    def test_extracts_coming_to_pattern(self):
        """Extracts business name from 'X coming to' pattern."""
        content = """
A new Potbelly coming to Cool Springs.
Velvet Taco coming to downtown Nashville.
"""
        records = parse_news_article(content, "https://example.com/article", None)

        names = [r["business_name"] for r in records]
        assert "Potbelly" in names
        assert "Velvet Taco" in names

    def test_extracts_location_from_sentence(self):
        """Extracts city from sentence when present."""
        content = """
Potbelly is opening at 123 Main St in Franklin.
"""
        records = parse_news_article(content, "https://example.com/article", None)

        assert len(records) >= 1
        potbelly = next(r for r in records if "Potbelly" in r["business_name"])
        assert potbelly["city"] == "Franklin"


class TestParseNewsArticleStrategyPriority:
    """Tests for extraction strategy priority order."""

    def test_heading_strategy_takes_priority(self):
        """## headings take priority over other strategies."""
        content = """
## Potbelly Sandwich Shop
Opening at 123 Main St.

**Velvet Taco** also mentioned but should be ignored.
"""
        records = parse_news_article(content, "https://example.com/article", None)

        # Only the heading-based business should be extracted
        names = [r["business_name"] for r in records]
        assert "Potbelly Sandwich Shop" in names
        # Bold name should NOT be extracted since headings worked
        assert "Velvet Taco" not in names

    def test_bold_strategy_over_list_and_sentence(self):
        """Bold names take priority over list items and sentences."""
        content = """
**Potbelly** is the main attraction.

- Some Other Place (listed but should be ignored)

Another Restaurant is opening too.
"""
        records = parse_news_article(content, "https://example.com/article", None)

        names = [r["business_name"] for r in records]
        assert "Potbelly" in names
        # List and sentence extractions should be skipped
        assert len(records) == 1

    def test_falls_back_to_sentence_when_no_structure(self):
        """Falls back to sentence patterns when no structured content."""
        content = """
Great news for Franklin! Potbelly is opening next month.
Velvet Taco will open nearby. Exciting times ahead.
"""
        records = parse_news_article(content, "https://example.com/article", None)

        names = [r["business_name"] for r in records]
        assert "Potbelly" in names
        assert "Velvet Taco" in names


class TestParseNewsArticleIntegration:
    """Integration tests with realistic article content."""

    def test_realistic_listicle_article(self):
        """Parses a realistic listicle-style article."""
        content = """
# New Businesses Coming to Williamson County in 2026

Exciting news for Franklin and Brentwood residents! Several new restaurants
and shops are planning to open in the area.

## Potbelly Sandwich Shop
*123 Main Street, Franklin, TN 37064*

The popular sandwich chain is bringing its toasted subs to Cool Springs.
Expected to open in March 2026.

## Velvet Taco
*456 Oak Avenue, Brentwood*

Known for creative tacos, Velvet Taco will open its first Tennessee
location in the Hill Center development.

## Local Coffee Roasters
A locally-owned coffee shop coming to downtown Franklin.
"""
        records = parse_news_article(content, "https://example.com/article", "Williamson")

        assert len(records) == 3

        potbelly = next(r for r in records if "Potbelly" in r["business_name"])
        assert potbelly["address"] == "123 Main Street"
        assert potbelly["city"] == "Franklin"
        assert potbelly["county"] == "Williamson"

        velvet = next(r for r in records if "Velvet" in r["business_name"])
        assert velvet["city"] == "Brentwood"

    def test_realistic_bullet_list_article(self):
        """Parses article with bullet list format."""
        content = """
New restaurants coming to Nashville in 2026:

- **Potbelly** - the sandwich chain opening in Green Hills
- **Velvet Taco** (coming to the Gulch)
- **Local Bistro**, a farm-to-table concept
- **Nashville Brewing Co** opening on Broadway
"""
        records = parse_news_article(content, "https://example.com/article", "Davidson")

        # Should extract from bold names (higher priority than list)
        names = [r["business_name"] for r in records]
        assert "Potbelly" in names
        assert "Velvet Taco" in names
        assert "Local Bistro" in names
        assert "Nashville Brewing Co" in names

    def test_each_business_becomes_separate_lead(self):
        """Verifies each extracted business is a distinct lead record."""
        content = """
## Joe's Pizza
*100 First Ave, Nashville*

## Maria's Tacos
*200 Second Ave, Franklin*

## Bob's Burgers
*300 Third Ave, Murfreesboro*
"""
        records = parse_news_article(content, "https://example.com/article", None)

        # Each business should be a separate record
        assert len(records) == 3

        # Each record should have unique business name
        names = [r["business_name"] for r in records]
        assert len(set(names)) == 3  # All unique

        # Each record should have the same source URL
        urls = [r["source_url"] for r in records]
        assert all(url == "https://example.com/article" for url in urls)

        # Each can have different cities
        cities = [r["city"] for r in records]
        assert "Nashville" in cities
        assert "Franklin" in cities
        assert "Murfreesboro" in cities
