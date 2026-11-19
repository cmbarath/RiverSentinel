"""
River Sentinel 2.0 - Phase 7 System Reliability & Integration Test Suite
Validates:
1. Liveness Probe (/api/health/live)
2. Readiness Probe (/api/health/ready)
3. Authorized Operational Diagnostics (/api/health/status)
4. Structured Logging & Correlation Header Propagation
5. Global Sanitized Error Handlers
6. Notification Outbox Worker Batch Claiming & Heartbeat Recording
7. Stuck Processing Job Recovery
8. Sensor Telemetry Future-Timestamp Drift Rejection
9. Sensor Telemetry Message Deduplication & Idempotency
10. Sensor Stale-Data Detection & Parameter Quality Status
11. AI Provider Timeout & Resilience Handling
12. ML Governance & Alert Suppression Invariance
13. Role-Based Access Control (RBAC) Security Boundaries
14. Automated Database Backup & Isolated Restore Verification
"""

import os
import sys
import unittest
import json
import uuid
import time
from datetime import datetime, timezone, timedelta

# Ensure backend root is in sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import create_app
from services.supabase_service import execute_sql, supabase_get, supabase_insert
from services.device_auth_service import hash_device_token, generate_device_token
from services.notification_worker import NotificationWorker
from scripts.backup_database import backup_database
from scripts.restore_database import restore_and_verify_isolated

TEST_DEVICE_CODE = "DEV-TEST-ESP32-PHASE7"
TEST_DEVICE_TOKEN = generate_device_token()


