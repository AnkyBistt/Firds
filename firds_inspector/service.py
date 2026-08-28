"""
Service layer for FIRDS Reference Data operations.
Encapsulates DLTINS XML retrieval, parsing, search, and cross-region reconciliation for API endpoints.
"""

import os
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

from .models import (
    FinancialInstrument,
    GeneralAttributes,
    TradingVenueAttributes,
    TechnicalAttributes,
    DiffResult,
)
from .cfi_decoder import decode_cfi
from .xml_parser import DltinsXmlParser
from .esma_client import EsmaFirdsClient
from .fca_client import FcaFirdsClient
from .comparator import InstrumentComparator
from .utils import normalize_isin, is_valid_isin_format, is_valid_date_format, format_date_str, logger


class FirdsService:
    """
    Core service handling reference data lookups, live ESMA/FCA ingestion, and reconciliation.
    """

    def __init__(self, cache_dir: Optional[Path] = None, data_dir: Optional[Path] = None):
        self.cache_dir = cache_dir
        self.data_dir = data_dir or (Path(os.getenv("FIRDS_DATA_DIR")) if os.getenv("FIRDS_DATA_DIR") else None)
        self.esma_client = EsmaFirdsClient(cache_dir=self.cache_dir)
        self.fca_client = FcaFirdsClient(cache_dir=self.cache_dir, local_uk_dir=self.data_dir)
        self.comparator = InstrumentComparator()

    def resolve_files_for_date(self, region: str, date_str: str, custom_dir: Optional[str] = None) -> List[Tuple[Path, str]]:
        """
        Locates DLTINS files for the given region and date.
        Returns list of tuples (file_path, region).
        """
        region = region.upper()
        resolved_files: List[Tuple[Path, str]] = []

        # 1. Custom directory check (only if explicitly specified)
        if custom_dir:
            target_dir = Path(custom_dir)
            if target_dir.exists():
                date_clean = date_str.replace("-", "")
                files = list(target_dir.glob(f"*{date_clean}*")) or list(target_dir.glob("*.zip")) + list(target_dir.glob("*.xml"))
                for f in files:
                    if f.suffix.lower() in (".zip", ".xml", ".gz"):
                        reg = "UK" if "uk" in f.name.lower() else "EU"
                        if region in ("ALL", reg):
                            resolved_files.append((f, reg))
                if resolved_files:
                    return resolved_files

        # 2. ESMA (EU) Live / Cached Lookup
        if region in ("EU", "ALL"):
            eu_files = self.esma_client.get_or_download_files_for_date(date_str)
            for f in eu_files:
                resolved_files.append((f, "EU"))

        # 3. FCA (UK) Lookup
        if region in ("UK", "ALL"):
            uk_files = self.fca_client.find_files_for_date(date_str)
            for f in uk_files:
                resolved_files.append((f, "UK"))

        return resolved_files

    def search_instruments(
        self,
        isin: str,
        date_str: str,
        region: str = "EU",
        custom_dir: Optional[str] = None,
        cfi_filter: Optional[str] = None,
        mic_filter: Optional[str] = None,
    ) -> List[FinancialInstrument]:
        """
        Searches for an ISIN across resolved DLTINS files for a specific date and region.
        """
        normalized_isin = normalize_isin(isin)
        target_set = {normalized_isin} if normalized_isin else None

        files_with_region = self.resolve_files_for_date(region, date_str, custom_dir)
        if not files_with_region:
            logger.warning(f"No DLTINS files found or downloaded for {region} on {date_str}")
            return []

        results: List[FinancialInstrument] = []
        for file_path, reg in files_with_region:
            parser = DltinsXmlParser(region=reg)
            for inst in parser.stream_file(
                file_path,
                target_isins=target_set,
                cfi_filter=cfi_filter,
                mic_filter=mic_filter,
            ):
                results.append(inst)

        return results

    def compare_instrument(
        self,
        isin: str,
        date_str: str,
        custom_dir: Optional[str] = None,
    ) -> DiffResult:
        """
        Performs cross-region comparison for an ISIN across EU and UK files.
        """
        normalized_isin = normalize_isin(isin)
        
        # Search EU
        eu_results = self.search_instruments(normalized_isin, date_str, region="EU", custom_dir=custom_dir)
        inst_eu = eu_results[0] if eu_results else None

        # Search UK
        uk_results = self.search_instruments(normalized_isin, date_str, region="UK", custom_dir=custom_dir)
        inst_uk = uk_results[0] if uk_results else None

        diff = self.comparator.compare_instruments(
            source=inst_eu,
            target=inst_uk,
            source_label="ESMA (EU)",
            target_label="FCA (UK)",
        )
        return diff

    def lookup_isin_direct(
        self,
        isin: str,
        region: str = "EU",
        custom_dir: Optional[str] = None,
    ) -> List[FinancialInstrument]:
        """
        Directly queries the ESMA master FIRDS database core by ISIN without needing a date.
        Returns all associated instrument venues and classification details.
        """
        clean_isin = normalize_isin(isin)
        if not clean_isin:
            return []

        # 1. Custom directory check (if custom_dir is provided)
        if custom_dir and isinstance(custom_dir, (str, Path)) and Path(custom_dir).exists():
            parser = DltinsXmlParser(region=region)
            found = parser.find_isin_in_directory(Path(custom_dir), clean_isin)
            if found:
                return found

        instruments: List[FinancialInstrument] = []

        # 2. Query ESMA Solr master database core (esma_registers_firds)
        docs = self.esma_client.lookup_isin_in_register(clean_isin)
        if docs:
            # Group records and extract venues
            general_data = None
            trading_venues: List[TradingVenueAttributes] = []
            seen_mics = set()
            tech_attr = None
            source_rec_type = "REGISTERED"

            for doc in docs:
                mic = doc.get("mic") or doc.get("rca_mic")
                if mic and mic not in seen_mics:
                    seen_mics.add(mic)
                    issr_req = (doc.get("mrkt_issr_trdng_rqst_flag", "").lower() in ("yes", "true", "1"))
                    trading_venues.append(
                        TradingVenueAttributes(
                            mic=mic,
                            issuer_request=issr_req,
                            first_trade_date=doc.get("mrkt_trdng_start_date"),
                            termination_date=doc.get("mrkt_trdng_trmination_date"),
                            admission_approval_date=doc.get("valid_from_date"),
                            custom_attributes={
                                "status": doc.get("status_label") or doc.get("status"),
                                "seniority": doc.get("bnd_seniority"),
                                "maturity_date": doc.get("bnd_maturity_date"),
                                "underlying_isin": doc.get("drv_underlng_isin"),
                            },
                        )
                    )

                if general_data is None or not general_data.full_name:
                    full_name = doc.get("gnr_full_name") or doc.get("full_name") or doc.get("instrm_full_name")
                    short_name = doc.get("gnr_short_name") or doc.get("short_name")
                    cfi_code = doc.get("gnr_cfi_code") or doc.get("cfi_code")
                    cfi_info = decode_cfi(cfi_code) if cfi_code else None
                    cfi_desc = cfi_info["summary"] if cfi_info else None
                    currency = doc.get("gnr_notional_curr_code") or doc.get("currency")
                    comm_flag = (doc.get("gnr_comm_derivative_flag", "").lower() in ("yes", "true", "1"))
                    lei = doc.get("lei") or doc.get("issuer_lei")

                    status_val = doc.get("status", "")
                    if status_val == "TERM":
                        source_rec_type = "TERMN"
                    elif status_val == "CANC":
                        source_rec_type = "CANC"
                    elif status_val == "NEWT" or doc.get("latest_received_flag") == "1":
                        source_rec_type = "NEWT"

                    general_data = GeneralAttributes(
                        isin=clean_isin,
                        full_name=full_name,
                        short_name=short_name,
                        cfi_code=cfi_code,
                        cfi_description=cfi_desc,
                        currency=currency,
                        commodity_derivative_indicator=comm_flag,
                        issuer_lei=lei,
                        debt_seniority=doc.get("bnd_seniority"),
                        expiry_date=doc.get("bnd_maturity_date"),
                        underlying_isin=doc.get("drv_underlng_isin"),
                    )

                    tech_attr = TechnicalAttributes(
                        relevant_competent_authority=doc.get("upcoming_rca") or doc.get("rca_mic"),
                        publication_date=doc.get("publication_date"),
                    )

            if general_data:
                inst = FinancialInstrument(
                    general=general_data,
                    record_type=source_rec_type,
                    trading_venues=trading_venues,
                    technical=tech_attr,
                    region=region.upper(),
                    source_file="ESMA FIRDS Master Register (Live Solr Database)",
                )
                instruments.append(inst)

        # 3. If not found in live Solr core, fallback to local/cached DLTINS files
        if not instruments:
            search_dirs = []
            if self.data_dir and self.data_dir.exists():
                search_dirs.append(self.data_dir)
            if self.cache_dir and self.cache_dir.exists():
                search_dirs.append(self.cache_dir)

            parser = DltinsXmlParser(region=region)
            for d in search_dirs:
                found = parser.find_isin_in_directory(d, clean_isin)
                if found:
                    instruments.extend(found)
                    break

        return instruments
