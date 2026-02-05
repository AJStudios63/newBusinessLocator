# Multi-Business Article Parser Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enhance `parse_news_article()` to extract multiple individual business leads from listicle-style news articles instead of creating a single lead from the article title.

**Architecture:** Add four extraction strategies (## headings, bold names, list items, sentence patterns) that run in priority order. First strategy to yield results wins. Each extracted business gets its own lead record with associated address when detectable.

**Tech Stack:** Python, regex, pytest

---

## Task 1: Add Tests for Bold Name Extraction

**Files:**
- Modify: `tests/test_parsers.py` (create if doesn't exist)

**Step 1: Create test file with bold name extraction tests**

```python
"""Tests for utils/parsers.py multi-business extraction."""

import pytest
from utils.parsers import parse_news_article


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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_parsers.py::TestParseNewsArticleBoldNames -v`
Expected: FAIL (tests don't exist yet or bold extraction not implemented)

---

## Task 2: Add Tests for List Item Extraction

**Files:**
- Modify: `tests/test_parsers.py`

**Step 1: Add list item extraction tests**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_parsers.py::TestParseNewsArticleListItems -v`
Expected: FAIL

---

## Task 3: Add Tests for Sentence Pattern Extraction

**Files:**
- Modify: `tests/test_parsers.py`

**Step 1: Add sentence pattern extraction tests**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_parsers.py::TestParseNewsArticleSentencePatterns -v`
Expected: FAIL

---

## Task 4: Add Tests for Strategy Priority

**Files:**
- Modify: `tests/test_parsers.py`

**Step 1: Add strategy priority tests**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_parsers.py::TestParseNewsArticleStrategyPriority -v`
Expected: FAIL

---

## Task 5: Implement Bold Name Extraction

**Files:**
- Modify: `utils/parsers.py:235-325` (within/after `parse_news_article`)

**Step 1: Add helper constants and function for bold extraction**

Add after `_find_tn_city` function (around line 211):

```python
# Generic words to skip when extracting bold names
_SKIP_BOLD_WORDS = {
    "new", "opening", "coming", "soon", "now", "open", "grand",
    "location", "store", "restaurant", "shop", "cafe", "bar",
    "the", "a", "an", "and", "or", "at", "in", "to", "for",
}


def _extract_bold_names(content: str) -> list[tuple[str, int]]:
    """Extract business names from **bold** or __bold__ markdown.

    Returns list of (name, line_index) tuples for address association.
    Filters out generic words and short strings.
    """
    results = []
    lines = content.splitlines()

    # Pattern for **text** or __text__
    bold_pattern = re.compile(r'\*\*([^*]+)\*\*|__([^_]+)__')

    for i, line in enumerate(lines):
        for match in bold_pattern.finditer(line):
            name = (match.group(1) or match.group(2)).strip()

            # Skip if too short
            if len(name) < 3:
                continue

            # Skip if it's a generic word
            if name.lower() in _SKIP_BOLD_WORDS:
                continue

            # Skip if it looks like an article title
            if is_article_title(name):
                continue

            results.append((name, i))

    return results
```

**Step 2: Run tests to check progress**

Run: `pytest tests/test_parsers.py::TestParseNewsArticleBoldNames::test_skips_generic_bold_words -v`
Expected: Still FAIL (not integrated into parse_news_article yet)

---

## Task 6: Implement List Item Extraction

**Files:**
- Modify: `utils/parsers.py`

**Step 1: Add helper function for list item extraction**

Add after `_extract_bold_names`:

```python
def _extract_list_items(content: str) -> list[tuple[str, int]]:
    """Extract business names from bullet or numbered lists.

    Handles:
    - Dash bullets: - Item
    - Asterisk bullets: * Item
    - Numbered: 1. Item, 2. Item

    Strips description text after common delimiters (-, –, (, ,).
    Returns list of (name, line_index) tuples.
    """
    results = []
    lines = content.splitlines()

    # Pattern for list items: dash, asterisk, or number followed by period
    list_pattern = re.compile(r'^\s*(?:[-*]|\d+\.)\s+(.+)$')

    for i, line in enumerate(lines):
        match = list_pattern.match(line)
        if not match:
            continue

        item_text = match.group(1).strip()

        # Extract business name before common delimiters
        # Split on: " - ", " – ", "(", ","
        name = re.split(r'\s+[-–]\s+|\s*\(|,\s*(?=[a-z])', item_text, maxsplit=1)[0].strip()

        # Skip if too short
        if len(name) < 3:
            continue

        # Skip if it looks like an article title
        if is_article_title(name):
            continue

        results.append((name, i))

    return results
```

**Step 2: Run tests**

Run: `pytest tests/test_parsers.py::TestParseNewsArticleListItems -v`
Expected: Still FAIL (not integrated yet)

---

## Task 7: Implement Sentence Pattern Extraction

**Files:**
- Modify: `utils/parsers.py`

**Step 1: Add helper function for sentence pattern extraction**

Add after `_extract_list_items`:

```python
# Patterns for extracting business names from sentences
_SENTENCE_PATTERNS = [
    # "X is opening" - captures text before "is opening"
    re.compile(r'\b([A-Z][A-Za-z\s&\']+?)\s+is\s+opening\b', re.IGNORECASE),
    # "X will open" - captures text before "will open"
    re.compile(r'\b([A-Z][A-Za-z\s&\']+?)\s+will\s+open\b', re.IGNORECASE),
    # "X coming to" - captures text before "coming to"
    re.compile(r'\b(?:A\s+new\s+)?([A-Z][A-Za-z\s&\']+?)\s+coming\s+to\b', re.IGNORECASE),
    # "X opens" - captures text before "opens"
    re.compile(r'\b([A-Z][A-Za-z\s&\']+?)\s+opens\b', re.IGNORECASE),
]


def _extract_from_sentences(content: str) -> list[tuple[str, int]]:
    """Extract business names from sentence patterns (fallback strategy).

    Matches patterns like:
    - "Potbelly is opening..."
    - "Velvet Taco will open..."
    - "A new Crumbl coming to..."

    Returns list of (name, line_index) tuples.
    """
    results = []
    lines = content.splitlines()
    seen_names = set()

    for i, line in enumerate(lines):
        for pattern in _SENTENCE_PATTERNS:
            for match in pattern.finditer(line):
                name = match.group(1).strip()

                # Clean up: remove leading articles
                name = re.sub(r'^(?:The|A|An)\s+', '', name, flags=re.IGNORECASE).strip()

                # Skip if too short
                if len(name) < 3:
                    continue

                # Skip if it looks like an article title
                if is_article_title(name):
                    continue

                # Skip duplicates within this extraction
                name_lower = name.lower()
                if name_lower in seen_names:
                    continue
                seen_names.add(name_lower)

                results.append((name, i))

    return results
```

**Step 2: Run tests**

Run: `pytest tests/test_parsers.py::TestParseNewsArticleSentencePatterns -v`
Expected: Still FAIL (not integrated yet)

---

## Task 8: Integrate Strategies into parse_news_article

**Files:**
- Modify: `utils/parsers.py:235-325` (replace `parse_news_article` function)

**Step 1: Add helper to build records from extracted names**

Add before `parse_news_article`:

```python
def _build_records_from_names(
    names_with_lines: list[tuple[str, int]],
    lines: list[str],
    source_url: str,
    county: str | None,
    source_type: str = "news_article",
) -> list[dict]:
    """Build BusinessRecord dicts from extracted names.

    For each name, attempts to find an address in nearby lines.
    """
    records = []

    for name, line_idx in names_with_lines:
        rec = _empty_record(source_url, source_type, county)
        rec["business_name"] = name

        # Look for address in current line and next 2 lines
        search_lines = lines[line_idx:line_idx + 3]
        address_line = _extract_address_line(search_lines)

        if address_line:
            street, city, zip_code = _split_address_parts(address_line)
            rec["address"] = street if street else address_line
            if city:
                rec["city"] = city
            if zip_code:
                rec["zip_code"] = zip_code

        # If city still not resolved, scan nearby lines for city mention
        if not rec["city"]:
            nearby_text = "\n".join(lines[max(0, line_idx - 1):line_idx + 3])
            rec["city"] = _find_tn_city(nearby_text)

        if rec["address"] or rec["city"]:
            rec["state"] = "TN"

        records.append(rec)

    return records
```

**Step 2: Refactor parse_news_article to use strategy pattern**

Replace the existing `parse_news_article` function:

```python
def parse_news_article(content: str, source_url: str, county: str | None = None) -> list[dict]:
    """Parse news articles to extract multiple business leads.

    Uses extraction strategies in priority order:
    1. ## Heading sections (most reliable)
    2. **Bold** or __bold__ names
    3. Bullet/numbered list items
    4. Sentence patterns like "X is opening" (fallback)

    First strategy to yield results wins to prevent double-counting.
    """
    lines = content.splitlines()

    # Strategy 1: ## Heading sections (existing logic)
    records = _parse_heading_sections(content, source_url, county)
    if records:
        return records

    # Strategy 2: Bold names
    bold_names = _extract_bold_names(content)
    if bold_names:
        return _build_records_from_names(bold_names, lines, source_url, county)

    # Strategy 3: List items
    list_names = _extract_list_items(content)
    if list_names:
        return _build_records_from_names(list_names, lines, source_url, county)

    # Strategy 4: Sentence patterns (fallback)
    sentence_names = _extract_from_sentences(content)
    if sentence_names:
        return _build_records_from_names(sentence_names, lines, source_url, county)

    return []


def _parse_heading_sections(content: str, source_url: str, county: str | None) -> list[dict]:
    """Extract businesses from ## heading sections (original logic)."""
    sections = re.split(r"(?=^## )", content, flags=re.MULTILINE)

    records: list[dict] = []

    for section in sections:
        lines = section.splitlines()
        if not lines:
            continue

        first_line = lines[0].strip()
        if not first_line.startswith("## "):
            continue

        business_name = first_line.lstrip("# ").strip()
        if not business_name:
            continue

        body_lines = lines[1:]
        address_line = _extract_address_line(body_lines)

        rec = _empty_record(source_url, "news_article", county)
        rec["business_name"] = business_name

        if address_line:
            street, city, zip_code = _split_address_parts(address_line)
            rec["address"] = street if street else address_line
            if city:
                rec["city"] = city
            if zip_code:
                rec["zip_code"] = zip_code

        if not rec["city"]:
            rec["city"] = _find_tn_city(section)

        if rec["address"] or rec["city"]:
            rec["state"] = "TN"

        records.append(rec)

    return records
```

**Step 3: Run all parser tests**

Run: `pytest tests/test_parsers.py -v`
Expected: PASS

---

## Task 9: Update Configuration Files

**Files:**
- Modify: `config/sources.yaml:36-63`
- Modify: `config/chains.yaml`

**Step 1: Add news domains to extractable_domains**

In `config/sources.yaml`, add to the `extractable_domains` list:

```yaml
extractable_domains:
  # ... existing entries ...
  # Regional news sites
  - wilcosun.com
  - newschannel5.com
  - wtvf.com
```

**Step 2: Add common chains to chains.yaml**

Append to `config/chains.yaml`:

```yaml
  # Additional chains from news articles
  - Potbelly
  - "Velvet Taco"
  - "Nothing Bundt Cakes"
  - "Raising Cane's"
  - "Portillo's"
  - "First Watch"
  - "Dutch Bros"
  - "Jeni's"
  - "Snooze"
```

**Step 3: Commit configuration changes**

```bash
git add config/sources.yaml config/chains.yaml
git commit -m "config: Add news domains and common chains for article parsing"
```

---

## Task 10: Add Integration Test

**Files:**
- Modify: `tests/test_parsers.py`

**Step 1: Add integration test with realistic article content**

```python
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
```

**Step 2: Run all tests**

Run: `pytest tests/test_parsers.py -v`
Expected: PASS

**Step 3: Commit implementation**

```bash
git add utils/parsers.py tests/test_parsers.py
git commit -m "feat: Add multi-business extraction to news article parser

Implements four extraction strategies in priority order:
1. ## Heading sections (existing)
2. **Bold** markdown names
3. Bullet/numbered list items
4. Sentence patterns (fallback)

First strategy to yield results wins to prevent double-counting.
Each extracted business gets its own lead record.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 11: Run Full Test Suite and Verify

**Files:**
- None (verification only)

**Step 1: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests PASS

**Step 2: Run ETL pipeline in dry-run mode**

Run: `python -m cli.main run --dry-run`
Expected: Pipeline runs without errors, may show new multi-business extractions

**Step 3: Check for any regressions**

Run: `python -m cli.main leads --limit 10`
Expected: Existing leads still display correctly
