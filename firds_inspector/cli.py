"""
Main Command Line Interface for FIRDS Inspector & Reconciler.
"""

import sys
import argparse
from pathlib import Path
from typing import List, Optional, Set
from datetime import date

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns

from .models import FinancialInstrument, DiffResult
from .xml_parser import DltinsXmlParser
from .esma_client import EsmaFirdsClient
from .fca_client import FcaFirdsClient
from .comparator import InstrumentComparator
from .db_inspector import DatabaseInspector
from .exporter import ReportExporter
from .interactive import run_interactive_wizard
from .utils import normalize_isin, is_valid_isin_format, format_date_str, logger

console = Console()


def display_instrument_details(inst: FinancialInstrument):
    """
    Renders instrument details with rich tables, badges, and decoded attributes.
    """
    rec_type_color = "green" if inst.record_type == "NEWT" else ("yellow" if inst.record_type == "MODI" else "red")
    region_color = "blue" if inst.region == "EU" else "magenta"

    header_text = Text()
    header_text.append(f"ISIN: {inst.isin}  ", style="bold white")
    header_text.append(f"[{inst.region}]  ", style=f"bold {region_color}")
    header_text.append(f"[{inst.record_type}]  ", style=f"bold {rec_type_color}")
    header_text.append(f"Source: {inst.source_file or 'Unknown'}", style="dim")

    console.print(Panel(header_text, title="Financial Instrument Details", border_style="cyan"))

    # 1. General Attributes Table
    gen_table = Table(title="General Attributes", show_header=True, header_style="bold cyan")
    gen_table.add_column("Attribute", style="dim", width=24)
    gen_table.add_column("Value", style="bold white")

    g = inst.general
    gen_table.add_row("Full Name", g.full_name or "N/A")
    gen_table.add_row("Short Name", g.short_name or "N/A")
    gen_table.add_row("CFI Code", f"{g.cfi_code or 'N/A'}")
    if g.cfi_description:
        gen_table.add_row("CFI Classification", f"[italic green]{g.cfi_description}[/italic green]")
    gen_table.add_row("Notional Currency", g.currency or "N/A")
    gen_table.add_row("Commodity Derivative", str(g.commodity_derivative_indicator) if g.commodity_derivative_indicator is not None else "N/A")
    gen_table.add_row("Issuer LEI", g.issuer_lei or "[italic red]Missing[/italic red]")

    console.print(gen_table)

    # 2. Trading Venues Table
    if inst.trading_venues:
        venue_table = Table(title=f"Trading Venues ({len(inst.trading_venues)})", show_header=True, header_style="bold magenta")
        venue_table.add_column("MIC", style="bold yellow")
        venue_table.add_column("Issuer Req", justify="center")
        venue_table.add_column("First Trade Date")
        venue_table.add_column("Termination Date")
        venue_table.add_column("Admission Approval")

        for tv in inst.trading_venues:
            term_str = tv.termination_date or "Active"
            term_style = "red" if tv.termination_date else "green"
            venue_table.add_row(
                tv.mic,
                str(tv.issuer_request) if tv.issuer_request is not None else "N/A",
                format_date_str(tv.first_trade_date),
                f"[{term_style}]{format_date_str(tv.termination_date)}[/{term_style}]",
                format_date_str(tv.admission_approval_date),
            )
        console.print(venue_table)
    else:
        console.print("[dim yellow]No Trading Venues associated with this record.[/dim yellow]")

    # 3. Technical Attributes
    if inst.technical:
        tech_table = Table(title="Technical Attributes", show_header=True, header_style="bold blue")
        tech_table.add_column("Attribute", style="dim", width=24)
        tech_table.add_column("Value")

        t = inst.technical
        tech_table.add_row("Relevant Competent Authority", t.relevant_competent_authority or "N/A")
        tech_table.add_row("Publication Date", format_date_str(t.publication_date))
        console.print(tech_table)

    console.print()


