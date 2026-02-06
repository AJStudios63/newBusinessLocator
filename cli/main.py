from __future__ import annotations

import csv
import re
import subprocess
import sys
from pathlib import Path

import click

from config.settings import DB_PATH, PROJECT_ROOT, SCORING_YAML
from db.schema import init_db
from db.queries import (
    get_leads, get_lead, update_stage, get_stats,
    get_stage_history, get_pipeline_runs,
)
from utils.logging_config import setup_logging
from etl.transform import classify, score_lead, _load_yaml


@click.group()
@click.option("--log-level", default="INFO", envvar="LOG_LEVEL",
              type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
              help="Set the logging level (default: INFO, or LOG_LEVEL env var).")
@click.option("--log-console", is_flag=True, default=False,
              help="Also output logs to console (in addition to file).")
@click.pass_context
def cli(ctx, log_level, log_console):
    """New Business Locator — POS lead generation pipeline."""
    # Initialize logging with the specified level
    setup_logging(level=log_level.upper(), log_to_file=True, log_to_console=log_console)
    # Store in context for potential use by subcommands
    ctx.ensure_object(dict)
    ctx.obj["log_level"] = log_level


@cli.command()
@click.option("--dry-run", is_flag=True, default=False, help="Print results without writing to DB.")
def run(dry_run):
    """Execute the full ETL pipeline."""
    # Import here to avoid circular imports at module load time
    from etl.pipeline import run_pipeline

    click.echo("Starting pipeline...")
    result = run_pipeline(dry_run=dry_run)

    if result["error"]:
        click.echo(f"[FAILED] {result['error']}", err=True)
        sys.exit(1)

    if dry_run:
        click.echo(f"\n[DRY RUN] Found {result['leads_found']} leads (no DB writes).\n")
        if result["business_records"]:
            # Print a preview table
            _print_leads_table(result["business_records"])
        else:
            click.echo("No leads found.")
    else:
        click.echo(
            f"[DONE] run_id={result['run_id']} | "
            f"found={result['leads_found']} new={result['leads_new']} dupes={result['leads_dupes']}"
        )


@cli.command()
@click.option("--stage", default=None, help="Filter by stage.")
@click.option("--county", default=None, help="Filter by county.")
@click.option("--min-score", "min_score", default=None, type=int, help="Minimum pos_score.")
@click.option("--sort", default="pos_score", help="Column to sort by (desc). Default: pos_score.")
@click.option("--limit", default=50, type=int, help="Max rows to show. Default: 50.")
def leads(stage, county, min_score, sort, limit):
    """List leads as a formatted table."""
    conn = init_db(DB_PATH)
    try:
        rows = get_leads(conn, stage=stage, county=county, min_score=min_score, sort=sort, limit=limit)
    except ValueError as exc:
        conn.close()
        click.echo(str(exc), err=True)
        sys.exit(1)
    conn.close()

    if not rows:
        click.echo("No leads match the filters.")
        return

    _print_leads_table(rows)


@cli.command("lead")
@click.argument("lead_id", type=int)
def lead_detail(lead_id):
    """Show full detail for a single lead."""
    conn = init_db(DB_PATH)
    row = get_lead(conn, lead_id)
    conn.close()

    if row is None:
        click.echo(f"No lead with id={lead_id}.", err=True)
        sys.exit(1)

    # Print every field on its own line, nicely aligned
    labels = {
        "id": "ID", "fingerprint": "Fingerprint", "business_name": "Business",
        "business_type": "Type", "raw_type": "Raw Type", "address": "Address",
        "city": "City", "state": "State", "zip_code": "ZIP", "county": "County",
        "license_date": "License Date", "pos_score": "Score", "stage": "Stage",
        "source_url": "Source URL", "source_type": "Source Type", "notes": "Notes",
        "created_at": "Created", "updated_at": "Updated",
        "contacted_at": "Contacted", "closed_at": "Closed",
    }
    max_label_len = max(len(v) for v in labels.values())
    for key, label in labels.items():
        val = row.get(key, "")
        click.echo(f"  {label.ljust(max_label_len)}  {val if val is not None else '—'}")


@cli.command()
@click.argument("lead_id", type=int)
@click.option("--stage", required=True, type=click.Choice(["New", "Qualified", "Contacted", "Follow-up", "Closed-Won", "Closed-Lost"]), help="New stage value.")
@click.option("--note", default=None, help="Note to append.")
def update(lead_id, stage, note):
    """Update a lead's pipeline stage and optionally add a note."""
    conn = init_db(DB_PATH)
    try:
        update_stage(conn, lead_id, stage, note)
        click.echo(f"Lead {lead_id} → {stage}" + (f" (note added)" if note else ""))
    except ValueError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)
    finally:
        conn.close()


