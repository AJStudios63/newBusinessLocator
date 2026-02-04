"""
Transform phase of the ETL pipeline.

Routes raw extracts to the appropriate parser, classifies business types,
filters out chain businesses, scores leads, infers counties from city
mappings, and deduplicates the final record set.
"""

import yaml
from datetime import datetime
from config.settings import SCORING_YAML, CHAINS_YAML, SOURCES_YAML
from utils.parsers import parse_license_table, parse_news_article, parse_snippet
from utils.dedup import generate_fingerprint


def _load_yaml(path) -> dict:
    """Load a yaml file."""
    with open(path, "r") as fh:
        return yaml.safe_load(fh)


def _validate_scoring(scoring: dict) -> None:
    """
    Validate that scoring.yaml contains all required keys with correct types.

    Raises ValueError if any required key is missing or has the wrong type.
    """
    required_keys = {
        "type_scores": dict,
        "business_type_keywords": dict,
        "source_scores": dict,
        "address_scores": dict,
        "recency_scores": list,
    }

    missing_keys = []
    type_errors = []

    for key, expected_type in required_keys.items():
        if key not in scoring:
            missing_keys.append(key)
        elif not isinstance(scoring[key], expected_type):
            actual_type = type(scoring[key]).__name__
            type_errors.append(
                f"'{key}' should be {expected_type.__name__}, got {actual_type}"
            )

    errors = []
    if missing_keys:
        errors.append(f"Missing required keys: {', '.join(missing_keys)}")
    if type_errors:
        errors.extend(type_errors)

    if errors:
        raise ValueError(
            f"Invalid scoring.yaml configuration: {'; '.join(errors)}"
        )


def _build_city_to_county_map(sources: dict) -> dict[str, str]:
    """
    From sources.yaml counties dict, build a reverse map:
    {city_lowercase: county_name}.
    """
    city_to_county: dict[str, str] = {}
    for county_name, cities in sources.get("counties", {}).items():
        for city in cities:
            city_to_county[city.lower()] = county_name
    return city_to_county


def classify(record: dict, type_keywords: dict) -> dict:
    """
    Classify a BusinessRecord by matching raw_type against the keyword
    lists defined in scoring.yaml.

    If raw_type is None or empty the business_type is set to 'other'.
    Otherwise the keyword map is walked in insertion order; the first
    type whose keyword list contains a case-insensitive substring match
    against raw_type wins.  When no keyword matches the type falls back
    to 'other'.

    The record is mutated in place and also returned for convenience.
    """
    raw_type = record.get("raw_type")
    if not raw_type:
        record["business_type"] = "other"
        return record

    raw_type_lower = raw_type.lower()
    for biz_type, keywords in type_keywords.items():
        for kw in keywords:
            if kw.lower() in raw_type_lower:
                record["business_type"] = biz_type
                return record

    record["business_type"] = "other"
    return record


def is_chain(business_name: str, chain_list: list[str]) -> bool:
    """
    Return True if any chain name from *chain_list* appears as a
    case-insensitive substring of *business_name*.
    """
    name_lower = business_name.lower()
    return any(chain.lower() in name_lower for chain in chain_list)


def score_lead(record: dict, scoring: dict) -> int:
    """
    Compute a lead-quality score (0-100) from four components:

    A) Business-type score   – looked up from scoring['type_scores'];
                                defaults to 10 for 'other'.
    B) Source-confidence     – looked up from scoring['source_scores'];
                                defaults to 0 for unknown source types.
    C) Address completeness  – tiered: street+city+zip (15),
                                street+city (10), city only (5), none (0).
    D) Recency               – days since license_date, matched against
                                the ordered recency_scores thresholds.

    The raw sum is clamped to [0, 100] before being returned.  The
    computed score is also stored in record['pos_score'].
    """
    # A) Business type score
    type_scores = scoring.get("type_scores", {})
    biz_type = record.get("business_type", "other")
    type_score = type_scores.get(biz_type, 10)

    # B) Source confidence
    source_scores = scoring.get("source_scores", {})
    source_score = source_scores.get(record.get("source_type"), 0)

    # C) Address completeness
    address_scores = scoring.get("address_scores", {})
    has_street = bool(record.get("address"))
    has_city = bool(record.get("city"))
    has_zip = bool(record.get("zip_code"))

    if has_street and has_city and has_zip:
        addr_score = address_scores.get("street_city_zip", 15)
    elif has_street and has_city:
        addr_score = address_scores.get("street_city", 10)
    elif has_city:
        addr_score = address_scores.get("city_only", 5)
    else:
        addr_score = address_scores.get("none", 0)

    # D) Recency
    recency_score = 0
    license_date_raw = record.get("license_date")
    if license_date_raw:
        license_date = _parse_date(license_date_raw)
        if license_date is not None:
            days_ago = (datetime.today().date() - license_date).days
            for tier in scoring.get("recency_scores", []):
                max_days = tier.get("max_days")
                if max_days is None or days_ago <= max_days:
                    recency_score = tier.get("score", 0)
                    break

    total = type_score + source_score + addr_score + recency_score
    total = max(0, min(100, total))
    record["pos_score"] = total
    return total


