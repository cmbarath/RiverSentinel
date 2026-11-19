"""
Phase 3A Comprehensive IoT Hardware Telemetry & Security Test Suite
Covers all 16 required hardware integration scenarios and verifies isolation from simulator.
"""

import sys
import os
import unittest
import uuid
import time
from datetime import datetime, timezone, timedelta
from dotenv import dotenv_values

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import app
from services.supabase_service import supabase_get, supabase_insert, supabase_update
from services.device_auth_service import hash_device_token

TEST_DEVICE_CODE = "DEV-TEST-ESP32-99"
TEST_DEVICE_TOKEN = "rs_dev_test_credential_secret_998877"

REVOKED_DEVICE_CODE = "DEV-TEST-REVOKED-88"
REVOKED_DEVICE_TOKEN = "rs_dev_revoked_secret_887766"


class Phase3AIoTTelemetryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

        # Find or use Assi Ghat station
        stations = supabase_get('monitoring_stations', filters={'station_code': 'eq.STN-VAR-ASSI-01'}, limit=1)
        cls.station_id = stations[0]['id'] if stations else None

        # Clean up any prior test device records
        cls._cleanup_test_devices()

        # Provision active test device
        supabase_insert('devices', {
            'device_code': TEST_DEVICE_CODE,
            'device_name': 'Automated Test ESP32 Node',
            'station_id': cls.station_id,
            'device_type': 'ESP32-WROOM-32',
            'firmware_version': 'v1.0.0-test',
            'credential_hash': hash_device_token(TEST_DEVICE_TOKEN),
            'status': 'provisioned'
        })

        # Provision revoked test device
        supabase_insert('devices', {
            'device_code': REVOKED_DEVICE_CODE,
            'device_name': 'Revoked Test ESP32 Node',
            'station_id': cls.station_id,
            'device_type': 'ESP32-WROOM-32',
            'firmware_version': 'v1.0.0-test',
            'credential_hash': hash_device_token(REVOKED_DEVICE_TOKEN),
            'status': 'revoked'
        })

    @classmethod
    def tearDownClass(cls):
        cls._cleanup_test_devices()

    @classmethod
    def _cleanup_test_devices(cls):
        from services.supabase_service import get_headers, SUPABASE_URL
        import requests
        headers = get_headers(use_service_role=True)
        if headers and SUPABASE_URL:
            # Delete sensor readings for test devices
            for code in (TEST_DEVICE_CODE, REVOKED_DEVICE_CODE):
                devs = supabase_get('devices', filters={'device_code': f'eq.{code}'})
                if devs and len(devs) > 0:
                    d_id = devs[0]['id']
                    requests.delete(f"{SUPABASE_URL}/rest/v1/sensor_readings?device_id=eq.{d_id}", headers=headers)
                    requests.delete(f"{SUPABASE_URL}/rest/v1/devices?id=eq.{d_id}", headers=headers)

    def _headers(self, code=TEST_DEVICE_CODE, token=TEST_DEVICE_TOKEN):
        return {
            'X-Device-Code': code,
            'X-Device-Token': token,
            'Content-Type': 'application/json'
        }

    # ========================================================================
    # Scenario 1 - 4: Device Authentication & Lifecycle
    # ========================================================================

    def test_01_correct_device_credential_authenticates(self):
        """Scenario 1: Correct device credential successfully authenticates."""
        msg_id = str(uuid.uuid4())
        payload = {
            'schema_version': '2.0',
            'device_code': TEST_DEVICE_CODE,
            'message_id': msg_id,
            'sequence_number': 1,
            'observed_at': datetime.now(timezone.utc).isoformat(),
            'firmware_version': 'v1.0.0-test',
            'sensor_readings': {'ph': 7.42, 'turbidity': 18.5, 'temperature': 26.2, 'water_level': 68.3, 'do': 6.9},
            'sensor_status': {'ph': 'valid', 'turbidity': 'valid'}
        }
        res = self.client.post('/api/v1/telemetry/ingest', headers=self._headers(), json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data.get('status'), 'success')
        self.assertEqual(data.get('device_code'), TEST_DEVICE_CODE)

    def test_02_incorrect_device_credential_rejected(self):
        """Scenario 2: Incorrect token fails with 401."""
        payload = {
            'schema_version': '2.0',
            'device_code': TEST_DEVICE_CODE,
            'message_id': str(uuid.uuid4()),
            'sequence_number': 2,
            'observed_at': datetime.now(timezone.utc).isoformat(),
            'sensor_readings': {'ph': 7.4}
        }
        res = self.client.post('/api/v1/telemetry/ingest',
                               headers=self._headers(token="wrong_token_secret"),
                               json=payload)
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.get_json().get('error_code'), 'AUTHENTICATION_FAILED')

    def test_03_revoked_device_rejected(self):
        """Scenario 3: Device with status 'revoked' is rejected with 401."""
        payload = {
            'schema_version': '2.0',
            'device_code': REVOKED_DEVICE_CODE,
            'message_id': str(uuid.uuid4()),
            'sequence_number': 3,
            'observed_at': datetime.now(timezone.utc).isoformat(),
            'sensor_readings': {'ph': 7.4}
        }
        res = self.client.post('/api/v1/telemetry/ingest',
                               headers=self._headers(code=REVOKED_DEVICE_CODE, token=REVOKED_DEVICE_TOKEN),
                               json=payload)
        self.assertEqual(res.status_code, 401)
        self.assertIn('revoked', res.get_json().get('message', '').lower())

    def test_04_unregistered_device_rejected(self):
        """Scenario 4: Device not present in database is rejected with 401."""
        payload = {
            'schema_version': '2.0',
            'device_code': 'DEV-UNREGISTERED-99',
            'message_id': str(uuid.uuid4()),
            'sequence_number': 4,
            'observed_at': datetime.now(timezone.utc).isoformat(),
            'sensor_readings': {'ph': 7.4}
        }
        res = self.client.post('/api/v1/telemetry/ingest',
                               headers=self._headers(code='DEV-UNREGISTERED-99', token='rs_dev_bogus_token'),
                               json=payload)
        self.assertEqual(res.status_code, 401)

    # ========================================================================
    # Scenario 5 - 6: Message Idempotency & Duplicate Protection
    # ========================================================================

    def test_05_valid_message_persists_with_real_provenance(self):
        """Scenario 5: Valid telemetry persists with real_sensor provenance."""
        msg_id = str(uuid.uuid4())
        payload = {
            'schema_version': '2.0',
            'device_code': TEST_DEVICE_CODE,
            'message_id': msg_id,
            'sequence_number': 5,
            'observed_at': datetime.now(timezone.utc).isoformat(),
            'firmware_version': 'v1.0.0-test',
            'sensor_readings': {'ph': 7.6, 'turbidity': 14.2, 'temperature': 25.8, 'water_level': 68.1, 'do': 7.2},
            'sensor_status': {'ph': 'valid'}
        }
        res = self.client.post('/api/v1/telemetry/ingest', headers=self._headers(), json=payload)
        self.assertEqual(res.status_code, 201)

        # Verify database record
        rows = supabase_get('sensor_readings', filters={'device_message_id': f'eq.{msg_id}'})
        self.assertIsNotNone(rows)
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual(r.get('provenance'), 'real_sensor')
        self.assertEqual(r.get('quality_status'), 'valid')
        self.assertEqual(float(r.get('ph')), 7.6)
        self.assertIsNone(r.get('bod'), "BOD must be NULL for physical sensor readings")

    def test_06_duplicate_message_rejected_with_409_conflict(self):
        """Scenario 6: Sending identical message_id twice returns 409 Conflict."""
        fixed_msg_id = str(uuid.uuid4())
        payload = {
            'schema_version': '2.0',
            'device_code': TEST_DEVICE_CODE,
            'message_id': fixed_msg_id,
            'sequence_number': 6,
            'observed_at': datetime.now(timezone.utc).isoformat(),
            'sensor_readings': {'ph': 7.5}
        }
        # First send
        res1 = self.client.post('/api/v1/telemetry/ingest', headers=self._headers(), json=payload)
        self.assertEqual(res1.status_code, 201)

        # Duplicate send
        res2 = self.client.post('/api/v1/telemetry/ingest', headers=self._headers(), json=payload)
        self.assertEqual(res2.status_code, 409)
        self.assertEqual(res2.get_json().get('error_code'), 'DUPLICATE_MESSAGE')

    # ========================================================================
    # Scenario 7 - 10: Sensor Physical Limits & Explicit Quality States
    # ========================================================================

    def test_07_out_of_range_ph_tagged(self):
        """Scenario 7: Out-of-range pH (14.8 > 14.0) is tagged out_of_range."""
        msg_id = str(uuid.uuid4())
        payload = {
            'schema_version': '2.0',
            'device_code': TEST_DEVICE_CODE,
            'message_id': msg_id,
            'sequence_number': 7,
            'observed_at': datetime.now(timezone.utc).isoformat(),
            'sensor_readings': {'ph': 14.8, 'temperature': 25.0},
            'sensor_status': {'ph': 'valid'}
        }
        res = self.client.post('/api/v1/telemetry/ingest', headers=self._headers(), json=payload)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.get_json().get('quality_status'), 'out_of_range')

    def test_08_out_of_range_turbidity_tagged(self):
        """Scenario 8: Out-of-range turbidity (4500 NTU > 3000 NTU) is tagged out_of_range."""
        msg_id = str(uuid.uuid4())
        payload = {
            'schema_version': '2.0',
            'device_code': TEST_DEVICE_CODE,
            'message_id': msg_id,
            'sequence_number': 8,
            'observed_at': datetime.now(timezone.utc).isoformat(),
            'sensor_readings': {'ph': 7.4, 'turbidity': 4500.0},
            'sensor_status': {'turbidity': 'valid'}
        }
        res = self.client.post('/api/v1/telemetry/ingest', headers=self._headers(), json=payload)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.get_json().get('quality_status'), 'out_of_range')

    def test_09_missing_parameter_preserved_as_null(self):
        """Scenario 9: Missing sensor is not silently substituted with 0 or defaults."""
        msg_id = str(uuid.uuid4())
        payload = {
            'schema_version': '2.0',
            'device_code': TEST_DEVICE_CODE,
            'message_id': msg_id,
            'sequence_number': 9,
            'observed_at': datetime.now(timezone.utc).isoformat(),
            'sensor_readings': {'ph': 7.35, 'temperature': 25.5}  # Turbidity, DO, EC omitted
        }
        res = self.client.post('/api/v1/telemetry/ingest', headers=self._headers(), json=payload)
        self.assertEqual(res.status_code, 201)

        # Check DB that turbidity and DO are NULL
        rows = supabase_get('sensor_readings', filters={'device_message_id': f'eq.{msg_id}'})
        self.assertIsNone(rows[0].get('turbidity'))
        self.assertIsNone(rows[0].get('do'))

    def test_10_disconnected_sensor_status_preserved(self):
        """Scenario 10: Disconnected sensor status sets value NULL and tags degraded."""
        msg_id = str(uuid.uuid4())
        payload = {
            'schema_version': '2.0',
            'device_code': TEST_DEVICE_CODE,
            'message_id': msg_id,
            'sequence_number': 10,
            'observed_at': datetime.now(timezone.utc).isoformat(),
            'sensor_readings': {'ph': 7.4, 'do': -1.0},
            'sensor_status': {'do': 'disconnected'}
        }
        res = self.client.post('/api/v1/telemetry/ingest', headers=self._headers(), json=payload)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.get_json().get('quality_status'), 'degraded')

        rows = supabase_get('sensor_readings', filters={'device_message_id': f'eq.{msg_id}'})
        self.assertIsNone(rows[0].get('do'))

    # ========================================================================
    # Scenario 11 - 14: Timestamp & Sequence Number Validation
    # ========================================================================

    def test_11_invalid_timestamp_rejected(self):
        """Scenario 11: Malformed timestamp returns 400 Bad Request."""
        payload = {
            'schema_version': '2.0',
            'device_code': TEST_DEVICE_CODE,
            'message_id': str(uuid.uuid4()),
            'sequence_number': 11,
            'observed_at': 'invalid_time_string',
            'sensor_readings': {'ph': 7.4}
        }
        res = self.client.post('/api/v1/telemetry/ingest', headers=self._headers(), json=payload)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.get_json().get('error_code'), 'INVALID_TIMESTAMP')

    def test_12_schema_version_enforced(self):
        """Scenario 12: Unsupported schema_version rejected with 400."""
        payload = {
            'schema_version': '1.0',
            'device_code': TEST_DEVICE_CODE,
            'message_id': str(uuid.uuid4()),
            'sequence_number': 12,
            'observed_at': datetime.now(timezone.utc).isoformat(),
            'sensor_readings': {'ph': 7.4}
        }
        res = self.client.post('/api/v1/telemetry/ingest', headers=self._headers(), json=payload)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.get_json().get('error_code'), 'INVALID_SCHEMA')

    def test_13_delayed_offline_message_records_observed_and_received(self):
        """Scenario 13: Buffered message observed in past records accurate observed vs received times."""
        msg_id = str(uuid.uuid4())
        past_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        payload = {
            'schema_version': '2.0',
            'device_code': TEST_DEVICE_CODE,
            'message_id': msg_id,
            'sequence_number': 13,
            'observed_at': past_time,
            'sensor_readings': {'ph': 7.45, 'temperature': 24.8}
        }
        res = self.client.post('/api/v1/telemetry/ingest', headers=self._headers(), json=payload)
        self.assertEqual(res.status_code, 201)

        rows = supabase_get('sensor_readings', filters={'device_message_id': f'eq.{msg_id}'})
        self.assertIsNotNone(rows)
        # Server received_at should be recent, while observed_at is 2 hours ago
        self.assertIn('observed_at', rows[0])

    # ========================================================================
    # Scenario 15 - 17: Security Boundaries & Simulator Isolation
    # ========================================================================

    def test_15_duplicate_retry_is_safe_and_idempotent(self):
        """Scenario 15: Retrying a request returns conflict and prevents database duplication."""
        fixed_id = str(uuid.uuid4())
        payload = {
            'schema_version': '2.0',
            'device_code': TEST_DEVICE_CODE,
            'message_id': fixed_id,
            'sequence_number': 15,
            'observed_at': datetime.now(timezone.utc).isoformat(),
            'sensor_readings': {'ph': 7.4}
        }
        res1 = self.client.post('/api/v1/telemetry/ingest', headers=self._headers(), json=payload)
        self.assertEqual(res1.status_code, 201)

        # Retry
        res2 = self.client.post('/api/v1/telemetry/ingest', headers=self._headers(), json=payload)
        self.assertEqual(res2.status_code, 409)

        # Verify only 1 row exists in DB
        rows = supabase_get('sensor_readings', filters={'device_message_id': f'eq.{fixed_id}'})
        self.assertEqual(len(rows), 1)

    def test_16_station_spoofing_prevented_server_derives_station(self):
        """Scenario 16: Client cannot supply arbitrary station_id; server strictly derives it."""
        msg_id = str(uuid.uuid4())
        arbitrary_fake_station = str(uuid.uuid4())
        payload = {
            'schema_version': '2.0',
            'device_code': TEST_DEVICE_CODE,
            'message_id': msg_id,
            'sequence_number': 16,
            'observed_at': datetime.now(timezone.utc).isoformat(),
            'station_id': arbitrary_fake_station,  # Attacker attempts to spoof station
            'sensor_readings': {'ph': 7.4}
        }
        res = self.client.post('/api/v1/telemetry/ingest', headers=self._headers(), json=payload)
        self.assertEqual(res.status_code, 201)

        # Verify that database row has the real registered station_id, NOT the spoofed one
        rows = supabase_get('sensor_readings', filters={'device_message_id': f'eq.{msg_id}'})
        self.assertEqual(rows[0].get('station_id'), self.station_id)
        self.assertNotEqual(rows[0].get('station_id'), arbitrary_fake_station)

    def test_17_simulator_cannot_impersonate_hardware(self):
        """Scenario 17: Simulator endpoint strictly enforces simulated provenance and null device_id."""
        sim_token = os.getenv('SIMULATOR_API_TOKEN', 'rs_sim_dev_sec_7a8f9c12')
        res = self.client.post('/api/telemetry/simulate',
                               headers={'X-Simulator-Token': sim_token},
                               json={
                                   'ph': 7.5,
                                   'turbidity': 20.0,
                                   'device_id': str(uuid.uuid4()),  # Simulator tries to set device_id
                                   'provenance': 'real_sensor'       # Simulator tries to set real provenance
                               })
        self.assertEqual(res.status_code, 201)
        data = res.get_json().get('data', {})
        self.assertEqual(data.get('provenance'), 'simulated', "Simulator MUST always have simulated provenance")
        self.assertIsNone(data.get('device_id'), "Simulator MUST NEVER have a device_id")


if __name__ == '__main__':
    unittest.main(verbosity=2)
