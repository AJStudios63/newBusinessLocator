"""
Extract phase of the ETL pipeline.

Reads search queries from sources.yaml, calls Tavily search for each,
filters URLs against blocked/extractable domain lists and already-seen URLs,
extracts qualifying pages, and returns structured RawExtract dicts.
"""

from __future__ import annotations

import sqlite3
from urllib.parse import urlparse

import yaml

from config.settings import SOURCES_YAML, DB_PATH
from utils.tavily_client import TavilyClient
from utils.logging_config import get_logger
from db.schema import init_db
from db.queries import get_seen_urls

logger = get_logger("extract")


# ---------------------------------------------------------------------------
# RawExtract schema (plain dict)
# ---------------------------------------------------------------------------
# {
#     "raw_content" : str   — extracted page content or search snippet
#     "source_url"  : str
#     "county"      : str | None
#     "source_type" : str   — 'license_table', 'news_article', or 'search_snippet'
#     "title"       : str   — page title
# }


def _get_domain(url: str) -> str:
    """Extract domain from URL, stripping the 'www.' prefix if present."""
    netloc = urlparse(url).netloc
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


def _load_sources() -> dict:
    """Load and return the parsed contents of sources.yaml as a dict."""
    with open(SOURCES_YAML, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _validate_sources(sources: dict) -> None:
    """
    Validate that sources.yaml contains all required keys with correct types.

    Raises ValueError if any required key is missing or has the wrong type.
    """
    required_keys = {
        "queries": list,
        "extractable_domains": list,
        "blocked_domains": list,
    }

    missing_keys = []
    type_errors = []

    for key, expected_type in required_keys.items():
        if key not in sources:
            missing_keys.append(key)
        elif not isinstance(sources[key], expected_type):
            actual_type = type(sources[key]).__name__
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
            f"Invalid sources.yaml configuration: {'; '.join(errors)}"
        )


def _determine_source_type(title: str) -> str:
    """
    Classify a page title into a source type.

    Returns 'license_table' if the title (case-insensitive) contains
    'new business license' or 'business licenses'; otherwise returns
    'news_article'.
    """
    lower = title.lower()
    if "new business license" in lower or "business licenses" in lower:
        return "license_table"
    return "news_article"


def _domain_matches(domain: str, domain_list: list[str]) -> bool:
    """
    Return True if *domain* ends with any entry in *domain_list*.

    This lets a bare domain like 'tennessean.com' match subdomains such as
    'www.tennessean.com' (after www has already been stripped) as well as
    deeper subdomains like 'sub.tennessean.com'.
    """
    for pattern in domain_list:
        if domain == pattern or domain.endswith("." + pattern):
            return True
    return False


