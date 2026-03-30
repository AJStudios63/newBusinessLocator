"""
TN County Clerk business list scraper.

Fetches new business license data from secure.tncountyclerk.com/businesslist
using a 3-step session flow: county selection → form page → date-range search.
"""

from __future__ import annotations

import requests
from bs4 import BeautifulSoup

from utils.logging_config import get_logger

logger = get_logger("clerk_scraper")

BASE_URL = "https://secure.tncountyclerk.com"


class ClerkScraper:
    """Client for the TN County Clerk business list portal."""

    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "NewBusinessLocator/1.0 (ETL Pipeline)",
        })

    def fetch_county(
        self,
        county_code: int,
        start_date: str,
        end_date: str,
    ) -> list[dict]:
        """
        Fetch new business licenses for a county within a date range.

        Parameters
        ----------
        county_code : int
            Numeric county code (e.g., 19 for Davidson).
        start_date : str
            Start date in yyyy-mm-dd format.
        end_date : str
            End date in yyyy-mm-dd format.

        Returns
        -------
        list[dict]
            Each dict has keys: business_name, product, address, owner, date.

        Raises
        ------
        ValueError
            If a required token cannot be extracted from the portal HTML.
        Exception
            If any HTTP request fails.
        """
        # Step 1: GET county page to establish session and get renewalToken
        logger.debug(f"Step 1: Selecting county {county_code}")
        resp1 = self.session.get(
            f"{self.base_url}/index.php?countylist={county_code}"
        )
        resp1.raise_for_status()

        renewal_token = self._extract_hidden_field(resp1.text, "renewalToken")
        if not renewal_token:
            raise ValueError(
                f"Could not find renewalToken in county page for code {county_code}"
            )

        # Step 2: POST to business list page to get search form token
        logger.debug(f"Step 2: Loading search form for county {county_code}")
        resp2 = self.session.post(
            f"{self.base_url}/businesslist/index.php",
            data={
                "countylist": county_code,
                "renewalToken": renewal_token,
            },
        )
        resp2.raise_for_status()

        search_token = self._extract_hidden_field(resp2.text, "token")
        if not search_token:
            raise ValueError(
                f"Could not find search token in form page for county {county_code}"
            )

        # Step 3: POST date-range search
        logger.debug(f"Step 3: Searching {start_date} to {end_date} for county {county_code}")
        resp3 = self.session.post(
            f"{self.base_url}/businesslist/searchResults.php",
            data={
                "token": search_token,
                "BmStartDateSTART_DATE": start_date,
                "BmStartDateEND_DATE": end_date,
                "BmStartDateALIAS": "a",
                "orderby": "a.bmBusName",
                "orderbyvalue": "ASC",
                "countylist": county_code,
            },
        )
        resp3.raise_for_status()

        return self._parse_results_table(resp3.text)

    def _extract_hidden_field(self, html: str, field_name: str) -> str | None:
        """Extract the value of a hidden input field from HTML."""
        soup = BeautifulSoup(html, "html.parser")
        field = soup.find("input", {"name": field_name, "type": "hidden"})
        if field and field.get("value"):
            return field["value"]
        return None

    def _parse_results_table(self, html: str) -> list[dict]:
        """Parse the results HTML table into a list of business dicts."""
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if not table:
            return []

        rows = table.find_all("tr", class_=["even", "odd"])
        results = []

        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 5:
                continue

            results.append({
                "business_name": cells[0].get_text(strip=True),
                "product": cells[1].get_text(strip=True),
                "address": cells[2].get_text(strip=True),
                "owner": cells[3].get_text(strip=True),
                "date": cells[4].get_text(strip=True),
            })

        return results
