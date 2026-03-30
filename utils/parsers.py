from __future__ import annotations

import re
from pathlib import Path

import yaml


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _empty_record(source_url: str, source_type: str, county: str | None = None) -> dict:
    """Return a BusinessRecord dict pre-filled with defaults."""
    return {
        "business_name": None,
        "business_type": None,
        "raw_type": None,
        "address": None,
        "city": None,
        "state": None,
        "zip_code": None,
        "county": county,
        "license_date": None,
        "source_url": source_url,
        "source_type": source_type,
        "notes": None,
    }


def _title_case(text: str) -> str:
    """Title-case text, handling apostrophes correctly.

    Python's str.title() capitalizes after apostrophes (e.g., "JOE'S" → "Joe'S").
    This function handles that edge case: "JOE'S CAFE" → "Joe's Cafe".
    """
    return re.sub(
        r"[A-Za-z]+('[A-Za-z]+)?",
        lambda m: m.group(0).capitalize(),
        text,
    )


def _split_address_parts(address_str: str) -> tuple[str | None, str | None, str | None]:
    """Best-effort split of a combined address string into (address, city, zip).

    Handles two common formats:
        "123 Main St, Nashville, TN 37201"
        "123 Main St, Nashville 37201"

    Returns (street, city, zip_code) — any part may be None if not found.
    """
    if not address_str:
        return None, None, None

    # Try to extract a ZIP code (5 digits, optionally followed by -4)
    zip_match = re.search(r"\b(\d{5}(?:-\d{4})?)\b", address_str)
    zip_code = zip_match.group(1) if zip_match else None

    parts = [p.strip() for p in address_str.split(",")]

    if len(parts) >= 3:
        # "Street, City, State ZIP"
        street = parts[0] if parts[0] else None
        city = parts[1] if len(parts) > 1 and parts[1] else None
        # City might still have extra whitespace; already stripped above
        return street, city, zip_code

    if len(parts) == 2:
        # "Street, City ZIP" or "Street, City"
        street = parts[0] if parts[0] else None
        remainder = parts[1]
        # Strip any state abbreviation and zip from remainder to isolate city
        city = re.sub(r"[,\s]*\b[A-Z]{2}\b.*$", "", remainder).strip()
        city = city if city else None
        return street, city, zip_code

    # No comma — return the whole thing as street only
    return address_str.strip() or None, None, zip_code


# ---------------------------------------------------------------------------
# Header-column mapping helpers for parse_license_table
# ---------------------------------------------------------------------------

_HEADER_SYNONYMS: dict[str, list[str]] = {
    "license_date": ["date", "license date", "lic. date", "filing date"],
    "business_name": ["business", "business name", "name", "company", "company name"],
    "raw_type": ["product", "type", "product type", "business type", "category"],
    "address": ["address", "location", "addr"],
}


def _map_header_to_field(header: str) -> str | None:
    """Return the canonical field name for a header string, or None."""
    h = header.lower().strip()
    for field, synonyms in _HEADER_SYNONYMS.items():
        if h in synonyms:
            return field
    return None


# ---------------------------------------------------------------------------
# FILE-LEVEL PARSERS
# ---------------------------------------------------------------------------


