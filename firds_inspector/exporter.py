"""
Exporter for FIRDS inspection and reconciliation reports (JSON, CSV, Markdown).
"""

import json
import csv
from pathlib import Path
from typing import List, Union, Optional

from .models import FinancialInstrument, DiffResult
from .utils import logger


class ReportExporter:
    """
    Exports instrument records and diff reconciliation results to various formats.
    """

    @staticmethod
    def export_instruments_json(instruments: List[FinancialInstrument], output_path: Union[str, Path]):
        """Exports a list of FinancialInstrument objects to JSON."""
        data = [inst.to_dict() for inst in instruments]
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Exported {len(instruments)} instrument(s) to JSON: {output_path}")

    @staticmethod
    def export_instruments_csv(instruments: List[FinancialInstrument], output_path: Union[str, Path]):
        """Exports instruments to flattened CSV format."""
        if not instruments:
            return

        fieldnames = [
            "isin",
            "region",
            "record_type",
            "full_name",
            "short_name",
            "cfi_code",
            "cfi_description",
            "currency",
            "commodity_derivative_indicator",
            "issuer_lei",
            "trading_venues",
            "competent_authority",
            "publication_date",
            "source_file",
        ]

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for inst in instruments:
                g = inst.general
                t = inst.technical
                venues_str = ", ".join(tv.mic for tv in inst.trading_venues)

                row = {
                    "isin": inst.isin,
                    "region": inst.region,
                    "record_type": inst.record_type,
                    "full_name": g.full_name,
                    "short_name": g.short_name,
                    "cfi_code": g.cfi_code,
                    "cfi_description": g.cfi_description,
                    "currency": g.currency,
                    "commodity_derivative_indicator": g.commodity_derivative_indicator,
                    "issuer_lei": g.issuer_lei,
                    "trading_venues": venues_str,
                    "competent_authority": t.relevant_competent_authority if t else "",
                    "publication_date": t.publication_date if t else "",
                    "source_file": inst.source_file,
                }
                writer.writerow(row)

        logger.info(f"Exported {len(instruments)} instrument(s) to CSV: {output_path}")

    @staticmethod
    def export_diff_markdown(diff: DiffResult, output_path: Union[str, Path]):
        """Exports a DiffResult to Markdown format."""
        lines = [
            f"# FIRDS Reconciliation Report: {diff.isin}",
            "",
            f"- **Source ({diff.source_name})**: {'Found' if diff.source_instrument else 'MISSING'}",
            f"- **Target ({diff.target_name})**: {'Found' if diff.target_instrument else 'MISSING'}",
            f"- **Status**: {'DISCREPANCIES FOUND' if diff.has_differences else 'IDENTICAL'}",
            "",
            "## Field Level Comparison",
            "",
            f"| Field | {diff.source_name} | {diff.target_name} | Match | Notes |",
            "| --- | --- | --- | --- | --- |",
        ]

        for fd in diff.field_diffs:
            match_icon = "MATCH" if fd.is_match else "DIFF"
            lines.append(f"| {fd.field_name} | {fd.source_value} | {fd.target_value} | {match_icon} | {fd.description or ''} |")

        if diff.diagnostics:
            lines.extend([
                "",
                "## Ingestion Diagnostics & Failure Causes",
                "",
            ])
            for diag in diff.diagnostics:
                lines.append(f"- {diag}")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info(f"Exported diff report to Markdown: {output_path}")
