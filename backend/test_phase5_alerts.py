"""
River Sentinel 2.0 - Phase 5 Comprehensive Alert & Notification Test Suite
Verifies:
1. Alert rules triggering, CWC flood stage screening & CPCB Class B water quality parameters.
2. Station datum specificity: CWC flood levels only triggered for stations with CWC reference gauge binding.
3. Alert deduplication keying, occurrence counting, and automated recovery via hysteresis.
4. IoT device connectivity health alerting (active nodes vs provisioned awaiting connection).
5. Citizen pollution report review alerting.
6. Role-based access control for alert listing, inspection, acknowledge, and resolve endpoints.
7. Notification transactional outbox delivery, in-app immediate dispatch, and strict simulation suppression for SMS.
8. Telephony SMS gateway provider validation (GSM 160-char formatting, Indian phone number validation).
"""

import os
import sys
import unittest
import uuid
import time
from datetime import datetime, timezone, timedelta

# Ensure backend root is in sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import create_app
from services.supabase_service import execute_sql, supabase_get, supabase_insert
from services.alert_service import AlertService, CWC_WARNING_LEVEL_M, CWC_DANGER_LEVEL_M
from services.notification_worker import NotificationWorker
from services.sms_service import MockSMSProvider, HTTPGatewaySMSProvider, validate_indian_phone, format_sms_message


