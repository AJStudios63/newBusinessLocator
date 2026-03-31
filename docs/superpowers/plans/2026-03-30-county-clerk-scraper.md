# TN County Clerk Scraper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a scraper for the TN County Clerk business list portal (`secure.tncountyclerk.com`) that fetches structured new-business license data and integrates it into the existing ETL pipeline, replacing the Tavily-based Tier A `*countysource.com` queries for supported counties.

**Architecture:** A new `ClerkScraper` client in `utils/clerk_scraper.py` handles the 3-step session flow (county selection → form page → date-range search). A new `parse_clerk_table()` parser in `utils/parsers.py` converts the HTML table rows into BusinessRecord dicts. The extract phase (`etl/extract.py`) gains a new step that runs clerk scraping before Tavily queries, producing `RawExtract` dicts with `source_type: "clerk_table"`. Scoring config adds `clerk_table` as a new source type scoring 20 (same as `license_table` — this is authoritative county clerk data). The pipeline orchestration (`etl/pipeline.py`) requires no changes — clerk results are just more RawExtract dicts flowing through the same transform/load pipeline.

**Tech Stack:** Python `requests` (already in requirements.txt), `BeautifulSoup4` (new dependency), existing SQLite/YAML infrastructure.

---

## Research Findings: Scraper vs. Current Approach

### Which counties support the business list?

The TN County Clerk portal (`secure.tncountyclerk.com/businesslist/`) is available for **43 of 95** TN counties. Of our 13 configured counties:

| County | Clerk Portal? | Current Source | Recommendation |
|--------|:---:|---|---|
| Davidson | Yes (code 19) | davidsoncountysource.com Tier A | **Replace** with clerk scraper |
| Williamson | Yes (code 94) | williamsonsource.com Tier A | **Replace** with clerk scraper |
| Wilson | Yes (code 95) | wilsoncountysource.com Tier A | **Replace** with clerk scraper |
| Robertson | Yes (code 74) | robertsoncountysource.com Tier A | **Replace** with clerk scraper |
| Maury | Yes (code 60) | maurycountysource.com Tier A | **Replace** with clerk scraper |
| Dickson | Yes (code 22) | dicksoncountysource.com Tier A | **Replace** with clerk scraper |
| Cheatham | Yes (code 11) | cheathamcountysource.com Tier A | **Replace** with clerk scraper |
| Montgomery | Yes (code 63) | Tier B only (no countysource) | **Add** clerk scraper (new data!) |
| **Rutherford** | **No** | Tier B only | Keep Tier B queries only |
| **Sumner** | **No** | Tier B only | Keep Tier B queries only |
| **Putnam** | **No** | Tier B only | Keep Tier B queries only |
| Coffee | No | Tier B only | Keep Tier B queries only |
| Franklin | No | Tier B only | Keep Tier B queries only |

### Why replace `*countysource.com` Tier A queries?

1. **Authoritative source** — The county clerk IS the issuing authority. The `*countysource.com` sites are local news blogs that repackage this same data (sometimes with a delay).
2. **No Tavily credits consumed** — Clerk scraping uses direct HTTP requests, saving Tavily API credits for Tier B/C news discovery.
3. **Structured data** — The clerk portal returns consistent HTML tables with 5 columns: Business Name, Product (raw_type), Address, Business Owner, Date. No markdown parsing needed.
4. **Date-range control** — We can query exact date ranges (e.g., last 30 days) instead of hoping Tavily finds the right article.
5. **Gains Montgomery County** — Montgomery (Clarksville, ~220k population) has no `*countysource.com` site but DOES have the clerk portal. This is net-new structured data.

### What the clerk portal returns

Sample row from a Davidson County query (30-day range, 437 results):
```html
<tr class="even">
    <td>ABOVE PAR PAINTING</td>      <!-- Business Name -->
    <td>PAINTING</td>                 <!-- Product (maps to raw_type) -->
    <td>249 THUSS AVE  NASHVILLE TN 37211</td>  <!-- Address -->
    <td>ALEX  SENGMANYVONG</td>       <!-- Business Owner -->
    <td>2026-03-27</td>               <!-- Date -->
</tr>
```

### Portal session flow

The portal requires a 3-step session:

