"""
Tests for ISO 10962 CFI Code Decoder.
"""

import unittest
from firds_inspector.cfi_decoder import decode_cfi


class TestCfiDecoder(unittest.TestCase):
    def test_decode_equity(self):
        res = decode_cfi("ESVUFR")
        self.assertTrue(res["is_valid"])
        self.assertEqual(res["category"], "Equities")
        self.assertEqual(res["group"], "Common / Ordinary Shares")
        self.assertIn("Voting: Voting", res["details"])
        self.assertIn("Payment: Fully Paid", res["details"])

    def test_decode_debt(self):
        res = decode_cfi("DBFTFR")
        self.assertTrue(res["is_valid"])
        self.assertEqual(res["category"], "Debt Instruments")
        self.assertEqual(res["group"], "Bonds")
        self.assertIn("Interest: Fixed rate", res["details"])

    def test_decode_invalid(self):
        res = decode_cfi("INVALID")
        self.assertFalse(res["is_valid"])


if __name__ == "__main__":
    unittest.main()