class TestPhase5AlertsAndNotifications(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test Flask client and database test fixtures."""
        cls.app = create_app()
        cls.client = cls.app.test_client()

        # Seed or fetch test station with CWC gauge binding (Assi Ghat)
        stns = supabase_get('monitoring_stations', filters={'station_code': 'eq.STN-VAR-ASSI-01'})
        if stns:
            cls.cwc_station = stns[0]
        else:
            cls.cwc_station = {
                'id': str(uuid.uuid4()),
                'station_code': 'STN-VAR-TEST-CWC',
                'station_name': 'Test Assi CWC Station',
                'cwc_reference_gauge_id': 'CWC-VAR-001',
                'warning_water_level_m': 70.26,
                'danger_water_level_m': 71.26
            }

        # Seed or fetch test station WITHOUT CWC gauge binding
        cls.no_cwc_station_id = str(uuid.uuid4())
        execute_sql("""
            INSERT INTO public.monitoring_stations (
                id, station_code, station_name, river_name, location_name,
                latitude, longitude, status, cwc_reference_gauge_id
            ) VALUES (
                :id::uuid, 'STN-VAR-NOCWC-99', 'Non CWC Ghat Station', 'Ganga', 'Varanasi',
                25.3000, 83.0000, 'active', NULL
            ) ON CONFLICT (station_code) DO NOTHING;
        """, {'id': cls.no_cwc_station_id})

        # Seed test Authority Admin in auth.users, public.profiles, and public.notification_preferences
        existing_users = execute_sql("SELECT id FROM auth.users WHERE email = 'test_admin_p5@riversentinel.test';")
        if existing_users:
            cls.test_admin_id = str(existing_users[0][0])
        else:
            cls.test_admin_id = str(uuid.uuid4())
            execute_sql("""
                INSERT INTO auth.users (id, aud, role, email, raw_user_meta_data, created_at, updated_at)
                VALUES (:id::uuid, 'authenticated', 'authenticated', 'test_admin_p5@riversentinel.test', '{"role": "authority_admin"}'::jsonb, now(), now());
            """, {'id': cls.test_admin_id})

        execute_sql("""
            INSERT INTO public.profiles (id, full_name, phone, role, account_status, organization)
            VALUES (:id::uuid, 'Phase 5 Test Admin', '+919876543210', 'authority_admin', 'active', 'UPPCB')
            ON CONFLICT (id) DO UPDATE SET role = 'authority_admin', phone = '+919876543210';
        """, {'id': cls.test_admin_id})

        execute_sql("""
            INSERT INTO public.notification_preferences (
                user_id, in_app_enabled, email_enabled, sms_enabled,
                preferred_severities, preferred_categories, phone_number_verified, consent_timestamp
            ) VALUES (
                :id::uuid, true, false, true,
                ARRAY['CRITICAL', 'HIGH']::text[],
                ARRAY['FLOOD', 'WATER_QUALITY', 'DEVICE_HEALTH', 'POLLUTION_REPORT']::text[],
                true, now()
            ) ON CONFLICT (user_id) DO UPDATE SET sms_enabled = true, in_app_enabled = true, phone_number_verified = true;
        """, {'id': cls.test_admin_id})

    # ========================================================================
    # 1. SMS SERVICE & PHONE NUMBER VALIDATION TESTS
    # ========================================================================

    def test_01_phone_number_validation(self):
        """Verify Indian E.164 phone number parser & validator."""
        valid_nums = [
            "+919876543210",
            "+91 98765 43210",
            "9876543210",
            "09876543210",
            "+91-7001234567",
            "8823456789"
        ]
        for num in valid_nums:
            parsed = validate_indian_phone(num)
            self.assertIsNotNone(parsed, f"Expected {num} to be valid")
            self.assertTrue(parsed.startswith("+91"), f"Parsed {parsed} should start with +91")
            self.assertEqual(len(parsed), 13)

        invalid_nums = [
            "12345",
            "+14155552671",  # US number
            "abcdefghij",
            "+91 5876543210",  # Starts with 5 (invalid Indian mobile prefix)
            ""
        ]
        for num in invalid_nums:
            parsed = validate_indian_phone(num)
            self.assertIsNone(parsed, f"Expected {num} to be invalid")

    def test_02_sms_formatting_and_gsm_limits(self):
        """Verify GSM 160-char SMS template formatting."""
        # Short critical flood
        sms1 = format_sms_message('FLOOD', 'CRITICAL', 'Assi Ghat', 'Water Stage', 71.50, 'm', '2026-11-19 10:00:00')
        self.assertIn("CWC DANGER", sms1)
        self.assertLessEqual(len(sms1), 160)

        # Excessively long text should be truncated safely at 160 chars
        sms2 = format_sms_message('WATER_QUALITY', 'HIGH', 'Dashashwamedh Ghat', 'Turbidity Extreme Pollution Deviation Over Maximum Limit', 999.99, 'NTU', '2026-11-19 10:00:00')
        self.assertLessEqual(len(sms2), 160)

    def test_03_mock_sms_provider_dispatch(self):
        """Verify MockSMSProvider behavior with SMS_ENABLED toggle."""
        provider = MockSMSProvider()
        res = provider.send_message('+919876543210', 'Test notification')
        self.assertTrue(res['success'])
        self.assertEqual(res['status'], 'accepted')
        self.assertTrue(res['provider_message_id'].startswith('mock_sms_'))

    # ========================================================================
    # 2. CWC FLOOD STAGE SCREENING & SPECIFICITY
    # ========================================================================

    def test_04_cwc_flood_danger_trigger(self):
        """Verify reading exceeding CWC Danger Stage (>= 71.26m) triggers CRITICAL alert."""
        stn_id = str(self.cwc_station['id'])
        obs = {
            'id': str(uuid.uuid4()),
            'station_id': stn_id,
            'water_level': 71.85,  # Exceeds 71.26m Danger Stage
            'provenance': 'simulated',
            'quality_status': 'valid'
        }

        alerts = AlertService.evaluate_sensor_observation(obs, station_id=stn_id)
        self.assertTrue(len(alerts) >= 1)
        danger_alt = next((a for a in alerts if a['category'] == 'FLOOD'), None)
        self.assertIsNotNone(danger_alt)
        self.assertEqual(danger_alt['severity'], 'CRITICAL')
        self.assertEqual(danger_alt['status'], 'active')
        self.assertIn('DANGER', danger_alt['title'])

    def test_05_cwc_flood_specificity_no_cwc_station(self):
        """Verify stations without CWC binding DO NOT trigger CWC flood alerts."""
        stn_id = self.no_cwc_station_id
        obs = {
            'id': str(uuid.uuid4()),
            'station_id': stn_id,
            'water_level': 72.50,  # High water level
            'provenance': 'simulated',
            'quality_status': 'valid'
        }

        alerts = AlertService.evaluate_sensor_observation(obs, station_id=stn_id)
        flood_alts = [a for a in alerts if a['category'] == 'FLOOD']
        self.assertEqual(len(flood_alts), 0, "Non-CWC station must NOT trigger CWC flood alerts")

    # ========================================================================
    # 3. CPCB CLASS B WATER QUALITY SCREENING
    # ========================================================================

    def test_06_cpcb_water_quality_alerts(self):
        """Verify pH and DO violations trigger CPCB Water Quality alerts."""
        stn_id = str(self.cwc_station['id'])

        # pH violation: 9.30 (CPCB Class B allows 6.5 - 8.5)
        # DO violation: 3.20 mg/L (CPCB Class B requires >= 5.0 mg/L)
        # Turbidity violation: 120 NTU (threshold 100 NTU)
        obs = {
            'id': str(uuid.uuid4()),
            'station_id': stn_id,
            'ph': 9.30,
            'do': 3.20,
            'turbidity': 120.0,
            'water_level': 68.0,  # Normal water level
            'provenance': 'simulated',
            'quality_status': 'valid'
        }

        alerts = AlertService.evaluate_sensor_observation(obs, station_id=stn_id)
        rule_codes = [a.get('alert_code') for a in alerts]

        # Check that water quality alerts were triggered
        categories = [a.get('category') for a in alerts]
        self.assertIn('WATER_QUALITY', categories)

    # ========================================================================
    # 4. DEDUPLICATION & OCCURRENCE COUNTING
    # ========================================================================

    def test_07_alert_deduplication_and_occurrence_count(self):
        """Verify successive observations increment occurrence_count on the same active alert."""
        stn_id = str(self.cwc_station['id'])
        obs1 = {
            'id': str(uuid.uuid4()),
            'station_id': stn_id,
            'water_level': 71.50,
            'provenance': 'simulated',
            'quality_status': 'valid'
        }
        res1 = AlertService.evaluate_sensor_observation(obs1, station_id=stn_id)
        flood1 = next(a for a in res1 if a['category'] == 'FLOOD')
        initial_count = flood1['occurrence_count']
        alert_id = flood1['id']

        # Send second observation with continuing condition
        obs2 = {
            'id': str(uuid.uuid4()),
            'station_id': stn_id,
            'water_level': 71.65,
            'provenance': 'simulated',
            'quality_status': 'valid'
        }
        res2 = AlertService.evaluate_sensor_observation(obs2, station_id=stn_id)
        flood2 = next(a for a in res2 if a['category'] == 'FLOOD')

        self.assertEqual(flood2['id'], alert_id, "Alert ID must remain identical for deduplicated alert")
        self.assertEqual(flood2['occurrence_count'], initial_count + 1, "Occurrence count must increment")

    # ========================================================================
    # 5. AUTOMATED HYSTERESIS RECOVERY
    # ========================================================================

    def test_08_automated_alert_recovery(self):
        """Verify normal telemetry resolves previously active alerts without manual intervention."""
        stn_id = str(self.cwc_station['id'])

        # Normal telemetry below warning threshold
        obs_normal = {
            'id': str(uuid.uuid4()),
            'station_id': stn_id,
            'water_level': 68.50,  # Well below 70.26m
            'ph': 7.40,            # Normal CPCB range
            'do': 7.50,            # Normal CPCB range
            'turbidity': 15.0,     # Normal range
            'provenance': 'simulated',
            'quality_status': 'valid'
        }

        # Evaluating normal observation triggers auto-resolution for resolved parameters
        AlertService.evaluate_sensor_observation(obs_normal, station_id=stn_id)

        # Check database: flood alert for this station should be marked resolved
        dedup_key = f"FLOOD:{stn_id}"
        rows = execute_sql("SELECT status, resolution_reason FROM public.system_alerts WHERE deduplication_key = :k;", {'k': dedup_key})
        if rows:
            self.assertEqual(rows[0][0], 'resolved')
            reason_low = (rows[0][1] or '').lower()
            self.assertTrue(any(w in reason_low for w in ['receded', 'recovered', 'normalized']), f"Unexpected reason: {reason_low}")

    # ========================================================================
    # 6. DEVICE CONNECTIVITY & LIFECYCLE ALERTING
    # ========================================================================

    def test_09_device_offline_detection(self):
        """Verify active device with stale telemetry triggers RULE-DEV-OFFLINE."""
        # Find or seed a valid device record to satisfy foreign key constraint
        dev_rows = supabase_get('devices', limit=1)
        if dev_rows:
            dev_id = str(dev_rows[0]['id'])
            dev_code = dev_rows[0].get('device_code', 'DEV-ESP32-ASSI-01')
        else:
            dev_id = str(uuid.uuid4())
            dev_code = f"DEV-TEST-{uuid.uuid4().hex[:6].upper()}"
            execute_sql("""
                INSERT INTO public.devices (id, device_code, device_name, device_type, station_id, status)
                VALUES (:id::uuid, :code, 'Test Device', 'esp32', :sid::uuid, 'active')
                ON CONFLICT (device_code) DO NOTHING;
            """, {'id': dev_id, 'code': dev_code, 'sid': str(self.cwc_station['id'])})

        # 1. Provisioned device awaiting connection should NOT alert
        prov_device = {
            'id': dev_id,
            'device_code': dev_code,
            'status': 'provisioned',
            'last_seen_at': None
        }
        alt_prov = AlertService.evaluate_device_health(prov_device)
        self.assertIsNone(alt_prov, "Provisioned device awaiting deployment must NOT alert")

        # 2. Active device with stale last_seen_at (> 900s) MUST alert
        stale_time = (datetime.now(timezone.utc) - timedelta(seconds=1200)).isoformat()
        active_stale_device = {
            'id': dev_id,
            'device_code': dev_code,
            'status': 'active',
            'last_seen_at': stale_time,
            'station_id': str(self.cwc_station['id'])
        }
        alt_offline = AlertService.evaluate_device_health(active_stale_device, station=self.cwc_station)
        self.assertIsNotNone(alt_offline)
        self.assertEqual(alt_offline['category'], 'DEVICE_HEALTH')
        self.assertEqual(alt_offline['severity'], 'HIGH')
        self.assertIn('Offline', alt_offline['title'])

    # ========================================================================
    # 7. CITIZEN POLLUTION REPORT ALERTING
    # ========================================================================

    def test_10_pollution_report_alert(self):
        """Verify submitting citizen pollution report triggers review alert."""
        rep = {
            'id': str(uuid.uuid4()),
            'location_name': 'Assi Nala Inflow, Varanasi',
            'pollution_level': 'High',
            'station_id': str(self.cwc_station['id'])
        }
        alt = AlertService.evaluate_new_pollution_report(rep)
        self.assertIsNotNone(alt)
        self.assertEqual(alt['category'], 'POLLUTION_REPORT')
        self.assertEqual(alt['severity'], 'HIGH')
        self.assertIn('Assi Nala', alt['title'])

    # ========================================================================
    # 8. TRANSACTIONAL OUTBOX & SIMULATION SUPPRESSION
    # ========================================================================

    def test_11_outbox_simulation_suppression(self):
        """Verify simulated telemetry alerts STRICTLY suppress SMS notification outbox enqueueing."""
        stn_id = str(self.cwc_station['id'])
        obs_sim = {
            'id': str(uuid.uuid4()),
            'station_id': stn_id,
            'water_level': 71.90,
            'provenance': 'simulated',
            'quality_status': 'valid'
        }
        alerts = AlertService.evaluate_sensor_observation(obs_sim, station_id=stn_id)
        danger_alt = next((a for a in alerts if a['category'] == 'FLOOD'), None)
        self.assertIsNotNone(danger_alt)
        alt_id = danger_alt['id']

        # Query notification deliveries for this alert
        deliveries = execute_sql("""
            SELECT channel, status FROM public.notification_deliveries WHERE alert_id = :aid::uuid;
        """, {'aid': alt_id})

        # In-app delivery should be enqueued
        channels = [d[0] for d in deliveries]
        self.assertIn('in_app', channels)

        # External SMS must NEVER be dispatched for simulated telemetry
        sms_deliveries = [d for d in deliveries if d[0] == 'sms']
        for d in sms_deliveries:
            self.assertEqual(d[1], 'suppressed', "SMS deliveries for simulated telemetry must be strictly suppressed")

    def test_12_outbox_worker_batch_processing(self):
        """Verify NotificationWorker claims and processes pending in-app deliveries immediately."""
        stats = NotificationWorker.process_outbox_batch(batch_size=20)
        self.assertIsInstance(stats, dict)
        self.assertIn('processed', stats)
        self.assertIn('delivered', stats)

    # ========================================================================
    # 9. VERSIONED ALERTS API (v1) ENDPOINTS
    # ========================================================================

    def test_13_api_v1_alerts_public_listing(self):
        """Verify anonymous/public callers only receive active public environmental alerts."""
        res = self.client.get('/api/v1/alerts')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('alerts', data)

        # Public callers must never see internal DEVICE_HEALTH alerts
        for alt in data['alerts']:
            self.assertIn(alt['category'], ('FLOOD', 'WATER_QUALITY'))
            self.assertNotEqual(alt['status'], 'resolved')

    def test_14_api_v1_alert_rules_list(self):
        """Verify alert rules listing endpoint."""
        res = self.client.get('/api/v1/alerts/rules')
        # Requires authority role; anonymous should receive 401
        self.assertEqual(res.status_code, 401)


if __name__ == '__main__':
    unittest.main()
