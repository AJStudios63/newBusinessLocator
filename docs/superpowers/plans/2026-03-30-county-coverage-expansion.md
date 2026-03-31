# County Coverage Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Maximize lead quality and volume for all 12 Middle Tennessee counties in the pipeline by adding missing license table sources, improving search queries, and adding alternative data sources for counties without `*countysource.com` sites.

**Architecture:** The ETL pipeline already supports three source tiers (license tables, news articles, search snippets). Counties with `*countysource.com` sites produce high-quality license table leads (score 70-90). Counties without them rely on low-quality news/snippet leads (score 23-35). This plan adds missing Tier A sources where they exist, adds `rutherfordsource.com` and `boropulse.com` as news sources, improves Tier B queries for underperforming counties, and adds direct extract URLs for recently published license table pages we haven't captured yet.

**Tech Stack:** Python 3.12, YAML config, SQLite, Tavily Search/Extract API, pytest

---

## Current County Assessment

| County | Leads | Primary Source | Tier A (License) | Quality |
|--------|------:|----------------|-------------------|---------|
| Davidson | 3,145 | `davidsoncountysource.com` | YES | Excellent |
| Wilson | 675 | `wilsoncountysource.com` | YES | Excellent |
| Williamson | 427 | `williamsonsource.com` | YES | Excellent |
| Cheatham | 371 | `cheathamcountysource.com` | YES | Good |
| Sumner | 109 | `sumnercountysource.com` | Tier A query exists but site has NO license tables | Poor |
| Maury | 49 | `maurycountysource.com` | YES (direct URLs only) | Good |
| Robertson | 16 | `robertsoncountysource.com` | YES (direct URLs only) | OK |
| Dickson | 11 | `dicksoncountysource.com` | YES (direct URLs only) | OK |
| Montgomery | 8 | News/snippets only | NO - no `*countysource.com` site exists | Very Poor |
| Coffee | 8 | News/snippets only | NO - no `*countysource.com` site exists | Very Poor |
| Rutherford | 7 | News/snippets only | NO - `rutherfordsource.com` exists but has no license tables | Very Poor |
| Franklin | 11 | News/snippets only | NO - no `*countysource.com` site exists | Very Poor |
| Putnam | 6 | Snippets only | NO - no `*countysource.com` site exists | Very Poor |

### Key Findings

1. **`sumnercountysource.com`** has a Tier A search query but the site publishes NO license table pages. All 109 Sumner leads come from news articles (99) and snippets (10) picked up by the Tier A `site:` query returning general news instead of license tables.

2. **`rutherfordsource.com`** exists but publishes no license tables. It's a news site. It IS in the codebase as a seen URL source but NOT in `extractable_domains`.

3. **`boropulse.com`** (Murfreesboro) is already returning useful Rutherford County news but is NOT in `extractable_domains`, so leads come as low-quality snippets.

4. **Counties without any `*countysource.com` site:** Montgomery, Coffee, Franklin, Putnam. These need alternative sources (local government sites, chambers of commerce, local news).

5. **Robertson, Dickson, Maury** have working `*countysource.com` sites but only have direct extract URLs (no Tier A search query), limiting discovery to manually-configured URLs.

6. **Sumner's Tier A query is wasted** - `site:sumnercountysource.com new business licenses` returns general news, not license data. Should be removed/replaced.

---

## File Structure

**Files to modify:**
- `config/sources.yaml` - Add missing Tier A queries, fix Sumner, add extractable domains, add direct URLs
- `etl/extract.py` - No changes needed (infrastructure already supports all source types)
- `etl/transform.py` - No changes needed (parsers handle all formats)
- `utils/parsers.py` - No changes needed (flexible table parser works for all county source sites)

**Files to create:**
- `scripts/discover_county_urls.py` - One-time discovery script to find recent license table URLs from county source sites
- `tests/test_county_coverage.py` - Validation tests for sources.yaml completeness

---

### Task 1: Add Tier A Search Queries for Counties with Working License Table Sites

Three counties (Robertson, Dickson, Maury) have working `*countysource.com` sites with license table pages but are missing Tier A search queries. This means the pipeline only finds their pages via hardcoded `direct_extract_urls` instead of dynamically discovering new pages.

**Files:**
- Modify: `config/sources.yaml:103-118`
- Test: `tests/test_county_coverage.py` (create)

- [ ] **Step 1: Write validation test for Tier A query coverage**

Create `tests/test_county_coverage.py`:

