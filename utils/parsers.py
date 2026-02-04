from __future__ import annotations

import re


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

        # Default state to TN (Nashville-area pipeline assumption)
        if rec["address"] or rec["city"]:
            rec["state"] = "TN"

        records.append(rec)

    return records


# ---------------------------------------------------------------------------


# Known Nashville-area city names used by multiple parsers
_TN_CITIES = [
    "Nashville", "Franklin", "Brentwood", "Murfreesboro", "Gallatin",
    "Hendersonville", "Lebanon", "Smyrna", "Goodlettsville", "Madison",
    "Antioch", "Hermitage", "Spring Hill", "Columbia",
    "Shelbyville", "McMinnville", "Cookeville", "Clarksville",
    "Dickson", "Springfield", "Carthage", "Tullahoma", "Pulaski",
]


def _find_tn_city(text: str) -> str | None:
    """Return the first known TN city found in *text*, or None."""
    for city in _TN_CITIES:
        # Word-boundary match, case-insensitive
        if re.search(r"\b" + re.escape(city) + r"\b", text, re.IGNORECASE):
            return city
    return None


def _extract_address_line(lines: list[str]) -> str | None:
    """Pick the best address-like line from a list of candidate lines.

    Prefers lines that start with '*' (italic markdown) and contain a digit.
    Falls back to any line that starts with a digit followed by a street name.
    """
    # Priority 1: italic-markdown lines with a number (street address)
    for line in lines:
        cleaned = line.lstrip("* ").strip()
        if cleaned and re.match(r"\d", cleaned):
            return cleaned

    # Priority 2: any line starting with a digit
    for line in lines:
        cleaned = line.strip()
        if re.match(r"\d+\s+\S", cleaned):
            return cleaned

    return None


def parse_news_article(content: str, source_url: str, county: str | None = None) -> list[dict]:
    """Parse news articles that use ## headings for business names.

    Each ## section is treated as one business.  Address lines are detected
    by italic-markdown markers (*) or by a leading street number.  City is
    extracted from the address when present, or looked up against a known
    list of Nashville-area cities.

    If no ## headings are found at all, a fallback heuristic scans plain
    lines for words like "opening", "new", "launches", etc. and attempts to
    pull a business name from those sentences.
    """
    sections = re.split(r"(?=^## )", content, flags=re.MULTILINE)

    records: list[dict] = []
    found_heading = False

    for section in sections:
        lines = section.splitlines()
        if not lines:
            continue

        # Detect whether this section starts with a ## heading
        first_line = lines[0].strip()
        if not first_line.startswith("## "):
            # This is either the preamble (before any ##) or a non-heading block
            continue

        found_heading = True
        business_name = first_line.lstrip("# ").strip()
        if not business_name:
            continue

        # Gather candidate address lines (italic or street-number lines)
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

        # If city still not resolved, scan the whole section text
        if not rec["city"]:
            rec["city"] = _find_tn_city(section)

        if rec["address"] or rec["city"]:
            rec["state"] = "TN"

        records.append(rec)

    # ---------------------------------------------------------------------------
    # Fallback: no ## headings found — scan for announcement-style lines
    # ---------------------------------------------------------------------------
    if not found_heading:
        announce_keywords = re.compile(
            r"\b(opening|opens|new|launch(?:es|ed)?|now open|grand opening|debut(?:s|ed)?)\b",
            re.IGNORECASE,
        )
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped or announce_keywords.search(stripped) is None:
                continue

            # Heuristic: business name is likely the first quoted string, or
            # everything before the keyword.
            quoted = re.search(r'["\u201c]([^"\u201d]+)["\u201d]', stripped)
            if quoted:
                biz_name = quoted.group(1).strip()
            else:
                # Take text before the first announcement keyword
                match = announce_keywords.search(stripped)
                biz_name = stripped[: match.start()].strip().rstrip(",.:;-–—").strip()

            if not biz_name:
                continue

            rec = _empty_record(source_url, "news_article", county)
            rec["business_name"] = biz_name
            rec["city"] = _find_tn_city(stripped)
            if rec["city"]:
                rec["state"] = "TN"
            records.append(rec)

    return records


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
