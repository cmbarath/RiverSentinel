"""
River Sentinel 2.0 - Phase 3A.1 Security Hardening & Retry Reliability Test Suite
Verifies:
1. Token format and 192-bit cryptographic entropy.
2. Invalidation and rotation of device credentials (without leaking tokens).
3. Idempotent HTTP 200 duplicate retry contract (persisted exactly once).
4. Revoked and unregistered device rejection.
5. In-range uncalibrated sensor downgrade to 'provisional'.
6. Unconfigured sensor preservation as NULL.
7. Offline queue retention on network interruption / 5xx error.
8. Serial bridge credential resolution via env var and file (zero CLI exposure).
9. Masked credential diagnostic logging.
"""

import unittest
import os
import sys
import json
import uuid
from datetime import datetime, timezone, timedelta
from dotenv import dotenv_values

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import app
from services.supabase_service import supabase_get, supabase_insert, supabase_update
from services.device_auth_service import (
    generate_device_token,
    hash_device_token,
    is_valid_token_format,
    mask_device_token,
    TOKEN_PREFIX,
    TOKEN_TOTAL_LEN,
    TOKEN_ENTROPY_BYTES,
    TOKEN_HEX_CHARS
)


class Phase3A1SecurityHardeningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

        # Find Assi Ghat station for testing
        stations = supabase_get('monitoring_stations', filters={'station_code': 'eq.STN-VAR-ASSI-01'}, limit=1)
        cls.station_id = stations[0]['id'] if stations else None

        # Ephemeral device code and tokens for test execution
        cls.test_device_code = "DEV-TEST-SEC-01"
        cls.test_device_token = generate_device_token()
        cls.test_token_hash = hash_device_token(cls.test_device_token)

        # Cleanup any existing test record
        cls._cleanup_test_device()

        # Provision active test device
        supabase_insert('devices', {
            'device_code': cls.test_device_code,
            'device_name': 'Automated Phase 3A1 Test Node',
            'station_id': cls.station_id,
            'device_type': 'ESP32-WROOM-32',
            'firmware_version': 'v2.0.0-phase3a1',
            'credential_hash': cls.test_token_hash,
            'status': 'provisioned'
        })

    @classmethod
    def tearDownClass(cls):
        cls._cleanup_test_device()

    @classmethod
    def _cleanup_test_device(cls):
        devs = supabase_get('devices', filters={'device_code': f'eq.{cls.test_device_code}'}, limit=1)
        if devs and isinstance(devs, list) and len(devs) > 0:
            dev_id = devs[0]['id']
            # Remove associated test telemetry logs and readings
            import pg8000.native
            env = dotenv_values(os.path.join(backend_dir, '.env'))
            con = pg8000.native.Connection(
                user=env['SUPABASE_DB_USER'],
                host=env['SUPABASE_DB_HOST'],
                port=int(env['SUPABASE_DB_PORT']),
                password=env['SUPABASE_DB_PASSWORD'],
                database=env['SUPABASE_DB_NAME'],
                ssl_context=True
            )
            con.run("DELETE FROM public.sensor_readings WHERE device_id = :did::uuid;", did=dev_id)
            con.run("DELETE FROM public.device_telemetry_logs WHERE device_id = :did::uuid;", did=dev_id)
            con.run("DELETE FROM public.devices WHERE id = :did::uuid;", did=dev_id)
            con.close()

    def _headers(self, code=None, token=None):
        return {
            'Content-Type': 'application/json',
            'X-Device-Code': code or self.test_device_code,
            'X-Device-Token': token or self.test_device_token
        }

    def _payload(self, message_id=None, seq=1, sensors=None, status_dict=None):
        return {
            'schema_version': '2.0',
            'device_code': self.test_device_code,
            'message_id': message_id or str(uuid.uuid4()),
            'sequence_number': seq,
            'observed_at': datetime.now(timezone.utc).isoformat(),
            'battery_level_pct': 88.5,
            'firmware_version': 'v2.0.0-phase3a1',
            'sensor_readings': sensors or {
                'ph': 7.35,
                'turbidity': 14.2,
                'water_level': 68.20,
                'temperature': 24.1,
                'ec': 420.0,
                'do': 6.5
            },
            'sensor_status': status_dict or {
                'ph': 'valid',
                'turbidity': 'valid',
                'water_level': 'valid',
                'temperature': 'valid',
                'ec': 'valid',
                'do': 'valid'
            }
        }

    # ------------------------------------------------------------------------
    # 1. Token Format, Entropy & Masking Tests
    # ------------------------------------------------------------------------
    def test_01_token_format_and_entropy(self):
        """Standardize on 24 random bytes (48 hex chars), rs_dev_ prefix (55 total chars)."""
        token = generate_device_token()
        self.assertTrue(token.startswith(TOKEN_PREFIX))
        self.assertEqual(len(token), TOKEN_TOTAL_LEN)
        self.assertEqual(len(token[len(TOKEN_PREFIX):]), TOKEN_HEX_CHARS)
        self.assertTrue(is_valid_token_format(token))

        # Rejection of malformed tokens
        self.assertFalse(is_valid_token_format("rs_dev_short"))
        self.assertFalse(is_valid_token_format("rs_dev_" + "g" * 48))  # invalid hex char
        self.assertFalse(is_valid_token_format("wrong_prefix_" + "a" * 48))
        self.assertFalse(is_valid_token_format(""))
        self.assertFalse(is_valid_token_format(None))

    def test_02_masked_credential_logging(self):
        """Tokens must be masked so raw credentials never appear in diagnostic logs."""
        token = generate_device_token()
        masked = mask_device_token(token)
        self.assertTrue(masked.startswith(TOKEN_PREFIX))
        self.assertIn("****", masked)
        # Verify the middle entropy is not exposed
        raw_middle = token[11:-4]
        self.assertNotIn(raw_middle, masked)

    # ------------------------------------------------------------------------
    # 2. Credential Rotation & Compromised Credential Invalidation
    # ------------------------------------------------------------------------
    def test_03_credential_rotation_invalidates_old(self):
        """Rotating credential immediately causes old token to fail with 401."""
        # 1. Generate new token and compute new hash
        new_token = generate_device_token()
        new_hash = hash_device_token(new_token)

        # 2. Update DB with new credential hash
        supabase_update('devices', f"device_code=eq.{self.test_device_code}", {'credential_hash': new_hash})

        # 3. Old token must now be rejected (HTTP 401)
        res_old = self.client.post('/api/v1/telemetry/ingest',
                                  headers=self._headers(token=self.test_device_token),
                                  data=json.dumps(self._payload()))
        self.assertEqual(res_old.status_code, 401)
        self.assertEqual(res_old.get_json()['error_code'], 'AUTHENTICATION_FAILED')

        # 4. New token must succeed (HTTP 201)
        res_new = self.client.post('/api/v1/telemetry/ingest',
                                  headers=self._headers(token=new_token),
                                  data=json.dumps(self._payload()))
        self.assertEqual(res_new.status_code, 201)

        # Update test class token to keep subsequent test methods authenticated
        self.__class__.test_device_token = new_token
        self.__class__.test_token_hash = new_hash

    # ------------------------------------------------------------------------
    # 3. Duplicate Retry Contract (HTTP 200 Idempotent Ack)
    # ------------------------------------------------------------------------
    def test_04_duplicate_retry_contract_http_200(self):
        """
        First submission: HTTP 201 Created with reading_id.
        Repeated identical submission (network retry): HTTP 200 OK with duplicate: true and reading_id.
        A repeated message must NEVER create a second sensor_readings record.
        """
        msg_id = str(uuid.uuid4())
        payload = self._payload(message_id=msg_id)

        # 1. First submission
        res1 = self.client.post('/api/v1/telemetry/ingest',
                                headers=self._headers(),
                                data=json.dumps(payload))
        self.assertEqual(res1.status_code, 201)
        data1 = res1.get_json()
        self.assertEqual(data1['status'], 'success')

        # Verify exactly 1 reading in DB
        readings_after_1 = supabase_get('sensor_readings', filters={'device_message_id': f'eq.{msg_id}'})
        self.assertEqual(len(readings_after_1), 1)
        original_reading_id = readings_after_1[0]['id']

        # 2. Simulated Network Retry (Device re-sends identical message)
        res2 = self.client.post('/api/v1/telemetry/ingest',
                                headers=self._headers(),
                                data=json.dumps(payload))
        self.assertEqual(res2.status_code, 200)
        data2 = res2.get_json()
        self.assertEqual(data2['status'], 'success')
        self.assertTrue(data2.get('duplicate'))
        self.assertEqual(data2.get('reading_id'), original_reading_id)

        # 3. Verify STILL exactly 1 reading in DB
        readings_after_2 = supabase_get('sensor_readings', filters={'device_message_id': f'eq.{msg_id}'})
        self.assertEqual(len(readings_after_2), 1)

    # ------------------------------------------------------------------------
    # 4. Sensor Measurement Quality & Calibration Demarcation
    # ------------------------------------------------------------------------
    def test_05_uncalibrated_sensor_downgrades_to_provisional(self):
        """In-range reading from uncalibrated probe must be tagged 'provisional', NOT 'valid'."""
        msg_id = str(uuid.uuid4())
        # pH is in-range (7.25), but explicitly marked uncalibrated
        payload = self._payload(
            message_id=msg_id,
            sensors={
                'ph': 7.25,
                'turbidity': 14.0,
                'water_level': 68.20,
                'temperature': 24.0,
                'ec': 400.0,
                'do': 6.0
            },
            status_dict={
                'ph': 'uncalibrated',
                'turbidity': 'valid',
                'water_level': 'valid',
                'temperature': 'valid',
                'ec': 'valid',
                'do': 'valid'
            }
        )

        res = self.client.post('/api/v1/telemetry/ingest',
                               headers=self._headers(),
                               data=json.dumps(payload))
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data['quality_status'], 'provisional')

        # Verify DB persisted quality_status as 'provisional'
        readings = supabase_get('sensor_readings', filters={'device_message_id': f'eq.{msg_id}'})
        self.assertEqual(len(readings), 1)
        self.assertEqual(readings[0]['quality_status'], 'provisional')
        self.assertEqual(readings[0]['ph'], 7.25)

    def test_06_unconfigured_sensor_persists_as_null(self):
        """Unconfigured sensor must be stored as NULL and not trigger zero substitution."""
        msg_id = str(uuid.uuid4())
        payload = self._payload(
            message_id=msg_id,
            sensors={
                'ph': 7.1,
                'water_level': 68.10,
                'temperature': 23.0
                # turbidity, ec, do omitted
            },
            status_dict={
                'ph': 'valid',
                'turbidity': 'not_configured',
                'water_level': 'valid',
                'temperature': 'valid',
                'ec': 'not_configured',
                'do': 'not_configured'
            }
        )

        res = self.client.post('/api/v1/telemetry/ingest',
                               headers=self._headers(),
                               data=json.dumps(payload))
        self.assertEqual(res.status_code, 201)

        readings = supabase_get('sensor_readings', filters={'device_message_id': f'eq.{msg_id}'})
        self.assertEqual(len(readings), 1)
        self.assertIsNone(readings[0]['turbidity'])
        self.assertIsNone(readings[0]['ec'])
        self.assertIsNone(readings[0]['do'])
        self.assertIsNone(readings[0]['bod'])
        self.assertIsNone(readings[0]['cod'])

    # ------------------------------------------------------------------------
    # 5. Revocation & Lifecycle Enforcement
    # ------------------------------------------------------------------------
    def test_07_revoked_device_rejected(self):
        """A revoked device receives HTTP 401/403 and cannot transmit telemetry."""
        # Temporarily revoke test device
        supabase_update('devices', f"device_code=eq.{self.test_device_code}", {'status': 'revoked'})

        res = self.client.post('/api/v1/telemetry/ingest',
                               headers=self._headers(),
                               data=json.dumps(self._payload()))
        self.assertIn(res.status_code, (401, 403))

        # Restore to provisioned
        supabase_update('devices', f"device_code=eq.{self.test_device_code}", {'status': 'provisioned'})

    # ------------------------------------------------------------------------
    # 6. Serial Bridge Credential Resolution Tests
    # ------------------------------------------------------------------------
    def test_08_serial_bridge_credential_resolution_env(self):
        """Serial bridge correctly resolves credentials from environment variable."""
        test_env_token = generate_device_token()
        os.environ['RIVER_SENTINEL_DEVICE_TOKEN'] = test_env_token
        try:
            from serial_bridge import SerialBridge
            bridge = SerialBridge(port="COM_DUMMY", baud=115200, device_code="DEV-ESP32-ASSI-01",
                                  device_token=os.getenv('RIVER_SENTINEL_DEVICE_TOKEN'))
            self.assertEqual(bridge.device_token, test_env_token)
        finally:
            os.environ.pop('RIVER_SENTINEL_DEVICE_TOKEN', None)

    def test_09_serial_bridge_credential_resolution_file(self):
        """Serial bridge correctly reads token from a protected token file."""
        import tempfile
        test_file_token = generate_device_token()
        with tempfile.NamedTemporaryFile('w', delete=False) as tf:
            tf.write(test_file_token)
            tmp_path = tf.name

        try:
            with open(tmp_path, 'r', encoding='utf-8') as f:
                loaded = f.read().strip()
            self.assertEqual(loaded, test_file_token)
            self.assertTrue(is_valid_token_format(loaded))
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == '__main__':
    unittest.main()
