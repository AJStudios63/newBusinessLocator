"""Tests for the TN County Clerk business list scraper."""

from unittest.mock import MagicMock, patch
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


def _make_mock_session(results_html=RESULTS_HTML):
    """Create a mock requests.Session that returns the 3-step HTML."""
    session = MagicMock()

    resp1 = MagicMock()
    resp1.status_code = 200
    resp1.text = COUNTY_PAGE_HTML
    resp1.raise_for_status = MagicMock()

    resp2 = MagicMock()
    resp2.status_code = 200
    resp2.text = SEARCH_FORM_HTML
    resp2.raise_for_status = MagicMock()

    resp3 = MagicMock()
    resp3.status_code = 200
    resp3.text = results_html
    resp3.raise_for_status = MagicMock()

    session.get.return_value = resp1
    session.post.side_effect = [resp2, resp3]
    session.headers = {}

    return session


class TestClerkScraperInit:
    """Test ClerkScraper initialization."""

    def test_has_headers(self):
        scraper = ClerkScraper()
        assert scraper._headers is not None
        assert "User-Agent" in scraper._headers

    def test_base_url(self):
        scraper = ClerkScraper()
        assert scraper.base_url == "https://secure.tncountyclerk.com"


class TestClerkScraperFetchCounty:
    """Test the 3-step session flow and result parsing."""

    @patch("utils.clerk_scraper.requests.Session")
    def test_fetch_returns_list_of_dicts(self, MockSession):
        MockSession.return_value = _make_mock_session()
        scraper = ClerkScraper()

        results = scraper.fetch_county(county_code=19, start_date="2026-03-01", end_date="2026-03-31")

        assert isinstance(results, list)
        assert len(results) == 3

    @patch("utils.clerk_scraper.requests.Session")
    def test_result_dict_has_required_fields(self, MockSession):
        MockSession.return_value = _make_mock_session()
        scraper = ClerkScraper()

        results = scraper.fetch_county(county_code=19, start_date="2026-03-01", end_date="2026-03-31")
        row = results[0]

        assert row["business_name"] == "TACO FIESTA"
        assert row["product"] == "RESTAURANT"
        assert row["address"] == "123 MAIN ST  NASHVILLE TN 37201"
        assert row["owner"] == "JOHN DOE"
        assert row["date"] == "2026-03-15"

    @patch("utils.clerk_scraper.requests.Session")
    def test_parses_all_rows(self, MockSession):
        MockSession.return_value = _make_mock_session()
        scraper = ClerkScraper()

        results = scraper.fetch_county(county_code=19, start_date="2026-03-01", end_date="2026-03-31")

        names = [r["business_name"] for r in results]
        assert names == ["TACO FIESTA", "GLAMOUR NAILS", "QUICK FIX PLUMBING"]

    @patch("utils.clerk_scraper.requests.Session")
    def test_empty_results_returns_empty_list(self, MockSession):
        MockSession.return_value = _make_mock_session(results_html=EMPTY_RESULTS_HTML)
        scraper = ClerkScraper()

        results = scraper.fetch_county(county_code=19, start_date="2026-03-01", end_date="2026-03-31")

        assert results == []

    @patch("utils.clerk_scraper.requests.Session")
    def test_session_flow_calls_correct_urls(self, MockSession):
        mock_session = _make_mock_session()
        MockSession.return_value = mock_session
        scraper = ClerkScraper()

        scraper.fetch_county(county_code=19, start_date="2026-03-01", end_date="2026-03-31")

        # Step 1: GET county page
        mock_session.get.assert_called_once()
        get_url = mock_session.get.call_args[0][0]
        assert "countylist=19" in get_url

        # Step 2 & 3: two POSTs
        assert mock_session.post.call_count == 2

        # Step 2: POST to businesslist/index.php
        post1_url = mock_session.post.call_args_list[0][0][0]
        assert "businesslist/index.php" in post1_url
        post1_data = mock_session.post.call_args_list[0][1]["data"]
        assert post1_data["renewalToken"] == "abc123token"

        # Step 3: POST to businesslist/searchResults.php
        post2_url = mock_session.post.call_args_list[1][0][0]
        assert "searchResults.php" in post2_url
        post2_data = mock_session.post.call_args_list[1][1]["data"]
        assert post2_data["token"] == "def456searchtoken"
        assert post2_data["BmStartDateSTART_DATE"] == "2026-03-01"
        assert post2_data["BmStartDateEND_DATE"] == "2026-03-31"

    @patch("utils.clerk_scraper.requests.Session")
    def test_http_error_raises_exception(self, MockSession):
        mock_session = MagicMock()
        mock_session.headers = {}
        resp = MagicMock()
        resp.raise_for_status.side_effect = Exception("503 Service Unavailable")
        mock_session.get.return_value = resp
        MockSession.return_value = mock_session
        scraper = ClerkScraper()

        with pytest.raises(Exception, match="503"):
            scraper.fetch_county(county_code=19, start_date="2026-03-01", end_date="2026-03-31")

    @patch("utils.clerk_scraper.requests.Session")
    def test_missing_renewal_token_raises(self, MockSession):
        mock_session = MagicMock()
        mock_session.headers = {}
        resp = MagicMock()
        resp.status_code = 200
        resp.text = "<html><body>No token here</body></html>"
        resp.raise_for_status = MagicMock()
        mock_session.get.return_value = resp
        MockSession.return_value = mock_session
        scraper = ClerkScraper()

        with pytest.raises(ValueError, match="renewalToken"):
            scraper.fetch_county(county_code=19, start_date="2026-03-01", end_date="2026-03-31")
