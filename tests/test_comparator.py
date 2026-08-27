"""
Tests for InstrumentComparator and Ingestion Diagnostics.
"""

import unittest
from firds_inspector.models import (
    FinancialInstrument,
    GeneralAttributes,
    TradingVenueAttributes,
)
from firds_inspector.comparator import InstrumentComparator


class TestComparator(unittest.TestCase):
    def setUp(self):
        self.comparator = InstrumentComparator()

        self.inst_eu = FinancialInstrument(
            general=GeneralAttributes(
                isin="US0378331005",
                full_name="APPLE INC",
                short_name="APPLE/ORD SHS",
                cfi_code="ESVUFR",
                currency="USD",
                issuer_lei="HW6821973GWENKNIQL71",
            ),
            record_type="NEWT",
            trading_venues=[
                TradingVenueAttributes(mic="XNAS", first_trade_date="1980-12-12"),
                TradingVenueAttributes(mic="XFRA"),
            ],
            region="EU",
        )

        self.inst_uk = FinancialInstrument(
            general=GeneralAttributes(
                isin="US0378331005",
                full_name="APPLE INC",
                short_name="APPLE/ORD USD0.00001",  # Slightly different short name
                cfi_code="ESVUFR",
                currency="USD",
                issuer_lei="HW6821973GWENKNIQL71",
            ),
            record_type="NEWT",
            trading_venues=[
                TradingVenueAttributes(mic="AQXE"),
                TradingVenueAttributes(mic="XLON"),
            ],
            region="UK",
        )

    def test_compare_identical(self):
        diff = self.comparator.compare_instruments(self.inst_eu, self.inst_eu, "EU", "EU")
        self.assertFalse(diff.has_differences)

    def test_compare_with_differences(self):
        diff = self.comparator.compare_instruments(self.inst_eu, self.inst_uk, "EU", "UK")
        self.assertTrue(diff.has_differences)
        # Check that short name diff is captured
        short_name_diff = next(d for d in diff.field_diffs if d.field_name == "Short Name")
        self.assertFalse(short_name_diff.is_match)

    def test_diagnose_problematic_record(self):
        bad_inst = FinancialInstrument(
            general=GeneralAttributes(
                isin="US9999999999",
                full_name="TEST INSTRUMENT",
                issuer_lei=None,  # Missing LEI
            ),
            record_type="CANC",  # Cancellation
            trading_venues=[
                TradingVenueAttributes(mic="XNYS", termination_date="2020-01-01T00:00:00Z")  # Expired
            ],
        )

        diags = self.comparator.diagnose_potential_ingestion_issues(bad_inst)
        self.assertTrue(any("CANC" in d for d in diags))
        self.assertTrue(any("LEI is missing" in d for d in diags))
        self.assertTrue(any("expired termination date" in d for d in diags))


if __name__ == "__main__":
    unittest.main()