1. **GET** `https://secure.tncountyclerk.com/index.php?countylist={code}` — Sets PHP session cookie + returns `renewalToken` in a hidden field
2. **POST** `https://secure.tncountyclerk.com/businesslist/index.php` with `countylist={code}&renewalToken={token}` — Returns the search form page with a new `token` hidden field
3. **POST** `https://secure.tncountyclerk.com/businesslist/searchResults.php` with `token={token}&BmStartDateSTART_DATE={yyyy-mm-dd}&BmStartDateEND_DATE={yyyy-mm-dd}&BmStartDateALIAS=a&orderby=a.bmBusName&orderbyvalue=ASC&countylist={code}` — Returns HTML results table

No CAPTCHA, no JavaScript challenge. Session cookies (PHPSESSID, AWSALB) must be maintained across all 3 steps.

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `utils/clerk_scraper.py` | **Create** | `ClerkScraper` class: session management, 3-step flow, HTML table parsing to raw dicts |
| `utils/parsers.py` | **Modify** | Add `parse_clerk_table()` function that converts clerk raw dicts to BusinessRecord dicts |
| `etl/extract.py` | **Modify** | Add clerk scraping step before Tavily queries, producing RawExtract dicts |
| `config/sources.yaml` | **Modify** | Add `clerk_counties` config section; remove Tier A `site:*countysource.com` queries |
| `config/scoring.yaml` | **Modify** | Add `clerk_table: 20` to source_scores |
| `requirements.txt` | **Modify** | Add `beautifulsoup4` |
| `tests/test_clerk_scraper.py` | **Create** | Unit tests for ClerkScraper (mocked HTTP) |
| `tests/test_parsers.py` | **Modify** | Add tests for `parse_clerk_table()` |
| `tests/test_extract.py` | **Modify** | Add tests for clerk extraction integration |
| `tests/conftest.py` | **Modify** | Add clerk-related fixtures (sample HTML, mock responses) |

---

## Task 1: Add `beautifulsoup4` dependency

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add beautifulsoup4 to requirements.txt**

```
beautifulsoup4>=4.12
```

Add this line after the existing dependencies in `requirements.txt`.

- [ ] **Step 2: Install the dependency**

Run: `pip install -r requirements.txt`
Expected: Successfully installed beautifulsoup4

- [ ] **Step 3: Verify import works**

Run: `python3 -c "from bs4 import BeautifulSoup; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "chore: add beautifulsoup4 dependency for clerk scraper"
```

---

## Task 2: Add `clerk_counties` config and `clerk_table` source score

**Files:**
- Modify: `config/sources.yaml`
- Modify: `config/scoring.yaml`

- [ ] **Step 1: Add `clerk_counties` section to sources.yaml**

Add this new top-level section after the `counties` section in `config/sources.yaml`:

```yaml
# TN County Clerk portal (secure.tncountyclerk.com/businesslist)
# Only counties that have the business list feature are listed here.
# Code is the numeric county ID used by the portal.
clerk_counties:
  Davidson: 19
  Williamson: 94
  Wilson: 95
  Robertson: 74
  Maury: 60
  Dickson: 22
  Cheatham: 11
  Montgomery: 63
```

- [ ] **Step 2: Remove Tier A `site:*countysource.com` queries from sources.yaml**

Delete all 7 queries in the `# Tier A — License Tables` section:

```yaml
  # Tier A — License Tables  (REMOVE THIS ENTIRE BLOCK)
  - query: "site:davidsoncountysource.com new business licenses"
    county: Davidson
    tier: A
  - query: "site:williamsonsource.com new business licenses"
    county: Williamson
    tier: A
  - query: "site:wilsoncountysource.com new business licenses"
    county: Wilson
    tier: A
  - query: "site:cheathamcountysource.com new business licenses"
    county: Cheatham
    tier: A
  - query: "site:robertsoncountysource.com new business licenses"
    county: Robertson
    tier: A
  - query: "site:maurycountysource.com new business licenses"
    county: Maury
    tier: A
  - query: "site:dicksoncountysource.com new business licenses"
    county: Dickson
    tier: A
```

Keep the `direct_extract_urls` section — those are historical URLs already in `seen_urls` and won't be re-fetched anyway.

- [ ] **Step 3: Add `clerk_table` to scoring.yaml source_scores**

In `config/scoring.yaml`, add `clerk_table: 20` to the `source_scores` section:

