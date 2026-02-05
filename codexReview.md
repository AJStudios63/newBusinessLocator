# Code Review Findings

## Findings
- [High] Load is not atomic: per-row commits in `insert_lead`/`insert_seen_url` combined with no transaction in `run_load` can leave partial data if any later step fails (e.g., log write or pipeline run update). This can also misreport a failed run with zero counts while rows are already persisted. (`etl/load.py:46`, `etl/load.py:74`, `db/queries.py:37`, `db/queries.py:278`)
- [High] `parse_snippet` can emit a record with `business_name=None` when a result title is empty/stripped, which violates the NOT NULL constraint and can crash the pipeline on insert. (`utils/parsers.py:329`, `db/schema.py:10`)
- [Medium] `dry_run` promises no DB writes, but `run_extract` still calls `init_db` when no connection is passed, which will create/modify the DB file and run DDL. That breaks the dry-run contract and can create `data/leads.db` unexpectedly. (`etl/pipeline.py:23`, `etl/extract.py:101`)
- [Medium] `update_stage` returns early when the stage is unchanged, so a user cannot append a note without changing stage (CLI requires a stage). This silently drops notes for same-stage updates. (`db/queries.py:142`, `cli/main.py:94`)
- [Medium] External HTTP calls have no timeouts; a hung Tavily request can block the pipeline indefinitely. (`utils/tavily_client.py:31`, `utils/tavily_client.py:68`)
- [Low] Invalid `--sort` values raise a `ValueError` and surface a stack trace because the CLI does not catch the error. (`cli/main.py:52`, `db/queries.py:97`)

## Open Questions / Assumptions
- Should `dry_run` be allowed to read an existing DB but never create/modify it? If yes, consider a read-only connection or skipping DB access when absent.
- Is it acceptable to append notes without a stage change? If so, the CLI/DB should allow that pathway.

## Testing Gaps
- No automated tests are present. Consider adding unit tests for parsers and scoring (`utils/parsers.py`, `etl/transform.py`) and an integration test for `run_pipeline`/`run_load` to cover duplicate handling and failure/rollback behavior.
