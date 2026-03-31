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
