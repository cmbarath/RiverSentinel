"""
Test script for flood prediction API endpoint (River Sentinel 2.0)
Tests active 6-feature Random Forest model contract via test client.
"""

import os
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import create_app


class TestFloodPredictionAPI(unittest.TestCase):
    """Test flood prediction with canonical 6-feature scenarios"""

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def test_low_risk_scenario(self):
        """Test flood prediction: Low Risk scenario"""
        low_risk = {
            "water_level": 65.5,
            "discharge": 8000.0,
            "rain_varanasi": 2.0,
            "rain_upstream": 5.0,
            "temperature": 28.0,
            "humidity": 60.0
        }
        res = self.client.post("/api/flood/predict", json=low_risk)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("risk_level"), "LOW")

    def test_high_risk_scenario(self):
        """Test flood prediction: High Risk scenario"""
        high_risk = {
            "water_level": 70.5,
            "discharge": 15000.0,
            "rain_varanasi": 85.0,
            "rain_upstream": 120.0,
            "temperature": 25.0,
            "humidity": 95.0
        }
        res = self.client.post("/api/flood/predict", json=high_risk)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("risk_level"), "HIGH")

    def test_get_live_prediction(self):
        """Test GET /api/flood/predict endpoint (live sensor auto-evaluation)"""
        res = self.client.get("/api/flood/predict")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("risk_level", data)
        self.assertIn("flood_probability", data)


if __name__ == "__main__":
    unittest.main()
