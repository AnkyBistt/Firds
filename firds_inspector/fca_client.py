"""
FCA UK FIRDS Data Locator & Downloader.
Handles locating UK FIRDS DLTINS files from local directory, cache, or configured endpoints.
"""

import os
from pathlib import Path
from typing import List, Optional, Dict, Any

from .utils import get_cache_dir, logger


class FcaFirdsClient:
    """
    Client and locator for UK FCA FIRDS files.
    Supports local repository scan, cache lookup, or custom HTTP endpoint.
    """

    def __init__(self, cache_dir: Optional[Path] = None, local_uk_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or get_cache_dir("uk")
        self.local_uk_dir = Path(local_uk_dir) if local_uk_dir else None

    def find_files_for_date(self, date_str: str) -> List[Path]:
        """
        Finds UK FIRDS files for the given date (YYYY-MM-DD) across local directories and cache.
        """
        date_clean = date_str.replace("-", "")
        results: List[Path] = []

        # 1. Search in user-specified local UK directory
        if self.local_uk_dir and self.local_uk_dir.exists():
            for p in self.local_uk_dir.rglob(f"*{date_clean}*"):
                if p.suffix.lower() in (".zip", ".xml", ".gz") and p.is_file():
                    results.append(p)

        # 2. Search in UK cache directory
        date_folder = self.cache_dir / date_clean
        if date_folder.exists():
            for p in date_folder.glob("*"):
                if p.suffix.lower() in (".zip", ".xml", ".gz") and p.is_file():
                    results.append(p)

        # Remove duplicates
        unique_results = list({p.resolve(): p for p in results}.values())
        if unique_results:
            logger.info(f"Found {len(unique_results)} UK FIRDS file(s) for date {date_str}.")
        else:
            logger.warning(f"No UK FIRDS files found for {date_str}. Provide via --dltins-dir or drop into {self.cache_dir}")

        return unique_results
