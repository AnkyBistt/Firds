"""
Service layer for FIRDS Reference Data operations.
Encapsulates DLTINS XML retrieval, parsing, search, and cross-region reconciliation for API endpoints.
"""

import os
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

from .models import FinancialInstrument, DiffResult
from .xml_parser import DltinsXmlParser
from .esma_client import EsmaFirdsClient
from .fca_client import FcaFirdsClient
from .comparator import InstrumentComparator
from .utils import normalize_isin, is_valid_isin_format, is_valid_date_format, logger


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

        # 1. Custom directory / bundled sample_data check
        target_dir = Path(custom_dir) if custom_dir else self.data_dir
        if target_dir and target_dir.exists():
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