def run_extract(
    client: TavilyClient | None = None,
    conn: sqlite3.Connection | None = None,
    use_db: bool = True,
) -> list[dict]:
    """
    Main extract entry point.  Returns a list of RawExtract dicts.

    Parameters
    ----------
    client : TavilyClient | None
        An already-instantiated TavilyClient.  One is created automatically
        when not provided.
    conn : sqlite3.Connection | None
        An already-open DB connection.  One is created via init_db when not
        provided.
    use_db : bool
        When False, skip all database access (no init_db, no seen_urls lookup).

    Returns
    -------
    list[dict]
        RawExtract dicts collected across all queries.
    """
    # ------------------------------------------------------------------
    # 1. Load configuration from sources.yaml
    # ------------------------------------------------------------------
    logger.info("Loading configuration from sources.yaml")
    sources = _load_sources()
    _validate_sources(sources)
    queries: list[dict] = sources.get("queries", [])
    extractable_domains: list[str] = sources.get("extractable_domains", [])
    blocked_domains: list[str] = sources.get("blocked_domains", [])
    direct_extract_urls: list[dict] = sources.get("direct_extract_urls", [])
    logger.debug(f"Loaded {len(queries)} queries, {len(extractable_domains)} extractable domains, {len(direct_extract_urls)} direct URLs")

    # ------------------------------------------------------------------
    # 2. Open DB connection and fetch already-seen URLs
    # ------------------------------------------------------------------
    owns_connection = False
    if use_db:
        owns_connection = conn is None
        if owns_connection:
            conn = init_db(DB_PATH)
        seen_urls: set[str] = get_seen_urls(conn)
    else:
        seen_urls = set()

    try:
        # ------------------------------------------------------------------
        # 3. Create TavilyClient if not provided
        # ------------------------------------------------------------------
        if client is None:
            client = TavilyClient()

        # In-memory set to deduplicate URLs discovered within this single run
        processed_this_run: set[str] = set()

        results: list[dict] = []

        # ------------------------------------------------------------------
        # 4. Process direct extract URLs first (license tables)
        # ------------------------------------------------------------------
        if direct_extract_urls:
            logger.info(f"Processing {len(direct_extract_urls)} direct extract URLs")
            for url_entry in direct_extract_urls:
                url: str = url_entry.get("url", "")
                county: str | None = url_entry.get("county")

                if not url:
                    continue

                # Skip if already seen in DB or processed this run
                if url in seen_urls or url in processed_this_run:
                    logger.debug(f"Skipping already-seen direct URL: {url}")
                    continue

                # Extract the page content
                logger.debug(f"Extracting direct URL: {url}")
                extracted = client.extract(url)
                if extracted is None:
                    logger.warning(f"Failed to extract direct URL: {url}")
                    continue

                extracted_content: str = extracted.get("content", "")
                title: str = extracted.get("title", "")

                # Determine source type from title (should be license_table for these URLs)
                source_type: str = _determine_source_type(title)

                results.append({
                    "raw_content": extracted_content,
                    "source_url": url,
                    "county": county,
                    "source_type": source_type,
                    "title": title,
                })

                processed_this_run.add(url)

            logger.info(f"Collected {len(results)} extracts from direct URLs")

        # ------------------------------------------------------------------
        # 5. Iterate over every search query
        # ------------------------------------------------------------------
        for query_entry in queries:
            query_text: str = query_entry.get("query", "")
            county: str | None = query_entry.get("county")

            # 5a – Search
            logger.debug(f"Searching for: {query_text}")
            search_results: list[dict] = client.search(query_text, max_results=10)
            if not search_results:
                # Empty or failed search — move on to the next query
                logger.debug(f"No results for query: {query_text}")
                continue
            logger.debug(f"Found {len(search_results)} results for query: {query_text}")

            # 5b – Process each individual search result
            for result in search_results:
                url: str = result.get("url", "")
                if not url:
                    continue

                domain = _get_domain(url)

                # --- filter: blocked domain -------------------------------------------
                if _domain_matches(domain, blocked_domains):
                    continue

                # --- filter: already seen (DB) or already processed (this run) ---------
                if url in seen_urls or url in processed_this_run:
                    continue

                # --- branch: extractable vs. snippet ----------------------------------
                if _domain_matches(domain, extractable_domains):
                    # Attempt full-page extraction
                    extracted = client.extract(url)
                    if extracted is None:
                        # Extraction failed — skip this URL entirely
                        continue

                    extracted_content: str = extracted.get("content", "")
                    # Title: prefer extracted title, fall back to search-result title
                    title: str = extracted.get("title") or result.get("title", "")
                    source_type: str = _determine_source_type(title)

                    results.append({
                        "raw_content": extracted_content,
                        "source_url": url,
                        "county": county,
                        "source_type": source_type,
                        "title": title,
                    })
                else:
                    # Domain is neither blocked nor extractable — keep as snippet
                    results.append({
                        "raw_content": result.get("content", ""),
                        "source_url": url,
                        "county": county,
                        "source_type": "search_snippet",
                        "title": result.get("title", ""),
                    })

                # Mark URL as processed so we don't revisit it later in this run
                processed_this_run.add(url)

        logger.info(f"Extract completed: {len(results)} raw extracts collected")
        return results

    finally:
        # ------------------------------------------------------------------
        # 6. Ensure connection cleanup on success or error
        # ------------------------------------------------------------------
        if owns_connection and conn:
            conn.close()
