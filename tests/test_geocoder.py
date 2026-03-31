"""
Tests for utils/geocoder.py

Uses unittest.mock to mock HTTP responses - no real API calls.
"""

import json
import unittest
import urllib.error
from unittest.mock import MagicMock, Mock, patch

from utils.geocoder import _build_query_string, geocode_batch, geocode_lead


class TestBuildQueryString(unittest.TestCase):
    """Test _build_query_string helper function."""

    def test_full_address(self):
        """Full address with all fields."""
        record = {
            "address": "123 Main St",
            "city": "Nashville",
            "state": "TN",
            "zip_code": "37201"
        }
        result = _build_query_string(record)
        self.assertEqual(result, "123 Main St, Nashville, TN, 37201")

    def test_without_zip(self):
        """Address without zip code."""
        record = {
            "address": "123 Main St",
            "city": "Nashville",
            "state": "TN"
        }
        result = _build_query_string(record)
        self.assertEqual(result, "123 Main St, Nashville, TN")

    def test_city_only(self):
        """City and state only (no address or zip)."""
        record = {
            "city": "Nashville",
            "state": "TN"
        }
        result = _build_query_string(record)
        self.assertEqual(result, "Nashville, TN")

    def test_city_with_default_state(self):
        """City without explicit state defaults to TN."""
        record = {
            "city": "Nashville"
        }
        result = _build_query_string(record)
        self.assertEqual(result, "Nashville, TN")

    def test_no_city(self):
        """No city returns None."""
        record = {
            "address": "123 Main St"
        }
        result = _build_query_string(record)
        self.assertIsNone(result)

    def test_empty_record(self):
        """Empty record returns None."""
        record = {}
        result = _build_query_string(record)
        self.assertIsNone(result)

    def test_whitespace_handling(self):
        """Strips whitespace from fields."""
        record = {
            "address": "  123 Main St  ",
            "city": "  Nashville  ",
            "state": "  TN  ",
            "zip_code": "  37201  "
        }
        result = _build_query_string(record)
        self.assertEqual(result, "123 Main St, Nashville, TN, 37201")