```python
"""Validate sources.yaml has complete county coverage."""

import yaml
import pytest
from config.settings import SOURCES_YAML


def _load_sources():
    with open(SOURCES_YAML, "r") as fh:
        return yaml.safe_load(fh)


# Counties that have *countysource.com license table sites
COUNTIES_WITH_LICENSE_SITES = [
    "Davidson", "Williamson", "Wilson", "Cheatham",
    "Robertson", "Maury", "Dickson",
]


class TestTierAQueries:
    """Every county with a *countysource.com site should have a Tier A query."""

    def test_all_license_site_counties_have_tier_a_query(self):
        sources = _load_sources()
        tier_a_counties = {
            q["county"]
            for q in sources["queries"]
            if q.get("tier") == "A"
        }
        for county in COUNTIES_WITH_LICENSE_SITES:
            assert county in tier_a_counties, (
                f"{county} has a *countysource.com site but no Tier A search query"
            )


class TestTierBQueries:
    """Every county in the counties map should have at least one Tier B query."""

    def test_all_counties_have_tier_b_query(self):
        sources = _load_sources()
        tier_b_counties = {
            q["county"]
            for q in sources["queries"]
            if q.get("tier") == "B" and q.get("county")
        }
        for county in sources["counties"]:
            assert county in tier_b_counties, (
                f"{county} is in counties map but has no Tier B search query"
            )


class TestExtractableDomains:
    """County source sites should be in extractable_domains."""

    def test_license_site_domains_extractable(self):
        sources = _load_sources()
        domains = sources["extractable_domains"]
        expected_domains = [
            "davidsoncountysource.com",
            "williamsonsource.com",
            "wilsoncountysource.com",
            "sumnercountysource.com",
            "robertsoncountysource.com",
            "maurycountysource.com",
            "dicksoncountysource.com",
            "cheathamcountysource.com",
            "rutherfordsource.com",
            "boropulse.com",
        ]
        for domain in expected_domains:
            assert domain in domains, f"{domain} not in extractable_domains"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_county_coverage.py -v`

Expected: FAIL on `test_all_license_site_counties_have_tier_a_query` (Robertson, Maury, Dickson missing), FAIL on `test_license_site_domains_extractable` (rutherfordsource.com, boropulse.com missing).

- [ ] **Step 3: Add missing Tier A queries to sources.yaml**

In `config/sources.yaml`, add after the existing Tier A queries (after the Cheatham entry around line 118):

```yaml
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

- [ ] **Step 4: Run test to verify Tier A coverage passes**

Run: `pytest tests/test_county_coverage.py::TestTierAQueries -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add config/sources.yaml tests/test_county_coverage.py
git commit -m "feat: add Tier A search queries for Robertson, Maury, Dickson counties"
```

---

### Task 2: Fix Sumner County - Remove Broken Tier A, Improve Tier B

Sumner County's `sumnercountysource.com` does NOT publish license table pages. The current Tier A query returns general news articles that get misclassified. Remove the broken Tier A query and improve the Tier B query to target better local news sources.

**Files:**
- Modify: `config/sources.yaml:113-115` (remove Sumner Tier A)
- Modify: `config/sources.yaml:133-135` (improve Sumner Tier B)
- Modify: `tests/test_county_coverage.py`

- [ ] **Step 1: Update test to exclude Sumner from Tier A requirement**

In `tests/test_county_coverage.py`, update the `COUNTIES_WITH_LICENSE_SITES` list:

```python
# Counties that have *countysource.com license table sites
# Note: Sumner's sumnercountysource.com does NOT publish license tables
COUNTIES_WITH_LICENSE_SITES = [
    "Davidson", "Williamson", "Wilson", "Cheatham",
    "Robertson", "Maury", "Dickson",
]
```

(This is already correct from Task 1 — Sumner is not in the list. No change needed.)

- [ ] **Step 2: Remove Sumner Tier A query from sources.yaml**

Remove these lines from `config/sources.yaml`:

```yaml
  - query: "site:sumnercountysource.com new business licenses"
    county: Sumner
    tier: A
```

- [ ] **Step 3: Improve Sumner Tier B query**

Replace the existing Sumner Tier B query:

```yaml
  - query: "new business opening Gallatin Hendersonville Sumner County 2026"
    county: Sumner
    tier: B
```

With two more targeted queries:

```yaml
  - query: "new business opening Gallatin Hendersonville Sumner County Tennessee 2026"
    county: Sumner
    tier: B
  - query: "new restaurant store salon opening Gallatin Hendersonville Portland Tennessee 2026"
    county: Sumner
    tier: B
