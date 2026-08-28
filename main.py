"""
FastAPI Web Application for FIRDS Reference Data API.
Production-ready for Render deployment.
"""

import os
import sys
from pathlib import Path
from typing import Optional, List
from datetime import datetime

# Add package directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from fastapi import FastAPI, Query, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from firds_inspector.service import FirdsService
from firds_inspector.schemas import (
    SearchResponse,
    CompareResponse,
    HealthResponse,
    ErrorResponse,
    FinancialInstrumentSchema,
    GeneralAttributesSchema,
    TradingVenueSchema,
    TechnicalAttributesSchema,
    FieldDiffSchema,
)
from firds_inspector.utils import (
    normalize_isin,
    is_valid_isin_format,
    is_valid_date_format,
    get_cache_dir,
    logger,
)

# Initialize FastAPI App
app = FastAPI(
    title="FIRDS Reference Data API",
    description=(
        "Production-ready REST API for querying and reconciling ESMA (EU) and FCA (UK) "
        "Financial Instruments Reference Data System (FIRDS DLTINS auth.036.001.02/03) XML feeds."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for web integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service instance
service = FirdsService()


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    tags=["System"],
)
def health_check():
    """
    Returns service health status and active cache configuration.
    """
    cache_path = str(get_cache_dir("eu"))
    return {
        "status": "ok",
        "service": "firds-reference-data-api",
        "version": "1.0.0",
        "cache_directory": cache_path,
    }


@app.get(
    "/",
    summary="API Root Information",
    tags=["System"],
)
def root():
    """
    Root endpoint providing API information and documentation links.
    """
    return {
        "message": "Welcome to FIRDS Reference Data API",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "search_endpoint": "/search?isin={ISIN}&date={YYYY-MM-DD}&region={EU|UK}",
    }


@app.get(
    "/search",
    response_model=SearchResponse,
    responses={
        200: {"description": "Matching financial instruments found", "model": SearchResponse},
        400: {"description": "Invalid input parameters (ISIN, Date, or Region)", "model": ErrorResponse},
        404: {"description": "No instruments found matching query", "model": ErrorResponse},
        502: {"description": "Upstream ESMA/FCA download or network failure", "model": ErrorResponse},
    },
    summary="Search FIRDS DLTINS Instrument Reference Data",
    tags=["Reference Data"],
)
def search_isin(
    isin: str = Query(..., description="12-character ISO 6166 ISIN (e.g. AT0000A0SL91, US0378331005)"),
    date: str = Query(..., description="Publication Date in YYYY-MM-DD format (e.g. 2024-01-15)"),
    region: str = Query("EU", description="Regulatory region: EU, UK, or ALL (case-insensitive)"),
    dltins_dir: Optional[str] = Query(None, description="Optional custom directory containing local DLTINS files (e.g. sample_data)"),
):
    """
    Queries FIRDS DLTINS reference data for a given ISIN, date, and region.
    If not found locally, connects to the ESMA Solr API to download and stream reference data.
    """
    # 1. Validate ISIN format
    clean_isin = normalize_isin(isin)
    if not is_valid_isin_format(clean_isin):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid ISIN '{isin}'. An ISIN must be a 12-character alphanumeric code (e.g. US0378331005).",
        )

    # 2. Validate Date format
    clean_date = date.strip()
    if not is_valid_date_format(clean_date):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date '{date}'. Date must be in YYYY-MM-DD format (e.g. 2024-01-15).",
        )

    # 3. Validate Region
    clean_region = region.strip().upper()
    if clean_region not in ("EU", "UK", "ALL"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid region '{region}'. Supported regions are 'EU', 'UK', or 'ALL'.",
        )

    # 4. Search via Service
    try:
        instruments = service.search_instruments(
            isin=clean_isin,
            date_str=clean_date,
            region=clean_region,
            custom_dir=dltins_dir,
        )
    except Exception as e:
        logger.error(f"Error processing FIRDS search for {clean_isin}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to retrieve or parse reference data from regulatory feed: {str(e)}",
        )

    if not instruments:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No matching instruments found for ISIN '{clean_isin}' on date '{clean_date}' in region '{clean_region}'.",
        )

    # Convert to response schemas
    formatted_instruments = []
    for inst in instruments:
        g = inst.general
        t = inst.technical
        formatted_instruments.append(
            FinancialInstrumentSchema(
                isin=inst.isin,
                region=inst.region,
                record_type=inst.record_type,
                source_file=inst.source_file,
                general=GeneralAttributesSchema(
                    isin=g.isin,
                    full_name=g.full_name,
                    short_name=g.short_name,
                    cfi_code=g.cfi_code,
                    cfi_description=g.cfi_description,
                    currency=g.currency,
                    commodity_derivative_indicator=g.commodity_derivative_indicator,
                    issuer_lei=g.issuer_lei,
                    custom_attributes=g.custom_attributes,
                ),
                trading_venues=[
                    TradingVenueSchema(
                        mic=tv.mic,
                        issuer_request=tv.issuer_request,
                        first_trade_date=tv.first_trade_date,
                        termination_date=tv.termination_date,
                        admission_approval_date=tv.admission_approval_date,
                        request_for_admission_date=tv.request_for_admission_date,
                        custom_attributes=tv.custom_attributes,
                    )
                    for tv in inst.trading_venues
                ],
                technical=TechnicalAttributesSchema(
                    relevant_competent_authority=t.relevant_competent_authority if t else None,
                    publication_date=t.publication_date if t else None,
                    record_date=t.record_date if t else None,
                ) if t else None,
            )
        )

    return {
        "success": True,
        "query_isin": clean_isin,
        "date": clean_date,
        "region": clean_region,
        "count": len(formatted_instruments),
        "instruments": formatted_instruments,
    }


