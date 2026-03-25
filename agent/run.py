"""
Main agent orchestrator.

Usage:
  python -m agent.run                              # all EMEA countries (default)
  python -m agent.run --geo NAMERICA               # all North America + LatAm
  python -m agent.run --geo APAC                   # all Asia-Pacific
  python -m agent.run --geo ALL                    # every country across all geos
  python -m agent.run --sub-region "Nordics"       # EMEA sub-region
  python -m agent.run --countries "Israel"         # specific countries
  python -m agent.run --geo NAMERICA --min-score 7

  # Legacy flags (kept for backward compat):
  python -m agent.run --global-region "EMEA"
  python -m agent.run --global-region "North America"
"""
import argparse
import sys

import anthropic
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

from .config import (
    ANTHROPIC_API_KEY, TIDB_CONNECTION_STRING, MIN_FIT_SCORE,
    COUNTRY_REGION, COUNTRY_GEO, GEO_REGIONS, EMEA_REGIONS, all_countries,
)
from .discovery import discover_companies
from .scraper import scrape_text
from .analyzer import analyse_company
from .storage import db_conn, upsert_lead, get_conn

console = Console()

# Map legacy --global-region names to new geo keys
_LEGACY_GEO_MAP = {
    "emea":          "EMEA",
    "north america": "NAMERICA",
    "namerica":      "NAMERICA",
    "apac":          "APAC",
}


def run_country(
    country: str,
    client: anthropic.Anthropic,
    min_score: int,
    progress: Progress,
    task_id,
) -> tuple[int, int]:
    """
    Run the full pipeline for one country.
    Returns (processed, stored) counts.
    """
    sub_region = COUNTRY_REGION.get(country, "Unknown")
    geo        = COUNTRY_GEO.get(country, "EMEA")

    # Derive global_region for backward compat storage
    _geo_to_gr = {"NAMERICA": "North America", "APAC": "APAC", "EMEA": "EMEA"}
    global_region = _geo_to_gr.get(geo, geo)

    progress.update(task_id, description=f"[cyan]{country}[/cyan] — discovering...")

    companies = discover_companies(country, client, geo=geo)
    if not companies:
        return 0, 0

    processed = 0
    stored = 0

    progress.update(task_id, total=len(companies), completed=0,
                    description=f"[cyan]{country}[/cyan] — analysing {len(companies)} companies")

    for i, company in enumerate(companies):
        name    = company.get("name", "").strip()
        website = company.get("website", "").strip()
        if not name or not website:
            continue

        progress.update(task_id, completed=i,
                        description=f"[cyan]{country}[/cyan] — {name[:40]}")

        content  = scrape_text(website)
        analysis = analyse_company(client, name, website, content, geo=geo, country=country)
        if not analysis:
            continue
        processed += 1

        if analysis["fit_score"] < min_score:
            continue

        # HQ country correction
        hq_country = analysis.pop("hq_country", country)
        if hq_country and hq_country != country:
            if hq_country not in COUNTRY_REGION:
                console.print(f"  [yellow]Skipping {name}: HQ in {hq_country} (not in target countries)[/yellow]")
                continue
            console.print(f"  [cyan]HQ correction: {name} moved from {country} to {hq_country}[/cyan]")
            actual_country    = hq_country
            actual_sub_region = COUNTRY_REGION[hq_country]
            actual_geo        = COUNTRY_GEO[hq_country]
            _geo_to_gr        = {"NAMERICA": "North America", "APAC": "APAC", "EMEA": "EMEA"}
            actual_global_region = _geo_to_gr.get(actual_geo, actual_geo)
        else:
            actual_country       = country
            actual_sub_region    = sub_region
            actual_geo           = geo
            actual_global_region = global_region
        analysis["discovery_country"] = country

        try:
            with db_conn() as conn:
                upsert_lead(conn, name, website, actual_country, actual_global_region, actual_sub_region, actual_geo, analysis, website)
            stored += 1
        except Exception as e:
            console.print(f"  [red]Storage error for {name}: {e}[/red]")

    progress.update(task_id, completed=len(companies),
                    description=f"[green]{country}[/green] — done ({stored} stored)")
    return processed, stored