def display_diff_result(diff: DiffResult):
    """
    Renders reconciliation side-by-side diff table with color highlights and diagnostics.
    """
    status_text = Text()
    status_text.append(f"Reconciliation Diff: {diff.isin}\n", style="bold cyan")
    status_text.append(f"Comparing: [{diff.source_name}] vs [{diff.target_name}]\n", style="bold")
    if diff.has_differences:
        status_text.append("STATUS: DISCREPANCIES DETECTED", style="bold red")
    else:
        status_text.append("STATUS: PERFECT MATCH (Identical)", style="bold green")

    console.print(Panel(status_text, border_style="red" if diff.has_differences else "green"))

    # Table of fields
    table = Table(show_header=True, header_style="bold white")
    table.add_column("Field / Attribute", style="cyan", width=28)
    table.add_column(diff.source_name, justify="left")
    table.add_column(diff.target_name, justify="left")
    table.add_column("Match Status", justify="center", width=14)

    for fd in diff.field_diffs:
        match_str = "[bold green]MATCH[/bold green]" if fd.is_match else "[bold red]DIFF[/bold red]"
        src_val_str = str(fd.source_value)
        tgt_val_str = str(fd.target_value)
        
        if not fd.is_match:
            src_val_str = f"[yellow]{src_val_str}[/yellow]"
            tgt_val_str = f"[yellow]{tgt_val_str}[/yellow]"

        table.add_row(fd.field_name, src_val_str, tgt_val_str, match_str)

    console.print(table)

    # Diagnostics panel
    if diff.diagnostics:
        diag_text = Text()
        for d in diff.diagnostics:
            if "WARNING" in d or "CAUTION" in d:
                diag_text.append(f"- {d}\n", style="bold yellow")
            elif "NOTE" in d or "INFO" in d:
                diag_text.append(f"- {d}\n", style="cyan")
            else:
                diag_text.append(f"- {d}\n", style="white")

        console.print(Panel(diag_text, title="[DIAGNOSTICS] Ingestion Root-Cause Analysis", border_style="yellow"))

    console.print()


def search_files_for_instruments(
    files: List[Path],
    region: str,
    target_isins: Optional[Set[str]] = None,
    cfi_filter: Optional[str] = None,
    mic_filter: Optional[str] = None,
) -> List[FinancialInstrument]:
    """
    Parses a list of files using the DltinsXmlParser and returns matching instruments.
    """
    parser = DltinsXmlParser(region=region)
    found = []
    for f in files:
        if f.exists():
            for inst in parser.stream_file(f, target_isins=target_isins, cfi_filter=cfi_filter, mic_filter=mic_filter):
                found.append(inst)
    return found