@app.get(
    "/compare",
    response_model=CompareResponse,
    responses={
        200: {"description": "Reconciliation diff returned", "model": CompareResponse},
        400: {"description": "Invalid input parameters", "model": ErrorResponse},
    },
    summary="Compare ISIN between ESMA (EU) and FCA (UK)",
    tags=["Reference Data"],
)
def compare_isin(
    isin: str = Query(..., description="12-character ISO 6166 ISIN to reconcile"),
    date: str = Query(..., description="Publication Date in YYYY-MM-DD format"),
    dltins_dir: Optional[str] = Query(None, description="Optional custom directory containing DLTINS files"),
):
    """
    Performs field-by-field cross-region reconciliation diff between ESMA (EU) and FCA (UK) feeds
    and returns root-cause diagnostics for missing records.
    """
    clean_isin = normalize_isin(isin)
    if not is_valid_isin_format(clean_isin):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid ISIN '{isin}'. Must be 12 alphanumeric characters.",
        )

    clean_date = date.strip()
    if not is_valid_date_format(clean_date):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date '{date}'. Must be YYYY-MM-DD.",
        )

    diff = service.compare_instrument(
        isin=clean_isin,
        date_str=clean_date,
        custom_dir=dltins_dir,
    )

    formatted_diffs = [
        FieldDiffSchema(
            field_name=fd.field_name,
            source_value=fd.source_value,
            target_value=fd.target_value,
            is_match=fd.is_match,
            description=fd.description,
        )
        for fd in diff.field_diffs
    ]

    return {
        "success": True,
        "isin": diff.isin,
        "date": clean_date,
        "has_differences": diff.has_differences,
        "source_region": diff.source_name,
        "target_region": diff.target_name,
        "field_diffs": formatted_diffs,
        "diagnostics": diff.diagnostics,
    }


# Custom Exception Handler to return clean JSON errors
@app.exception_handler(HTTPException)
def custom_http_exception_handler(request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": "Request Error" if exc.status_code < 500 else "Server Error",
            "detail": exc.detail,
        },
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    logger.info(f"Starting FIRDS API on {host}:{port}")
    uvicorn.run("main:app", host=host, port=port, reload=True)
