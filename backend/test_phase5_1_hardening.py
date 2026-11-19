"""
River Sentinel 2.0 - Phase 5.1 Hardening Test Suite
Verifies all 13 required verification scenarios:
1. CPCB Class B evaluation with all 4 statutory criteria present (pH, DO, BOD, Total Coliform).
2. Missing BOD yields partial_assessment and compliant_for_measured_parameters.
3. Missing Total Coliform yields partial_assessment and compliant_for_measured_parameters.
4. Turbidity-only warning tagged as OPERATIONAL_SCREENING / RULE-TURB-HIGH (not CPCB statutory).
5. Simultaneous low DO and high turbidity produce independent simultaneous alerts.
6. Duplicate alert occurrence updates occurrence_count on the existing alert.
7. Two distinct devices going offline produce separate device-specific alert identities.
8. Citizen or field officer callers to outbox trigger receive HTTP 403; X-Worker-Secret allowed.
9. Unauthorized delivery callback to DLR webhook rejected with HTTP 401.
10. GSM 7-bit single and multi-segment encoding calculations.
11. Unicode UCS-2 encoding calculation for Hindi Devanagari template (<= 70 chars).
12. Distinction between carrier acceptance (status='accepted', delivered_at=NULL) and DLR handset delivery.
13. Telephony dispatch safely suppressed/unconfigured when SMS_ENABLED is False.
"""

import os
import sys
import unittest
import uuid
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

# Ensure backend root is in sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import create_app
from services.supabase_service import execute_sql, supabase_get, supabase_insert
from services.alert_service import AlertService
from services.notification_worker import NotificationWorker
from services.sms_service import (
    calculate_sms_segments,
    format_sms_message,
    format_sms_message_hindi,
    validate_indian_phone,
    MockSMSProvider
)