@cli.command()
def stats():
    """Show summary dashboard: totals by stage, county, type; avg score; last run."""
    conn = init_db(DB_PATH)
    s = get_stats(conn)
    conn.close()

    click.echo(f"\n{'=== STATS ==='}")
    click.echo(f"  Total leads : {s['total_leads']}")
    avg_score = s['avg_score']
    click.echo(f"  Avg score   : {avg_score:.1f}" if avg_score is not None else "  Avg score   : N/A")

    click.echo(f"\n  By Stage:")
    for stage, count in sorted(s["by_stage"].items()):
        click.echo(f"    {stage:<15} {count}")

    click.echo(f"\n  By County:")
    for county, count in sorted(s["by_county"].items(), key=lambda x: -x[1]):
        click.echo(f"    {county or '(none)':<15} {count}")

    click.echo(f"\n  By Type:")
    for btype, count in sorted(s["by_type"].items(), key=lambda x: -x[1]):
        click.echo(f"    {btype or '(none)':<15} {count}")

    if s["last_run"]:
        lr = s["last_run"]
        click.echo(f"\n  Last Run:")
        click.echo(f"    ID        : {lr['id']}")
        click.echo(f"    Started   : {lr['run_started_at']}")
        click.echo(f"    Finished  : {lr['run_finished_at']}")
        click.echo(f"    Status    : {lr['status']}")
        click.echo(f"    Found     : {lr['leads_found']}  New: {lr['leads_new']}  Dupes: {lr['leads_dupes']}")
    click.echo("")


@cli.command()
@click.argument("lead_id", type=int)
def history(lead_id):
    """Show stage-change audit trail for a lead."""
    conn = init_db(DB_PATH)
    rows = get_stage_history(conn, lead_id)
    conn.close()

    if not rows:
        click.echo(f"No stage history for lead {lead_id}.")
        return

    click.echo(f"\n  Stage history for lead {lead_id}:")
    click.echo(f"  {'#':<4} {'From':<15} {'To':<15} {'When'}")
    click.echo(f"  {'-'*4} {'-'*15} {'-'*15} {'-'*24}")
    for i, row in enumerate(rows, 1):
        click.echo(f"  {i:<4} {row['old_stage'] or '—':<15} {row['new_stage']:<15} {row['changed_at']}")
    click.echo("")


@cli.command()
@click.option("--stage", default=None, help="Filter by stage.")
@click.option("--county", default=None, help="Filter by county.")
@click.option("--min-score", "min_score", default=None, type=int, help="Minimum pos_score.")
@click.option("--output", "-o", required=True, type=click.Path(writable=True, dir_okay=False), help="Output CSV file path.")
def export(stage, county, min_score, output):
    """Export filtered leads to CSV."""
    conn = init_db(DB_PATH)
    rows = get_leads(conn, stage=stage, county=county, min_score=min_score, limit=10000)
    conn.close()

    if not rows:
        click.echo("No leads match the filters — nothing exported.")
        return

    fieldnames = [
        "id", "fingerprint", "business_name", "business_type", "raw_type",
        "address", "city", "state", "zip_code", "county", "license_date",
        "pos_score", "stage", "source_url", "source_type", "notes",
        "created_at", "updated_at", "contacted_at", "closed_at",
    ]

    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    click.echo(f"Exported {len(rows)} leads to {output}")


