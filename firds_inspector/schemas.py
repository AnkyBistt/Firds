"""
Pydantic Schemas for FastAPI FIRDS Reference Data API.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class GeneralAttributesSchema(BaseModel):
    isin: str = Field(..., example="US0378331005", description="12-character ISO 6166 ISIN")
    full_name: Optional[str] = Field(None, example="APPLE INC COMMON STOCK")
    short_name: Optional[str] = Field(None, example="APPLE/ORD SHS")
    cfi_code: Optional[str] = Field(None, example="ESVUFR", description="6-character ISO 10962 CFI code")
    cfi_description: Optional[str] = Field(None, example="Equities -> Common / Ordinary Shares (Voting: Voting, Transfer: Free/Unrestricted, Payment: Fully Paid, Form: Registered)")
    currency: Optional[str] = Field(None, example="USD", description="3-character ISO 4217 Currency code")
    commodity_derivative_indicator: Optional[bool] = Field(None, example=False)
    issuer_lei: Optional[str] = Field(None, example="HW6821973GWENKNIQL71", description="20-character ISO 17442 Legal Entity Identifier")
    custom_attributes: Dict[str, Any] = Field(default_factory=dict)


class TradingVenueSchema(BaseModel):
    mic: str = Field(..., example="XNAS", description="4-character ISO 10383 Market Identifier Code")
    issuer_request: Optional[bool] = Field(None, example=True)
    first_trade_date: Optional[str] = Field(None, example="1980-12-12T00:00:00Z")
    termination_date: Optional[str] = Field(None, example=None)
    admission_approval_date: Optional[str] = Field(None, example="1980-12-12T00:00:00Z")
    request_for_admission_date: Optional[str] = Field(None, example=None)
    custom_attributes: Dict[str, Any] = Field(default_factory=dict)


class TechnicalAttributesSchema(BaseModel):
    relevant_competent_authority: Optional[str] = Field(None, example="DE")
    publication_date: Optional[str] = Field(None, example="2024-01-15")
    record_date: Optional[str] = Field(None, example=None)


class FinancialInstrumentSchema(BaseModel):
    isin: str = Field(..., example="US0378331005")
    region: str = Field(..., example="EU", description="Regulatory region: EU or UK")
    record_type: str = Field(..., example="NEWT", description="Record event type: NEWT, MODI, CANC, TERMN")
    source_file: Optional[str] = Field(None, example="DLTINS_20240115_01of01.zip")
    general: GeneralAttributesSchema
    trading_venues: List[TradingVenueSchema] = Field(default_factory=list)
    technical: Optional[TechnicalAttributesSchema] = None


class SearchResponse(BaseModel):
    success: bool = Field(True, example=True)
    query_isin: str = Field(..., example="US0378331005")
    date: str = Field(..., example="2024-01-15")
    region: str = Field(..., example="EU")
    count: int = Field(..., example=1)
    instruments: List[FinancialInstrumentSchema]


class FieldDiffSchema(BaseModel):
    field_name: str = Field(..., example="Short Name")
    source_value: Any = Field(..., example="APPLE/ORD SHS")
    target_value: Any = Field(..., example="APPLE/ORD USD0.00001")
    is_match: bool = Field(..., example=False)
    description: Optional[str] = Field(None)


class CompareResponse(BaseModel):
    success: bool = Field(True, example=True)
    isin: str = Field(..., example="US0378331005")
    date: str = Field(..., example="2024-01-15")
    has_differences: bool = Field(..., example=True)
    source_region: str = Field(..., example="ESMA (EU)")
    target_region: str = Field(..., example="FCA (UK)")
    field_diffs: List[FieldDiffSchema]
    diagnostics: List[str] = Field(default_factory=list, description="Ingestion failure root-cause analysis flags")


class HealthResponse(BaseModel):
    status: str = Field("ok", example="ok")
    service: str = Field("firds-reference-data-api", example="firds-reference-data-api")
    version: str = Field("1.0.0", example="1.0.0")
    cache_directory: str = Field(..., example="/tmp/firds_cache/eu")


class ErrorResponse(BaseModel):
    success: bool = Field(False, example=False)
    error: str = Field(..., example="Invalid ISIN")
    detail: str = Field(..., example="The provided ISIN 'INVALID' must be a 12-character alphanumeric code.")
