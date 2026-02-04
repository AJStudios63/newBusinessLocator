"""
Tests for utils/dedup.py

Tests the deduplication utilities:
- normalize_name: normalizes business names for fingerprinting
- normalize_city: normalizes city names
- generate_fingerprint: generates a unique fingerprint for deduplication
"""

import pytest

from utils.dedup import normalize_name, normalize_city, generate_fingerprint


# ---------------------------------------------------------------------------
# normalize_name Tests
# ---------------------------------------------------------------------------


class TestNormalizeName:
    """Tests for the normalize_name function."""

    def test_lowercases_name(self):
        """Converts name to lowercase."""
        assert "test business" in normalize_name("Test Business")

    def test_strips_llc_suffix(self):
        """Strips LLC suffix."""
        assert normalize_name("Test Business LLC") == "test business"
        assert normalize_name("Test Business L.L.C.") == "test business"

    def test_strips_inc_suffix(self):
        """Strips Inc suffix."""
        assert normalize_name("Test Business Inc") == "test business"
        assert normalize_name("Test Business Inc.") == "test business"

    def test_strips_corp_suffix(self):
        """Strips Corp suffix."""
        assert normalize_name("Test Business Corp") == "test business"
        assert normalize_name("Test Business Corp.") == "test business"

    def test_strips_ltd_suffix(self):
        """Strips Ltd suffix."""
        assert normalize_name("Test Business Ltd") == "test business"
        assert normalize_name("Test Business Ltd.") == "test business"

    def test_strips_co_suffix(self):
        """Strips Co suffix."""
        assert normalize_name("Test Business Co") == "test business"
        assert normalize_name("Test Business Co.") == "test business"

    def test_removes_punctuation_except_hyphens(self):
        """Removes punctuation except hyphens."""
        assert normalize_name("Joe's Cafe!") == "joes cafe"
        assert normalize_name("Test & Verify") == "test verify"
        assert normalize_name("Test-Hyphen") == "test-hyphen"

    def test_removes_common_words(self):
        """Removes common words like 'the', 'and', '&'."""
        assert normalize_name("The Coffee Shop") == "coffee shop"
        assert normalize_name("Bread and Butter") == "bread butter"

    def test_collapses_whitespace(self):
        """Collapses multiple spaces into one."""
        assert normalize_name("Test    Business") == "test business"
        assert normalize_name("  Test Business  ") == "test business"

    def test_empty_string(self):
        """Returns empty string for empty input."""
        assert normalize_name("") == ""

    def test_none_input(self):
        """Returns empty string for None input."""
        assert normalize_name(None) == ""

    def test_preserves_hyphens(self):
        """Preserves hyphens in business names."""
        assert normalize_name("Chick-fil-A") == "chick-fil-a"
        assert normalize_name("In-N-Out") == "in-n-out"


# ---------------------------------------------------------------------------
# normalize_city Tests
# ---------------------------------------------------------------------------


class TestNormalizeCity:
    """Tests for the normalize_city function."""

    def test_lowercases_city(self):
        """Converts city to lowercase."""
        assert normalize_city("Nashville") == "nashville"

    def test_strips_whitespace(self):
        """Strips leading/trailing whitespace."""
        assert normalize_city("  Nashville  ") == "nashville"

    def test_empty_string(self):
        """Returns empty string for empty input."""
        assert normalize_city("") == ""

    def test_none_input(self):
        """Returns empty string for None input."""
        assert normalize_city(None) == ""


# ---------------------------------------------------------------------------
# generate_fingerprint Tests
# ---------------------------------------------------------------------------


class TestGenerateFingerprint:
    """Tests for the generate_fingerprint function."""

    def test_generates_fingerprint(self):
        """Generates a fingerprint from name and city."""
        fp = generate_fingerprint("Test Business", "Nashville")

        assert isinstance(fp, str)
        assert len(fp) == 32  # SHA-256 truncated to 32 hex chars

    def test_deterministic(self):
        """Same inputs produce same fingerprint."""
        fp1 = generate_fingerprint("Test Business", "Nashville")
        fp2 = generate_fingerprint("Test Business", "Nashville")

        assert fp1 == fp2

    def test_different_inputs_different_fingerprints(self):
        """Different inputs produce different fingerprints."""
        fp1 = generate_fingerprint("Business A", "Nashville")
        fp2 = generate_fingerprint("Business B", "Nashville")
        fp3 = generate_fingerprint("Business A", "Franklin")

        assert fp1 != fp2
        assert fp1 != fp3
        assert fp2 != fp3

    def test_normalizes_name_before_hashing(self):
        """Normalizes name before generating fingerprint."""
        fp1 = generate_fingerprint("Test Business LLC", "Nashville")
        fp2 = generate_fingerprint("test business", "nashville")

        assert fp1 == fp2

    def test_normalizes_city_before_hashing(self):
        """Normalizes city before generating fingerprint."""
        fp1 = generate_fingerprint("Test Business", "NASHVILLE")
        fp2 = generate_fingerprint("Test Business", "nashville")

        assert fp1 == fp2

    def test_handles_none_name(self):
        """Handles None name by using empty string."""
        fp = generate_fingerprint(None, "Nashville")

        assert isinstance(fp, str)
        assert len(fp) == 32

    def test_handles_none_city(self):
        """Handles None city by using empty string."""
        fp = generate_fingerprint("Test Business", None)

        assert isinstance(fp, str)
        assert len(fp) == 32

    def test_handles_both_none(self):
        """Handles both name and city as None."""
        fp = generate_fingerprint(None, None)

        assert isinstance(fp, str)
        assert len(fp) == 32

    def test_case_insensitive(self):
        """Fingerprint is case-insensitive."""
        fp1 = generate_fingerprint("THE COFFEE SHOP LLC", "NASHVILLE")
        fp2 = generate_fingerprint("the coffee shop", "nashville")

        assert fp1 == fp2