```yaml
source_scores:
  license_table: 20
  clerk_table: 20
  news_article: 15
  search_snippet: 8
```

- [ ] **Step 4: Validate YAML files**

Run: `python3 -c "import yaml; yaml.safe_load(open('config/sources.yaml')); yaml.safe_load(open('config/scoring.yaml')); print('OK')"`
Expected: `OK`

- [ ] **Step 5: Run existing tests to verify nothing broke**

Run: `python3 -m pytest tests/ -x -q`
Expected: All tests pass (some Tier A query count assertions may need updating — fix those if they fail)

- [ ] **Step 6: Commit**

```bash
git add config/sources.yaml config/scoring.yaml
git commit -m "config: add clerk_counties mapping and clerk_table source score, remove Tier A queries"
```

---

## Task 3: Build `ClerkScraper` client with tests (TDD)

**Files:**
- Create: `utils/clerk_scraper.py`
- Create: `tests/test_clerk_scraper.py`

- [ ] **Step 1: Write the test file with fixtures and first test**

Create `tests/test_clerk_scraper.py`:

```python
"""Tests for the TN County Clerk business list scraper."""

from unittest.mock import MagicMock, patch, PropertyMock
import pytest

from utils.clerk_scraper import ClerkScraper


# ---------------------------------------------------------------------------
# Fixtures — sample HTML responses from each step of the 3-step flow
# ---------------------------------------------------------------------------

COUNTY_PAGE_HTML = """
<html><body>
<form method="post" action="/businesslist/index.php">
  <input type="hidden" name="renewalToken" value="abc123token">
  <input type="hidden" name="countylist" value="19">
  <input type="submit" value="Continue">
</form>
</body></html>
"""

SEARCH_FORM_HTML = """
<html><body>
<form name="search" method="post" action="searchResults.php">
  <input type="hidden" name="token" value="def456searchtoken">
  <input type="hidden" name="countylist" value="19">
  <input type="text" name="BmStartDateSTART_DATE">
  <input type="text" name="BmStartDateEND_DATE">
  <input type="hidden" name="BmStartDateALIAS" value="a">
  <select name="orderby">
    <option value="a.bmBusName">Business Name</option>
  </select>
  <input type="submit" value="Search">
</form>
</body></html>
"""

RESULTS_HTML = """
<html><body>
<table>
<tr>
  <th>Business Name</th><th>Product</th><th>Address</th>
  <th>Business Owner</th><th>Date</th>
</tr>
<tr class="even">
  <td>TACO FIESTA</td>
  <td>RESTAURANT</td>
  <td>123 MAIN ST  NASHVILLE TN 37201</td>
  <td>JOHN DOE</td>
  <td>2026-03-15</td>
</tr>
<tr class="odd">
  <td>GLAMOUR NAILS</td>
  <td>NAIL SALON</td>
  <td>456 ELM AVE  FRANKLIN TN 37064</td>
  <td>JANE SMITH</td>
  <td>2026-03-20</td>
</tr>
<tr class="even">
  <td>QUICK FIX PLUMBING</td>
  <td>PLUMBING</td>
  <td>789 OAK DR  NASHVILLE TN 37211</td>
  <td>BOB JONES</td>
  <td>2026-03-22</td>
</tr>
</table>
</body></html>
"""

EMPTY_RESULTS_HTML = """
<html><body>
<table>
<tr>
  <th>Business Name</th><th>Product</th><th>Address</th>
  <th>Business Owner</th><th>Date</th>
</tr>
</table>
</body></html>
"""


class TestClerkScraperInit:
    """Test ClerkScraper initialization."""

    def test_creates_session(self):
        scraper = ClerkScraper()
        assert scraper.session is not None

    def test_base_url(self):
        scraper = ClerkScraper()
        assert scraper.base_url == "https://secure.tncountyclerk.com"


class TestClerkScraperFetchCounty:
    """Test the 3-step session flow and result parsing."""

    def _mock_session(self):
        """Create a mock requests.Session that returns the 3-step HTML."""
        session = MagicMock()

        # Step 1: GET county page → returns renewalToken
        resp1 = MagicMock()
        resp1.status_code = 200
        resp1.text = COUNTY_PAGE_HTML
        resp1.raise_for_status = MagicMock()

        # Step 2: POST to business list → returns search form with token
        resp2 = MagicMock()
        resp2.status_code = 200
        resp2.text = SEARCH_FORM_HTML
        resp2.raise_for_status = MagicMock()

        # Step 3: POST search → returns results table
        resp3 = MagicMock()
        resp3.status_code = 200
        resp3.text = RESULTS_HTML
        resp3.raise_for_status = MagicMock()

        session.get.return_value = resp1
        session.post.side_effect = [resp2, resp3]

        return session

    def test_fetch_returns_list_of_dicts(self):
        scraper = ClerkScraper()
        scraper.session = self._mock_session()

        results = scraper.fetch_county(county_code=19, start_date="2026-03-01", end_date="2026-03-31")

        assert isinstance(results, list)
        assert len(results) == 3

    def test_result_dict_has_required_fields(self):
        scraper = ClerkScraper()
        scraper.session = self._mock_session()

        results = scraper.fetch_county(county_code=19, start_date="2026-03-01", end_date="2026-03-31")
        row = results[0]

        assert row["business_name"] == "TACO FIESTA"
        assert row["product"] == "RESTAURANT"
        assert row["address"] == "123 MAIN ST  NASHVILLE TN 37201"
        assert row["owner"] == "JOHN DOE"
        assert row["date"] == "2026-03-15"

    def test_parses_all_rows(self):
        scraper = ClerkScraper()
        scraper.session = self._mock_session()

        results = scraper.fetch_county(county_code=19, start_date="2026-03-01", end_date="2026-03-31")

        names = [r["business_name"] for r in results]
        assert names == ["TACO FIESTA", "GLAMOUR NAILS", "QUICK FIX PLUMBING"]

    def test_empty_results_returns_empty_list(self):
        scraper = ClerkScraper()
        session = self._mock_session()
        # Override step 3 to return empty results
        resp3 = MagicMock()
        resp3.status_code = 200
        resp3.text = EMPTY_RESULTS_HTML
        resp3.raise_for_status = MagicMock()
        session.post.side_effect = [session.post.side_effect[0], resp3]

        scraper.session = session
        results = scraper.fetch_county(county_code=19, start_date="2026-03-01", end_date="2026-03-31")

        assert results == []

    def test_session_flow_calls_correct_urls(self):
        scraper = ClerkScraper()
        scraper.session = self._mock_session()

        scraper.fetch_county(county_code=19, start_date="2026-03-01", end_date="2026-03-31")

        # Step 1: GET county page
        scraper.session.get.assert_called_once()
        get_url = scraper.session.get.call_args[0][0]
        assert "countylist=19" in get_url

        # Step 2 & 3: two POSTs
        assert scraper.session.post.call_count == 2

        # Step 2: POST to businesslist/index.php
        post1_url = scraper.session.post.call_args_list[0][0][0]
        assert "businesslist/index.php" in post1_url
        post1_data = scraper.session.post.call_args_list[0][1]["data"]
        assert post1_data["renewalToken"] == "abc123token"

        # Step 3: POST to businesslist/searchResults.php
        post2_url = scraper.session.post.call_args_list[1][0][0]
        assert "searchResults.php" in post2_url
        post2_data = scraper.session.post.call_args_list[1][1]["data"]
        assert post2_data["token"] == "def456searchtoken"
        assert post2_data["BmStartDateSTART_DATE"] == "2026-03-01"
        assert post2_data["BmStartDateEND_DATE"] == "2026-03-31"

    def test_http_error_raises_exception(self):
        scraper = ClerkScraper()
        session = MagicMock()
        resp = MagicMock()
        resp.raise_for_status.side_effect = Exception("503 Service Unavailable")
        session.get.return_value = resp
        scraper.session = session

        with pytest.raises(Exception, match="503"):
            scraper.fetch_county(county_code=19, start_date="2026-03-01", end_date="2026-03-31")

    def test_missing_renewal_token_raises(self):
        scraper = ClerkScraper()
        session = MagicMock()
        resp = MagicMock()
        resp.status_code = 200
        resp.text = "<html><body>No token here</body></html>"
        resp.raise_for_status = MagicMock()
        session.get.return_value = resp
        scraper.session = session

        with pytest.raises(ValueError, match="renewalToken"):
            scraper.fetch_county(county_code=19, start_date="2026-03-01", end_date="2026-03-31")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_clerk_scraper.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'utils.clerk_scraper'`