```

- [ ] **Step 4: Run all tests**

Run: `pytest tests/test_county_coverage.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add config/sources.yaml tests/test_county_coverage.py
git commit -m "fix: remove broken Sumner Tier A query, improve Tier B coverage"
```

---

### Task 3: Add Rutherford County News Sources

Rutherford County (Murfreesboro, Smyrna, La Vergne) has only 7 leads despite being the 5th largest county in Tennessee. `rutherfordsource.com` exists as a news site and `boropulse.com` covers Murfreesboro. Add both as extractable domains and improve search queries.

**Files:**
- Modify: `config/sources.yaml` (extractable_domains, queries)

- [ ] **Step 1: Add Rutherford news domains to extractable_domains**

In `config/sources.yaml`, add to `extractable_domains` section under `# Local news`:

```yaml
  - rutherfordsource.com
  - boropulse.com
```

- [ ] **Step 2: Add Rutherford-specific search queries**

Replace the single existing Rutherford Tier B query:

```yaml
  - query: "new business opening Murfreesboro Smyrna Rutherford County 2026"
    county: Rutherford
    tier: B
```

With more targeted queries:

```yaml
  - query: "new business opening Murfreesboro Smyrna Rutherford County Tennessee 2026"
    county: Rutherford
    tier: B
  - query: "new restaurant store salon opening Murfreesboro Smyrna La Vergne Tennessee 2026"
    county: Rutherford
    tier: B
  - query: "site:boropulse.com new business opening Murfreesboro 2025 2026"
    county: Rutherford
    tier: B
  - query: "site:rutherfordsource.com new business opening Murfreesboro 2025 2026"
    county: Rutherford
    tier: B
```

- [ ] **Step 3: Run validation tests**

Run: `pytest tests/test_county_coverage.py -v`
Expected: PASS (including extractable domain check for rutherfordsource.com and boropulse.com)

- [ ] **Step 4: Commit**

```bash
git add config/sources.yaml
git commit -m "feat: add Rutherford County news sources (rutherfordsource.com, boropulse.com)"
```

---

### Task 4: Improve Outer Ring County Coverage (Montgomery, Coffee, Franklin, Putnam)

These four counties have no `*countysource.com` sites and rely entirely on generic news/snippet queries. Improve by adding local news domains as extractable and adding targeted search queries.

**Files:**
- Modify: `config/sources.yaml` (extractable_domains, queries)

- [ ] **Step 1: Add local news domains to extractable_domains**

Add to `extractable_domains` under `# Regional news sites`:

```yaml
  - clarksvillenow.com
  - mainstreetmediatn.com
  - cookevillesocial.com
  - 3bmedianews.com
  - goodnewsmags.com
  - 931go.com
```

- [ ] **Step 2: Improve Montgomery County queries**

Replace the existing Montgomery Tier B query:

```yaml
  - query: "new business opening Clarksville Montgomery County Tennessee 2026"
    county: Montgomery
    tier: B
```

With:

```yaml
  - query: "new business opening Clarksville Montgomery County Tennessee 2026"
    county: Montgomery
    tier: B
  - query: "new restaurant store salon opening Clarksville Tennessee 2025 2026"
    county: Montgomery
    tier: B
  - query: "site:clarksvillenow.com new business opening 2025 2026"
    county: Montgomery
    tier: B
```

- [ ] **Step 3: Improve Putnam County queries**

Replace the existing Putnam Tier B query:

```yaml
  - query: "new business opening Cookeville Algood Putnam County Tennessee 2026"
    county: Putnam
    tier: B
```

With:

```yaml
  - query: "new business opening Cookeville Algood Putnam County Tennessee 2026"
    county: Putnam
    tier: B
  - query: "new restaurant store salon opening Cookeville Tennessee 2025 2026"
    county: Putnam
    tier: B
```

- [ ] **Step 4: Improve Coffee County queries**

Replace the existing Coffee Tier B query:

```yaml
  - query: "new business opening Manchester Tullahoma Coffee County Tennessee 2026"
    county: Coffee
    tier: B
```

With:

```yaml
  - query: "new business opening Manchester Tullahoma Coffee County Tennessee 2026"
    county: Coffee
    tier: B
  - query: "new restaurant store salon opening Tullahoma Manchester Tennessee 2025 2026"
    county: Coffee
    tier: B
  - query: "site:tullahomanews.com new business opening 2025 2026"
    county: Coffee
    tier: B
```

- [ ] **Step 5: Improve Franklin County queries**

Replace the existing Franklin County Tier B query:

```yaml
  - query: "new business opening Winchester Decherd Franklin County Tennessee 2026"
    county: Franklin
    tier: B
```

With:

```yaml
  - query: "new business opening Winchester Decherd Franklin County Tennessee 2026"
    county: Franklin
    tier: B
  - query: "new restaurant store salon opening Winchester Decherd Estill Springs Tennessee 2025 2026"
    county: Franklin
    tier: B
```

