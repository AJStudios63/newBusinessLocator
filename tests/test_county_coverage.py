"""Validate sources.yaml has complete county coverage."""

import yaml
import pytest
from config.settings import SOURCES_YAML


def _load_sources():
    with open(SOURCES_YAML, "r") as fh:
        return yaml.safe_load(fh)


COUNTIES_WITH_CLERK_PORTAL = [
    "Davidson", "Williamson", "Wilson", "Cheatham",
    "Robertson", "Maury", "Dickson", "Montgomery",
]


class TestClerkCounties:
    def test_all_clerk_portal_counties_configured(self):
        sources = _load_sources()
        clerk_counties = sources.get("clerk_counties", {})
        for county in COUNTIES_WITH_CLERK_PORTAL:
            assert county in clerk_counties, (
                f"{county} has clerk portal access but is not in clerk_counties config"
            )

    def test_clerk_counties_have_valid_codes(self):
        sources = _load_sources()
        clerk_counties = sources.get("clerk_counties", {})
        for county, code in clerk_counties.items():
            assert isinstance(code, int), f"{county} clerk code should be int, got {type(code)}"
            assert 1 <= code <= 95, f"{county} clerk code {code} out of range 1-95"


class TestTierBQueries:
    def test_all_counties_have_tier_b_query(self):
        sources = _load_sources()
        tier_b_counties = {
            q["county"] for q in sources["queries"]
            if q.get("tier") == "B" and q.get("county")
        }
        for county in sources["counties"]:
            assert county in tier_b_counties, (
                f"{county} is in counties map but has no Tier B search query"
            )


class TestExtractableDomains:
    def test_license_site_domains_extractable(self):
        sources = _load_sources()
        domains = sources["extractable_domains"]
        expected_domains = [
            "davidsoncountysource.com", "williamsonsource.com",
            "wilsoncountysource.com", "sumnercountysource.com",
            "robertsoncountysource.com", "maurycountysource.com",
            "dicksoncountysource.com", "cheathamcountysource.com",
            "rutherfordsource.com", "boropulse.com",
        ]
        for domain in expected_domains:
            assert domain in domains, f"{domain} not in extractable_domains"


class TestCityMap:
    def test_davidson_cities(self):
        sources = _load_sources()
        davidson = sources["counties"]["Davidson"]
        for city in ["Nashville", "Antioch", "Madison", "Hermitage", "Goodlettsville"]:
            assert city in davidson, f"{city} missing from Davidson cities"

    def test_rutherford_cities(self):
        sources = _load_sources()
        rutherford = sources["counties"]["Rutherford"]
        for city in ["Murfreesboro", "Smyrna", "La Vergne", "Eagleville"]:
            assert city in rutherford, f"{city} missing from Rutherford cities"

    def test_sumner_cities(self):
        sources = _load_sources()
        sumner = sources["counties"]["Sumner"]
        for city in ["Gallatin", "Hendersonville", "Portland", "Westmoreland", "Millersville", "White House"]:
            assert city in sumner, f"{city} missing from Sumner cities"

    def test_wilson_cities(self):
        sources = _load_sources()
        wilson = sources["counties"]["Wilson"]
        for city in ["Lebanon", "Mount Juliet", "Watertown"]:
            assert city in wilson, f"{city} missing from Wilson cities"

    def test_williamson_cities(self):
        sources = _load_sources()
        williamson = sources["counties"]["Williamson"]
        for city in ["Franklin", "Brentwood", "Nolensville", "Spring Hill", "Fairview", "Thompson's Station"]:
            assert city in williamson, f"{city} missing from Williamson cities"

    def test_montgomery_cities(self):
        sources = _load_sources()
        montgomery = sources["counties"]["Montgomery"]
        for city in ["Clarksville"]:
            assert city in montgomery, f"{city} missing from Montgomery cities"