def main():
    parser = argparse.ArgumentParser(description="db9 Global Lead Generation Agent")
    parser.add_argument("--geo",           type=str, help="Target geo: EMEA, NAMERICA, APAC, or ALL")
    parser.add_argument("--countries",     type=str, help="Comma-separated country names")
    parser.add_argument("--sub-region",    type=str, help="Sub-region e.g. 'Nordics', 'DACH', 'Southeast Asia'")
    parser.add_argument("--min-score",     type=int, default=MIN_FIT_SCORE,
                        help="Minimum fit score to store a lead (default: %(default)s)")
    # Legacy flags kept for backward compatibility
    parser.add_argument("--global-region", type=str,
                        help="[Legacy] Global region: EMEA, 'North America', APAC")
    args = parser.parse_args()

    if not ANTHROPIC_API_KEY:
        console.print("[red]Error: ANTHROPIC_API_KEY not set in .env[/red]")
        sys.exit(1)
    if not TIDB_CONNECTION_STRING:
        console.print("[red]Error: TIDB_CONNECTION_STRING not set in .env[/red]")
        sys.exit(1)

    # Resolve target countries
    if args.countries:
        countries = [c.strip() for c in args.countries.split(",")]
        geo_label = "Custom"
    elif args.sub_region:
        # Search all geos for the named sub-region
        countries = []
        for geo_data in GEO_REGIONS.values():
            if args.sub_region in geo_data:
                countries = geo_data[args.sub_region]
                break
        if not countries:
            all_sub = [r for gd in GEO_REGIONS.values() for r in gd]
            console.print(f"[red]Unknown sub-region: {args.sub_region}[/red]")
            console.print(f"Valid sub-regions: {', '.join(sorted(all_sub))}")
            sys.exit(1)
        geo_label = args.sub_region
    elif args.geo:
        geo_key = _LEGACY_GEO_MAP.get(args.geo.lower(), args.geo.upper())
        if geo_key == "ALL":
            countries = all_countries()
        else:
            countries = all_countries(geo_key)
            if not countries:
                console.print(f"[red]Unknown geo: {args.geo}[/red]")
                console.print(f"Valid geos: {', '.join(GEO_REGIONS.keys())} or ALL")
                sys.exit(1)
        geo_label = geo_key
    elif args.global_region:
        # Legacy --global-region flag
        geo_key = _LEGACY_GEO_MAP.get(args.global_region.lower(), args.global_region.upper())
        countries = all_countries(geo_key)
        if not countries:
            console.print(f"[red]Unknown global region: {args.global_region}[/red]")
            sys.exit(1)
        geo_label = geo_key
    else:
        countries = all_countries("EMEA")  # default: EMEA for backward compat
        geo_label = "EMEA"

    console.rule(f"[bold blue]db9 Global Lead Generation Agent — {geo_label}[/bold blue]")
    console.print(f"Target: [bold]{len(countries)} countries[/bold]  |  "
                  f"Min fit score: [bold]{args.min_score}[/bold]")
    console.print()

    try:
        conn = get_conn()
        conn.close()
    except Exception as e:
        console.print(f"[red]DB connection failed: {e}[/red]")
        console.print("[yellow]Hint: check TIDB_CONNECTION_STRING in .env[/yellow]")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    total_processed = 0
    total_stored = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        transient=False,
    ) as progress:
        task = progress.add_task("Starting...", total=100)

        for i, country in enumerate(countries):
            progress.update(task, completed=int(i / len(countries) * 100))
            processed, stored = run_country(country, client, args.min_score, progress, task)
            total_processed += processed
            total_stored += stored

        progress.update(task, completed=100, description="[green]All countries complete[/green]")

    console.print()
    table = Table(title="Run Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="bold green")
    table.add_row("Geo", geo_label)
    table.add_row("Countries processed", str(len(countries)))
    table.add_row("Companies analysed", str(total_processed))
    table.add_row("Leads stored", str(total_stored))
    console.print(table)
    console.print("\n[bold]Run the dashboard:[/bold]  uvicorn dashboard.main:app --reload --port 8002\n")


if __name__ == "__main__":
    main()