- [ ] **Step 3: Implement ClerkScraper**

Create `utils/clerk_scraper.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_clerk_scraper.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add utils/clerk_scraper.py tests/test_clerk_scraper.py
git commit -m "feat: add ClerkScraper client for TN County Clerk portal"
```

---

## Task 4: Add `parse_clerk_table()` parser with tests (TDD)

**Files:**
- Modify: `utils/parsers.py`
- Modify: `tests/test_parsers.py`

- [ ] **Step 1: Write tests for `parse_clerk_table()`**

Add to `tests/test_parsers.py`:

```python
class TestParseClerkTable:
    """Tests for parse_clerk_table()."""

    def test_parses_single_row(self):
        from utils.parsers import parse_clerk_table

        rows = [
            {
                "business_name": "TACO FIESTA",
                "product": "RESTAURANT",
                "address": "123 MAIN ST  NASHVILLE TN 37201",
                "owner": "JOHN DOE",
                "date": "2026-03-15",
            }
        ]

        records = parse_clerk_table(rows, county="Davidson")

        assert len(records) == 1
        rec = records[0]
        assert rec["business_name"] == "TACO FIESTA"
        assert rec["raw_type"] == "RESTAURANT"
        assert rec["address"] == "123 MAIN ST"
        assert rec["city"] == "NASHVILLE"
        assert rec["state"] == "TN"
        assert rec["zip_code"] == "37201"
        assert rec["county"] == "Davidson"
        assert rec["license_date"] == "2026-03-15"
        assert rec["source_type"] == "clerk_table"
        assert "tncountyclerk.com" in rec["source_url"]

    def test_parses_multiple_rows(self):
        from utils.parsers import parse_clerk_table

        rows = [
            {
                "business_name": "TACO FIESTA",
                "product": "RESTAURANT",
                "address": "123 MAIN ST  NASHVILLE TN 37201",
                "owner": "JOHN DOE",
                "date": "2026-03-15",
            },
            {
                "business_name": "GLAMOUR NAILS",
                "product": "NAIL SALON",
                "address": "456 ELM AVE  FRANKLIN TN 37064",
                "owner": "JANE SMITH",
                "date": "2026-03-20",
            },
        ]

        records = parse_clerk_table(rows, county="Davidson")
        assert len(records) == 2
        assert records[0]["business_name"] == "TACO FIESTA"
        assert records[1]["business_name"] == "GLAMOUR NAILS"

    def test_empty_rows_returns_empty_list(self):
        from utils.parsers import parse_clerk_table

        records = parse_clerk_table([], county="Davidson")
        assert records == []

    def test_skips_rows_with_no_business_name(self):
        from utils.parsers import parse_clerk_table

        rows = [
            {
                "business_name": "",
                "product": "RESTAURANT",
                "address": "123 MAIN ST  NASHVILLE TN 37201",
                "owner": "JOHN DOE",
                "date": "2026-03-15",
            }
        ]

        records = parse_clerk_table(rows, county="Davidson")
        assert records == []

    def test_address_parsing_without_zip(self):
        from utils.parsers import parse_clerk_table

        rows = [
            {
                "business_name": "BOB'S BURGERS",
                "product": "RESTAURANT",
                "address": "789 OAK DR  NASHVILLE TN",
                "owner": "BOB",
                "date": "2026-03-22",
            }
        ]

        records = parse_clerk_table(rows, county="Davidson")
        assert len(records) == 1
        assert records[0]["city"] == "NASHVILLE"
        assert records[0]["state"] == "TN"
        assert records[0]["zip_code"] is None

    def test_source_url_includes_county(self):
        from utils.parsers import parse_clerk_table

        rows = [
            {
                "business_name": "TEST BIZ",
                "product": "RETAIL",
                "address": "1 ST  FRANKLIN TN 37064",
                "owner": "X",
                "date": "2026-01-01",
            }
        ]

        records = parse_clerk_table(rows, county="Williamson")
        assert "tncountyclerk.com" in records[0]["source_url"]
        assert "Williamson" in records[0]["source_url"] or "94" in records[0]["source_url"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_parsers.py::TestParseClerkTable -v`
