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

    # 1. Mode Selection
    mode = Prompt.ask(
        "Select Operation Mode",
        choices=["1. Single ISIN Lookup", "2. Compare EU vs UK", "3. Batch ISINs Check", "4. Search by CFI/MIC"],
        default="1. Single ISIN Lookup",
    )

    compare_mode = ("Compare" in mode)
    batch_mode = ("Batch" in mode)
    search_filter_mode = ("Search" in mode)

    isin = None
    batch_file = None
    cfi_filter = None
    mic_filter = None

    if batch_mode:
        batch_file = Prompt.ask("Enter path to text file containing ISINs (one per line)")
    elif search_filter_mode:
        cfi_filter = Prompt.ask("Enter CFI prefix (e.g. ES, DB, OC) [press Enter to skip]", default="") or None
        mic_filter = Prompt.ask("Enter Venue MIC (e.g. XNAS, XLON, XPAR) [press Enter to skip]", default="") or None
    else:
        while True:
            isin_input = Prompt.ask("Enter ISIN to inspect (e.g. US0378331005, GB0002634946)")
            normalized = normalize_isin(isin_input)
            if is_valid_isin_format(normalized):
                isin = normalized
                break
            else:
                if Confirm.ask(f"'{normalized}' does not match standard 12-char ISIN format. Proceed anyway?", default=True):
                    isin = normalized
                    break

    # 2. Region selection (if not compare mode)
    region = "ALL"
    if not compare_mode:
        region = Prompt.ask(
            "Select Region",
            choices=["EU", "UK", "ALL"],
            default="EU",
        )

    # 3. Date selection
    today_str = date.today().isoformat()
    date_val = Prompt.ask(
        "Enter Publication Date (YYYY-MM-DD)",
        default="2024-01-15",
    )

    # 4. Local Directory / Cache source
    use_local = Confirm.ask("Do you want to scan a custom local folder/archive containing DLTINS files?", default=False)
    local_dir = None
    if use_local:
        local_dir = Prompt.ask("Enter directory path containing DLTINS zip/xml files")

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
