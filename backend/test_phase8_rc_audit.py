"""
Release Candidate End-to-End Journey, RBAC & API Contract Audit for River Sentinel 2.0
Phase 8: Comprehensive Platform Verification (Citizen, Authority, Field Officer Journeys,
Privacy Isolation, and API Envelope Standard Compliance).
"""

import unittest
import os
import sys
import json
from unittest.mock import patch

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import create_app


class TestPhase8RCAudit(unittest.TestCase):
    """Release Candidate Audit Test Suite."""

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    # =========================================================================
    # 1. CITIZEN END-TO-END USER JOURNEY
    # =========================================================================

    def test_01_citizen_journey_stations_discovery(self):
        """Citizen Journey: Discovery of Varanasi monitoring stations."""
        res = self.client.get('/api/v1/stations')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get('status'), 'success')
        stations = data.get('stations', [])
        self.assertGreaterEqual(len(stations), 1)

        # Check expected station code structure
        station_codes = [s.get('station_code') for s in stations]
        self.assertTrue(any('ASSI' in code or 'DASH' in code for code in station_codes if code))

    def test_02_citizen_journey_telemetry_and_safety_screening(self):
        """Citizen Journey: Fetch latest telemetry and verify CPCB Class B safety screening."""
        res = self.client.get('/api/v1/stations/STN-VAR-ASSI-01/evaluate-safety')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get('status'), 'success')

        # Verify CPCB Class B parameters
        bathing = data.get('bathing_water_screening', {})
        self.assertEqual(bathing.get('cpcb_class'), 'Class B (Outdoor Bathing)')
        self.assertIn('ph', bathing.get('criteria', {}))
        self.assertIn('dissolved_oxygen', bathing.get('criteria', {}))

        # Turbidity must NOT be evaluated as a statutory Class B requirement
        self.assertNotIn('turbidity', bathing.get('criteria', {}))

    def test_03_citizen_journey_notification_preferences(self):
        """Citizen Journey: Read and update notification preferences with RBAC."""
        citizen_user = {'id': '11111111-1111-1111-1111-111111111111', 'email': 'citizen1@varanasi.org'}
        citizen_profile = {'id': '11111111-1111-1111-1111-111111111111', 'role': 'citizen', 'full_name': 'Aarav Sharma'}

        with patch('services.auth_service.extract_bearer_token', return_value='fake-cit-jwt'):
            with patch('services.auth_service.verify_supabase_jwt', return_value=citizen_user):
                with patch('services.auth_service.get_user_profile', return_value=citizen_profile):
                    res = self.client.get('/api/v1/notifications/preferences', headers={'Authorization': 'Bearer fake-cit-jwt'})
                    self.assertEqual(res.status_code, 200)
                    data = res.get_json()
                    self.assertEqual(data.get('status'), 'success')
                    self.assertIn('preferences', data)
                    prefs = data['preferences']
                    self.assertIn('in_app_enabled', prefs)
                    self.assertIn('preferred_severities', prefs)

    # =========================================================================
    # 2. AUTHORITY END-TO-END USER JOURNEY
    # =========================================================================

    def test_04_authority_journey_command_center_overview(self):
        """Authority Journey: Access high-level analytics overview with authority_admin role."""
        admin_user = {'id': 'auth-admin-001', 'email': 'officer@uppcb.gov.in'}
        admin_profile = {'id': 'auth-admin-001', 'role': 'authority_admin', 'full_name': 'Chief Environmental Officer'}

        with patch('services.auth_service.extract_bearer_token', return_value='fake-admin-jwt'):
            with patch('services.auth_service.verify_supabase_jwt', return_value=admin_user):
                with patch('services.auth_service.get_user_profile', return_value=admin_profile):
                    res = self.client.get('/api/v1/analytics/overview', headers={'Authorization': 'Bearer fake-admin-jwt'})
                    self.assertEqual(res.status_code, 200)
                    data = res.get_json()
                    self.assertEqual(data.get('status'), 'success')
                    self.assertIn('stations', data)
                    self.assertIn('devices', data)
                    self.assertIn('cwc_reference_gauge', data)

    def test_05_authority_journey_alert_lifecycle(self):
        """Authority Journey: Acknowledge and resolve an active water quality alert."""
        admin_user = {'id': 'auth-admin-001', 'email': 'officer@uppcb.gov.in'}
        admin_profile = {'id': 'auth-admin-001', 'role': 'authority_admin', 'full_name': 'Chief Environmental Officer'}

        with patch('services.auth_service.extract_bearer_token', return_value='fake-admin-jwt'):
            with patch('services.auth_service.verify_supabase_jwt', return_value=admin_user):
                with patch('services.auth_service.get_user_profile', return_value=admin_profile):
                    with patch('services.alert_service.AlertService.acknowledge_alert', return_value={
                        'status': 'success', 'alert_id': 'alt-999', 'state': 'ACKNOWLEDGED'
                    }):
                        res_ack = self.client.post('/api/v1/alerts/alt-999/acknowledge',
                                                  headers={'Authorization': 'Bearer fake-admin-jwt'},
                                                  json={'notes': 'Field team deployed to inspect upstream drain.'})
                        self.assertEqual(res_ack.status_code, 200)
                        self.assertEqual(res_ack.get_json().get('status'), 'success')

                    with patch('services.alert_service.AlertService.resolve_alert', return_value={
                        'status': 'success', 'alert_id': 'alt-999', 'state': 'RESOLVED'
                    }):
                        res_res = self.client.post('/api/v1/alerts/alt-999/resolve',
                                                  headers={'Authorization': 'Bearer fake-admin-jwt'},
                                                  json={'reason': 'Drain sluice gate closed successfully.'})
                        self.assertEqual(res_res.status_code, 200)
                        self.assertEqual(res_res.get_json().get('status'), 'success')

    def test_06_authority_journey_legal_notice_generation(self):
        """Authority Journey: Generate statutory environmental notice."""
        admin_user = {'id': 'auth-admin-001', 'email': 'officer@uppcb.gov.in'}
        admin_profile = {'id': 'auth-admin-001', 'role': 'authority_admin', 'full_name': 'Chief Environmental Officer'}

        with patch('services.auth_service.extract_bearer_token', return_value='fake-admin-jwt'):
            with patch('services.auth_service.verify_supabase_jwt', return_value=admin_user):
                with patch('services.auth_service.get_user_profile', return_value=admin_profile):
                    payload = {
                        'target_entity': 'Industrial Facility Alpha',
                        'violation_type': 'Direct Effluent Discharge',
                        'location': 'Assi Ghat Drain Outfall'
                    }
                    res = self.client.post('/api/authority/generate-notice',
                                           headers={'Authorization': 'Bearer fake-admin-jwt'},
                                           json=payload)
                    self.assertEqual(res.status_code, 200)
                    data = res.get_json()
                    self.assertEqual(data.get('status'), 'success')
                    self.assertIn('RIVER SENTINEL', data.get('content', ''))

    # =========================================================================
    # 3. FIELD OFFICER JOURNEY & ROLE-BASED ACCESS CONTROL
    # =========================================================================

    def test_07_field_officer_can_view_assigned_station_telemetry(self):
        """Field Officer Journey: Officer accesses station sensor data."""
        officer_user = {'id': 'field-off-01', 'email': 'field1@uppcb.gov.in'}
        officer_profile = {'id': 'field-off-01', 'role': 'field_officer', 'full_name': 'Field Officer Singh'}

        with patch('services.auth_service.extract_bearer_token', return_value='fake-field-jwt'):
            with patch('services.auth_service.verify_supabase_jwt', return_value=officer_user):
                with patch('services.auth_service.get_user_profile', return_value=officer_profile):
                    res = self.client.get('/api/v1/stations/STN-VAR-ASSI-01/latest',
                                          headers={'Authorization': 'Bearer fake-field-jwt'})
                    self.assertEqual(res.status_code, 200)
                    data = res.get_json()
                    self.assertEqual(data.get('status'), 'success')
                    self.assertIn('reading', data)

    def test_08_field_officer_forbidden_from_admin_only_actions(self):
        """Field Officer Journey: Verify RBAC denies access to authority_admin-only endpoints."""
        officer_user = {'id': 'field-off-01', 'email': 'field1@uppcb.gov.in'}
        officer_profile = {'id': 'field-off-01', 'role': 'field_officer', 'full_name': 'Field Officer Singh'}

        with patch('services.auth_service.extract_bearer_token', return_value='fake-field-jwt'):
            with patch('services.auth_service.verify_supabase_jwt', return_value=officer_user):
                with patch('services.auth_service.get_user_profile', return_value=officer_profile):
                    # Trigger alert requires 'authority_admin' role only
                    res = self.client.post('/api/authority/trigger-alert',
                                           headers={'Authorization': 'Bearer fake-field-jwt'},
                                           json={'level': 'HIGH', 'message': 'Simulated Flood Alert'})
                    self.assertEqual(res.status_code, 403)
                    data = res.get_json()
                    self.assertIn('error', data)

    # =========================================================================
    # 4. CROSS-JOURNEY PRIVACY ISOLATION & UNPROTECTED ACCESS CONTROL
    # =========================================================================

    def test_09_unauthenticated_requests_blocked_from_protected_routes(self):
        """Verify unauthenticated requests return 401 on protected endpoints."""
        protected_routes = [
            ('GET', '/api/v1/analytics/overview'),
            ('GET', '/api/v1/notifications/preferences'),
            ('POST', '/api/authority/generate-notice'),
            ('POST', '/api/authority/trigger-alert')
        ]
        for method, route in protected_routes:
            if method == 'GET':
                res = self.client.get(route)
            else:
                res = self.client.post(route, json={})
            self.assertEqual(res.status_code, 401, f"Expected 401 for unauthenticated {method} {route}")
            data = res.get_json()
            self.assertIn('error', data)

    def test_10_csv_telemetry_export_schema_and_units(self):
        """Verify CSV telemetry export contains canonical headers, units and data."""
        res = self.client.get('/api/v1/export/sensor-data')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get('Content-Type'), 'text/csv; charset=utf-8')
        csv_text = res.get_data(as_text=True)
        lines = csv_text.strip().split('\n')
        self.assertGreaterEqual(len(lines), 1)

        # Canonical columns must be present
        header = lines[0]
        expected_cols = ['ID', 'Timestamp_UTC', 'Station_Code', 'Station_Name', 'pH', 'Turbidity_NTU',
                         'Temperature_C', 'DO_mg_L', 'Provenance', 'Quality_Status']
        for col in expected_cols:
            self.assertIn(col, header, f"Missing expected CSV export column: {col}")

    # =========================================================================
    # 5. ERROR ENVELOPES & RFC 7807 COMPLIANCE
    # =========================================================================

    def test_11_error_envelope_standardization(self):
        """Verify API errors contain standard error attributes (error_code, message, status)."""
        res = self.client.get('/api/v1/stations/NON_EXISTENT_STATION_XYZ')
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertEqual(data.get('status'), 'error')
        self.assertEqual(data.get('error_code'), 'NOT_FOUND')
        self.assertIn('message', data)


if __name__ == '__main__':
    unittest.main()
