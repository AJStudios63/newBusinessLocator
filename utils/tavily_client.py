from __future__ import annotations

import time

import requests

from config.settings import TAVILY_API_KEY
from utils.logging_config import get_logger

logger = get_logger("tavily_client")

BASE_URL: str = "https://api.tavily.com"
DEFAULT_TIMEOUT: tuple[int, int] = (5, 20)

# Rate limiting configuration
RATE_LIMIT_DELAY: float = 0.5  # seconds between API calls
MAX_RETRIES: int = 3  # maximum retry attempts for 429 responses
INITIAL_BACKOFF: float = 1.0  # initial backoff delay in seconds for 429 responses

# User-Agent header for HTTP requests
USER_AGENT: str = "newBusinessLocator/1.0"
DEFAULT_HEADERS: dict[str, str] = {"User-Agent": USER_AGENT}


class TavilyClient:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key: str = api_key or TAVILY_API_KEY
        if not self.api_key:
            raise ValueError("TAVILY_API_KEY not set")

    def search(self, query: str, max_results: int = 10) -> list[dict]:
        """POST to {BASE_URL}/search and return the 'results' list.

        Each result dict contains at minimum: title, url, content.
        Returns an empty list on any HTTP error or if the 'results' key
        is missing from the response.
        """
        time.sleep(RATE_LIMIT_DELAY)

        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "include_domains": [],
            "exclude_domains": [],
        }

        # Retry with exponential backoff for 429 responses
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.post(
                    f"{BASE_URL}/search",
                    json=payload,
                    headers=DEFAULT_HEADERS,
                    timeout=DEFAULT_TIMEOUT,
                )
                if response.status_code == 429:
                    if attempt < MAX_RETRIES - 1:
                        backoff_delay = INITIAL_BACKOFF * (2 ** attempt)
                        logger.debug(f"Rate limited (429), retrying in {backoff_delay}s (attempt {attempt + 1}/{MAX_RETRIES})")
                        time.sleep(backoff_delay)
                        continue
                    logger.warning(f"Rate limited (429) after {MAX_RETRIES} attempts for search query")
                    return []
                response.raise_for_status()
                break
            except requests.RequestException as e:
                logger.error(f"HTTP request failed for search: {e}")
                return []

        try:
            data = response.json()
        except ValueError:
            return []

        results = data.get("results")
        if not isinstance(results, list):
            return []

        # Ensure each result has at minimum the expected keys; skip malformed entries
        cleaned: list[dict] = []
        for item in results:
            if not isinstance(item, dict):
                continue
            if "title" not in item or "url" not in item or "content" not in item:
                continue
            cleaned.append(item)

        return cleaned

    def extract(self, url: str) -> dict | None:
        """POST to {BASE_URL}/extract and return extracted content.

        The returned dict contains 'content' (or 'raw_content'), 'url', and 'title' keys.
        Returns None on any error or if extraction fails.
        """
        time.sleep(RATE_LIMIT_DELAY)

        payload = {
            "api_key": self.api_key,
            "urls": url,  # API expects 'urls' (can be string or array)
        }

        # Retry with exponential backoff for 429 responses
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.post(
                    f"{BASE_URL}/extract",
                    json=payload,
                    headers=DEFAULT_HEADERS,
                    timeout=DEFAULT_TIMEOUT,
                )
                if response.status_code == 429:
                    if attempt < MAX_RETRIES - 1:
                        backoff_delay = INITIAL_BACKOFF * (2 ** attempt)
                        logger.debug(f"Rate limited (429), retrying in {backoff_delay}s (attempt {attempt + 1}/{MAX_RETRIES})")
                        time.sleep(backoff_delay)
                        continue
                    logger.warning(f"Rate limited (429) after {MAX_RETRIES} attempts for extract: {url}")
                    return None
                response.raise_for_status()
                break
            except requests.RequestException as e:
                logger.error(f"HTTP request failed for extract {url}: {e}")
                return None

        try:
            data = response.json()
        except ValueError:
            return None

        # Response format: {"results": [...], "failed_results": [...]}
        results = data.get("results", [])
        if not results:
            failed = data.get("failed_results", [])
            if failed:
                logger.debug(f"Extract failed for {url}: {failed[0].get('error', 'unknown error')}")
            return None

        # Return first result, normalizing content field name
        result = results[0]
        # API may return 'raw_content' or 'content' depending on version
        if "raw_content" in result and "content" not in result:
            result["content"] = result["raw_content"]

        return result
