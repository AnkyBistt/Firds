"""
Integration and Unit Tests for FastAPI FIRDS Endpoints.
"""

import unittest
from pathlib import Path
from fastapi.testclient import TestClient

from main import app


class TestFastApiEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.sample_dir = str(Path(__file__).parent.parent / "sample_data")

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["service"], "firds-reference-data-api")

    def test_root_endpoint(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("docs", data)
        self.assertIn("health", data)

    def test_search_valid_isin_sample_data(self):
        response = self.client.get(
            "/search",
            params={
                "isin": "US0378331005",
                "date": "2024-01-15",
                "region": "EU",
                "dltins_dir": self.sample_dir,
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["query_isin"], "US0378331005")
        self.assertGreaterEqual(data["count"], 1)

        inst = data["instruments"][0]
        self.assertEqual(inst["isin"], "US0378331005")
        self.assertEqual(inst["general"]["full_name"], "APPLE INC COMMON STOCK")
        self.assertEqual(inst["general"]["currency"], "USD")
        self.assertEqual(inst["general"]["issuer_lei"], "HW6821973GWENKNIQL71")

    def test_search_invalid_isin_format(self):
        response = self.client.get(
            "/search",
            params={
                "isin": "INVALID_ISIN",
                "date": "2024-01-15",
                "region": "EU",
            },
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("Invalid ISIN", data["detail"])

    def test_search_invalid_date_format(self):
        response = self.client.get(
            "/search",
            params={
                "isin": "US0378331005",
                "date": "15-01-2024",  # Wrong format
                "region": "EU",
            },
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("Invalid date", data["detail"])

    def test_search_invalid_region(self):
        response = self.client.get(
            "/search",
            params={
                "isin": "US0378331005",
                "date": "2024-01-15",
                "region": "USA",  # Unsupported region
            },
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("Invalid region", data["detail"])

    def test_search_not_found(self):
        response = self.client.get(
            "/search",
            params={
                "isin": "GB0000000000",
                "date": "2024-01-15",
                "region": "EU",
                "dltins_dir": self.sample_dir,
            },
        )
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("No matching instruments found", data["detail"])

    def test_compare_endpoint(self):
        response = self.client.get(
            "/compare",
            params={
                "isin": "US0378331005",
                "date": "2024-01-15",
                "dltins_dir": self.sample_dir,
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["isin"], "US0378331005")
        self.assertTrue(data["has_differences"])
        self.assertGreater(len(data["field_diffs"]), 0)


if __name__ == "__main__":
    unittest.main()
