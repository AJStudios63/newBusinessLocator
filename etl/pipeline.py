"""
ETL pipeline orchestrator.

Coordinates extract → transform → load, manages the pipeline_runs audit row,
catches and records errors, and writes to pipeline.log.
"""

from __future__ import annotations

from datetime import datetime

from config.settings import DB_PATH
from db.schema import init_db
from db.queries import insert_pipeline_run, update_pipeline_run
from etl.extract import run_extract
from etl.transform import run_transform
from etl.load import run_load, log_pipeline_run
from utils.logging_config import get_logger

logger = get_logger("pipeline")


def run_pipeline(dry_run: bool = False) -> dict:
    """
    Execute the full ETL pipeline.

    Parameters
    ----------
    dry_run : bool
        When True, extract and transform are executed normally so the caller
        can inspect results, but nothing is written to the database (no load,
        no pipeline_runs row, no seen_urls inserts, no log line).

    Returns
    -------
    dict with keys:
        run_id        : int | None    – the pipeline_runs row id (None on dry_run)
        status        : str           – 'completed' or 'failed'
        leads_found   : int
        leads_new     : int           – 0 on dry_run
        leads_dupes   : int           – 0 on dry_run
        business_records : list[dict] – the transformed records (useful for dry_run display)
        raw_extracts     : list[dict] – the raw extracts (useful for dry_run display)
        error         : str | None
    """
    run_id = None
    conn = None
    run_started_at = datetime.now().isoformat()

    logger.info(f"Pipeline starting (dry_run={dry_run})")

    try:
        # --- open DB and create audit row (skip on dry_run) -----------------
        if not dry_run:
            conn = init_db(DB_PATH)
            run_id = insert_pipeline_run(conn, run_started_at)
            logger.debug(f"Created pipeline run with id={run_id}")

        # --- EXTRACT --------------------------------------------------------
        logger.info("Starting extract phase")
        raw_extracts = run_extract(conn=conn, use_db=not dry_run)

        # --- TRANSFORM ------------------------------------------------------
        logger.info("Starting transform phase")
        business_records = run_transform(raw_extracts)

        # --- LOAD (skip on dry_run) -----------------------------------------
        if dry_run:
            logger.info(f"Dry run completed: {len(business_records)} leads found")
            return {
                "run_id": None,
                "status": "completed",
                "leads_found": len(business_records),
                "leads_new": 0,
                "leads_dupes": 0,
                "business_records": business_records,
                "raw_extracts": raw_extracts,
                "error": None,
            }

        logger.info("Starting load phase")
        counts = run_load(business_records, raw_extracts, run_id, conn=conn)

        logger.info(f"Pipeline completed successfully: run_id={run_id}, found={counts['leads_found']}, new={counts['leads_new']}, dupes={counts['leads_dupes']}")
        return {
            "run_id": run_id,
            "status": "completed",
            "leads_found": counts["leads_found"],
            "leads_new": counts["leads_new"],
            "leads_dupes": counts["leads_dupes"],
            "business_records": business_records,
            "raw_extracts": raw_extracts,
            "error": None,
        }

    except Exception as exc:
        # --- record the failure in the DB and log (if we have a run_id) -----
        error_msg = str(exc)
        logger.error(f"Pipeline failed: {error_msg}")
        if run_id is not None and conn is not None:
            try:
                update_pipeline_run(conn, run_id, status="failed", leads_found=0, leads_new=0, leads_dupes=0, error_message=error_msg)
            except Exception as inner_exc:
                logger.warning(f"Failed to record pipeline error: {inner_exc}")
            log_pipeline_run(run_id, 0, 0, 0, status="failed", error=error_msg)

        return {
            "run_id": run_id,
            "status": "failed",
            "leads_found": 0,
            "leads_new": 0,
            "leads_dupes": 0,
            "business_records": [],
            "raw_extracts": [],
            "error": error_msg,
        }

    finally:
        if conn is not None:
            conn.close()