Expected: FAIL — `ImportError: cannot import name 'parse_clerk_table'`

- [ ] **Step 3: Implement `parse_clerk_table()` in `utils/parsers.py`**

Add this function to the end of `utils/parsers.py`, before the `parse_snippet` function:

```python
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
        rec["business_name"] = name
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
        city = city if city else None
        return street, city, zip_code

    # Fallback: try comma splitting
    street, city, zip_code_fallback = _split_address_parts(address)
    return street, city, zip_code or zip_code_fallback
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_parsers.py::TestParseClerkTable -v`
Expected: All tests PASS

- [ ] **Step 5: Run full test suite**

Run: `python3 -m pytest tests/ -x -q`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add utils/parsers.py tests/test_parsers.py
git commit -m "feat: add parse_clerk_table() parser for county clerk data"
```

---

## Task 5: Add `clerk_table` routing in transform phase

**Files:**
- Modify: `etl/transform.py`
- Modify: `config/scoring.yaml` (already done in Task 2, verify)

- [ ] **Step 1: Write a test for clerk_table routing**

Add to `tests/test_transform.py` (or `tests/test_pipeline.py` depending on where transform routing is tested):

```python
class TestClerkTableRouting:
    """Test that clerk_table source_type routes to parse_clerk_table."""

    def test_clerk_table_extract_produces_records(self, sample_scoring_config, sample_sources_config, sample_chains_config):
        from etl.transform import run_transform

        raw_extracts = [
            {
                "raw_content": "",  # Not used by clerk_table
                "source_url": "https://secure.tncountyclerk.com/businesslist/Davidson",
                "county": "Davidson",
                "source_type": "clerk_table",
                "title": "County Clerk Business List",
                "clerk_rows": [
                    {
                        "business_name": "TACO FIESTA",
                        "product": "RESTAURANT",
                        "address": "123 MAIN ST  NASHVILLE TN 37201",
                        "owner": "JOHN DOE",
                        "date": "2026-03-15",
                    }
                ],
            }
        ]

        with patch("etl.transform._load_yaml") as mock_load:
            mock_load.side_effect = [sample_scoring_config, sample_chains_config, sample_sources_config]
            records = run_transform(raw_extracts)

        assert len(records) >= 1
        taco = [r for r in records if r["business_name"] == "TACO FIESTA"]
        assert len(taco) == 1
        assert taco[0]["source_type"] == "clerk_table"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_transform.py::TestClerkTableRouting -v`
Expected: FAIL

- [ ] **Step 3: Add clerk_table routing in `etl/transform.py`**

In `etl/transform.py`, add the import at the top:

```python
from utils.parsers import parse_license_table, parse_news_article, parse_snippet, parse_clerk_table
```

Then modify the routing block (around line 405) to add a new branch:

```python
        if source_type == "license_table":
            parsed = parse_license_table(raw_content, source_url, county)
        elif source_type == "clerk_table":
            clerk_rows = extract.get("clerk_rows", [])
            parsed = parse_clerk_table(clerk_rows, county=county)
        elif source_type == "news_article":
            parsed = parse_news_article(raw_content, source_url, county)
        elif source_type == "search_snippet":
            parsed = parse_snippet(title, raw_content, source_url, county)
        else:
            logger.warning(f"Unknown source_type '{source_type}' for URL {source_url}, treating as search_snippet")
            parsed = parse_snippet(title, raw_content, source_url, county)
