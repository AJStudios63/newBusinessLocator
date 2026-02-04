import json
import sqlite3
from datetime import datetime

from config.settings import DB_PATH, LOG_PATH
from db.schema import init_db
from db.queries import insert_lead, insert_seen_url, update_pipeline_run


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
        url = extract["source_url"]
        county = extract.get("county")
        seen_url_pairs.append((url, county))
        if url not in seen_url_set:
            seen_url_set.add(url)
            unique_source_urls.append(url)

    # 3. Insert each source URL into seen_urls.
    for url, county in seen_url_pairs:
        insert_seen_url(conn, url, county)

    # 4. Insert each BusinessRecord, tracking new vs dupe via changes().
    leads_new = 0

    for record in business_records:
        # 4a. Ensure 'stage' defaults to 'New' if missing or None.
        if not record.get("stage"):
            record["stage"] = "New"

        # 4b. Insert the lead (INSERT OR IGNORE on fingerprint).
        insert_lead(conn, record)

        # 4c. Check whether the row was actually inserted or skipped.
        cursor = conn.execute("SELECT changes()")
        changes = cursor.fetchone()[0]
        if changes == 1:
            leads_new += 1

    # 5. Compute final counts.
    leads_found = len(business_records)
    leads_dupes = leads_found - leads_new

    # 6. Build sources_queried JSON from the deduplicated URL list.
    sources_queried = json.dumps(unique_source_urls)

    # 7. Update the pipeline_runs row with final counts and status.
    update_pipeline_run(
        conn,
        run_id,
        status="completed",
        leads_found=leads_found,
        leads_new=leads_new,
        leads_dupes=leads_dupes,
        error_message=None,
        sources_queried=sources_queried,
    )

    # 8. Append a summary line to LOG_PATH.
    log_pipeline_run(run_id, leads_found, leads_new, leads_dupes)

    # 9. Commit the transaction.
    conn.commit()

    # Close the connection only if we opened it.
    if owns_connection:
        conn.close()

    # 10. Return the counts dict.
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
    with open(LOG_PATH, "a") as log_file:
        log_file.write(line)
