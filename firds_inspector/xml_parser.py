"""
High-performance Streaming ISO 20022 auth.036.001.02 (DLTINS) XML Parser.
Parses large XML and ZIP files efficiently with low memory footprint using iterparse.
"""

import io
import zipfile
import gzip
from pathlib import Path
from typing import Iterator, List, Optional, Set, Dict, Any, Union
import xml.etree.ElementTree as ET

from .models import (
    FinancialInstrument,
    GeneralAttributes,
    TradingVenueAttributes,
    TechnicalAttributes,
)
from .cfi_decoder import decode_cfi
from .utils import logger


def _get_local_tag(tag: str) -> str:
    """Strips XML namespace from tag if present (e.g. '{urn:...}Id' -> 'Id')."""
    return tag.split("}")[-1] if "}" in tag else tag


def _get_child_text(parent: ET.Element, child_tag: str) -> Optional[str]:
    """Finds direct or nested child with matching local tag and returns its text."""
    for child in parent:
        if _get_local_tag(child.tag) == child_tag:
            return child.text.strip() if child.text else None
    return None


def _get_all_children_by_local_tag(parent: ET.Element, child_tag: str) -> List[ET.Element]:
    """Returns all child elements matching the local tag."""
    return [child for child in parent if _get_local_tag(child.tag) == child_tag]