class TestGeocodeLead(unittest.TestCase):
    """Test geocode_lead function."""

    @patch("utils.geocoder.urllib.request.urlopen")
    def test_successful_geocode(self, mock_urlopen):
        """Successful geocoding returns lat/lon tuple."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.read.return_value = json.dumps([
            {"lat": "36.1627", "lon": "-86.7816"}
        ]).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        record = {"city": "Nashville", "state": "TN"}
        lat, lon = geocode_lead(record)

        self.assertEqual(lat, 36.1627)
        self.assertEqual(lon, -86.7816)

    @patch("utils.geocoder.urllib.request.urlopen")
    def test_empty_response(self, mock_urlopen):
        """Empty API response returns (None, None)."""
        # Mock empty response
        mock_response = Mock()
        mock_response.read.return_value = json.dumps([]).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        record = {"city": "NoSuchCity", "state": "TN"}
        lat, lon = geocode_lead(record)

        self.assertIsNone(lat)
        self.assertIsNone(lon)

    @patch("utils.geocoder.urllib.request.urlopen")
    def test_network_error(self, mock_urlopen):
        """Network error returns (None, None) without raising exception."""
        # Mock URLError
        mock_urlopen.side_effect = urllib.error.URLError("Network error")

        record = {"city": "Nashville", "state": "TN"}
        lat, lon = geocode_lead(record)

        self.assertIsNone(lat)
        self.assertIsNone(lon)

    @patch("utils.geocoder.urllib.request.urlopen")
    def test_http_error(self, mock_urlopen):
        """HTTP error returns (None, None) without raising exception."""
        # Mock HTTPError
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "http://test.com", 500, "Server Error", {}, None
        )

        record = {"city": "Nashville", "state": "TN"}
        lat, lon = geocode_lead(record)

        self.assertIsNone(lat)
        self.assertIsNone(lon)

    def test_no_city(self):
        """Record without city returns (None, None)."""
        record = {"address": "123 Main St"}
        lat, lon = geocode_lead(record)

        self.assertIsNone(lat)
        self.assertIsNone(lon)

    @patch("utils.geocoder.urllib.request.urlopen")
    def test_malformed_json(self, mock_urlopen):
        """Malformed JSON response returns (None, None)."""
        # Mock invalid JSON
        mock_response = Mock()
        mock_response.read.return_value = b"invalid json"
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        record = {"city": "Nashville", "state": "TN"}
        lat, lon = geocode_lead(record)

        self.assertIsNone(lat)
        self.assertIsNone(lon)

    @patch("utils.geocoder.urllib.request.urlopen")
    def test_missing_lat_lon_keys(self, mock_urlopen):
        """Response missing lat/lon keys returns (None, None)."""
        # Mock response without lat/lon
        mock_response = Mock()
        mock_response.read.return_value = json.dumps([
            {"name": "Nashville"}
        ]).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        record = {"city": "Nashville", "state": "TN"}
        lat, lon = geocode_lead(record)

        self.assertIsNone(lat)
        self.assertIsNone(lon)


class TestGeocodeBatch(unittest.TestCase):
    """Test geocode_batch function."""

    @patch("utils.geocoder.geocode_lead")
    def test_skips_records_with_existing_coords(self, mock_geocode):
        """Records with existing lat/lng are not geocoded."""
        records = [
            {"id": 1, "city": "Nashville", "latitude": 36.1, "longitude": -86.7},
            {"id": 2, "city": "Memphis", "latitude": 35.1, "longitude": -90.0}
        ]

        result = geocode_batch(records)

        # No API calls should be made
        mock_geocode.assert_not_called()
        self.assertEqual(len(result), 2)

    @patch("utils.geocoder.geocode_lead")
    @patch("utils.geocoder.time.sleep")
    def test_geocodes_records_without_coords(self, mock_sleep, mock_geocode):
        """Records without coords are geocoded."""
        # Mock geocode responses
        mock_geocode.side_effect = [
            (36.1627, -86.7816),  # Nashville
            (35.1495, -90.0490)   # Memphis
        ]

        records = [
            {"id": 1, "city": "Nashville", "latitude": None, "longitude": None},
            {"id": 2, "city": "Memphis", "latitude": None, "longitude": None}
        ]

        result = geocode_batch(records)

        # Should make 2 API calls
        self.assertEqual(mock_geocode.call_count, 2)

        # Records should be updated
        self.assertEqual(result[0]["latitude"], 36.1627)
        self.assertEqual(result[0]["longitude"], -86.7816)
        self.assertEqual(result[1]["latitude"], 35.1495)
        self.assertEqual(result[1]["longitude"], -90.0490)

    @patch("utils.geocoder.geocode_lead")
    @patch("utils.geocoder.time.sleep")
    def test_cache_prevents_duplicate_api_calls(self, mock_sleep, mock_geocode):
        """Same query uses cache, doesn't make duplicate API calls."""
        # Mock single geocode response
        mock_geocode.return_value = (36.1627, -86.7816)

        records = [
            {"id": 1, "city": "Nashville", "state": "TN", "latitude": None, "longitude": None},
            {"id": 2, "city": "Nashville", "state": "TN", "latitude": None, "longitude": None}
        ]

        result = geocode_batch(records)

        # Should only make 1 API call (second is cache hit)
        self.assertEqual(mock_geocode.call_count, 1)

        # Both records should have same coords
        self.assertEqual(result[0]["latitude"], 36.1627)
        self.assertEqual(result[0]["longitude"], -86.7816)
        self.assertEqual(result[1]["latitude"], 36.1627)
        self.assertEqual(result[1]["longitude"], -86.7816)

    @patch("utils.geocoder.geocode_lead")
    @patch("utils.geocoder.time.sleep")
    def test_mutates_records_in_place(self, mock_sleep, mock_geocode):
        """Records are mutated in-place (not copied)."""
        mock_geocode.return_value = (36.1627, -86.7816)

        original_records = [
            {"id": 1, "city": "Nashville", "latitude": None, "longitude": None}
        ]

        result = geocode_batch(original_records)

        # Should be the same list object
        self.assertIs(result, original_records)

        # Original list should be modified
        self.assertEqual(original_records[0]["latitude"], 36.1627)
        self.assertEqual(original_records[0]["longitude"], -86.7816)

    @patch("utils.geocoder.geocode_lead")
    @patch("utils.geocoder.time.sleep")
    def test_progress_callback(self, mock_sleep, mock_geocode):
        """Progress callback is called every 10 records."""
        mock_geocode.return_value = (36.1, -86.7)

        # Create 25 records
        records = [
            {"id": i, "city": f"City{i}", "latitude": None, "longitude": None}
            for i in range(25)
        ]

        callback = MagicMock()
        geocode_batch(records, progress_callback=callback)

        # Should be called at idx 10 and 20 (not 25, since 25 % 10 != 0)
        self.assertEqual(callback.call_count, 2)
        callback.assert_any_call(10, 25)
        callback.assert_any_call(20, 25)

    @patch("utils.geocoder.geocode_lead")
    @patch("utils.geocoder.time.sleep")
    def test_handles_failed_geocodes(self, mock_sleep, mock_geocode):
        """Failed geocodes set None values."""
        # Mock failure
        mock_geocode.return_value = (None, None)

        records = [
            {"id": 1, "city": "NoSuchCity", "latitude": None, "longitude": None}
        ]

        result = geocode_batch(records)

        # Should still update record (with None values)
        self.assertIsNone(result[0]["latitude"])
        self.assertIsNone(result[0]["longitude"])

    @patch("utils.geocoder.geocode_lead")
    @patch("utils.geocoder.time.sleep")
    def test_mixed_records(self, mock_sleep, mock_geocode):
        """Mix of records with/without coords works correctly."""
        mock_geocode.return_value = (36.1627, -86.7816)

        records = [
            {"id": 1, "city": "Nashville", "latitude": 36.0, "longitude": -86.0},  # already has coords
            {"id": 2, "city": "Memphis", "latitude": None, "longitude": None},     # needs geocoding
            {"id": 3, "city": "Knoxville", "latitude": 35.0, "longitude": None},   # partial coords
        ]

        result = geocode_batch(records)

        # Should geocode records 2 and 3 (not 1)
        self.assertEqual(mock_geocode.call_count, 2)

        # Record 1 unchanged
        self.assertEqual(result[0]["latitude"], 36.0)
        self.assertEqual(result[0]["longitude"], -86.0)

        # Records 2 and 3 updated
        self.assertEqual(result[1]["latitude"], 36.1627)
        self.assertEqual(result[1]["longitude"], -86.7816)
        self.assertEqual(result[2]["latitude"], 36.1627)
        self.assertEqual(result[2]["longitude"], -86.7816)


if __name__ == "__main__":
    unittest.main()
