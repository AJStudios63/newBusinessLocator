"""
Geocoding utility using OpenStreetMap's Nominatim API.

Uses stdlib only (no pip dependencies). Never raises exceptions - all errors
are caught and logged, returning None values for failed geocoding attempts.
"""

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)

# Nominatim requires a custom User-Agent
_USER_AGENT = "NewBusinessLocator/1.0 (lead-gen-pipeline)"
_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
# Nominatim requires max 1 req/sec - we use 1.1s to be safe
_MIN_INTERVAL = 1.1


def _build_query_string(record: dict) -> str | None:
    """
    Build a geocoding query string from a lead record.

    Args:
        record: Dict with optional keys: address, city, state, zip_code

    Returns:
        Query string like "123 Main St, Nashville, TN, 37201" or None if no city
    """
    city = record.get("city", "").strip()
    if not city:
        return None

    parts = []

    address = record.get("address", "").strip()
    if address:
        parts.append(address)

    parts.append(city)

    state = record.get("state", "TN").strip()
    if state:
        parts.append(state)

    zip_code = record.get("zip_code", "").strip()
    if zip_code:
        parts.append(zip_code)

    return ", ".join(parts)


def geocode_lead(record: dict) -> tuple[float | None, float | None]:
    """
    Geocode a single lead record using Nominatim API.

    Args:
        record: Dict with address fields (address, city, state, zip_code)

    Returns:
        Tuple of (latitude, longitude) as floats, or (None, None) on failure

    Never raises exceptions - all errors are caught and logged.
    """
    query = _build_query_string(record)
    if not query:
        logger.warning("Cannot geocode record without city: %s", record)
        return (None, None)

    try:
        # Build request URL
        params = {
            "q": query,
            "format": "json",
            "limit": "1",
            "countrycodes": "us"
        }
        url = f"{_NOMINATIM_URL}?{urllib.parse.urlencode(params)}"

        # Make request with custom User-Agent
        req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))

        # Extract lat/lon from first result
        if data and len(data) > 0:
            result = data[0]
            lat = float(result["lat"])
            lon = float(result["lon"])
            logger.debug("Geocoded '%s' -> (%s, %s)", query, lat, lon)
            return (lat, lon)
        else:
            logger.warning("No results for query: %s", query)
            return (None, None)

    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, ValueError, json.JSONDecodeError) as e:
        logger.warning("Geocoding failed for '%s': %s", query, e)
        return (None, None)
    except Exception as e:
        logger.warning("Unexpected error geocoding '%s': %s", query, e)
        return (None, None)


def geocode_batch(records: list[dict], progress_callback=None) -> list[dict]:
    """
    Geocode a batch of lead records, respecting Nominatim rate limits.

    Args:
        records: List of lead dicts to geocode (mutated in-place)
        progress_callback: Optional function(geocoded_count, total_to_geocode)
                          called every 10 records

    Returns:
        The records list (for convenience - records are mutated in-place)

    Only geocodes records where latitude or longitude is None.
    Uses in-memory cache to avoid duplicate API calls for same query.
    Enforces 1.1s minimum interval between API requests.
    """
    # Filter to records that need geocoding
    to_geocode = [r for r in records if r.get("latitude") is None or r.get("longitude") is None]

    if not to_geocode:
        logger.info("No records need geocoding")
        return records

    logger.info("Geocoding %d records (out of %d total)", len(to_geocode), len(records))

    # In-memory cache: query_string -> (lat, lon)
    cache = {}
    last_request_time = 0.0
    succeeded = 0
    failed = 0
    skipped = 0

    for idx, record in enumerate(to_geocode, start=1):
        query = _build_query_string(record)

        if not query:
            skipped += 1
            continue

        # Check cache
        if query in cache:
            lat, lon = cache[query]
            record["latitude"] = lat
            record["longitude"] = lon
            if lat is not None and lon is not None:
                succeeded += 1
            else:
                failed += 1
            continue

        # Enforce rate limit
        elapsed = time.monotonic() - last_request_time
        if elapsed < _MIN_INTERVAL:
            sleep_time = _MIN_INTERVAL - elapsed
            time.sleep(sleep_time)

        # Make API call
        lat, lon = geocode_lead(record)
        last_request_time = time.monotonic()

        # Cache and update record
        cache[query] = (lat, lon)
        record["latitude"] = lat
        record["longitude"] = lon

        if lat is not None and lon is not None:
            succeeded += 1
        else:
            failed += 1

        # Progress callback every 10 records
        if progress_callback and idx % 10 == 0:
            progress_callback(idx, len(to_geocode))

    logger.info("Geocoding complete: %d succeeded, %d failed, %d skipped", succeeded, failed, skipped)

    return records
