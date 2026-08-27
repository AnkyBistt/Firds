"""
Interactive Wizard for FIRDS Inspector Console Application.
Guides the user step-by-step through ISIN lookup, region selection, and comparison.
"""

from typing import Optional, Dict, Any
from datetime import date
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.text import Text

from .utils import normalize_isin, is_valid_isin_format

console = Console()


def run_interactive_wizard() -> Dict[str, Any]:
    """
    Runs the interactive CLI wizard and returns the configuration dictionary.
    """
    console.print(
        Panel(
            Text.from_markup(
                "[bold cyan]FIRDS DLTINS Reference Data Inspector & Reconciler[/bold cyan]\n"
                "[dim]Search, inspect, and reconcile ESMA (EU) & FCA (UK) DLTINS ISO 20022 reference data[/dim]"
            ),
            border_style="cyan",
        )
    )

    console.print("\n[bold]Select an Operation Mode:[/bold]")
    console.print("  [cyan]1[/cyan] - Single ISIN Lookup")
    console.print("  [cyan]2[/cyan] - Compare EU vs UK (Reconciliation Diff)")
    console.print("  [cyan]3[/cyan] - Batch ISINs Check (from .txt file)")
    console.print("  [cyan]4[/cyan] - Search by CFI Code or Trading Venue MIC\n")

    # 1. Mode Selection - accepts 1, 2, 3, 4
    choice = Prompt.ask(
        "Enter mode number",
        choices=["1", "2", "3", "4"],
        default="1",
    )

    compare_mode = (choice == "2")
    batch_mode = (choice == "3")
    search_filter_mode = (choice == "4")

    isin = None
    batch_file = None
    cfi_filter = None
    mic_filter = None

    if batch_mode:
        batch_file = Prompt.ask("Enter path to text file containing ISINs (one per line)")
    elif search_filter_mode:
        cfi_filter = Prompt.ask("Enter CFI prefix (e.g. ES, DB, DC, OC) [press Enter to skip]", default="") or None
        mic_filter = Prompt.ask("Enter Venue MIC (e.g. XNAS, XLON, XPAR, WBAH) [press Enter to skip]", default="") or None
    else:
        while True:
            isin_input = Prompt.ask("Enter ISIN to inspect", default="AT0000A0SL91")
            normalized = normalize_isin(isin_input)
            if is_valid_isin_format(normalized):
                isin = normalized
                break
            else:
                if Confirm.ask(f"'{normalized}' does not match standard 12-char ISIN format. Proceed anyway?", default=True):
                    isin = normalized
                    break

    # 2. Region selection (if not compare mode)
    region = "EU"
    if not compare_mode:
        reg_input = Prompt.ask(
            "Select Region (EU / UK / ALL)",
            choices=["EU", "UK", "ALL", "eu", "uk", "all"],
            default="EU",
        )
        region = reg_input.upper()

    # 3. Date selection
    date_val = Prompt.ask(
        "Enter Publication Date (YYYY-MM-DD)",
        default="2024-01-15",
    )

    # 4. Local Directory / Cache source
    use_local = Confirm.ask("Do you want to scan a custom local folder/archive containing DLTINS files?", default=False)
    local_dir = None
    if use_local:
        local_dir = Prompt.ask("Enter directory path containing DLTINS zip/xml files", default="sample_data")

    # 5. Export option
    export_json = Prompt.ask("Export results to JSON file? (leave empty to skip)", default="") or None

    return {
        "isin": isin,
        "region": region,
        "date": date_val,
        "compare": compare_mode,
        "batch_file": batch_file,
        "cfi_filter": cfi_filter,
        "mic_filter": mic_filter,
        "dltins_dir": local_dir,
        "export_json": export_json,
    }
