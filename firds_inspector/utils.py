"""
Utility functions for FIRDS Inspector & Web API.
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
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def get_cache_dir(region: str = "eu", subfolder: Optional[str] = None) -> Path:
    """
    Returns path to local cache directory for FIRDS files.
    Priority:
    1. FIRDS_CACHE_DIR environment variable
    2. /tmp/firds_cache (if on Linux/Render ephemeral filesystem)
    3. ~/.firds_cache
    """
    env_cache = os.getenv("FIRDS_CACHE_DIR")
    if env_cache:
        base_dir = Path(env_cache) / region.lower()
    elif os.name != "nt" and Path("/tmp").exists():
        base_dir = Path("/tmp/firds_cache") / region.lower()
    else:
        base_dir = Path.home() / ".firds_cache" / region.lower()

    if subfolder:
        base_dir = base_dir / subfolder

    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def normalize_isin(isin: str) -> str:
    """Normalizes and validates ISIN string."""
    if not isin:
        return ""
    return isin.strip().upper()


def is_valid_isin_format(isin: str) -> bool:
    """Checks if ISIN matches standard 12-char alphanumeric format (2 letter country + 9 alphanum + 1 check digit)."""
    if not isin or len(isin) != 12:
        return False
    return bool(re.match(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$", isin))


def is_valid_date_format(date_str: str) -> bool:
    """Checks if date string matches YYYY-MM-DD format."""
    if not date_str or not isinstance(date_str, str):
        return False
    try:
        datetime.strptime(date_str.strip(), "%Y-%m-%d")
        return True
    except ValueError:
        return False


def format_date_str(date_val: Optional[str]) -> str:
    """Formats ISO date string to readable format."""
    if not date_val:
        return "N/A"
    try:
        if 'T' in date_val:
            dt = datetime.fromisoformat(date_val.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        return date_val
    except Exception:
        return date_val
