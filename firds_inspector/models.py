"""
Data models for FIRDS DLTINS financial instruments and reconciliation.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class GeneralAttributes:
    isin: str
    full_name: Optional[str] = None
    short_name: Optional[str] = None
    cfi_code: Optional[str] = None
    cfi_description: Optional[str] = None
    currency: Optional[str] = None
    commodity_derivative_indicator: Optional[bool] = None
    issuer_lei: Optional[str] = None
    debt_seniority: Optional[str] = None
    expiry_date: Optional[str] = None
    strike_price: Optional[str] = None
    underlying_isin: Optional[str] = None
    custom_attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "isin": self.isin,
            "full_name": self.full_name,
            "short_name": self.short_name,
            "cfi_code": self.cfi_code,
            "cfi_description": self.cfi_description,
            "currency": self.currency,
            "commodity_derivative_indicator": self.commodity_derivative_indicator,
            "issuer_lei": self.issuer_lei,
            "debt_seniority": self.debt_seniority,
            "expiry_date": self.expiry_date,
            "strike_price": self.strike_price,
            "underlying_isin": self.underlying_isin,
            "custom_attributes": self.custom_attributes,
        }


@dataclass
class TradingVenueAttributes:
    mic: str
    issuer_request: Optional[bool] = None
    admission_approval_date: Optional[str] = None
    request_for_admission_date: Optional[str] = None
    first_trade_date: Optional[str] = None
    termination_date: Optional[str] = None
    custom_attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mic": self.mic,
            "issuer_request": self.issuer_request,
            "admission_approval_date": self.admission_approval_date,
            "request_for_admission_date": self.request_for_admission_date,
            "first_trade_date": self.first_trade_date,
            "termination_date": self.termination_date,
            "custom_attributes": self.custom_attributes,
        }


@dataclass
class TechnicalAttributes:
    relevant_competent_authority: Optional[str] = None
    publication_date: Optional[str] = None
    record_date: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relevant_competent_authority": self.relevant_competent_authority,
            "publication_date": self.publication_date,
            "record_date": self.record_date,
        }


@dataclass
class FinancialInstrument:
    general: GeneralAttributes
    record_type: str  # NEWT, MODI, CANC, TERMN, UNKNOWN
    trading_venues: List[TradingVenueAttributes] = field(default_factory=list)
    technical: Optional[TechnicalAttributes] = None
    region: str = "EU"  # EU or UK
    source_file: Optional[str] = None
    raw_xml_snippet: Optional[str] = None

    @property
    def isin(self) -> str:
        return self.general.isin

    def to_dict(self) -> Dict[str, Any]:
        return {
            "isin": self.isin,
            "region": self.region,
            "record_type": self.record_type,
            "source_file": self.source_file,
            "general": self.general.to_dict(),
            "trading_venues": [tv.to_dict() for tv in self.trading_venues],
            "technical": self.technical.to_dict() if self.technical else None,
        }


@dataclass
class FieldDiff:
    field_name: str
    source_value: Any
    target_value: Any
    is_match: bool
    description: Optional[str] = None


@dataclass
class DiffResult:
    isin: str
    source_name: str
    target_name: str
    source_instrument: Optional[FinancialInstrument]
    target_instrument: Optional[FinancialInstrument]
    field_diffs: List[FieldDiff] = field(default_factory=list)
    diagnostics: List[str] = field(default_factory=list)

    @property
    def has_differences(self) -> bool:
        if self.source_instrument is None or self.target_instrument is None:
            return True
        return any(not d.is_match for d in self.field_diffs)