def parse_license_table(content: str, source_url: str, county: str | None = None) -> list[dict]:
    """Parse a markdown pipe-table with business license data.

    Detects the header row by looking for a line containing '|' and at least
    one recognisable keyword (business, name, date, product, address).
    The row immediately after the header is assumed to be the separator row
    (e.g. ---|---) and is skipped.  Every subsequent pipe-delimited line is
    treated as a data row until a blank line or end-of-content is reached.
    """
    lines = content.splitlines()

    # -- 1. Locate the header row -------------------------------------------
    header_keywords = {"business", "name", "date", "product", "address", "type", "location"}
    header_idx: int | None = None

    for i, line in enumerate(lines):
        if "|" not in line:
            continue
        cells = [c.strip().lower() for c in line.split("|")]
        if any(kw in cell for cell in cells for kw in header_keywords):
            header_idx = i
            break

    if header_idx is None:
        return []

    # -- 2. Parse header columns --------------------------------------------
    raw_headers = [c.strip() for c in lines[header_idx].split("|")]
    # Remove leading/trailing empty strings caused by leading/trailing '|'
    if raw_headers and raw_headers[0] == "":
        raw_headers = raw_headers[1:]
    if raw_headers and raw_headers[-1] == "":
        raw_headers = raw_headers[:-1]

    col_map: dict[int, str] = {}  # column index -> canonical field name
    for idx, hdr in enumerate(raw_headers):
        field = _map_header_to_field(hdr)
        if field:
            col_map[idx] = field

    # -- 3. Skip separator row ----------------------------------------------
    data_start = header_idx + 1
    if data_start < len(lines) and re.match(r"^[\s|:\-]+$", lines[data_start]):
        data_start += 1

    # -- 4. Parse data rows -------------------------------------------------
    records: list[dict] = []

    for line in lines[data_start:]:
        stripped = line.strip()
        if stripped == "":
            break  # blank line ends the table
        if "|" not in stripped:
            break

        cells = [c.strip() for c in stripped.split("|")]
        if cells and cells[0] == "":
            cells = cells[1:]
        if cells and cells[-1] == "":
            cells = cells[:-1]

        rec = _empty_record(source_url, "license_table", county)

        for col_idx, field in col_map.items():
            value = cells[col_idx].strip() if col_idx < len(cells) else ""
            if not value:
                continue

            if field == "license_date":
                rec["license_date"] = value
            elif field == "business_name":
                rec["business_name"] = value
            elif field == "raw_type":
                rec["raw_type"] = value
            elif field == "address":
                street, city, zip_code = _split_address_parts(value)
                rec["address"] = street
                if city:
                    rec["city"] = city
                if zip_code:
                    rec["zip_code"] = zip_code
                # If no comma-separated city was found, keep the raw address
                if rec["address"] is None:
                    rec["address"] = value

        # Skip rows where business_name is missing or is just repeating the header
        if not rec["business_name"]:
            continue
        if rec["business_name"].lower() in {h.lower() for h in raw_headers}:
            continue

        # If city wasn't parsed from address, try to detect it from the full address string
        if not rec["city"] and rec["address"]:
            rec["city"] = _find_tn_city(rec["address"])

        # Default state to TN (Nashville-area pipeline assumption)
        if rec["address"] or rec["city"]:
            rec["state"] = "TN"

        records.append(rec)

    return records


# ---------------------------------------------------------------------------


# Known Nashville-area city names — derived from sources.yaml at import time
def _load_tn_cities() -> list[str]:
    """Build city list from sources.yaml county→city mapping."""
    from config.settings import SOURCES_YAML
    try:
        with open(SOURCES_YAML, "r", encoding="utf-8") as fh:
            sources = yaml.safe_load(fh)
        cities = []
        for county_cities in (sources or {}).get("counties", {}).values():
            cities.extend(county_cities)
        return cities if cities else _TN_CITIES_FALLBACK
    except Exception:
        return _TN_CITIES_FALLBACK

# Fallback if sources.yaml is unavailable
_TN_CITIES_FALLBACK = [
    "Nashville", "Franklin", "Brentwood", "Murfreesboro", "Gallatin",
    "Hendersonville", "Lebanon", "Smyrna", "Goodlettsville", "Madison",
    "Antioch", "Hermitage", "Spring Hill", "Columbia",
    "Shelbyville", "McMinnville", "Cookeville", "Clarksville",
    "Dickson", "Springfield", "Carthage", "Tullahoma", "Pulaski",
]

_TN_CITIES = _load_tn_cities()


def _find_tn_city(text: str) -> str | None:
    """Return the first known TN city found in *text*, or None."""
    for city in _TN_CITIES:
        # Word-boundary match, case-insensitive
        if re.search(r"\b" + re.escape(city) + r"\b", text, re.IGNORECASE):
            return city
    return None


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

            # Skip if it looks like an article title (length heuristic)
            # Full article title detection would require importing from transform,
            # which would create a circular import. Using length check as proxy.
            if len(name) > 60:
                continue

            results.append((name, i))

    return results


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

        # Skip if it looks like an article title (too long)
        if len(name) > 60:
            continue

        results.append((name, i))

    return results


