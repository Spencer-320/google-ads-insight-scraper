from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.traceback import install

# Local imports
from parsers.ads_extractor import extract_from_ad_urls
from parsers.insights_extractor import build_insights_from_ads_or_search
from storage.save_ads import save_ads_records
from storage.save_insights import save_insights_records

app = typer.Typer(add_completion=False, help="Google Ads & Insight Scraper CLI")
console = Console()
install(show_locals=False)

def repo_root() -> Path:
    # src/ is one directory deep from repo root
    return Path(__file__).resolve().parent.parent

def load_text_lines(path: Path) -> List[str]:
    if not path.exists():
        return []
    return [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]

def load_settings() -> dict:
    cfg_path = repo_root() / "src" / "config" / "settings.json"
    if cfg_path.exists():
        with cfg_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    # Sensible defaults if missing
    return {
        "user_agent": "Mozilla/5.0 (compatible; Bitbash-GAT-Extractor/1.0)",
        "request_timeout_sec": 15,
        "max_retries": 3,
        "output": {
            "ads_json": str(repo_root() / "data" / "output" / "ads_output.json"),
            "insights_json": str(repo_root() / "data" / "output" / "insights_output.json"),
        },
    }

@app.command()
def run(
    ads_file: Optional[Path] = typer.Option(
        None,
        "--ads-file",
        "-a",
        help="Path to a file containing ad URLs (one per line). If provided, takes priority over --start-urls.",
    ),
    start_urls_file: Optional[Path] = typer.Option(
        None,
        "--start-urls",
        "-s",
        help="Path to a file containing Google Ads Transparency search URLs (one per line).",
    ),
    write_insights: bool = typer.Option(
        True,
        "--insights/--no-insights",
        help="Whether to compute and write insights output.",
    ),
):
    """
    Execute scraping flow:

    - If an ads file is present (or data/input/batch_ads.txt), extract detailed ads.
    - Else if a start URLs file is present (or data/input/start_urls.txt), derive insights.
    - Always write outputs to data/output/*.json (or as configured).
    """
    settings = load_settings()
    output_paths = settings.get("output", {})
    default_ads_file = repo_root() / "data" / "input" / "batch_ads.txt"
    default_start_file = repo_root() / "data" / "input" / "start_urls.txt"

    ads_file = ads_file or default_ads_file
    start_urls_file = start_urls_file or default_start_file

    batch_ads = load_text_lines(ads_file)
    start_urls = load_text_lines(start_urls_file)

    if not batch_ads and not start_urls:
        console.print(
            "[bold red]No input provided[/bold red]. "
            "Provide ad URLs in data/input/batch_ads.txt or search URLs in data/input/start_urls.txt, "
            "or pass --ads-file/--start-urls.",
        )
        raise typer.Exit(code=1)

    # Ads extraction (priority)
    ads_records = []
    if batch_ads:
        console.print(f"[bold cyan]Processing {len(batch_ads)} ad URL(s)[/bold cyan]")
        ads_records = extract_from_ad_urls(
            batch_ads,
            user_agent=settings.get("user_agent"),
            timeout_sec=float(settings.get("request_timeout_sec", 15)),
            max_retries=int(settings.get("max_retries", 3)),
        )
        save_ads_records(ads_records, Path(output_paths.get("ads_json", "")) or repo_root() / "data" / "output" / "ads_output.json")
        console.print(f"[green]Saved ads to[/green] {output_paths.get('ads_json')}")

    # Insights (from ads when available; otherwise from start_urls)
    if write_insights:
        console.print("[bold cyan]Computing insights[/bold cyan]")
        insights = build_insights_from_ads_or_search(
            ads_records=ads_records,
            start_urls=start_urls,
        )
        save_insights_records(insights, Path(output_paths.get("insights_json", "")) or repo_root() / "data" / "output" / "insights_output.json")
        console.print(f"[green]Saved insights to[/green] {output_paths.get('insights_json')}")

        # nice summary table
        tbl = Table(title="Insights Summary", show_lines=False)
        tbl.add_column("Metric", style="bold")
        tbl.add_column("Value")
        tbl.add_row("Total Ads", str(insights.get("insights_total_ads", 0)))
        tbl.add_row("Advertisers", str(len(insights.get("insights_advertisers", []))))
        tbl.add_row("Regions", str(len(insights.get("insights_regions", []))))
        tbl.add_row("Total Spend (est.)", str(insights.get("insights_total_ads_spend", 0)))
        console.print(tbl)

    console.print("[bold green]Done.[/bold green]")

if __name__ == "__main__":
    try:
        app()
    except Exception as e:
        Console().print(f"[bold red]Fatal error:[/bold red] {e}")
        sys.exit(1)