- [ ] **Step 6: Add Tier B queries for Maury, Robertson, Dickson**

These counties have Tier A (license tables) but no Tier B (news) queries. Add:

```yaml
  - query: "new business opening Columbia Maury County Tennessee 2026"
    county: Maury
    tier: B
  - query: "new business opening Springfield Robertson County Tennessee 2026"
    county: Robertson
    tier: B
  - query: "new business opening Dickson White Bluff Dickson County Tennessee 2026"
    county: Dickson
    tier: B
```

- [ ] **Step 7: Run validation tests**

Run: `pytest tests/test_county_coverage.py -v`
Expected: PASS (all counties now have Tier B queries)

- [ ] **Step 8: Commit**

```bash
git add config/sources.yaml
git commit -m "feat: improve search coverage for outer ring counties (Montgomery, Coffee, Franklin, Putnam, Maury, Robertson, Dickson)"
```

---

### Task 5: Create Discovery Script for Recent License Table URLs

County source sites publish new license table pages monthly. The `direct_extract_urls` list in sources.yaml is currently hardcoded with a few old URLs. Create a discovery script that uses the Tavily API to find recent pages we haven't captured.

**Files:**
- Create: `scripts/discover_county_urls.py`

- [ ] **Step 1: Write the discovery script**

Create `scripts/discover_county_urls.py`:

```python
#!/usr/bin/env python3
"""Discover recent license table URLs from county source sites.

Usage:
    python scripts/discover_county_urls.py [--update]

Without --update: prints discovered URLs not yet in seen_urls.
With --update: also adds them to direct_extract_urls in sources.yaml.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml
from config.settings import SOURCES_YAML, DB_PATH
from db.schema import init_db
from db.queries import get_seen_urls
from utils.tavily_client import TavilyClient


# County source sites that publish license tables
COUNTY_SITES = {
    "Davidson": "davidsoncountysource.com",
    "Williamson": "williamsonsource.com",
    "Wilson": "wilsoncountysource.com",
    "Cheatham": "cheathamcountysource.com",
    "Robertson": "robertsoncountysource.com",
    "Maury": "maurycountysource.com",
    "Dickson": "dicksoncountysource.com",
}


def discover_urls():
    """Search each county source site for license table pages."""
    client = TavilyClient()
    conn = init_db(DB_PATH)
    seen = get_seen_urls(conn)
    conn.close()

    new_urls = []

    for county, domain in COUNTY_SITES.items():
        print(f"\nSearching {county} ({domain})...")
        results = client.search(
            f"site:{domain} new business licenses",
            max_results=10,
        )

        for result in results:
            url = result.get("url", "")
            title = result.get("title", "")
            if "license" not in title.lower() and "license" not in url.lower():
                continue
            if url in seen:
                print(f"  [seen] {url}")
                continue
            print(f"  [NEW]  {url}")
            new_urls.append({"url": url, "county": county})

    return new_urls


def update_sources_yaml(new_urls):
    """Append new URLs to direct_extract_urls in sources.yaml."""
    with open(SOURCES_YAML, "r") as fh:
        sources = yaml.safe_load(fh)

    existing = {entry["url"] for entry in sources.get("direct_extract_urls", [])}
    added = 0

    for entry in new_urls:
        if entry["url"] not in existing:
            sources.setdefault("direct_extract_urls", []).append(entry)
            added += 1

    if added > 0:
        with open(SOURCES_YAML, "w") as fh:
            yaml.dump(sources, fh, default_flow_style=False, sort_keys=False)
        print(f"\nAdded {added} new URLs to sources.yaml")
    else:
        print("\nNo new URLs to add.")


def main():
    update = "--update" in sys.argv
    new_urls = discover_urls()

    print(f"\n{'='*60}")
    print(f"Found {len(new_urls)} new license table URLs")

    if new_urls and update:
        update_sources_yaml(new_urls)
    elif new_urls:
        print("\nRun with --update to add these to sources.yaml")
        print("URLs found:")
        for entry in new_urls:
            print(f"  - url: \"{entry['url']}\"")
            print(f"    county: {entry['county']}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Test the script in dry-run mode**

Run: `python scripts/discover_county_urls.py`
Expected: Lists new URLs found per county (may find 0 if all are already seen)

- [ ] **Step 3: Commit**

```bash
git add scripts/discover_county_urls.py
git commit -m "feat: add discovery script for county license table URLs"
```

---

### Task 6: Add Missing Cities to County Map

The `counties` dict in `sources.yaml` is used for city-to-county inference. Several counties are missing cities that appear in lead data, which prevents proper county assignment.

**Files:**
- Modify: `config/sources.yaml:1-53` (counties section)

- [ ] **Step 1: Write test for city coverage**

Add to `tests/test_county_coverage.py`:

```python
class TestCityMap:
    """County→city map should include all major cities."""

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
```

- [ ] **Step 2: Run test to see which cities are missing**

Run: `pytest tests/test_county_coverage.py::TestCityMap -v`
Expected: Some failures for missing cities

- [ ] **Step 3: Update county city lists in sources.yaml**

Update the `counties` section in `config/sources.yaml`:

```yaml
counties:
  Davidson:
    - Nashville
    - Antioch
    - Madison
    - Hermitage
    - Goodlettsville
    - Old Hickory
    - Joelton
    - Whites Creek
  Williamson:
    - Franklin
    - Brentwood
    - Nolensville
    - Spring Hill
    - Fairview
    - Thompson's Station
    - Arrington
  Rutherford:
    - Murfreesboro
    - Smyrna
    - La Vergne
    - Eagleville
  Sumner:
    - Gallatin
    - Hendersonville
    - Portland
    - Westmoreland
    - Millersville
    - White House
  Wilson:
    - Lebanon
    - Mount Juliet
    - Watertown
  Robertson:
    - Springfield
    - White House
    - Greenbrier
    - Cross Plains
    - Coopertown
  Maury:
    - Columbia
    - Mt. Pleasant
    - Spring Hill
  Dickson:
    - Dickson
    - White Bluff
    - Burns
    - Charlotte
  Cheatham:
    - Ashland City
    - Kingston Springs
    - Pleasant View
    - Pegram
  Montgomery:
    - Clarksville
  Coffee:
    - Manchester
    - Tullahoma
  Franklin:
    - Winchester
    - Decherd
    - Cowan
    - Estill Springs
  Putnam:
    - Cookeville
    - Algood
    - Baxter
    - Monterey