# Patterns for extracting business names from sentences
_SENTENCE_PATTERNS = [
    # Quoted names: "X" is opening, "X" will open, etc.
    re.compile(r'["\u201c]([^"\u201d]+)["\u201d]\s+is\s+opening\b', re.IGNORECASE),
    re.compile(r'["\u201c]([^"\u201d]+)["\u201d]\s+will\s+open\b', re.IGNORECASE),
    re.compile(r'["\u201c]([^"\u201d]+)["\u201d]\s+opens\b', re.IGNORECASE),
    re.compile(r'["\u201c]([^"\u201d]+)["\u201d]\s+launch(?:es|ed)?\b', re.IGNORECASE),
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

                # Skip if it looks like an article title (too long)
                if len(name) > 60:
                    continue

                # Skip duplicates within this extraction
                name_lower = name.lower()
                if name_lower in seen_names:
                    continue
                seen_names.add(name_lower)

                results.append((name, i))

    return results


def _extract_address_line(lines: list[str]) -> str | None:
    """Pick the best address-like line from a list of candidate lines.

    Prefers lines that start with '*' (italic markdown) and contain a digit.
    Falls back to any line that starts with a digit followed by a street name.
    """
    # Priority 1: italic-markdown lines with a number (street address)
    for line in lines:
        cleaned = line.lstrip("* ").rstrip("* ").strip()
        if cleaned and re.match(r"\d", cleaned):
            return cleaned

    # Priority 2: any line starting with a digit
    for line in lines:
        cleaned = line.strip()
        if re.match(r"\d+\s+\S", cleaned):
            return cleaned

    return None


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


# ---------------------------------------------------------------------------


def parse_clerk_table(
    rows: list[dict],
    county: str | None = None,
    county_code: int | None = None,
) -> list[dict]:
    """Convert raw clerk scraper dicts into BusinessRecord dicts.

    Each input dict has keys: business_name, product, address, owner, date.
    The address format is typically "STREET  CITY ST ZIP" (double-space separated).

    Parameters
    ----------
    rows : list[dict]
        Raw dicts from ClerkScraper.fetch_county().
    county : str | None
        County name for all records.
    county_code : int | None
        County code (used in source_url).
    """
    source_url = f"https://secure.tncountyclerk.com/businesslist/{county or county_code}"
    records = []

    for row in rows:
        name = row.get("business_name", "").strip()
        if not name:
            continue

        rec = _empty_record(source_url, "clerk_table", county)
        rec["business_name"] = _title_case(name)
        rec["raw_type"] = row.get("product", "").strip() or None
        rec["license_date"] = row.get("date", "").strip() or None

        # Parse address: typically "123 MAIN ST  NASHVILLE TN 37201"
        raw_addr = row.get("address", "").strip()
        if raw_addr:
            street, city, zip_code = _split_clerk_address(raw_addr)
            rec["address"] = street
            rec["city"] = city
            rec["zip_code"] = zip_code
            rec["state"] = "TN"

        records.append(rec)

    return records


def _split_clerk_address(address: str) -> tuple[str | None, str | None, str | None]:
    """Split a clerk portal address like '123 MAIN ST  NASHVILLE TN 37201'.

    The format uses double-space between street and city, then 'TN' state
    abbreviation followed by optional ZIP code.

    Returns (street, city, zip_code).
    """
    if not address:
        return None, None, None

    # Extract ZIP code
    zip_match = re.search(r"\b(\d{5}(?:-\d{4})?)\b", address)
    zip_code = zip_match.group(1) if zip_match else None

    # Try splitting on double-space (common clerk format)
    parts = re.split(r"\s{2,}", address)
    if len(parts) >= 2:
        street = parts[0].strip() or None
        remainder = parts[1].strip()
        # Strip state abbreviation and zip from remainder to get city
        city = re.sub(r"\s+TN\b.*$", "", remainder, flags=re.IGNORECASE).strip()
        city = city.title() if city else None
        return street, city, zip_code

    # Fallback: try comma splitting
    street, city, zip_code_fallback = _split_address_parts(address)
    return street, city, zip_code or zip_code_fallback


# ---------------------------------------------------------------------------


def parse_snippet(title: str, content: str, source_url: str, county: str | None = None) -> list[dict]:
    """Create a single BusinessRecord from a search-result snippet.

    The business name is derived from *title* by stripping common trailing
    separators and labels (e.g. " - News", " | Franklin, TN").  City is
    detected by scanning both title and content against a hard-coded list
    of Nashville-area cities.
    """
    # -- Strip common suffixes from title ------------------------------------
    # Patterns like " - Some Label", " | Some Label", " – …" at the end
    cleaned_title = re.split(r"\s+[-–|]+\s+", title)
    business_name = cleaned_title[0].strip()

    # Secondary strip: remove trailing parenthetical or "TN" state tags
    business_name = re.sub(r"\s*\(.*?\)\s*$", "", business_name).strip()
    business_name = re.sub(r",?\s*TN\b.*$", "", business_name).strip()

    # -- Detect city --------------------------------------------------------
    city = _find_tn_city(title) or _find_tn_city(content or "")

    if not business_name:
        return []

    rec = _empty_record(source_url, "search_snippet", county)
    rec["business_name"] = business_name
    rec["city"] = city
    if city:
        rec["state"] = "TN"

    return [rec]