@cli.command()
def rescore():
    """Re-classify and re-score all existing leads.

    Applies the updated classify() logic (with business-name fallback)
    to every lead in the database, then recalculates pos_score.
    Prints a summary of how many leads were re-classified.
    """
    # Load scoring configuration
    scoring = _load_yaml(SCORING_YAML)
    type_keywords = scoring.get("business_type_keywords", {})

    conn = init_db(DB_PATH)
    # Fetch all leads (high limit to get them all)
    all_leads = get_leads(conn, limit=100000, sort="id")

    if not all_leads:
        click.echo("No leads in database to rescore.")
        conn.close()
        return

    click.echo(f"Rescoring {len(all_leads)} leads...")

    reclassified_count = 0
    score_changes = []

    for lead in all_leads:
        old_type = lead.get("business_type")
        old_score = lead.get("pos_score", 0)

        # Re-classify (mutates the lead dict)
        classify(lead, type_keywords)
        new_type = lead.get("business_type")

        # Re-score (mutates the lead dict)
        score_lead(lead, scoring)
        new_score = lead.get("pos_score", 0)

        # Check if anything changed
        type_changed = old_type != new_type
        score_changed = old_score != new_score

        if type_changed or score_changed:
            reclassified_count += 1
            score_changes.append({
                "id": lead["id"],
                "name": lead.get("business_name", ""),
                "old_type": old_type,
                "new_type": new_type,
                "old_score": old_score,
                "new_score": new_score,
            })

            # Update the database
            conn.execute(
                "UPDATE leads SET business_type = ?, pos_score = ?, updated_at = datetime('now') WHERE id = ?;",
                (new_type, new_score, lead["id"]),
            )

    conn.commit()
    conn.close()

    # Print summary
    click.echo(f"\n=== RESCORE SUMMARY ===")
    click.echo(f"  Total leads processed: {len(all_leads)}")
    click.echo(f"  Leads re-classified:   {reclassified_count}")

    if score_changes:
        click.echo(f"\n  Changes:")
        click.echo(f"  {'ID':<5} {'Business Name':<35} {'Old Type':<12} {'New Type':<12} {'Old':<5} {'New':<5}")
        click.echo(f"  {'-'*5} {'-'*35} {'-'*12} {'-'*12} {'-'*5} {'-'*5}")
        for change in score_changes:
            click.echo(
                f"  {change['id']:<5} "
                f"{str(change['name'])[:34]:<35} "
                f"{str(change['old_type'] or 'other')[:11]:<12} "
                f"{str(change['new_type'] or 'other')[:11]:<12} "
                f"{change['old_score']:<5} "
                f"{change['new_score']:<5}"
            )
    else:
        click.echo("\n  No leads required re-classification.")

    click.echo("")


# ---------------------------------------------------------------------------
# Schedule subcommand group
# ---------------------------------------------------------------------------

PLIST_NAME = "com.newbusinesslocator.weekly.plist"
PLIST_TEMPLATE = PROJECT_ROOT / "scripts" / PLIST_NAME
LAUNCHAGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
INSTALLED_PLIST = LAUNCHAGENTS_DIR / PLIST_NAME


def _get_python_path() -> str:
    """Return the path to the current Python interpreter."""
    return sys.executable


def _generate_plist_content() -> str:
    """Generate plist content with paths filled in for current environment."""
    if not PLIST_TEMPLATE.exists():
        raise FileNotFoundError(f"Plist template not found at {PLIST_TEMPLATE}")

    content = PLIST_TEMPLATE.read_text()
    python_path = _get_python_path()
    project_root = str(PROJECT_ROOT)

    content = content.replace("__PYTHON_PATH__", python_path)
    content = content.replace("__PROJECT_ROOT__", project_root)

    return content


@cli.group()
def schedule():
    """Manage scheduled weekly pipeline runs (macOS launchd)."""
    pass