```

- [ ] **Step 4: Run tests to verify**

Run: `pytest tests/test_county_coverage.py::TestCityMap -v`
Expected: PASS

- [ ] **Step 5: Run rescore to re-infer counties with new city mappings**

Run: `python -m cli.main rescore`
Expected: Some leads get county inferred from newly-mapped cities

- [ ] **Step 6: Commit**

```bash
git add config/sources.yaml tests/test_county_coverage.py
git commit -m "feat: expand city-to-county map with missing cities across all counties"
```

---

### Task 7: Run Pipeline and Validate Results

Execute the pipeline with the updated sources configuration and validate that county coverage has improved.

**Files:**
- No files modified (execution + validation)

- [ ] **Step 1: Run full pipeline**

Run: `python -m cli.main run`
Expected: Pipeline completes successfully with new leads from previously underperforming counties.

- [ ] **Step 2: Check county distribution**

Run:
```bash
python3 -c "
from db.schema import init_db
conn = init_db('data/leads.db')
rows = conn.execute('''
    SELECT county, COUNT(*) as cnt, ROUND(AVG(pos_score),1) as avg
    FROM leads WHERE deleted_at IS NULL
    GROUP BY county ORDER BY cnt DESC
''').fetchall()
for r in rows:
    print(f'{(r[\"county\"] or \"(none)\"):<15} {r[\"cnt\"]:>5} leads  avg={r[\"avg\"]}')
conn.close()
"
```

Expected: Increased lead counts for Rutherford, Sumner, Montgomery, and other underperforming counties.

- [ ] **Step 3: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 4: Commit any sources.yaml updates from discovery**

If `discover_county_urls.py` was run with `--update`, commit the updated direct_extract_urls:

```bash
git add config/sources.yaml
git commit -m "feat: add discovered license table URLs from pipeline run"
```

---

## Notes for Future Maintenance

1. **Monthly URL refresh:** Run `python scripts/discover_county_urls.py --update` monthly to discover new license table pages published by county source sites.

2. **Sumner County alternative:** If a government site or chamber of commerce in Sumner County begins publishing license data, add it as a Tier A source. Currently `gallatintn.org/economic-development/` is the closest alternative but does not publish structured license tables.

3. **Credit budget:** Each new Tier B query costs 1 credit (search) + 2 credits per extractable URL found. The additional queries in this plan add approximately 15-20 queries, costing ~15-60 credits per pipeline run depending on extractable results.

4. **Rutherford County is high priority:** Murfreesboro is Tennessee's 6th largest city. If `rutherfordsource.com` or Rutherford County government ever publishes structured business license data, add it immediately as a Tier A source with `source_type: license_table`.
