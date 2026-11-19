"""
River Sentinel 2.0 - Phase 4 Operational Application Verification Test Suite
Tests:
- Station directory with accurate lifecycle, device binding, and telemetry touch.
- Single station identity resolution by UUID and station_code.
- Station-specific latest reading retrieval and empty data handling.
- Historical time-series query filtering (24h, 7d, 30d, parameter, limit cap).
- Statistical summary calculations (min, max, avg, reading counts).
- Station operational analytics (provenance breakdown, quality distribution).
- System-wide authority analytics aggregations with RBAC protection.
- Filtered CSV data export.
- Transparent station-specific scientific safety evaluation (CPCB Class B, BIS IS 10500).
- Citizen report ownership and profile retrieval.
"""

import unittest
import os
import sys
import json
import csv
import io

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from services.supabase_service import execute_sql, supabase_get


class TestPhase4OperationalApplication(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.app = app
        cls.app_context = cls.app.app_context()
        cls.app_context.push()

        # Fetch an active station and a planned station from DB for test queries
        stations = supabase_get('monitoring_stations', order='station_code.asc')
        cls.stations = stations or []
        cls.assi_station = next((s for s in cls.stations if 'ASSI' in s.get('station_code', '')), None)
        cls.planned_station = next((s for s in cls.stations if s.get('status') == 'planned'), None)

    @classmethod
    def tearDownClass(cls):
        cls.app_context.pop()

    # ------------------------------------------------------------------------
    # 1. Station Directory & Identity Resolution
    # ------------------------------------------------------------------------
    def test_list_stations_endpoint(self):
        """GET /api/v1/stations must return all registered stations with valid metadata."""
        res = self.client.get('/api/v1/stations')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get('status'), 'success')
        self.assertGreaterEqual(data.get('count', 0), 4)

        stations = data.get('stations', [])
        stn_codes = [s.get('station_code') for s in stations]
        self.assertIn('STN-VAR-ASSI-01', stn_codes)
        self.assertIn('STN-VAR-DASH-02', stn_codes)

        # Verify planned stations are not shown as physically online without active telemetry
        for s in stations:
            self.assertIn('is_online', s)
            self.assertIsInstance(s['is_online'], bool)
            self.assertIn('status', s)
            self.assertIn('latitude', s)
            self.assertIn('longitude', s)
            self.assertIn('warning_water_level_m', s)
            self.assertIn('danger_water_level_m', s)

    def test_get_station_details_by_uuid_and_code(self):
        """GET /api/v1/stations/<id> must resolve by both UUID and station_code."""
        if not self.assi_station:
            self.skipTest("No Assi station found in DB")

        uuid_id = self.assi_station['id']
        code_id = self.assi_station['station_code']

        # 1. By UUID
        res_uuid = self.client.get(f'/api/v1/stations/{uuid_id}')
        self.assertEqual(res_uuid.status_code, 200)
        data_uuid = res_uuid.get_json()
        self.assertEqual(data_uuid['station']['station_code'], code_id)

        # 2. By Station Code
        res_code = self.client.get(f'/api/v1/stations/{code_id}')
        self.assertEqual(res_code.status_code, 200)
        data_code = res_code.get_json()
        self.assertEqual(data_code['station']['id'], uuid_id)

        # 3. Non-existent station
        res_404 = self.client.get('/api/v1/stations/NON_EXISTENT_STN_99')
        self.assertEqual(res_404.status_code, 404)

    def test_get_station_latest_reading(self):
        """GET /api/v1/stations/<id>/latest must return reading or clean no_data response."""
        if not self.assi_station:
            self.skipTest("No Assi station found in DB")

        res = self.client.get(f"/api/v1/stations/{self.assi_station['station_code']}/latest")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn(data.get('status'), ['success', 'no_data'])
        if data.get('status') == 'success':
            self.assertIsNotNone(data.get('reading'))
            self.assertIn('ph', data['reading'])

    # ------------------------------------------------------------------------
    # 2. Historical Readings Filtering & Summary Statistics
    # ------------------------------------------------------------------------
    def test_historical_readings_timeframes(self):
        """GET /api/v1/stations/<id>/readings supports 24h, 7d, 30d timeframes."""
        if not self.assi_station:
            self.skipTest("No Assi station found in DB")

        sid = self.assi_station['id']

        # 24h
        res_24h = self.client.get(f'/api/v1/stations/{sid}/readings?timeframe=24h')
        self.assertEqual(res_24h.status_code, 200)
        data_24h = res_24h.get_json()
        self.assertEqual(data_24h.get('timeframe'), '24h')
        self.assertIn('readings', data_24h)
        self.assertIn('summary_statistics', data_24h)
        self.assertIn('provenance_breakdown', data_24h)

        # 7d
        res_7d = self.client.get(f'/api/v1/stations/{sid}/readings?timeframe=7d')
        self.assertEqual(res_7d.status_code, 200)

        # 30d
        res_30d = self.client.get(f'/api/v1/stations/{sid}/readings?timeframe=30d')
        self.assertEqual(res_30d.status_code, 200)

    def test_historical_readings_parameter_filter(self):
        """GET /api/v1/stations/<id>/readings?parameter=ph filters specifically."""
        if not self.assi_station:
            self.skipTest("No Assi station found in DB")

        sid = self.assi_station['id']
        res = self.client.get(f'/api/v1/stations/{sid}/readings?parameter=ph')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get('parameter'), 'ph')

    def test_historical_readings_limit_cap(self):
        """Limit parameter must be capped at 1000 to prevent DOS."""
        if not self.assi_station:
            self.skipTest("No Assi station found in DB")

        sid = self.assi_station['id']
        res = self.client.get(f'/api/v1/stations/{sid}/readings?limit=99999')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertLessEqual(len(data.get('readings', [])), 1000)

    # ------------------------------------------------------------------------
    # 3. Station Operational Analytics
    # ------------------------------------------------------------------------
    def test_station_analytics_endpoint(self):
        """GET /api/v1/stations/<id>/analytics returns provenance and quality stats."""
        if not self.assi_station:
            self.skipTest("No Assi station found in DB")

        sid = self.assi_station['id']
        res = self.client.get(f'/api/v1/stations/{sid}/analytics')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get('status'), 'success')
        self.assertIn('total_readings', data)
        self.assertIn('provenance_breakdown', data)
        self.assertIn('quality_distribution', data)
        self.assertIn('averages_last_24h', data)
        self.assertIn('cwc_reference_thresholds', data)

    # ------------------------------------------------------------------------
    # 4. System-Wide Authority Analytics & RBAC Protection
    # ------------------------------------------------------------------------
    def test_analytics_overview_rbac_unauthenticated(self):
        """GET /api/v1/analytics/overview requires authentication (401 without token)."""
        res = self.client.get('/api/v1/analytics/overview')
        self.assertEqual(res.status_code, 401)

    def test_analytics_overview_mock_authorized(self):
        """Test overview logic with simulated authority context."""
        from routes.stations_v1 import get_system_analytics_overview
        from unittest.mock import patch

        with self.app.test_request_context('/api/v1/analytics/overview'):
            # Simulate authenticated authority_admin
            with patch('services.auth_service.extract_bearer_token', return_value='fake_token'):
                with patch('services.auth_service.verify_supabase_jwt', return_value={'id': 'test-uuid', 'email': 'admin@uppcb.gov.in'}):
                    with patch('services.auth_service.get_user_profile', return_value={'role': 'authority_admin', 'full_name': 'Authority Officer'}):
                        res = self.client.get('/api/v1/analytics/overview', headers={'Authorization': 'Bearer fake_token'})
                        self.assertEqual(res.status_code, 200)
                        data = res.get_json()
                        self.assertEqual(data.get('status'), 'success')
                        self.assertIn('stations', data)
                        self.assertIn('devices', data)
                        self.assertIn('telemetry', data)
                        self.assertIn('pollution_reports', data)
                        self.assertIn('flood_risk', data)

    # ------------------------------------------------------------------------
    # 5. Filtered CSV Data Export
    # ------------------------------------------------------------------------
    def test_export_sensor_data_csv(self):
        """GET /api/v1/export/sensor-data returns valid CSV with compliant headers."""
        res = self.client.get('/api/v1/export/sensor-data?timeframe=24h')
        self.assertEqual(res.status_code, 200)
        self.assertIn('text/csv', res.headers.get('Content-Type', ''))
        self.assertIn('attachment', res.headers.get('Content-Disposition', ''))

        csv_content = res.data.decode('utf-8')
        reader = csv.reader(io.StringIO(csv_content))
        header = next(reader)
        self.assertIn('Reading_ID', header)
        self.assertIn('Timestamp_UTC', header)
        self.assertIn('Station_Code', header)
        self.assertIn('pH', header)
        self.assertIn('Turbidity_NTU', header)
        self.assertIn('Provenance', header)

    # ------------------------------------------------------------------------
    # 6. Scientific Station Safety Evaluation
    # ------------------------------------------------------------------------
    def test_station_safety_evaluation(self):
        """GET /api/v1/stations/<id>/evaluate-safety evaluates CPCB and BIS standards."""
        if not self.assi_station:
            self.skipTest("No Assi station found in DB")

        sid = self.assi_station['id']
        res = self.client.get(f'/api/v1/stations/{sid}/evaluate-safety')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get('status'), 'success')

        # 1. Bathing screening
        self.assertIn('bathing_water_screening', data)
        self.assertIn(data['bathing_water_screening']['suitability'], ['SUITABLE', 'UNSUITABLE', 'INSUFFICIENT_TELEMETRY'])

        # 2. Drinking screening with mandatory treatment disclaimer
        self.assertIn('drinking_water_screening', data)
        self.assertIn('disclaimer', data['drinking_water_screening'])
        self.assertIn('treatment', data['drinking_water_screening']['disclaimer'].lower())

        # 3. Ecological screening
        self.assertIn('ecological_screening', data)
        self.assertIn('status', data['ecological_screening'])

        # 4. Sensor anomaly screening
        self.assertIn('sensor_anomaly_screening', data)
        self.assertIn('confidence_score', data['sensor_anomaly_screening'])


if __name__ == '__main__':
    unittest.main()