class TestPhase7Reliability(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()
        cls.worker_secret = os.getenv('WORKER_API_SECRET', 'test_worker_secret_key_varanasi')

        # Provision test device for telemetry testing
        execute_sql("DELETE FROM public.devices WHERE device_code = :dc;", {'dc': TEST_DEVICE_CODE})
        stations = supabase_get('monitoring_stations', limit=1)
        cls.station_id = stations[0]['id'] if stations else None

        supabase_insert('devices', {
            'device_code': TEST_DEVICE_CODE,
            'device_name': 'Phase 7 Test Node',
            'station_id': cls.station_id,
            'device_type': 'ESP32-WROOM-32',
            'firmware_version': 'v2.0.0-phase7',
            'credential_hash': hash_device_token(TEST_DEVICE_TOKEN),
            'status': 'online'
        })

    @classmethod
    def tearDownClass(cls):
        execute_sql("DELETE FROM public.devices WHERE device_code = :dc;", {'dc': TEST_DEVICE_CODE})

    def test_01_liveness_probe(self):
        """Verify lightweight /api/health/live probe returns 200 alive."""
        res = self.client.get('/api/health/live')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get('status'), 'alive')
        self.assertIn('uptime_seconds', data)
        self.assertIn('timestamp', data)

    def test_02_readiness_probe(self):
        """Verify /api/health/ready performs dependency checks without exposing secrets."""
        res = self.client.get('/api/health/ready')
        self.assertIn(res.status_code, [200, 503])
        data = res.get_json()
        self.assertIn(data.get('status'), ['healthy', 'degraded', 'unavailable'])
        self.assertIn('database', data)
        self.assertIn('models', data)
        self.assertIn('workers', data)
        # Ensure no sensitive credentials leaked
        text = res.get_data(as_text=True)
        self.assertNotIn('service_role', text)
        self.assertNotIn('SUPABASE_DB_PASSWORD', text)
        self.assertNotIn('GROQ_API_KEY', text)

    def test_03_health_status_security(self):
        """Verify /api/health/status rejects anonymous requests and succeeds with worker secret."""
        anon_res = self.client.get('/api/health/status')
        self.assertEqual(anon_res.status_code, 403)

        auth_res = self.client.get('/api/health/status', headers={'X-Worker-Secret': self.worker_secret})
        self.assertEqual(auth_res.status_code, 200)
        data = auth_res.get_json()
        self.assertEqual(data.get('status'), 'success')
        self.assertIn('database', data)
        self.assertIn('flood_inference', data)
        self.assertIn('water_quality_evaluation', data)
        self.assertIn('notification_worker', data)

    def test_04_structured_logging_correlation_headers(self):
        """Verify incoming requests receive correlation ID and request ID response headers."""
        custom_corr_id = f"test-corr-{uuid.uuid4()}"
        res = self.client.get('/api/health/live', headers={'X-Correlation-ID': custom_corr_id})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get('X-Correlation-ID'), custom_corr_id)
        self.assertTrue(res.headers.get('X-Request-ID'))

    def test_05_sanitized_error_handling(self):
        """Verify 404 and client errors return sanitized JSON with correlation ID."""
        res = self.client.get('/api/non_existent_endpoint_for_test')
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertEqual(data.get('status'), 'error')
        self.assertIn('correlation_id', data)
        self.assertEqual(data.get('error_code'), 'RESOURCE_NOT_FOUND')

    def test_06_worker_batch_claiming_and_heartbeat(self):
        """Verify notification worker runs a batch and updates worker_heartbeats."""
        stats = NotificationWorker.process_outbox_batch(batch_size=5)
        self.assertIsInstance(stats, dict)
        self.assertIn('processed', stats)
        self.assertIn('recovered_stuck', stats)

        rows = execute_sql("SELECT worker_name, status, last_heartbeat FROM public.worker_heartbeats WHERE worker_name = 'notification_worker';")
        self.assertTrue(len(rows) > 0)
        self.assertEqual(rows[0][0], 'notification_worker')

    def test_07_worker_stuck_job_recovery(self):
        """Verify worker automatically recovers stuck processing jobs older than 5 minutes."""
        now_dt = datetime.now(timezone.utc)
        stuck_time = (now_dt - timedelta(minutes=10)).isoformat()
        test_delivery_id = str(uuid.uuid4())
        alert_rows = execute_sql("SELECT id FROM public.system_alerts LIMIT 1;")
        alert_id = str(alert_rows[0][0]) if alert_rows else str(uuid.uuid4())

        # Seed an artificial stuck delivery record
        try:
            execute_sql("""
                INSERT INTO public.notification_deliveries (
                    id, alert_id, idempotency_key, channel, provider, status, recipient_phone, attempt_count, max_attempts, updated_at, created_at
                ) VALUES (
                    :id::uuid, :aid::uuid, :idem, 'sms', 'mock', 'processing', '+919876543210', 1, 3, :stuck_t, :stuck_t
                );
            """, {'id': test_delivery_id, 'aid': alert_id, 'idem': f"IDEM-{test_delivery_id}", 'stuck_t': stuck_time})

            recovered = NotificationWorker.recover_stuck_processing_jobs(stuck_timeout_seconds=300)
            self.assertGreaterEqual(recovered, 1)

            check = execute_sql("SELECT status FROM public.notification_deliveries WHERE id = :id::uuid;", {'id': test_delivery_id})
            if check:
                self.assertEqual(check[0][0], 'queued')
        finally:
            execute_sql("DELETE FROM public.notification_deliveries WHERE id = :id::uuid;", {'id': test_delivery_id})

    def test_08_sensor_future_timestamp_rejected(self):
        """Verify edge telemetry rejects future timestamps exceeding 300s clock drift."""
        future_time = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        payload = {
            'schema_version': '2.0',
            'message_id': str(uuid.uuid4()),
            'sequence_number': 1,
            'observed_at': future_time,
            'sensor_readings': {'ph': 7.4, 'turbidity': 15.0}
        }
        res = self.client.post(
            '/api/v1/telemetry/ingest',
            headers={'X-Device-Code': TEST_DEVICE_CODE, 'X-Device-Token': TEST_DEVICE_TOKEN},
            json=payload
        )
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data.get('error_code'), 'FUTURE_TIMESTAMP')

    def test_09_sensor_message_deduplication(self):
        """Verify edge telemetry endpoint is idempotent on duplicate message_id."""
        msg_id = str(uuid.uuid4())
        valid_time = datetime.now(timezone.utc).isoformat()
        payload = {
            'schema_version': '2.0',
            'message_id': msg_id,
            'sequence_number': 1,
            'observed_at': valid_time,
            'sensor_readings': {'ph': 7.45, 'turbidity': 12.0}
        }
        headers = {
            'X-Device-Code': TEST_DEVICE_CODE,
            'X-Device-Token': TEST_DEVICE_TOKEN
        }
        res1 = self.client.post('/api/v1/telemetry/ingest', headers=headers, json=payload)
        self.assertEqual(res1.status_code, 201)

        # Duplicate submission with identical message_id
        res2 = self.client.post('/api/v1/telemetry/ingest', headers=headers, json=payload)
        self.assertEqual(res2.status_code, 200)
        data2 = res2.get_json()
        self.assertTrue(data2.get('duplicate'))

    def test_10_sensors_latest_stale_detection(self):
        """Verify /api/sensors/latest provides staleness metrics and missing parameter tracking."""
        res = self.client.get('/api/sensors/latest')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('is_stale', data)
        self.assertIn('time_since_last_observation_seconds', data)
        self.assertIn('missing_parameters', data)
        self.assertIn('quality_status', data)

    def test_11_ai_resilience(self):
        """Verify AI endpoints reject empty inputs cleanly without unhandled crashes."""
        res = self.client.post('/api/ai/chat', json={})
        self.assertEqual(res.status_code, 400)

        res_img = self.client.post('/api/ai/analyze-image', data={})
        self.assertEqual(res_img.status_code, 400)

    def test_12_ml_governance_invariance(self):
        """Verify ML endpoints strictly maintain research_only status and alert suppression."""
        res_flood = self.client.post('/api/flood/predict', json={'water_level': 67.8})
        self.assertEqual(res_flood.status_code, 200)
        data_flood = res_flood.get_json()
        self.assertEqual(data_flood.get('model_version'), 'flood_stage_forecaster_v1')
        self.assertEqual(data_flood.get('prediction_status'), 'research_only')
        self.assertFalse(data_flood.get('alert_eligible'))

        res_wq = self.client.post('/api/water-quality/predict', json={'ph': 7.6, 'do': 6.5})
        self.assertEqual(res_wq.status_code, 200)
        data_wq = res_wq.get_json()
        self.assertEqual(data_wq.get('model_version'), 'water_quality_evaluator_v1')
        self.assertFalse(data_wq.get('alert_eligible'))

    def test_13_rbac_security_boundaries(self):
        """Verify authority administration endpoints reject anonymous callers."""
        res_rules = self.client.get('/api/v1/alerts/rules')
        self.assertEqual(res_rules.status_code, 401)

        res_outbox = self.client.post('/api/v1/notifications/process-outbox')
        self.assertEqual(res_outbox.status_code, 401)

    def test_14_backup_and_isolated_restore(self):
        """Verify automated backup creation and subsequent isolated restore verification."""
        backup_path = backup_database()
        self.assertTrue(os.path.exists(backup_path))

        report = restore_and_verify_isolated(backup_path)
        self.assertTrue(report['success'])
        self.assertEqual(len(report['discrepancies']), 0)
        self.assertEqual(report['foreign_key_integrity']['status'], 'PASSED')
        self.assertLess(report['restore_duration_seconds'], 10.0)


if __name__ == '__main__':
    unittest.main()