def _parse_date(date_str: str) -> "datetime.date | None":
    """
    Attempt to parse *date_str* using the four expected formats.
    Returns a datetime.date on success, None if nothing matches.
    """
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%B %d, %Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except (ValueError, AttributeError):
            continue
    return None


def infer_county(record: dict, city_to_county: dict) -> dict:
    """
    If the record already has a county value, return it unchanged.
    Otherwise attempt to look up the county from *city_to_county* using
    the record's city.  The record is mutated in place and returned.
    """
    if record.get("county"):
        return record

    city = record.get("city")
    if city:
        inferred = city_to_county.get(city.lower().strip())
        if inferred:
            record["county"] = inferred

    return record


def deduplicate(records: list[dict]) -> list[dict]:
    """
    Deduplicate *records* by fingerprint.

    A fingerprint is generated from each record's business_name and city.
    When two records share the same fingerprint only the one with the
    higher pos_score is retained.  Every record in the returned list has
    a 'fingerprint' key.
    """
    best: dict[str, dict] = {}
    for record in records:
        fp = generate_fingerprint(
            record.get("business_name", ""),
            record.get("city", ""),
        )
        record["fingerprint"] = fp

        existing = best.get(fp)
        if existing is None or record.get("pos_score", 0) > existing.get("pos_score", 0):
            best[fp] = record

    return list(best.values())


def run_transform(raw_extracts: list[dict]) -> list[dict]:
    """
    Main transform entry-point.

    Accepts a list of RawExtract dicts and returns a list of fully
    processed BusinessRecord dicts with *fingerprint* and *pos_score*
    populated.

    Pipeline
    --------
    1. Load YAML configuration files.
    2. Build the city-to-county reverse map.
    3. Route each RawExtract to the correct parser and flatten all
       resulting BusinessRecords into a single list.
    4. For every BusinessRecord: classify its type, drop it if it
       belongs to a known chain, score it, and infer its county.
    5. Deduplicate the list (higher pos_score wins on collision).
    6. Return the final list.
    """
    # 1. Load configuration
    scoring = _load_yaml(SCORING_YAML)
    _validate_scoring(scoring)
    chains_cfg = _load_yaml(CHAINS_YAML)
    sources = _load_yaml(SOURCES_YAML)

    type_keywords: dict = scoring.get("business_type_keywords", {})
    chain_list: list[str] = chains_cfg.get("chains", [])

    # 2. Build city -> county lookup
    city_to_county = _build_city_to_county_map(sources)

    # 3. Parse raw extracts into BusinessRecords
    all_records: list[dict] = []
    for extract in raw_extracts:
        source_type = extract.get("source_type", "")
        raw_content = extract.get("raw_content", "")
        source_url = extract.get("source_url", "")
        county = extract.get("county")
        title = extract.get("title", "")

        if source_type == "license_table":
            parsed = parse_license_table(raw_content, source_url, county)
        elif source_type == "news_article":
            parsed = parse_news_article(raw_content, source_url, county)
        elif source_type == "search_snippet":
            parsed = parse_snippet(title, raw_content, source_url, county)
        else:
            # Unknown source type – skip silently
            continue

        all_records.extend(parsed)

    # 4. Classify, filter chains, score, infer county
    output_records: list[dict] = []
    for record in all_records:
        classify(record, type_keywords)

        if is_chain(record.get("business_name", ""), chain_list):
            continue

        score_lead(record, scoring)
        infer_county(record, city_to_county)
        output_records.append(record)

    # 5. Deduplicate
    output_records = deduplicate(output_records)

    # 6. Return
    return output_records
