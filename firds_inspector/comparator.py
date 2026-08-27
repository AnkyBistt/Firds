"""
Reconciliation & Diff Comparator Engine for FIRDS Reference Data.
Compares financial instruments between regions (EU vs UK) or against database models,
and diagnoses potential ingestion failure causes.
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, date

from .models import (
    FinancialInstrument,
    DiffResult,
    FieldDiff,
    TradingVenueAttributes,
)
from .utils import logger


class InstrumentComparator:
    """
    Compares two FinancialInstrument records and performs ingestion diagnostics.
    """

    def compare_instruments(
        self,
        source: Optional[FinancialInstrument],
        target: Optional[FinancialInstrument],
        source_label: str = "Source",
        target_label: str = "Target",
    ) -> DiffResult:
        """
        Performs field-by-field diff between two instruments.
        """
        isin = (source.isin if source else (target.isin if target else "UNKNOWN"))
        field_diffs: List[FieldDiff] = []
        diagnostics: List[str] = []

        if source is None and target is None:
            return DiffResult(
                isin=isin,
                source_name=source_label,
                target_name=target_label,
                source_instrument=None,
                target_instrument=None,
                diagnostics=["Both source and target records are missing."],
            )

        if source is None:
            diagnostics.append(f"ISIN exists in {target_label} but is completely missing in {source_label}.")
            return DiffResult(
                isin=isin,
                source_name=source_label,
                target_name=target_label,
                source_instrument=None,
                target_instrument=target,
                field_diffs=[
                    FieldDiff("Record Presence", f"Missing in {source_label}", f"Present in {target_label}", False)
                ],
                diagnostics=diagnostics,
            )

        if target is None:
            diagnostics.append(f"ISIN exists in {source_label} but is completely missing in {target_label}.")
            # Run diagnostics on why target might not have it
            diag_reasons = self.diagnose_potential_ingestion_issues(source)
            diagnostics.extend(diag_reasons)
            return DiffResult(
                isin=isin,
                source_name=source_label,
                target_name=target_label,
                source_instrument=source,
                target_instrument=None,
                field_diffs=[
                    FieldDiff("Record Presence", f"Present in {source_label}", f"Missing in {target_label}", False)
                ],
                diagnostics=diagnostics,
            )

        # 1. Compare Record Type
        field_diffs.append(
            FieldDiff(
                "Record Type",
                source.record_type,
                target.record_type,
                source.record_type == target.record_type,
            )
        )

        # 2. Compare General Attributes
        g_src = source.general
        g_tgt = target.general

        self._compare_field(field_diffs, "Full Name", g_src.full_name, g_tgt.full_name)
        self._compare_field(field_diffs, "Short Name", g_src.short_name, g_tgt.short_name)
        self._compare_field(field_diffs, "CFI Code", g_src.cfi_code, g_tgt.cfi_code)
        self._compare_field(field_diffs, "Currency", g_src.currency, g_tgt.currency)
        self._compare_field(field_diffs, "Commodity Deriv Ind", g_src.commodity_derivative_indicator, g_tgt.commodity_derivative_indicator)
        self._compare_field(field_diffs, "Issuer LEI", g_src.issuer_lei, g_tgt.issuer_lei)

        # 3. Compare Trading Venues (MICs)
        src_mics = {tv.mic: tv for tv in source.trading_venues}
        tgt_mics = {tv.mic: tv for tv in target.trading_venues}

        all_mics = sorted(set(src_mics.keys()) | set(tgt_mics.keys()))
        for mic in all_mics:
            tv_src = src_mics.get(mic)
            tv_tgt = tgt_mics.get(mic)

            if tv_src and not tv_tgt:
                field_diffs.append(FieldDiff(f"Trading Venue ({mic})", "Listed", "Not Listed", False, f"Venue only in {source_label}"))
            elif tv_tgt and not tv_src:
                field_diffs.append(FieldDiff(f"Trading Venue ({mic})", "Not Listed", "Listed", False, f"Venue only in {target_label}"))
            elif tv_src and tv_tgt:
                # Compare venue specific fields
                self._compare_field(field_diffs, f"{mic} First Trade Date", tv_src.first_trade_date, tv_tgt.first_trade_date)
                self._compare_field(field_diffs, f"{mic} Termination Date", tv_src.termination_date, tv_tgt.termination_date)
                self._compare_field(field_diffs, f"{mic} Admission Approval", tv_src.admission_approval_date, tv_tgt.admission_approval_date)

        # 4. Compare Technical Attributes
        if source.technical or target.technical:
            rca_src = source.technical.relevant_competent_authority if source.technical else None
            rca_tgt = target.technical.relevant_competent_authority if target.technical else None
            self._compare_field(field_diffs, "Relevant Competent Authority", rca_src, rca_tgt)

            pbl_src = source.technical.publication_date if source.technical else None
            pbl_tgt = target.technical.publication_date if target.technical else None
            self._compare_field(field_diffs, "Publication Date", pbl_src, pbl_tgt)

        # Ingestion diagnostics
        diagnostics.extend(self.diagnose_potential_ingestion_issues(source))

        return DiffResult(
            isin=isin,
            source_name=source_label,
            target_name=target_label,
            source_instrument=source,
            target_instrument=target,
            field_diffs=field_diffs,
            diagnostics=diagnostics,
        )

    def _compare_field(self, diff_list: List[FieldDiff], field_name: str, val_src: Any, val_tgt: Any):
        # Normalize strings for comparison
        is_match = (val_src == val_tgt)
        if isinstance(val_src, str) and isinstance(val_tgt, str):
            is_match = (val_src.strip() == val_tgt.strip())
        
        diff_list.append(
            FieldDiff(
                field_name=field_name,
                source_value=val_src if val_src is not None else "<empty>",
                target_value=val_tgt if val_tgt is not None else "<empty>",
                is_match=is_match,
            )
        )

    def diagnose_potential_ingestion_issues(self, instrument: FinancialInstrument) -> List[str]:
        """
        Analyzes the instrument data and flags common reasons why daily ETL pipelines drop records.
        """
        reasons = []

        # 1. Check Record Type
        if instrument.record_type == "CANC":
            reasons.append("[WARNING] Record type is 'CANC' (Cancellation). Ingestion pipelines often discard or purge cancelled records.")
        elif instrument.record_type == "TERMN":
            reasons.append("[WARNING] Record type is 'TERMN' (Termination). Instrument may have been marked inactive or skipped.")

        # 2. Check Termination Date
        today_str = date.today().isoformat()
        for tv in instrument.trading_venues:
            if tv.termination_date:
                try:
                    term_dt = tv.termination_date.split("T")[0]
                    if term_dt < today_str:
                        reasons.append(f"[NOTE] Venue {tv.mic} has expired termination date: {tv.termination_date}. Some ETL filters out expired venues.")
                except Exception:
                    pass

        # 3. Missing Mandatory Fields
        if not instrument.general.issuer_lei:
            reasons.append("[CAUTION] Issuer LEI is missing. Databases with NOT NULL or foreign key constraints on LEI will fail to insert.")

        if not instrument.general.cfi_code:
            reasons.append("[CAUTION] CFI code is missing. Classification-based ingestion pipelines may reject unclassified instruments.")

        if not instrument.trading_venues:
            reasons.append("[WARNING] No Trading Venues (MICs) attached. Pipeline expecting at least one venue mapping may skip.")

        # 4. Multi-Venue complexity
        if len(instrument.trading_venues) > 1:
            mics = ", ".join(tv.mic for tv in instrument.trading_venues)
            reasons.append(f"[INFO] Instrument is multi-listed across {len(instrument.trading_venues)} venues ({mics}). Check for primary MIC mapping rules.")

        return reasons
