"""
Database Inspector for FIRDS Ingested Data.
Connects to PostgreSQL, SQLite, or other relational databases using sqlite3 or SQLAlchemy/psycopg2
to query and compare ingested instrument records.
"""

import sqlite3
from typing import Optional, Dict, Any, List
from pathlib import Path

from .models import FinancialInstrument, GeneralAttributes, TradingVenueAttributes
from .utils import logger


class DatabaseInspector:
    """
    Queries environment databases to retrieve stored FIRDS records.
    """

    def __init__(self, connection_string_or_path: Optional[str] = None):
        self.conn_str = connection_string_or_path

    def query_sqlite(self, db_path: str, isin: str, table_name: str = "financial_instruments") -> Optional[FinancialInstrument]:
        """
        Queries a local SQLite database for the given ISIN.
        """
        path = Path(db_path)
        if not path.exists():
            logger.warning(f"SQLite DB not found: {path}")
            return None

        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Find instrument
            cursor.execute(f"SELECT * FROM {table_name} WHERE UPPER(isin) = ?", (isin.upper(),))
            row = cursor.fetchone()
            if not row:
                return None

            row_dict = dict(row)

            # Map typical column names
            full_nm = row_dict.get("full_name") or row_dict.get("fullname") or row_dict.get("name")
            shrt_nm = row_dict.get("short_name") or row_dict.get("shortname")
            cfi = row_dict.get("cfi_code") or row_dict.get("cfi") or row_dict.get("classification")
            ccy = row_dict.get("currency") or row_dict.get("ccy")
            lei = row_dict.get("issuer_lei") or row_dict.get("lei") or row_dict.get("issuer")
            rec_type = row_dict.get("record_type") or "INGESTED_DB"

            venues = []
            # Check if there is a mic column
            mic = row_dict.get("mic") or row_dict.get("trading_venue")
            if mic:
                venues.append(TradingVenueAttributes(mic=mic))

            general = GeneralAttributes(
                isin=isin.upper(),
                full_name=full_nm,
                short_name=shrt_nm,
                cfi_code=cfi,
                currency=ccy,
                issuer_lei=lei,
            )

            return FinancialInstrument(
                general=general,
                record_type=rec_type,
                trading_venues=venues,
                region="DATABASE",
                source_file=f"SQLite: {path.name}",
            )

        except Exception as e:
            logger.error(f"Error querying SQLite database: {e}")
            return None
        finally:
            if 'conn' in locals() and conn:
                conn.close()
