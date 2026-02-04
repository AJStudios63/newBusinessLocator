import click
import csv
import sys
from config.settings import DB_PATH
from db.schema import init_db
from db.queries import (
    get_leads, get_lead, update_stage, get_stats,
    get_stage_history, get_pipeline_runs,
)


@click.group()
def cli():
    """New Business Locator — POS lead generation pipeline."""
    pass


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
    rows = get_leads(conn, stage=stage, county=county, min_score=min_score, sort=sort, limit=limit)
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
    click.echo(f"  Avg score   : {s['avg_score']:.1f}")

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
@click.option("--output", "-o", required=True, type=click.Path(), help="Output CSV file path.")
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