```

- [ ] **Step 4: Add `clerk_table` to scoring source_scores validation (if needed)**

Check if `score_lead()` in `etl/transform.py` uses source_scores from the YAML. If so, ensure `clerk_table: 20` is present in `config/scoring.yaml` (done in Task 2).

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/ -x -q`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add etl/transform.py tests/test_transform.py
git commit -m "feat: add clerk_table routing in transform phase"
```

---

## Task 6: Integrate clerk scraping into extract phase with tests (TDD)

**Files:**
- Modify: `etl/extract.py`
- Modify: `tests/test_extract.py`

- [ ] **Step 1: Write integration test for clerk extraction**

Add to `tests/test_extract.py`:

```python
class TestClerkExtraction:
    """Test that clerk counties are scraped during extract."""

    def test_clerk_counties_produce_raw_extracts(self):
        """Clerk scraping should produce RawExtract dicts with source_type=clerk_table."""
        mock_client = MagicMock()
        mock_client.search.return_value = []
        mock_client.credits_used = 0

        clerk_rows = [
            {
                "business_name": "TACO FIESTA",
                "product": "RESTAURANT",
                "address": "123 MAIN ST  NASHVILLE TN 37201",
                "owner": "JOHN DOE",
                "date": "2026-03-15",
            }
        ]

        sources_config = {
            "queries": [],
            "extractable_domains": [],
            "blocked_domains": [],
            "clerk_counties": {"Davidson": 19},
        }

        with patch("etl.extract._load_sources", return_value=sources_config), \
             patch("etl.extract.ClerkScraper") as MockScraper:

            mock_scraper_instance = MagicMock()
            mock_scraper_instance.fetch_county.return_value = clerk_rows
            MockScraper.return_value = mock_scraper_instance

            results, credits = run_extract(client=mock_client, use_db=False)

        assert len(results) == 1
        assert results[0]["source_type"] == "clerk_table"
        assert results[0]["county"] == "Davidson"
        assert results[0]["clerk_rows"] == clerk_rows

    def test_clerk_extraction_skips_on_http_error(self):
        """If clerk scraping fails for a county, log warning and continue."""
        mock_client = MagicMock()
        mock_client.search.return_value = []
        mock_client.credits_used = 0

        sources_config = {
            "queries": [],
            "extractable_domains": [],
            "blocked_domains": [],
            "clerk_counties": {"Davidson": 19},
        }

        with patch("etl.extract._load_sources", return_value=sources_config), \
             patch("etl.extract.ClerkScraper") as MockScraper:

            mock_scraper_instance = MagicMock()
            mock_scraper_instance.fetch_county.side_effect = Exception("503 Unavailable")
            MockScraper.return_value = mock_scraper_instance

            results, credits = run_extract(client=mock_client, use_db=False)

        # Should not crash, just return empty
        assert results == []

    def test_clerk_extraction_date_range_is_30_days(self):
        """Clerk scraping should use a 30-day date range ending today."""
        mock_client = MagicMock()
        mock_client.search.return_value = []
        mock_client.credits_used = 0

        sources_config = {
            "queries": [],
            "extractable_domains": [],
            "blocked_domains": [],
            "clerk_counties": {"Davidson": 19},
        }

        with patch("etl.extract._load_sources", return_value=sources_config), \
             patch("etl.extract.ClerkScraper") as MockScraper:

            mock_scraper_instance = MagicMock()
            mock_scraper_instance.fetch_county.return_value = []
            MockScraper.return_value = mock_scraper_instance

            run_extract(client=mock_client, use_db=False)

        call_kwargs = mock_scraper_instance.fetch_county.call_args[1]
        # Verify date range is approximately 30 days
        from datetime import datetime
        start = datetime.strptime(call_kwargs["start_date"], "%Y-%m-%d")
        end = datetime.strptime(call_kwargs["end_date"], "%Y-%m-%d")
        delta = (end - start).days
        assert 28 <= delta <= 31
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_extract.py::TestClerkExtraction -v`
Expected: FAIL

- [ ] **Step 3: Add clerk scraping to `etl/extract.py`**

Add these imports at the top of `etl/extract.py`:

```python
from datetime import datetime, timedelta
from utils.clerk_scraper import ClerkScraper
```

Then add a new step in `run_extract()`, after the direct_extract_urls block (step 4) and before the search query loop (step 5). Insert as new step 4b:

```python
        # ------------------------------------------------------------------
        # 4b. Scrape TN County Clerk portal for clerk_counties
        # ------------------------------------------------------------------
        clerk_counties: dict = sources.get("clerk_counties", {})
        if clerk_counties:
            logger.info(f"Scraping TN County Clerk portal for {len(clerk_counties)} counties")
            clerk = ClerkScraper()
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

            for county_name, county_code in clerk_counties.items():
                try:
                    logger.debug(f"Fetching clerk data for {county_name} (code={county_code})")
                    clerk_rows = clerk.fetch_county(
                        county_code=county_code,
                        start_date=start_date,
                        end_date=end_date,
                    )
                    if clerk_rows:
                        results.append({
                            "raw_content": "",
                            "source_url": f"https://secure.tncountyclerk.com/businesslist/{county_name}",
                            "county": county_name,
                            "source_type": "clerk_table",
                            "title": f"{county_name} County Clerk Business List",
                            "clerk_rows": clerk_rows,
                        })
                        logger.info(f"Found {len(clerk_rows)} clerk records for {county_name}")
                except Exception as exc:
                    logger.warning(f"Clerk scraping failed for {county_name}: {exc}")
                    continue

            logger.info(f"Clerk scraping complete, total extracts now: {len(results)}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_extract.py::TestClerkExtraction -v`
Expected: All tests PASS

- [ ] **Step 5: Run full test suite**

Run: `python3 -m pytest tests/ -x -q`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add etl/extract.py tests/test_extract.py
git commit -m "feat: integrate clerk scraping into extract phase"
```

---

## Task 7: End-to-end dry-run verification

**Files:**
- No files modified — this is a verification task

- [ ] **Step 1: Run the full test suite**

Run: `python3 -m pytest tests/ -v --tb=short`
Expected: All tests pass

- [ ] **Step 2: Run a dry-run pipeline to verify clerk integration**

Run: `python3 -m cli.main run --dry-run`
Expected: Output should show clerk records being fetched for Davidson, Williamson, Wilson, etc. May take 30-60 seconds due to HTTP requests. Verify:
- Clerk records appear with `source_type=clerk_table`
- Records have proper business names, addresses, raw_types
- No crash or error in the output
- Tier B/C queries still run normally after clerk scraping

- [ ] **Step 3: Spot-check scoring**

After the dry run, look at the output for clerk_table records. They should score well because:
- `raw_type` is populated (e.g., "RESTAURANT" → type_score 50)
- `source_type` is `clerk_table` → source_score 20
- Full address with city + zip → address_score 15
- Recent date → recency_score up to 15

A restaurant from the clerk portal should score ~90-100, much higher than the 23-max snippet scores from the current approach.

- [ ] **Step 4: Commit any test fixes needed**

If any tests failed due to the config changes (e.g., Tier A query count assertions), fix and commit:

```bash
git add -u
git commit -m "test: fix test assertions for clerk scraper integration"
```

---

## Task 8: Update `sources.yaml` validation and cleanup

**Files:**
- Modify: `etl/extract.py` (validation function)

- [ ] **Step 1: Update `_validate_sources()` to accept `clerk_counties` as optional**

The existing validation in `etl/extract.py` only requires `queries`, `extractable_domains`, and `blocked_domains`. Since `clerk_counties` is optional (the scraper skips gracefully if empty), no validation changes are strictly needed. However, add a type check if present:

In `_validate_sources()`, add after the existing validation:

```python
    # Optional key type checks
    if "clerk_counties" in sources and not isinstance(sources["clerk_counties"], dict):
        errors.append(
            f"'clerk_counties' should be dict, got {type(sources['clerk_counties']).__name__}"
        )
```

- [ ] **Step 2: Run tests**

Run: `python3 -m pytest tests/ -x -q`
Expected: All tests pass

- [ ] **Step 3: Commit**

```bash
git add etl/extract.py
git commit -m "feat: add optional clerk_counties validation in extract"
```

---

## Comparison: Clerk Scraper vs. Current Approach

| Dimension | Current (Tier A via Tavily) | Clerk Scraper |
|-----------|---------------------------|---------------|
| **Data source** | `*countysource.com` blog articles | County clerk (authoritative) |
| **Data quality** | Depends on blog publishing schedule | Direct from issuing authority |
| **Fields** | Business Name, Type, Address, Date | Business Name, Product, Address, Owner, Date |
| **raw_type** | From markdown table (if parsed) | Always populated ("RESTAURANT", "NAIL SALON", etc.) |
| **Scoring potential** | Up to 100 (license_table) | Up to 100 (clerk_table) |
| **Tavily credits** | ~7 search + ~7 extract = ~14 credits/run | 0 credits (direct HTTP) |
| **Coverage** | 7 counties with countysource.com | 8 counties (adds Montgomery) |
| **Freshness** | Blog may lag by days/weeks | Real-time (query any date range) |
| **Reliability** | Depends on blog being indexed by Tavily | Direct HTTP to government portal |
| **Failure mode** | Tavily returns no results → 0 leads | HTTP error → logged warning, continues |

**Recommendation:** The clerk scraper is strictly superior for counties that support it. It provides more data, more reliably, at zero API cost, with better classification (the "Product" field maps directly to raw_type). The Tier A `*countysource.com` queries should be removed for these counties. Tier B/C Tavily queries should be kept since they discover news articles and other non-license-table leads that the clerk portal doesn't cover.
