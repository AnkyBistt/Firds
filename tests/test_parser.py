"""
Tests for DltinsXmlParser (XML and ZIP streaming parsing).
"""

import unittest
from pathlib import Path

from firds_inspector.xml_parser import DltinsXmlParser


class TestDltinsXmlParser(unittest.TestCase):
    def setUp(self):
        self.sample_dir = Path(__file__).parent.parent / "sample_data"
        self.xml_path = self.sample_dir / "DLTINS_sample_EU.xml"
        self.zip_path = self.sample_dir / "DLTINS_sample_EU.zip"
        self.parser = DltinsXmlParser(region="EU")

    def test_parse_xml_file_all(self):
        instruments = list(self.parser.stream_file(self.xml_path))
        self.assertEqual(len(instruments), 4)

        # Check first instrument (Apple)
        aapl = instruments[0]
        self.assertEqual(aapl.isin, "US0378331005")
        self.assertEqual(aapl.record_type, "NEWT")
        self.assertEqual(aapl.general.full_name, "APPLE INC COMMON STOCK")
        self.assertEqual(aapl.general.short_name, "APPLE/ORD SHS")
        self.assertEqual(aapl.general.cfi_code, "ESVUFR")
        self.assertEqual(aapl.general.currency, "USD")
        self.assertEqual(aapl.general.issuer_lei, "HW6821973GWENKNIQL71")
        self.assertEqual(len(aapl.trading_venues), 2)
        self.assertEqual(aapl.trading_venues[0].mic, "XNAS")
        self.assertTrue(aapl.trading_venues[0].issuer_request)
        self.assertEqual(aapl.trading_venues[1].mic, "XFRA")

    def test_parse_zip_file(self):
        instruments = list(self.parser.stream_file(self.zip_path, target_isins={"GB0002634946"}))
        self.assertEqual(len(instruments), 1)
        bae = instruments[0]
        self.assertEqual(bae.isin, "GB0002634946")
        self.assertEqual(bae.general.currency, "GBP")
        self.assertEqual(bae.trading_venues[0].mic, "XLON")

    def test_filter_by_cfi(self):
        instruments = list(self.parser.stream_file(self.xml_path, cfi_filter="DB"))
        self.assertEqual(len(instruments), 1)
        self.assertEqual(instruments[0].isin, "DE0001102309")
        self.assertEqual(instruments[0].record_type, "MODI")

    def test_filter_by_mic(self):
        instruments = list(self.parser.stream_file(self.xml_path, mic_filter="XBER"))
        self.assertEqual(len(instruments), 1)
        self.assertEqual(instruments[0].isin, "DE0001102309")


if __name__ == "__main__":
    unittest.main()