class TestPhase51AlertHardening(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test Flask client and database test fixtures."""
        os.environ['TESTING'] = 'True'
        os.environ['WORKER_API_SECRET'] = 'test_worker_secret_key_varanasi'
        os.environ['SMS_WEBHOOK_SECRET'] = 'test_sms_webhook_token_varanasi'

        cls.app = create_app()
        cls.client = cls.app.test_client()

        # Seed or fetch test station
        stns = supabase_get('monitoring_stations', filters={'station_code': 'eq.STN-VAR-ASSI-01'})
        if stns:
            cls.test_station = stns[0]
        else:
            cls.test_station = {
                'id': str(uuid.uuid4()),
                'station_code': 'STN-VAR-TEST-01',
                'station_name': 'Test Assi Ghat Station',
                'cwc_reference_gauge_id': 'CWC-VAR-001',
                'warning_water_level_m': 70.26,
                'danger_water_level_m': 71.26
            }

        # Seed or resolve test devices for foreign key constraint satisfaction
        d1_rows = execute_sql("SELECT id FROM public.devices WHERE device_code = 'ESP32-P51-DEV-01';")
        if d1_rows:
            cls.test_device_1_id = str(d1_rows[0][0])
        else:
            cls.test_device_1_id = str(uuid.uuid4())
            execute_sql("""
                INSERT INTO public.devices (id, device_code, device_name, station_id, device_type, status, credential_hash)
                VALUES (:id::uuid, 'ESP32-P51-DEV-01', 'Test Node 1', :sid::uuid, 'ESP32-WROOM-32', 'online', 'hash_p51_01');
            """, {'id': cls.test_device_1_id, 'sid': str(cls.test_station['id'])})

        d2_rows = execute_sql("SELECT id FROM public.devices WHERE device_code = 'ESP32-P51-DEV-02';")
        if d2_rows:
            cls.test_device_2_id = str(d2_rows[0][0])
        else:
            cls.test_device_2_id = str(uuid.uuid4())
            execute_sql("""
                INSERT INTO public.devices (id, device_code, device_name, station_id, device_type, status, credential_hash)
                VALUES (:id::uuid, 'ESP32-P51-DEV-02', 'Test Node 2', :sid::uuid, 'ESP32-WROOM-32', 'online', 'hash_p51_02');
            """, {'id': cls.test_device_2_id, 'sid': str(cls.test_station['id'])})

    # ========================================================================
    # 1. CPCB CLASS B SCIENTIFIC CORRECTION & ASSESSMENT ACCURACY
    # ========================================================================

    def test_01_cpcb_class_b_all_four_criteria_present(self):
        """Scenario 1: All 4 statutory criteria evaluated for full CPCB Class B assessment."""
        # 1A. All 4 parameters pass: pH=7.4, DO=6.5 mg/L, BOD=2.1 mg/L, Coliform=300 MPN/100mL
        res_pass = AlertService.evaluate_cpcb_class_b_compliance(
            ph=7.4, do_v=6.5, bod=2.1, total_coliform=300.0
        )
        self.assertEqual(res_pass['compliance_status'], 'compliant_for_measured_parameters')
        self.assertEqual(res_pass['assessment_type'], 'full_assessment')
        self.assertTrue(res_pass['full_class_b_declared'])
        self.assertEqual(res_pass['verdict'], 'CPCB_CLASS_B_COMPLIANT')
        self.assertEqual(len(res_pass['missing_criteria']), 0)
        self.assertTrue(res_pass['criteria']['ph']['passed'])
        self.assertTrue(res_pass['criteria']['dissolved_oxygen']['passed'])
        self.assertTrue(res_pass['criteria']['bod']['passed'])
        self.assertTrue(res_pass['criteria']['total_coliform']['passed'])

        # 1B. One parameter fails (BOD=4.2 > 3.0 statutory limit)
        res_fail = AlertService.evaluate_cpcb_class_b_compliance(
            ph=7.4, do_v=6.5, bod=4.2, total_coliform=300.0
        )
        self.assertEqual(res_fail['compliance_status'], 'non_compliant_for_measured_parameters')
        self.assertEqual(res_fail['assessment_type'], 'full_assessment')
        self.assertTrue(res_fail['full_class_b_declared'])
        self.assertEqual(res_fail['verdict'], 'CPCB_CLASS_B_NON_COMPLIANT')
        self.assertFalse(res_fail['criteria']['bod']['passed'])

    def test_02_cpcb_class_b_missing_bod_partial_assessment(self):
        """Scenario 2: Missing BOD yields partial_assessment and compliant_for_measured_parameters."""
        res = AlertService.evaluate_cpcb_class_b_compliance(
            ph=7.5, do_v=6.2, bod=None, total_coliform=400.0
        )
        self.assertEqual(res['compliance_status'], 'compliant_for_measured_parameters')
        self.assertEqual(res['assessment_type'], 'partial_assessment')
        self.assertFalse(res['full_class_b_declared'])
        self.assertIn('BOD (5-day 20°C <= 3.0 mg/L)', res['missing_criteria'])
        self.assertIn('Statutory CPCB Class B (Outdoor Bathing) requires all 4 criteria', res['disclaimer'])

    def test_03_cpcb_class_b_missing_coliform_partial_assessment(self):
        """Scenario 3: Missing microbiological coliform yields partial_assessment."""
        res = AlertService.evaluate_cpcb_class_b_compliance(
            ph=7.2, do_v=5.8, bod=2.5, total_coliform=None
        )
        self.assertEqual(res['compliance_status'], 'compliant_for_measured_parameters')
        self.assertEqual(res['assessment_type'], 'partial_assessment')
        self.assertFalse(res['full_class_b_declared'])
        self.assertIn('Total Coliform (<= 500 MPN/100 mL)', res['missing_criteria'])

    def test_04_turbidity_operational_screening_not_cpcb_class_b(self):
        """Scenario 4: Turbidity-only exceedance is tagged OPERATIONAL_SCREENING / RULE-TURB-HIGH."""
        stn_id = str(self.test_station['id'])
        obs = {
            'id': str(uuid.uuid4()),
            'station_id': stn_id,
            'ph': 7.4,       # In CPCB range
            'do': 6.8,       # In CPCB range
            'turbidity': 140.0,  # Exceeds 100 NTU operational guideline
            'provenance': 'real_sensor',
            'quality_status': 'valid'
        }
        alerts = AlertService.evaluate_sensor_observation(obs, station_id=stn_id)
        turb_alt = next((a for a in alerts if a.get('rule_code') == 'RULE-TURB-HIGH' or 'Turbidity' in a.get('title', '')), None)
        self.assertIsNotNone(turb_alt, "High turbidity must trigger operational screening alert")
        self.assertEqual(turb_alt['category'], 'OPERATIONAL_SCREENING')
        self.assertEqual(turb_alt['rule_code'], 'RULE-TURB-HIGH')
        self.assertIn('High Turbidity Investigation', turb_alt['title'])

        # Verify alert record in database carries rule metadata
        rule_row = execute_sql("""
            SELECT is_cpcb_statutory, source_reference, rule_version
            FROM public.alert_rules WHERE rule_code = 'RULE-TURB-HIGH';
        """)
        self.assertTrue(len(rule_row) > 0)
        self.assertFalse(rule_row[0][0], "Turbidity rule must have is_cpcb_statutory = FALSE")
        self.assertEqual(rule_row[0][1], 'Project Investigation Guideline v2.0')
        self.assertEqual(rule_row[0][2], 2)

    # ========================================================================
    # 2. GRANULAR ALERT DEDUPLICATION & MULTI-PARAMETER CONCURRENCY
    # ========================================================================

    def test_05_simultaneous_low_do_and_high_turbidity_independent_alerts(self):
        """Scenario 5: Simultaneous low DO (<5.0) and high turbidity (>100) produce 2 distinct alerts."""
        stn_id = str(self.test_station['id'])
        # Cleanup any pre-existing active alerts for this test
        execute_sql("""
            UPDATE public.system_alerts SET status = 'resolved'
            WHERE station_id = :sid::uuid AND status = 'active';
        """, {'sid': stn_id})

        obs = {
            'id': str(uuid.uuid4()),
            'station_id': stn_id,
            'ph': 7.4,
            'do': 4.2,          # Violates CPCB DO minimum (5.0 mg/L)
            'turbidity': 130.0,  # Violates operational turbidity threshold (100.0 NTU)
            'provenance': 'real_sensor',
            'quality_status': 'valid'
        }
        alerts = AlertService.evaluate_sensor_observation(obs, station_id=stn_id)

        # Must generate 2 independent alerts
        self.assertGreaterEqual(len(alerts), 2, "Expected at least 2 distinct alerts for DO and Turbidity")

        do_alt = next((a for a in alerts if a['category'] == 'WATER_QUALITY'), None)
        turb_alt = next((a for a in alerts if a['category'] == 'OPERATIONAL_SCREENING'), None)

        self.assertIsNotNone(do_alt, "Must generate DO alert")
        self.assertIsNotNone(turb_alt, "Must generate Turbidity alert")
        self.assertNotEqual(do_alt['id'], turb_alt['id'], "DO and Turbidity must have independent alert IDs")

        # Verify distinct deduplication keys
        do_db = execute_sql("SELECT deduplication_key, rule_id FROM public.system_alerts WHERE id = :id::uuid;", {'id': do_alt['id']})
        turb_db = execute_sql("SELECT deduplication_key, rule_id FROM public.system_alerts WHERE id = :id::uuid;", {'id': turb_alt['id']})

        self.assertIn(':do', do_db[0][0])
        self.assertIn(':turbidity', turb_db[0][0])
        self.assertNotEqual(do_db[0][0], turb_db[0][0])

    def test_06_duplicate_occurrence_increments_counter(self):
        """Scenario 6: Subsequent observation of identical condition increments occurrence_count."""
        stn_id = str(self.test_station['id'])
        obs = {
            'id': str(uuid.uuid4()),
            'station_id': stn_id,
            'ph': 5.8,       # Violates pH minimum (6.5)
            'do': 6.5,
            'provenance': 'real_sensor',
            'quality_status': 'valid'
        }
        # First trigger
        res1 = AlertService.evaluate_sensor_observation(obs, station_id=stn_id)
        ph_alt1 = next((a for a in res1 if a.get('rule_code') == 'RULE-CPCB-PH-RANGE'), None)
        self.assertIsNotNone(ph_alt1)
        initial_id = ph_alt1['id']

        # Second trigger with identical condition
        obs2 = {
            'id': str(uuid.uuid4()),
            'station_id': stn_id,
            'ph': 5.7,
            'do': 6.5,
            'provenance': 'real_sensor',
            'quality_status': 'valid'
        }
        res2 = AlertService.evaluate_sensor_observation(obs2, station_id=stn_id)
        ph_alt2 = next((a for a in res2 if a.get('rule_code') == 'RULE-CPCB-PH-RANGE'), None)
        self.assertIsNotNone(ph_alt2)
        self.assertEqual(ph_alt2['id'], initial_id, "Duplicate must reuse existing alert record")

        # Verify occurrence count in DB is at least 2
        cnt = execute_sql("SELECT occurrence_count FROM public.system_alerts WHERE id = :id::uuid;", {'id': initial_id})
        self.assertGreaterEqual(cnt[0][0], 2)

    def test_07_device_health_distinct_device_identities(self):
        """Scenario 7: Two different offline devices produce independent device-specific alert identities."""
        dev1_id = self.test_device_1_id
        dev2_id = self.test_device_2_id
        stale_time = (datetime.now(timezone.utc) - timedelta(seconds=1800)).isoformat()

        d1 = {'id': dev1_id, 'device_code': 'ESP32-P51-DEV-01', 'status': 'online', 'last_seen_at': stale_time, 'station_id': str(self.test_station['id'])}
        d2 = {'id': dev2_id, 'device_code': 'ESP32-P51-DEV-02', 'status': 'online', 'last_seen_at': stale_time, 'station_id': str(self.test_station['id'])}

        alt1 = AlertService.evaluate_device_health(d1, station=self.test_station)
        alt2 = AlertService.evaluate_device_health(d2, station=self.test_station)

        self.assertIsNotNone(alt1)
        self.assertIsNotNone(alt2)
        self.assertNotEqual(alt1['id'], alt2['id'], "Different devices must have distinct alert IDs")

        row1 = execute_sql("SELECT deduplication_key FROM public.system_alerts WHERE id = :id::uuid;", {'id': alt1['id']})
        row2 = execute_sql("SELECT deduplication_key FROM public.system_alerts WHERE id = :id::uuid;", {'id': alt2['id']})
        self.assertEqual(row1[0][0], f"RULE-DEV-OFFLINE:{dev1_id}")
        self.assertEqual(row2[0][0], f"RULE-DEV-OFFLINE:{dev2_id}")

    # ========================================================================
    # 3. OUTBOX WORKER AUTHORIZATION & BOUNDED BATCHING
    # ========================================================================

    def test_08_outbox_trigger_authorization_and_guards(self):
        """Scenario 8: Non-authority callers receive HTTP 403; internal X-Worker-Secret succeeds."""
        # 8A. Anonymous caller receives 401
        res_anon = self.client.post('/api/v1/notifications/process-outbox')
        self.assertEqual(res_anon.status_code, 401)

        # 8B. Citizen role receives 403
        with patch('routes.alerts_v1.extract_bearer_token', return_value='citizen_token'):
            with patch('routes.alerts_v1.verify_supabase_jwt', return_value={'id': 'cit-uuid'}):
                with patch('routes.alerts_v1.get_user_profile', return_value={'role': 'citizen', 'full_name': 'Ram Kumar'}):
                    res_cit = self.client.post('/api/v1/notifications/process-outbox', headers={'Authorization': 'Bearer citizen_token'})
                    self.assertEqual(res_cit.status_code, 403)

        # 8C. Field Officer receives 403
        with patch('routes.alerts_v1.extract_bearer_token', return_value='officer_token'):
            with patch('routes.alerts_v1.verify_supabase_jwt', return_value={'id': 'fo-uuid'}):
                with patch('routes.alerts_v1.get_user_profile', return_value={'role': 'field_officer', 'full_name': 'Officer Verma'}):
                    res_fo = self.client.post('/api/v1/notifications/process-outbox', headers={'Authorization': 'Bearer officer_token'})
                    self.assertEqual(res_fo.status_code, 403)

        # 8D. Internal server token X-Worker-Secret succeeds with 200
        res_secret = self.client.post(
            '/api/v1/notifications/process-outbox?limit=10&skip_rate_limit=1',
            headers={'X-Worker-Secret': 'test_worker_secret_key_varanasi'}
        )
        self.assertEqual(res_secret.status_code, 200)
        data = res_secret.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['batch_size'], 10)
        self.assertIn('summary', data)

    # ========================================================================
    # 4. SMS ENCODING & REGULATORY READINESS (GSM 7-bit vs UCS-2)
    # ========================================================================

    def test_10_gsm7_encoding_segment_calculation(self):
        """Scenario 10: Verify GSM 7-bit single and multi-segment calculation."""
        # Single part (<= 160 characters)
        short_ascii = "River Sentinel Alert: Assi Ghat Ganga water stage normal at 68.5m."
        calc1 = calculate_sms_segments(short_ascii)
        self.assertEqual(calc1['encoding'], 'gsm7')
        self.assertEqual(calc1['segments'], 1)
        self.assertFalse(calc1['is_multipart'])
        self.assertGreaterEqual(calc1['remaining_in_segment'], 0)

        # Multi-part (> 160 characters, segmented at 153 chars/segment)
        long_ascii = "A" * 165
        calc2 = calculate_sms_segments(long_ascii)
        self.assertEqual(calc2['encoding'], 'gsm7')
        self.assertEqual(calc2['segments'], 2)
        self.assertTrue(calc2['is_multipart'])

    def test_11_ucs2_unicode_hindi_segment_calculation(self):
        """Scenario 11: Verify Unicode UCS-2 encoding calculation for Hindi message."""
        # Hindi message generated via template
        hindi_msg = format_sms_message_hindi('FLOOD', 'CRITICAL', 'अस्सी घाट', 'जलस्तर', '71.50', 'मी')
        calc = calculate_sms_segments(hindi_msg)
        self.assertEqual(calc['encoding'], 'ucs2')
        self.assertLessEqual(calc['character_count'], 70, "Single-segment Hindi SMS must not exceed 70 characters")
        self.assertEqual(calc['segments'], 1, "Hindi alert template must fit within a single 70-char segment")
        self.assertFalse(calc['is_multipart'])

    # ========================================================================
    # 5. DELIVERY STATUS ACCURACY & DLR WEBHOOK
    # ========================================================================

    def test_09_dlr_webhook_unauthorized_rejected(self):
        """Scenario 9: Unauthorized delivery callback rejected with HTTP 401."""
        res_no_tok = self.client.post('/api/v1/notifications/callback/sms', json={'provider_message_id': 'test-msg'})
        self.assertEqual(res_no_tok.status_code, 401)

        res_bad_tok = self.client.post(
            '/api/v1/notifications/callback/sms',
            headers={'X-SMS-Webhook-Token': 'wrong_secret'},
            json={'provider_message_id': 'test-msg'}
        )
        self.assertEqual(res_bad_tok.status_code, 401)

    def test_12_provider_accepted_vs_delivered_and_replay_prevention(self):
        """Scenario 12: Provider HTTP success sets 'accepted', DLR callback sets 'delivered'."""
        pmid = f"test-prov-{uuid.uuid4().hex[:12]}"
        delivery_id = str(uuid.uuid4())
        alt_id = str(uuid.uuid4())

        # Create a mock alert and delivery in 'accepted' state (simulating HTTP dispatch success)
        now_iso = datetime.now(timezone.utc).isoformat()
        alt_code = f"ALT-DLR-{uuid.uuid4().hex[:8].upper()}"
        execute_sql("""
            INSERT INTO public.system_alerts (
                id, alert_code, title, category, severity, status, source_type, deduplication_key, created_at, updated_at
            ) VALUES (
                :aid::uuid, :code, 'Test DLR Alert', 'FLOOD', 'HIGH', 'active', 'sensor_reading', :dedup, :now, :now
            );
        """, {'aid': alt_id, 'code': alt_code, 'dedup': f"TEST-DLR:{pmid}", 'now': now_iso})

        execute_sql("""
            INSERT INTO public.notification_deliveries (
                id, alert_id, channel, provider, status, provider_message_id, idempotency_key, accepted_at, delivered_at, created_at, updated_at
            ) VALUES (
                :did::uuid, :aid::uuid, 'sms', 'mock', 'accepted', :pmid, :idem, :now, NULL, :now, :now
            );
        """, {'did': delivery_id, 'aid': alt_id, 'pmid': pmid, 'idem': f"idem-{pmid}", 'now': now_iso})

        # Verify initial state: status is 'accepted' and delivered_at is NULL
        initial_row = execute_sql("SELECT status, delivered_at, accepted_at FROM public.notification_deliveries WHERE id = :did::uuid;", {'did': delivery_id})
        self.assertEqual(initial_row[0][0], 'accepted')
        self.assertIsNone(initial_row[0][1], "delivered_at must be NULL when status is accepted")
        self.assertIsNotNone(initial_row[0][2], "accepted_at must be populated on provider acceptance")

        # Now simulate asynchronous carrier DLR webhook callback
        res_dlr = self.client.post(
            '/api/v1/notifications/callback/sms',
            headers={'X-SMS-Webhook-Token': 'test_sms_webhook_token_varanasi'},
            json={
                'provider_message_id': pmid,
                'delivery_status': 'DELIVERED'
            }
        )
        self.assertEqual(res_dlr.status_code, 200)
        dlr_data = res_dlr.get_json()
        self.assertEqual(dlr_data['status'], 'success')
        self.assertEqual(dlr_data['new_status'], 'delivered')

        # Verify delivered_at is now populated in DB
        delivered_row = execute_sql("SELECT status, delivered_at, provider_callback_received_at FROM public.notification_deliveries WHERE id = :did::uuid;", {'did': delivery_id})
        self.assertEqual(delivered_row[0][0], 'delivered')
        self.assertIsNotNone(delivered_row[0][1], "delivered_at must be populated upon terminal DLR callback")
        self.assertIsNotNone(delivered_row[0][2], "provider_callback_received_at must be populated")

        # Test Replay Prevention: second callback must be safely ignored
        res_replay = self.client.post(
            '/api/v1/notifications/callback/sms',
            headers={'X-SMS-Webhook-Token': 'test_sms_webhook_token_varanasi'},
            json={
                'provider_message_id': pmid,
                'delivery_status': 'DELIVERED'
            }
        )
        self.assertEqual(res_replay.status_code, 200)
        replay_data = res_replay.get_json()
        self.assertEqual(replay_data['status'], 'ignored')
        self.assertEqual(replay_data['current_status'], 'delivered')

    def test_13_sms_unconfigured_safety(self):
        """Scenario 13: When SMS_ENABLED is False and provider is unconfigured, delivery fails safely without mock fabrication."""
        pmid_fail = f"test-fail-{uuid.uuid4().hex[:12]}"
        delivery_id = str(uuid.uuid4())
        alt_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()

        alt_code = f"ALT-FAIL-{uuid.uuid4().hex[:8].upper()}"
        execute_sql("""
            INSERT INTO public.system_alerts (
                id, alert_code, title, category, severity, status, source_type, deduplication_key, created_at, updated_at
            ) VALUES (
                :aid::uuid, :code, 'Test Fail Alert', 'FLOOD', 'HIGH', 'active', 'sensor_reading', :dedup, :now, :now
            );
        """, {'aid': alt_id, 'code': alt_code, 'dedup': f"TEST-FAIL:{pmid_fail}", 'now': now_iso})

        # Insert a queued SMS delivery with an external provider (not mock)
        execute_sql("""
            INSERT INTO public.notification_deliveries (
                id, alert_id, recipient_phone, channel, provider, status, idempotency_key, attempt_count, max_attempts, next_attempt_at, created_at, updated_at
            ) VALUES (
                :did::uuid, :aid::uuid, '+919876543210', 'sms', 'twilio', 'queued', :idem, 0, 3, :now, :now, :now
            );
        """, {'did': delivery_id, 'aid': alt_id, 'idem': f"idem-fail-{pmid_fail}", 'now': now_iso})

        # Process outbox with SMS_ENABLED forced to False
        with patch('services.notification_worker.SMS_ENABLED', False):
            stats = NotificationWorker.process_outbox_batch(batch_size=10)
            self.assertGreaterEqual(stats['failed'], 1)

        # Verify delivery is marked failed with GATEWAY_UNCONFIGURED
        fail_row = execute_sql("SELECT status, last_error_code FROM public.notification_deliveries WHERE id = :did::uuid;", {'did': delivery_id})
        self.assertEqual(fail_row[0][0], 'failed')
        self.assertEqual(fail_row[0][1], 'GATEWAY_UNCONFIGURED')


if __name__ == '__main__':
    unittest.main()