def main(args_list: Optional[List[str]] = None):
    parser = argparse.ArgumentParser(
        description="FIRDS DLTINS Reference Data Inspector & Reconciler (ESMA / FCA UK)",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument("--isin", type=str, help="ISIN to inspect (e.g. US0378331005)")
    parser.add_argument("--file", type=str, help="Batch file with list of ISINs (one per line)")
    parser.add_argument("--region", type=str, choices=["EU", "UK", "ALL", "eu", "uk", "all"], default="EU", help="Target region (EU, UK, or ALL)")
    parser.add_argument("--date", type=str, default=date.today().isoformat(), help="Publication Date in YYYY-MM-DD format (default: today)")
    parser.add_argument("--dltins-dir", type=str, help="Path to local directory containing DLTINS zip/xml files")
    parser.add_argument("--compare", action="store_true", help="Compare ISIN between EU and UK DLTINS files")
    parser.add_argument("--sqlite-db", type=str, help="Path to SQLite database to compare DLTINS record against ingested DB table")
    parser.add_argument("--cfi-filter", type=str, help="Filter by CFI code prefix (e.g. ES, DB, OC)")
    parser.add_argument("--mic-filter", type=str, help="Filter by Trading Venue MIC (e.g. XNAS, XLON)")
    parser.add_argument("--export-json", type=str, help="Path to export search or diff results as JSON")
    parser.add_argument("--export-csv", type=str, help="Path to export instruments list as CSV")
    parser.add_argument("--export-md", type=str, help="Path to export reconciliation report as Markdown")
    parser.add_argument("--interactive", action="store_true", help="Launch step-by-step interactive wizard")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose debug logging")

    args = parser.parse_args(args_list)

    if args.interactive or (not args.isin and not args.file and not args.cfi_filter and not args.mic_filter and len(sys.argv) == 1):
        wizard_config = run_interactive_wizard()
        args.isin = wizard_config.get("isin")
        args.region = wizard_config.get("region") or "EU"
        args.date = wizard_config.get("date")
        args.compare = wizard_config.get("compare", False)
        args.file = wizard_config.get("batch_file")
        args.cfi_filter = wizard_config.get("cfi_filter")
        args.mic_filter = wizard_config.get("mic_filter")
        args.dltins_dir = wizard_config.get("dltins_dir")
        args.export_json = wizard_config.get("export_json")

    region = args.region.upper()
    target_date = args.date.strip()
    target_isins: Set[str] = set()

    if args.isin:
        target_isins.add(normalize_isin(args.isin))

    if args.file:
        file_path = Path(args.file)
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    cleaned = normalize_isin(line)
                    if cleaned:
                        target_isins.add(cleaned)
            console.print(f"[cyan]Loaded {len(target_isins)} target ISIN(s) from {args.file}[/cyan]")
        else:
            console.print(f"[bold red]File not found: {args.file}[/bold red]")
            return

    # 1. Resolve files for EU
    eu_files: List[Path] = []
    if region in ("EU", "ALL") or args.compare:
        if args.dltins_dir:
            dir_path = Path(args.dltins_dir)
            eu_files.extend(list(dir_path.glob("*.zip")) + list(dir_path.glob("*.xml")))
        else:
            esma_client = EsmaFirdsClient()
            eu_files = esma_client.get_or_download_files_for_date(target_date)

    # 2. Resolve files for UK
    uk_files: List[Path] = []
    if region in ("UK", "ALL") or args.compare:
        if args.dltins_dir:
            dir_path = Path(args.dltins_dir)
            uk_files.extend(list(dir_path.glob("*UK*")) + list(dir_path.glob("*uk*")) + list(dir_path.glob("*.zip")) + list(dir_path.glob("*.xml")))
        else:
            fca_client = FcaFirdsClient()
            uk_files = fca_client.find_files_for_date(target_date)

    # 3. Handle Single or Batch Lookup
    if not args.compare:
        files_to_scan = []
        if region == "EU":
            files_to_scan = [(f, "EU") for f in eu_files]
        elif region == "UK":
            files_to_scan = [(f, "UK") for f in uk_files]
        else:
            files_to_scan = [(f, "EU") for f in eu_files] + [(f, "UK") for f in uk_files]

        all_found: List[FinancialInstrument] = []
        for file_path, reg in files_to_scan:
            parser = DltinsXmlParser(region=reg)
            for inst in parser.stream_file(
                file_path,
                target_isins=target_isins if target_isins else None,
                cfi_filter=args.cfi_filter,
                mic_filter=args.mic_filter,
            ):
                all_found.append(inst)

        if not all_found:
            console.print(f"[bold yellow]No instruments matching criteria found in {region} files for date {target_date}.[/bold yellow]")
            if target_isins:
                console.print(f"[dim]Searched ISINs: {', '.join(target_isins)}[/dim]")
        else:
            console.print(f"[bold green]Found {len(all_found)} matching instrument record(s):[/bold green]\n")
            for inst in all_found:
                display_instrument_details(inst)

        # Exporters
        if args.export_json:
            ReportExporter.export_instruments_json(all_found, args.export_json)
            console.print(f"[green]Exported JSON results to {args.export_json}[/green]")
        if args.export_csv:
            ReportExporter.export_instruments_csv(all_found, args.export_csv)
            console.print(f"[green]Exported CSV results to {args.export_csv}[/green]")

    # 4. Handle Comparison Mode (EU vs UK or DLTINS vs DB)
    else:
        comparator = InstrumentComparator()
        target_list = list(target_isins) if target_isins else []

        if not target_list:
            console.print("[bold red]Please provide at least one --isin or --file to compare.[/bold red]")
            return

        for isin_val in target_list:
            inst_eu: Optional[FinancialInstrument] = None
            inst_uk: Optional[FinancialInstrument] = None

            # Parse EU
            eu_found = search_files_for_instruments(eu_files, "EU", target_isins={isin_val})
            if eu_found:
                inst_eu = eu_found[0]

            # Compare against DB if specified, otherwise against UK files
            if args.sqlite_db:
                db_inspector = DatabaseInspector()
                db_inst = db_inspector.query_sqlite(args.sqlite_db, isin_val)
                diff = comparator.compare_instruments(
                    source=inst_eu,
                    target=db_inst,
                    source_label="DLTINS (EU)",
                    target_label="Database (Ingested)",
                )
                display_diff_result(diff)
                if args.export_md:
                    ReportExporter.export_diff_markdown(diff, args.export_md)
            else:
                uk_found = search_files_for_instruments(uk_files, "UK", target_isins={isin_val})
                if uk_found:
                    inst_uk = uk_found[0]

                diff = comparator.compare_instruments(
                    source=inst_eu,
                    target=inst_uk,
                    source_label="ESMA (EU)",
                    target_label="FCA (UK)",
                )
                display_diff_result(diff)
                if args.export_md:
                    ReportExporter.export_diff_markdown(diff, args.export_md)


if __name__ == "__main__":
    main()
