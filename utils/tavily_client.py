import os

import requests

from config.settings import TAVILY_API_KEY

BASE_URL = "https://api.tavily.com"


class TavilyClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or TAVILY_API_KEY
        if not self.api_key:
            raise ValueError("TAVILY_API_KEY not set")

    def search(self, query: str, max_results: int = 10) -> list[dict]:
        """POST to {BASE_URL}/search and return the 'results' list.

        Each result dict contains at minimum: title, url, content.
        Returns an empty list on any HTTP error or if the 'results' key
        is missing from the response.
        """
        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "include_domains": [],
            "exclude_domains": [],
        }

        try:
            response = requests.post(f"{BASE_URL}/search", json=payload)
            response.raise_for_status()
        except requests.RequestException:
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
        """POST to {BASE_URL}/extract and return the full response JSON.

        The returned dict is expected to contain 'content' and 'url' keys.
        Returns None on any error.
        """
        payload = {
            "api_key": self.api_key,
            "url": url,
        }

        try:
            response = requests.post(f"{BASE_URL}/extract", json=payload)
            response.raise_for_status()
        except requests.RequestException:
            return None

        try:
            data = response.json()
        except ValueError:
            return None

        return data
