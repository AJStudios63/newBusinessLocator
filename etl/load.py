from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from config.settings import DB_PATH, LOG_PATH
from db.schema import init_db
from db.queries import insert_lead, insert_seen_url, update_pipeline_run
from utils.logging_config import get_logger

logger = get_logger("load")


def run_load(
    business_records: list[dict],
    raw_extracts: list[dict],
    run_id: int,
    conn: sqlite3.Connection | None = None,
) -> dict:
    """
    Main load entry point.

    Args:
        business_records: cleaned, scored, deduplicated records from transform.
        raw_extracts: original RawExtract dicts from extract (needed for source URLs).
        run_id: the pipeline_runs row id to update.
        conn: optional existing DB connection (if None, open via init_db(DB_PATH)).

    Returns:
        dict with keys: leads_found (int), leads_new (int), leads_dupes (int).
    """
    # 1. Open DB connection if not provided.
    owns_connection = conn is None
    if owns_connection:
        conn = init_db(DB_PATH)

    # 2. Collect unique source URLs from raw_extracts as (source_url, county) pairs.
    seen_url_pairs: list[tuple[str, str | None]] = []
    unique_source_urls: list[str] = []
    seen_url_set: set[str] = set()

    for extract in raw_extracts:
        url = extract.get("source_url")
        if not url:
            continue
        county = extract.get("county")
        seen_url_pairs.append((url, county))
        if url not in seen_url_set:
            seen_url_set.add(url)
            unique_source_urls.append(url)

    # 3. Insert URLs and leads in a single transaction.
    leads_new = 0
    leads_found = len(business_records)
    logger.info(f"Loading {leads_found} business records and {len(unique_source_urls)} unique URLs")

    with conn:
        # 3a. Insert each source URL into seen_urls.
        for url, county in seen_url_pairs:
            insert_seen_url(conn, url, county, commit=False)

        # 3b. Insert each BusinessRecord, tracking new vs dupe via changes().
        for record in business_records:
            if not record.get("stage"):
                record["stage"] = "New"
            # Ensure source_batch_id is present (can be None)
            if "source_batch_id" not in record:
                record["source_batch_id"] = None

            insert_lead(conn, record, commit=False)
            cursor = conn.execute("SELECT changes()")
            changes = cursor.fetchone()[0]
            if changes == 1:
                leads_new += 1

        # 3c. Update the pipeline_runs row with final counts and status.
        leads_dupes = leads_found - leads_new
        sources_queried = json.dumps(unique_source_urls)
        update_pipeline_run(
            conn,
            run_id,
            status="completed",
            leads_found=leads_found,
            leads_new=leads_new,
            leads_dupes=leads_dupes,
            error_message=None,
            sources_queried=sources_queried,
            commit=False,
        )

    # 4. Append a summary line to LOG_PATH (best effort).
    try:
        log_pipeline_run(run_id, leads_found, leads_new, leads_dupes)
    except OSError:
        pass

    # Close the connection only if we opened it.
    if owns_connection:
        conn.close()

    # 10. Return the counts dict.
    logger.info(f"Load completed: {leads_new} new leads, {leads_dupes} duplicates")
    return {
        "leads_found": leads_found,
        "leads_new": leads_new,
        "leads_dupes": leads_dupes,
    }


def log_pipeline_run(
    run_id: int,
    leads_found: int,
    leads_new: int,
    leads_dupes: int,
    status: str = "completed",
    error: str | None = None,
) -> None:
    """
    Append a single line to LOG_PATH.
    Format: "{ISO timestamp} | run_id={run_id} | status={status} | found={leads_found} new={leads_new} dupes={leads_dupes} | error={error or 'none'}"
    """
    timestamp = datetime.now().isoformat()
    error_str = error or "none"
    line = (
        f"{timestamp} | run_id={run_id} | status={status} | "
        f"found={leads_found} new={leads_new} dupes={leads_dupes} | "
        f"error={error_str}\n"
    )
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a") as log_file:
            log_file.write(line)
    except OSError as e:
        logger.warning(f"Could not write to log file: {e}")
