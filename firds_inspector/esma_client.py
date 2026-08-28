"""
ESMA FIRDS Solr API Client.
Queries ESMA registers for DLTINS reference data files published on a given date, downloads and caches them.
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

try:
    import requests
except ImportError:
    requests = None

from .utils import get_cache_dir, logger


class EsmaFirdsClient:
    """
    Client for ESMA FIRDS register API (Solr).
    Supports both file download feed and direct database core queries by ISIN.
    """
    SOLR_FILES_URL = "https://registers.esma.europa.eu/solr/esma_registers_firds_files/select"
    SOLR_FIRDS_CORE_URL = "https://registers.esma.europa.eu/solr/esma_registers_firds/select"

    def __init__(self, cache_dir: Optional[Path] = None, timeout: int = 30):
        self.cache_dir = cache_dir or get_cache_dir("eu")
        self.timeout = timeout

    def lookup_isin_in_register(self, isin: str, rows: int = 50) -> List[Dict[str, Any]]:
        """
        Directly queries the ESMA FIRDS master register Solr core for an ISIN.
        Returns detailed instrument records across all European trading venues.
        """
        if requests is None:
            logger.warning("The 'requests' package is not installed.")
            return []

        clean_isin = isin.strip().upper()
        params = {
            "q": f"isin:{clean_isin}",
            "wt": "json",
            "rows": rows,
            "sort": "publication_date desc",
        }

        headers = {
            "User-Agent": "FIRDS-Data-Inspector/1.0",
            "Accept": "application/json",
        }

        try:
            logger.info(f"Querying ESMA master FIRDS database for ISIN '{clean_isin}'...")
            response = requests.get(self.SOLR_FIRDS_CORE_URL, params=params, headers=headers, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            docs = data.get("response", {}).get("docs", [])
            logger.info(f"Found {len(docs)} record(s) for ISIN '{clean_isin}' in ESMA database.")
            return docs

        except Exception as e:
            logger.error(f"Failed to query ESMA master FIRDS database for {clean_isin}: {e}")
            return []

    def get_latest_firds_files(self, rows: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieves the latest available DLTINS/FULINS files published by ESMA.
        """
        if requests is None:
            return []

        params = {
            "q": "*",
            "fq": "file_type:DLTINS",
            "wt": "json",
            "rows": rows,
            "sort": "publication_date desc",
        }

        headers = {
            "User-Agent": "FIRDS-Data-Inspector/1.0",
            "Accept": "application/json",
        }

        try:
            response = requests.get(self.SOLR_FILES_URL, params=params, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            return response.json().get("response", {}).get("docs", [])
        except Exception as e:
            logger.error(f"Failed to fetch latest FIRDS files from ESMA: {e}")
            return []

    def search_dltins_files(self, date_str: str, file_type: str = "DLTINS") -> List[Dict[str, Any]]:
        """
        Queries ESMA Solr for files published on the given date (YYYY-MM-DD).
        """
        if requests is None:
            logger.warning("The 'requests' package is not installed. Solr search is unavailable.")
            return []

        # Ensure date format is YYYY-MM-DD
        formatted_date = date_str.strip()
        start_date = f"{formatted_date}T00:00:00Z"
        end_date = f"{formatted_date}T23:59:59Z"

        params = {
            "q": "*",
            "fq": [
                f"publication_date:[{start_date} TO {end_date}]",
                f"file_type:{file_type}"
            ],
            "wt": "json",
            "rows": 100,
            "sort": "file_name asc",
        }

        headers = {
            "User-Agent": "FIRDS-Data-Inspector/1.0",
            "Accept": "application/json",
        }

        try:
            logger.info(f"Querying ESMA Solr API for {file_type} files on {formatted_date}...")
            response = requests.get(self.SOLR_FILES_URL, params=params, headers=headers, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            docs = data.get("response", {}).get("docs", [])
            logger.info(f"Found {len(docs)} {file_type} file(s) for {formatted_date} on ESMA.")
            return docs

        except Exception as e:
            logger.error(f"Failed to query ESMA Solr API for date {date_str}: {e}")
            return []

    def download_file(self, file_doc: Dict[str, Any], date_folder: Optional[str] = None) -> Optional[Path]:
        """
        Downloads a FIRDS zip file specified in file_doc and saves to local cache.
        """
        if requests is None:
            logger.error("'requests' package is not installed.")
            return None

        file_name = file_doc.get("file_name")
        download_url = file_doc.get("download_link")

        if not download_url:
            # Fallback to standard ESMA download link pattern
            download_url = f"https://registers.esma.europa.eu/solr/esma_registers_firds_files/download?file_name={file_name}"

        dest_dir = self.cache_dir / (date_folder or "downloads")
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / file_name

        if dest_path.exists() and dest_path.stat().st_size > 0:
            logger.info(f"Using cached file: {dest_path}")
            return dest_path

        logger.info(f"Downloading {file_name} from ESMA...")
        try:
            with requests.get(download_url, stream=True, timeout=self.timeout * 3) as r:
                r.raise_for_status()
                with open(dest_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)

            logger.info(f"Successfully downloaded: {dest_path} ({dest_path.stat().st_size / (1024*1024):.2f} MB)")
            return dest_path

        except Exception as e:
            logger.error(f"Download failed for {file_name}: {e}")
            if dest_path.exists():
                dest_path.unlink()  # Remove partial download
            return None

    def get_or_download_files_for_date(self, date_str: str) -> List[Path]:
        """
        High-level helper: checks cache first; if empty, queries ESMA and downloads DLTINS files.
        """
        date_folder = date_str.replace("-", "")
        cached_folder = self.cache_dir / date_folder

        # Check if files already exist in cache
        if cached_folder.exists():
            local_files = list(cached_folder.glob("*.zip")) + list(cached_folder.glob("*.xml"))
            if local_files:
                logger.info(f"Found {len(local_files)} cached file(s) for {date_str} in {cached_folder}")
                return local_files

        # Query and download
        docs = self.search_dltins_files(date_str)
        downloaded = []
        for doc in docs:
            path = self.download_file(doc, date_folder=date_folder)
            if path:
                downloaded.append(path)

        return downloaded
