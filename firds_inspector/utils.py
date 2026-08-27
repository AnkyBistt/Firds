"""
Utility functions for FIRDS Inspector.
"""

import os
import re
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

# Setup standard logging
logger = logging.getLogger("firds_inspector")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def get_cache_dir(region: str = "eu", subfolder: Optional[str] = None) -> Path:
    """
    Returns path to local cache directory for FIRDS files.
    Default: ~/.firds_cache/<region>/<subfolder> or ./cache/<region>/<subfolder>
    """
    base_dir = Path.home() / ".firds_cache" / region.lower()
    if subfolder:
        base_dir = base_dir / subfolder
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def normalize_isin(isin: str) -> str:
    """Normalizes and validates ISIN string."""
    if not isin:
        return ""
    cleaned = isin.strip().upper()
    return cleaned


def is_valid_isin_format(isin: str) -> bool:
    """Checks if ISIN matches standard 12-char alphanumeric format (2 letter country + 9 alphanum + 1 check digit)."""
    if not isin or len(isin) != 12:
        return False
    return bool(re.match(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$", isin))


def format_date_str(date_val: Optional[str]) -> str:
    """Formats ISO date string to YYYY-MM-DD or readable format."""
    if not date_val:
        return "N/A"
    try:
        if 'T' in date_val:
            dt = datetime.fromisoformat(date_val.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        return date_val
    except Exception:
        return date_val