class DltinsXmlParser:
    """
    Streaming parser for ESMA / FCA DLTINS (ISO 20022 auth.036.001.02) reference data files.
    """

    def __init__(self, region: str = "EU"):
        self.region = region.upper()

    def parse_record_element(self, record_elem: ET.Element, record_type: str, source_file: str) -> Optional[FinancialInstrument]:
        """
        Parses a single record element (NewRecord, ModfdRecord, CancRecord, TermntdRecord) into FinancialInstrument.
        """
        general_elem = None
        issuer_lei = None
        trading_venues: List[TradingVenueAttributes] = []
        tech_attrs = None
        custom_attrs: Dict[str, Any] = {}

        for child in record_elem:
            tag = _get_local_tag(child.tag)
            if tag == "FinInstrmGnlAttrbts":
                general_elem = child
            elif tag == "Issr":
                issuer_lei = child.text.strip() if child.text else None
            elif tag == "TradgVnAttrbts":
                mic = _get_child_text(child, "Id")
                if mic:
                    issuer_req_text = _get_child_text(child, "IssrReq")
                    issuer_req = (issuer_req_text.lower() == "true") if issuer_req_text else None
                    adm_dt = _get_child_text(child, "AdmssnApprvlDtByIssr")
                    req_adm_dt = _get_child_text(child, "ReqForAdmssnDt")
                    frst_trad_dt = _get_child_text(child, "FrstTradDt")
                    term_dt = _get_child_text(child, "TermntnDt")

                    trading_venues.append(
                        TradingVenueAttributes(
                            mic=mic,
                            issuer_request=issuer_req,
                            admission_approval_date=adm_dt,
                            request_for_admission_date=req_adm_dt,
                            first_trade_date=frst_trad_dt,
                            termination_date=term_dt,
                        )
                    )
            elif tag == "TechAttrbts":
                rca = _get_child_text(child, "RlvntCmptntAuthrty")
                pbl_dt = _get_child_text(child, "PblctnDt")
                rc_dt = _get_child_text(child, "RcrptDt")
                tech_attrs = TechnicalAttributes(
                    relevant_competent_authority=rca,
                    publication_date=pbl_dt,
                    record_date=rc_dt,
                )

        if general_elem is None:
            return None

        isin = _get_child_text(general_elem, "Id")
        if not isin:
            return None

        full_nm = _get_child_text(general_elem, "FullNm")
        shrt_nm = _get_child_text(general_elem, "ShrtNm")
        cfi = _get_child_text(general_elem, "ClssfctnFinInstrm")
        cfi_info = decode_cfi(cfi) if cfi else None
        cfi_desc = cfi_info["summary"] if cfi_info else None
        ccy = _get_child_text(general_elem, "NtnlCcy")
        cmmdty_ind_text = _get_child_text(general_elem, "CmmdtyDerivInd")
        cmmdty_ind = (cmmdty_ind_text.lower() == "true") if cmmdty_ind_text else None

        general = GeneralAttributes(
            isin=isin,
            full_name=full_nm,
            short_name=shrt_nm,
            cfi_code=cfi,
            cfi_description=cfi_desc,
            currency=ccy,
            commodity_derivative_indicator=cmmdty_ind,
            issuer_lei=issuer_lei,
        )

        return FinancialInstrument(
            general=general,
            record_type=record_type,
            trading_venues=trading_venues,
            technical=tech_attrs,
            region=self.region,
            source_file=source_file,
        )

    def stream_file(
        self,
        file_path: Union[str, Path],
        target_isins: Optional[Set[str]] = None,
        cfi_filter: Optional[str] = None,
        mic_filter: Optional[str] = None,
    ) -> Iterator[FinancialInstrument]:
        """
        Streams instruments from a given .xml, .zip, or .gz file.
        target_isins: set of uppercase ISINs to find.
        """
        path = Path(file_path)
        if not path.exists():
            logger.error(f"File not found: {path}")
            return

        if target_isins:
            target_isins = {isin.strip().upper() for isin in target_isins if isin}

        if path.suffix.lower() == ".zip":
            with zipfile.ZipFile(path, "r") as zf:
                for name in zf.namelist():
                    if name.lower().endswith(".xml"):
                        logger.debug(f"Parsing XML inside zip: {name}")
                        with zf.open(name) as xml_file:
                            yield from self._stream_xml_bytes(xml_file, f"{path.name}::{name}", target_isins, cfi_filter, mic_filter)
        elif path.suffix.lower() == ".gz":
            with gzip.open(path, "rb") as gz_file:
                yield from self._stream_xml_bytes(gz_file, path.name, target_isins, cfi_filter, mic_filter)
        else:
            with open(path, "rb") as xml_file:
                yield from self._stream_xml_bytes(xml_file, path.name, target_isins, cfi_filter, mic_filter)

    def _stream_xml_bytes(
        self,
        xml_source: Any,
        source_name: str,
        target_isins: Optional[Set[str]] = None,
        cfi_filter: Optional[str] = None,
        mic_filter: Optional[str] = None,
    ) -> Iterator[FinancialInstrument]:
        """
        Memory-safe iterparse loop with node clearing.
        """
        # Event type 'end' is triggered when an element's closing tag is read
        context = ET.iterparse(xml_source, events=("end",))
        
        # Tags that define individual records
        record_tags = {
            "NewRecord": "NEWT",
            "ModfdRecord": "MODI",
            "CancRecord": "CANC",
            "TermntdRecord": "TERMN",
            "FinInstrm": "RECORD",
        }

        for event, elem in context:
            local_tag = _get_local_tag(elem.tag)

            if local_tag in record_tags:
                rec_type = record_tags[local_tag]

                # If the tag is FinInstrm, look for child records
                if local_tag == "FinInstrm":
                    for child in elem:
                        child_local = _get_local_tag(child.tag)
                        if child_local in record_tags:
                            inst = self.parse_record_element(child, record_tags[child_local], source_name)
                            if inst and self._matches_filter(inst, target_isins, cfi_filter, mic_filter):
                                yield inst
                else:
                    inst = self.parse_record_element(elem, rec_type, source_name)
                    if inst and self._matches_filter(inst, target_isins, cfi_filter, mic_filter):
                        yield inst

                # Clear element and its children to reclaim memory
                elem.clear()

    def _matches_filter(
        self,
        inst: FinancialInstrument,
        target_isins: Optional[Set[str]],
        cfi_filter: Optional[str],
        mic_filter: Optional[str],
    ) -> bool:
        if target_isins and inst.isin.upper() not in target_isins:
            return False
        if cfi_filter and (not inst.general.cfi_code or not inst.general.cfi_code.upper().startswith(cfi_filter.upper())):
            return False
        if mic_filter:
            mics = [v.mic.upper() for v in inst.trading_venues]
            if mic_filter.upper() not in mics:
                return False
        return True

    def find_isin_in_directory(
        self,
        directory: Union[str, Path],
        isin: str,
        date_str: Optional[str] = None,
    ) -> List[FinancialInstrument]:
        """
        Scans all XML / ZIP files in a directory for the given ISIN.
        """
        dir_path = Path(directory)
        if not dir_path.exists():
            return []

        target_set = {isin.strip().upper()}
        found_instruments = []

        # Find all .xml and .zip files
        pattern = f"*{date_str.replace('-', '')}*" if date_str else "*"
        candidates = list(dir_path.glob(f"{pattern}.zip")) + list(dir_path.glob(f"{pattern}.xml"))

        if not candidates:
            # Fallback to all zip/xml in the directory
            candidates = list(dir_path.glob("*.zip")) + list(dir_path.glob("*.xml"))

        for file_path in candidates:
            try:
                for inst in self.stream_file(file_path, target_isins=target_set):
                    found_instruments.append(inst)
            except Exception as e:
                logger.warning(f"Error parsing {file_path.name}: {e}")

        return found_instruments