@schedule.command("install")
def schedule_install():
    """Install the launchd job for weekly pipeline runs."""
    # Check we're on macOS
    if sys.platform != "darwin":
        click.echo("Error: Schedule commands only work on macOS.", err=True)
        sys.exit(1)

    # Check if already installed
    if INSTALLED_PLIST.exists():
        click.echo(f"Job already installed at {INSTALLED_PLIST}")
        click.echo("Run 'schedule uninstall' first to reinstall.")
        sys.exit(1)

    # Ensure LaunchAgents directory exists
    LAUNCHAGENTS_DIR.mkdir(parents=True, exist_ok=True)

    # Generate and write the plist with correct paths
    try:
        plist_content = _generate_plist_content()
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    INSTALLED_PLIST.write_text(plist_content)
    click.echo(f"Created plist at {INSTALLED_PLIST}")

    # Load the job
    result = subprocess.run(
        ["launchctl", "load", str(INSTALLED_PLIST)],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        click.echo(f"Warning: launchctl load failed: {result.stderr.strip()}", err=True)
        click.echo("The plist was created but may not be active.")
    else:
        click.echo("Job loaded successfully.")
        click.echo("\nSchedule: Every Sunday at 6:00 AM")
        click.echo(f"Python:   {_get_python_path()}")
        click.echo(f"Project:  {PROJECT_ROOT}")
        click.echo(f"Logs:     {PROJECT_ROOT / 'logs'}/launchd_*.log")


@schedule.command("uninstall")
def schedule_uninstall():
    """Uninstall the launchd job."""
    if sys.platform != "darwin":
        click.echo("Error: Schedule commands only work on macOS.", err=True)
        sys.exit(1)

    if not INSTALLED_PLIST.exists():
        click.echo("No scheduled job found (plist not installed).")
        return

    # Unload the job first
    result = subprocess.run(
        ["launchctl", "unload", str(INSTALLED_PLIST)],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        # Job might not be loaded, but we still want to remove the file
        click.echo(f"Note: launchctl unload: {result.stderr.strip() or 'job may not have been loaded'}")

    # Remove the plist file
    INSTALLED_PLIST.unlink()
    click.echo(f"Removed {INSTALLED_PLIST}")
    click.echo("Scheduled job uninstalled.")


@schedule.command("status")
def schedule_status():
    """Show the status of the scheduled job."""
    if sys.platform != "darwin":
        click.echo("Error: Schedule commands only work on macOS.", err=True)
        sys.exit(1)

    click.echo("\n=== Schedule Status ===\n")

    # Check if plist is installed
    if not INSTALLED_PLIST.exists():
        click.echo("Status: NOT INSTALLED")
        click.echo(f"\nTo install, run: python -m cli.main schedule install")
        return

    click.echo(f"Plist:    {INSTALLED_PLIST}")
    click.echo("Status:   INSTALLED")

    # Check if job is loaded using launchctl list
    result = subprocess.run(
        ["launchctl", "list", "com.newbusinesslocator.weekly"],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        click.echo("Loaded:   YES")
        # Parse launchctl output - looks for LastExitStatus in the output
        output = result.stdout
        if '"LastExitStatus"' in output:
            # Parse the dictionary-like output format
            match = re.search(r'"LastExitStatus"\s*=\s*(\d+)', output)
            if match:
                exit_status = match.group(1)
                click.echo(f"Last Exit: {exit_status} (0 = success)")
    else:
        click.echo("Loaded:   NO (plist exists but job not loaded)")
        click.echo("\nTo load, run: launchctl load ~/Library/LaunchAgents/com.newbusinesslocator.weekly.plist")

    click.echo("\nSchedule: Every Sunday at 6:00 AM")

    # Show last run info from database
    conn = init_db(DB_PATH)
    runs = get_pipeline_runs(conn, limit=1)
    conn.close()

    if runs:
        last_run = runs[0]
        click.echo(f"\nLast Pipeline Run:")
        click.echo(f"  Time:   {last_run['run_started_at']}")
        click.echo(f"  Status: {last_run['status']}")
        click.echo(f"  Found:  {last_run['leads_found']} leads ({last_run['leads_new']} new)")
    else:
        click.echo("\nLast Pipeline Run: No runs recorded yet")

    # Check for launchd log files
    stdout_log = PROJECT_ROOT / "logs" / "launchd_stdout.log"
    stderr_log = PROJECT_ROOT / "logs" / "launchd_stderr.log"

    click.echo(f"\nLog files:")
    if stdout_log.exists():
        stat = stdout_log.stat()
        click.echo(f"  stdout: {stdout_log} ({stat.st_size} bytes)")
    else:
        click.echo(f"  stdout: (not created yet)")

    if stderr_log.exists():
        stat = stderr_log.stat()
        click.echo(f"  stderr: {stderr_log} ({stat.st_size} bytes)")
    else:
        click.echo(f"  stderr: (not created yet)")

    click.echo("")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _print_leads_table(rows: list[dict]) -> None:
    """Print a compact table of leads to stdout."""
    # Columns shown in list view: ID, Name, Type, City, County, Score, Stage
    click.echo(
        f"  {'ID':<5} {'Business Name':<35} {'Type':<14} {'City':<18} {'County':<12} {'Score':<6} {'Stage'}"
    )
    click.echo(
        f"  {'-'*5} {'-'*35} {'-'*14} {'-'*18} {'-'*12} {'-'*6} {'-'*15}"
    )
    for r in rows:
        click.echo(
            f"  {r.get('id', ''):<5} "
            f"{str(r.get('business_name', ''))[:34]:<35} "
            f"{str(r.get('business_type', '') or '')[:13]:<14} "
            f"{str(r.get('city', '') or '')[:17]:<18} "
            f"{str(r.get('county', '') or '')[:11]:<12} "
            f"{r.get('pos_score', 0):<6} "
            f"{r.get('stage', 'New')}"
        )
    click.echo(f"\n  {len(rows)} lead(s) shown.")


if __name__ == "__main__":
    cli()
