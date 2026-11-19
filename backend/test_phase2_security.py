"""
Phase 2 Comprehensive Security & Regression Test Suite
Validates Supabase RLS privacy rules, RBAC authorization, and API route security.
"""

import sys
import os
import unittest
import requests

# Ensure backend root is in Python sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import app
from dotenv import dotenv_values

env = dotenv_values(os.path.join(backend_dir, '.env'))
SUPABASE_URL = env.get('SUPABASE_URL', '').rstrip('/')
SUPABASE_ANON_KEY = env.get('SUPABASE_KEY', '')
SIMULATOR_TOKEN = env.get('SIMULATOR_API_TOKEN', 'rs_sim_dev_sec_7a8f9c12')


class Phase2SecurityAndRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.anon_headers = {
            'apikey': SUPABASE_ANON_KEY,
            'Authorization': f'Bearer {SUPABASE_ANON_KEY}'
        }

    # ========================================================================
    # 1. Supabase PostgREST RLS Security Tests
    # ========================================================================

    def test_01_anon_cannot_read_raw_pollution_reports(self):
        """Verify anonymous caller cannot access raw citizen pollution reports."""
        if not SUPABASE_URL or not SUPABASE_ANON_KEY:
            self.skipTest("Supabase credentials not configured in backend/.env")
        res = requests.get(f"{SUPABASE_URL}/rest/v1/pollution_reports", headers=self.anon_headers)
        # Should be 401 Unauthorized or permission denied
        self.assertIn(res.status_code, (401, 403), f"Expected 401/403, got {res.status_code}")

    def test_02_anon_cannot_read_user_profiles(self):
        """Verify anonymous caller cannot query profiles table."""
        if not SUPABASE_URL or not SUPABASE_ANON_KEY:
            self.skipTest("Supabase credentials not configured in backend/.env")
        res = requests.get(f"{SUPABASE_URL}/rest/v1/profiles", headers=self.anon_headers)
        self.assertIn(res.status_code, (401, 403), f"Expected 401/403, got {res.status_code}")

    def test_03_anon_cannot_read_devices(self):
        """Verify anonymous caller cannot list devices or PSK credential hashes."""
        if not SUPABASE_URL or not SUPABASE_ANON_KEY:
            self.skipTest("Supabase credentials not configured in backend/.env")
        res = requests.get(f"{SUPABASE_URL}/rest/v1/devices", headers=self.anon_headers)
        self.assertIn(res.status_code, (401, 403), f"Expected 401/403, got {res.status_code}")

    def test_04_anon_can_read_sanitized_telemetry_view(self):
        """Verify anonymous caller can read sanitized public telemetry view."""
        if not SUPABASE_URL or not SUPABASE_ANON_KEY:
            self.skipTest("Supabase credentials not configured in backend/.env")
        res = requests.get(f"{SUPABASE_URL}/rest/v1/public_sensor_telemetry?limit=5", headers=self.anon_headers)
        self.assertEqual(res.status_code, 200, f"Expected 200, got {res.status_code}")
        self.assertIsInstance(res.json(), list)

    def test_05_anon_can_read_active_stations(self):
        """Verify anonymous caller can read public active monitoring stations."""
        if not SUPABASE_URL or not SUPABASE_ANON_KEY:
            self.skipTest("Supabase credentials not configured in backend/.env")
        res = requests.get(f"{SUPABASE_URL}/rest/v1/monitoring_stations", headers=self.anon_headers)
        self.assertEqual(res.status_code, 200, f"Expected 200, got {res.status_code}")
        data = res.json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)

    # ========================================================================
    # 2. Backend Route Security & Authorization Tests
    # ========================================================================

    def test_06_authority_reports_endpoint_rejects_unauthenticated(self):
        """Verify /api/authority/reports rejects requests without JWT Bearer token."""
        res = self.client.get('/api/authority/reports')
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertEqual(data.get('error'), 'Unauthorized')

    def test_07_auth_me_rejects_unauthenticated(self):
        """Verify /api/auth/me rejects requests without JWT Bearer token."""
        res = self.client.get('/api/auth/me')
        self.assertEqual(res.status_code, 401)

    def test_08_devices_endpoint_rejects_unauthenticated(self):
        """Verify /api/devices rejects requests without valid role token."""
        res = self.client.get('/api/devices')
        self.assertEqual(res.status_code, 401)

    def test_09_public_stations_api_returns_stations(self):
        """Verify /api/stations returns active monitoring stations."""
        res = self.client.get('/api/stations')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get('status'), 'success')
        self.assertIn('stations', data)
        self.assertGreaterEqual(len(data['stations']), 1)

    def test_10_telemetry_ingest_rejects_invalid_token(self):
        """Verify /api/telemetry/simulate rejects unauthorized ingestion."""
        res = self.client.post('/api/telemetry/simulate',
                               headers={'X-Simulator-Token': 'wrong_token'},
                               json={'ph': 7.4, 'turbidity': 15.0})
        self.assertEqual(res.status_code, 401)

    def test_11_telemetry_ingest_accepts_valid_token(self):
        """Verify /api/telemetry/simulate persists telemetry with valid token."""
        res = self.client.post('/api/telemetry/simulate',
                               headers={'X-Simulator-Token': SIMULATOR_TOKEN},
                               json={
                                   'ph': 7.55,
                                   'turbidity': 22.0,
                                   'temperature': 25.5,
                                   'humidity': 64.0,
                                   'water_level': 68.2,
                                   'do': 7.1,
                                   'bod': 14.5,
                                   'provenance': 'simulated'
                               })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data.get('status'), 'success')

    def test_12_citizen_health_status_endpoint(self):
        """Verify /api/citizen/health-status returns public water evaluation."""
        res = self.client.get('/api/citizen/health-status')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get('status'), 'success')
        self.assertIn('bathing_safe', data)
        self.assertIn('drinking_safe', data)

    def test_13_flood_prediction_regression(self):
        """Verify flood ML prediction model remains operational."""
        res = self.client.post('/api/flood/predict', json={
            'water_level': 69.5,
            'rainfall': 45.0,
            'river_discharge': 1200.0,
            'upstream_level': 70.0,
            'humidity': 80.0,
            'soil_moisture': 35.0
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('risk_level', data)
        self.assertIn('flood_probability', data)

    def test_14_water_quality_prediction_regression(self):
        """Verify water quality ML prediction model remains operational."""
        res = self.client.post('/api/water-quality/predict', json={
            'ph': 7.4,
            'turbidity': 18.0,
            'temperature': 26.0,
            'do': 6.8,
            'conductivity': 510.0
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('quality_score', data)
        self.assertIn('quality_level', data)


if __name__ == '__main__':
    unittest.main(verbosity=2)
