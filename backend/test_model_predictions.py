"""
Test the legacy flood prediction model with random scenarios (Phase 0 Archive).
Superseded by Phase 6/6.1/8.1 validated models (models/flood_rf_2026.pkl, models/flood_ridge_governed.pkl).
Preserved for historical reference and structured as a standard unittest.TestCase.
"""

import os
import unittest
import numpy as np

class TestLegacyModelPredictions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model_path = os.path.join(os.path.dirname(__file__), 'flood_model.pkl')
        cls.scaler_path = os.path.join(os.path.dirname(__file__), 'flood_scaler.pkl')

    def test_legacy_model_scenarios(self):
        if not os.path.exists(self.model_path) or not os.path.exists(self.scaler_path):
            self.skipTest("Legacy flood_model.pkl or flood_scaler.pkl not present; superseded by Phase 6/6.1/8.1 models")

        import joblib
        model = joblib.load(self.model_path)
        scaler = joblib.load(self.scaler_path)

        test_scenarios = [
            {
                'name': 'Normal Conditions (No Flood Expected)',
                'water_level': 66.5,
                'discharge': 9000,
                'rain_varanasi': 5.0,
                'rain_upstream': 8.0,
                'temperature': 28.0,
                'humidity': 65.0
            },
            {
                'name': 'High Water Level (Flood Risk)',
                'water_level': 69.5,
                'discharge': 14000,
                'rain_varanasi': 80.0,
                'rain_upstream': 100.0,
                'temperature': 26.0,
                'humidity': 85.0
            }
        ]

        for scenario in test_scenarios:
            features = np.array([[
                scenario['water_level'],
                scenario['discharge'],
                scenario['rain_varanasi'],
                scenario['rain_upstream'],
                scenario['temperature'],
                scenario['humidity']
            ]])
            features_scaled = scaler.transform(features)
            pred = model.predict(features_scaled)
            self.assertIn(pred[0], [0, 1])

if __name__ == '__main__':
    unittest.main()
