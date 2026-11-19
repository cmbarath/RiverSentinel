"""
Sensors & Telemetry Routes Blueprint
Handles live sensor telemetry retrieval, citizen health status, simulator ingestion,
and production authenticated IoT edge device telemetry ingestion.
"""

from flask import Blueprint, jsonify, request
import os
import time
import uuid
from datetime import datetime, timezone
from services.supabase_service import get_latest_sensor_reading, supabase_insert, supabase_get
from services.device_auth_service import verify_device_credentials, touch_device_activity
from services.alert_service import AlertService

sensors_bp = Blueprint('sensors', __name__)

DEFAULT_SENSOR_DATA = {
    'ph': 7.5,
    'turbidity': 100.0,
    'temperature': 28.0,
    'humidity': 65.0,
    'ec': 500.0,
    'water_level': 68.5,
    'bod': 30.0,
    'cod': 150.0,
    'do': 7.0,
    'timestamp': int(time.time() * 1000),
    'status': 'default',
    'provenance': 'default',
    'is_simulated': False,
    'is_real': False,
    'temperature_error': False,
    'water_level_error': False
}


def _validated_sensor(reading, key, default, lo=None, hi=None):
    """Get a sensor value with range validation and fallback."""
    val = reading.get(key, default) if reading else default
    try:
        val = float(val)
    except (TypeError, ValueError):
        return default
    if lo is not None and val < lo:
        return default
    if hi is not None and val > hi:
        return default
    return val


@sensors_bp.route('/api/sensors/latest', methods=['GET'])
def get_latest_sensor():
    """Return latest sensor readings from Supabase (or safe defaults)."""
    reading = get_latest_sensor_reading()

    if not reading:
        return jsonify({
            **DEFAULT_SENSOR_DATA,
            'timestamp': int(time.time() * 1000),
            'status': 'default_fallback',
            'provenance': 'default'
        })

    temp = _validated_sensor(reading, 'temperature', 28.0, -10, 60)
    wl   = _validated_sensor(reading, 'water_level', 68.5, 0, 100)

    temperature_error = (temp <= -100 or temp > 60)
    water_level_error = (wl <= 0)

    raw_provenance = reading.get('provenance', 'real')
    if raw_provenance not in ('real', 'simulated', 'default'):
        raw_provenance = 'simulated' if reading.get('is_simulated') else 'real'

    return jsonify({
        'ph':                _validated_sensor(reading, 'ph', 7.5, 0, 14),
        'turbidity':         _validated_sensor(reading, 'turbidity', 100.0, 0, 5000),
        'temperature':       temp,
        'humidity':          _validated_sensor(reading, 'humidity', 65.0, 0, 100),
        'ec':                _validated_sensor(reading, 'ec', 500.0, 0, 10000),
        'water_level':       wl,
        'bod':               _validated_sensor(reading, 'bod', 30.0, 0, 500),
        'cod':               _validated_sensor(reading, 'cod', 150.0, 0, 1000),
        'do':                _validated_sensor(reading, 'do', 7.0, 0, 30),
        'timestamp':         reading.get('timestamp') or int(time.time() * 1000),
        'status':            reading.get('status', 'live'),
        'provenance':        raw_provenance,
        'is_simulated':      (raw_provenance == 'simulated'),
        'is_real':           (raw_provenance == 'real'),
        'quality_status':    reading.get('quality_status', 'valid'),
        'temperature_error': temperature_error,
        'water_level_error': water_level_error
    })


# ============================================================================
# SIMULATOR INGESTION ENDPOINT (DEVELOPMENT & TEST ONLY)
# ============================================================================

@sensors_bp.route('/api/telemetry/simulate', methods=['POST'])
def ingest_simulator_telemetry():
    """
    Dedicated simulator ingestion endpoint.
    Strictly isolated from physical hardware:
    - Authenticated via X-Simulator-Token.
    - Provenance is hardcoded to 'simulated'.
    - device_id is strictly NULL to prevent impersonation of physical hardware.
    """
    token = request.headers.get('X-Simulator-Token', '')
    expected_token = os.getenv('SIMULATOR_API_TOKEN', 'rs_sim_dev_sec_7a8f9c12')

    if not token or token != expected_token:
        return jsonify({
            'status': 'error',
            'message': 'Unauthorized: Invalid or missing simulator token'
        }), 401

    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({'status': 'error', 'message': 'Missing telemetry payload'}), 400

    try:
        ph = float(data.get('ph', 7.5))
        turbidity = float(data.get('turbidity', 15.0))
        water_level = float(data.get('water_level', 67.5))
        do_val = float(data.get('do', 7.0))

        if not (0.0 <= ph <= 14.0):
            return jsonify({'status': 'error', 'message': f'Invalid pH: {ph}'}), 400
        if not (0.0 <= turbidity <= 5000.0):
            return jsonify({'status': 'error', 'message': f'Invalid turbidity: {turbidity}'}), 400
        if not (0.0 <= water_level <= 100.0):
            return jsonify({'status': 'error', 'message': f'Invalid water_level: {water_level}'}), 400

        record = {
            'ph': round(ph, 2),
            'turbidity': round(turbidity, 2),
            'temperature': round(float(data.get('temperature', 26.0)), 2),
            'humidity': round(float(data.get('humidity', 65.0)), 2),
            'ec': round(float(data.get('ec', 480.0)), 2),
            'water_level': round(water_level, 2),
            'bod': round(float(data.get('bod', 15.0)), 2),
            'cod': round(float(data.get('cod', 75.0)), 2),
            'do': round(do_val, 2),
            'provenance': 'simulated',
            'status': data.get('status', 'live'),
            'quality_status': 'valid',
            'device_id': None,  # Strictly NULL for simulated data
            'station_id': data.get('station_id') if data.get('station_id') else None,
            'latitude': float(data.get('latitude', 25.3176)),
            'longitude': float(data.get('longitude', 82.9739))
        }

        res = supabase_insert('sensor_readings', record)
        if res:
            # Trigger alert evaluation for simulated telemetry (non-blocking, SMS strictly suppressed)
            try:
                rec_for_alert = res[0] if isinstance(res, list) and res else record
                AlertService.evaluate_sensor_observation(rec_for_alert, station_id=record.get('station_id'))
            except Exception as e:
                print(f"[WARN] AlertService evaluation error on simulated telemetry: {e}")

            return jsonify({
                'status': 'success',
                'message': 'Simulated telemetry persisted successfully',
                'data': record
            }), 201
        else:
            return jsonify({'status': 'error', 'message': 'Database persistence failed'}), 500

    except (ValueError, TypeError) as ve:
        return jsonify({'status': 'error', 'message': f'Data format error: {ve}'}), 400


# ============================================================================
# PRODUCTION PHYSICAL IOT DEVICE TELEMETRY INGESTION ENDPOINT (PHASE 3A)
# ============================================================================

@sensors_bp.route('/api/v1/telemetry/ingest', methods=['POST'])
def ingest_production_device_telemetry():
    """
    Production IoT Telemetry Ingestion Endpoint for ESP32-WROOM-32 Hardware.
    
    Authentication:
        - X-Device-Code: Registered device code (e.g. DEV-ESP32-ASSI-01)
        - X-Device-Token: High-entropy pre-shared device token (rs_dev_...)
        (Also accepts payload fields device_code & device_token if headers absent)
    
    Validation:
        - Versioned contract (schema_version == '2.0')
        - Constant-time SHA-256 token verification
        - Lifecycle state enforcement (provisioned -> transitions to online)
        - Server-derived station association (client station_id is ignored)
        - Message idempotency and duplicate rejection (UUID message_id)
        - Physical bounds checking & explicit quality status tagging
        - Device activity touching & telemetry audit logging
    """
    start_time = time.time()

    # 1. Extract device identification & credential
    device_code = request.headers.get('X-Device-Code') or ''
    device_token = request.headers.get('X-Device-Token') or ''

    data = request.get_json(silent=True) or {}
    if not device_code and 'device_code' in data:
        device_code = str(data['device_code']).strip()
    if not device_token and 'device_token' in data:
        device_token = str(data['device_token']).strip()

    if not device_code or not device_token:
        return jsonify({
            'status': 'error',
            'error_code': 'UNAUTHORIZED',
            'message': 'Missing X-Device-Code or X-Device-Token headers'
        }), 401

    # 2. Cryptographic & Lifecycle Authentication
    is_valid, device, auth_err = verify_device_credentials(device_code, device_token)
    if not is_valid or not device:
        return jsonify({
            'status': 'error',
            'error_code': 'AUTHENTICATION_FAILED',
            'message': auth_err or 'Device authentication failed'
        }), 401

    device_id = device['id']
    station_id = device['station_id']  # Server-derived; client station_id is untrusted

    # 3. Payload Schema Validation
    schema_version = data.get('schema_version')
    if schema_version != '2.0':
        return jsonify({
            'status': 'error',
            'error_code': 'INVALID_SCHEMA',
            'message': f"Unsupported schema_version '{schema_version}'. Expected '2.0'."
        }), 400

    raw_msg_id = data.get('message_id')
    if not raw_msg_id:
        return jsonify({
            'status': 'error',
            'error_code': 'MISSING_MESSAGE_ID',
            'message': 'Field message_id is required.'
        }), 400

    try:
        message_id = str(uuid.UUID(str(raw_msg_id)))
    except (ValueError, TypeError):
        return jsonify({
            'status': 'error',
            'error_code': 'INVALID_MESSAGE_ID',
            'message': f"message_id '{raw_msg_id}' is not a valid UUID."
        }), 400

    seq_num = data.get('sequence_number')
    if seq_num is None or not isinstance(seq_num, int) or seq_num < 1:
        return jsonify({
            'status': 'error',
            'error_code': 'INVALID_SEQUENCE_NUMBER',
            'message': 'sequence_number must be a positive integer >= 1.'
        }), 400

    observed_at_str = data.get('observed_at')
    if not observed_at_str:
        return jsonify({
            'status': 'error',
            'error_code': 'MISSING_TIMESTAMP',
            'message': 'observed_at timestamp is required.'
        }), 400

    try:
        # Validate ISO 8601 UTC timestamp format
        observed_dt = datetime.fromisoformat(observed_at_str.replace('Z', '+00:00'))
    except Exception as te:
        return jsonify({
            'status': 'error',
            'error_code': 'INVALID_TIMESTAMP',
            'message': f"observed_at must be valid ISO 8601 UTC: {te}"
        }), 400

    # 4. Duplicate Message Protection (Idempotent Retry Contract)
    existing = supabase_get('sensor_readings', filters={'device_message_id': f'eq.{message_id}'}, limit=1)
    if existing and isinstance(existing, list) and len(existing) > 0:
        original = existing[0]
        return jsonify({
            'status': 'success',
            'duplicate': True,
            'message': f"Message {message_id} was already processed and persisted.",
            'reading_id': original.get('id'),
            'persisted_at': original.get('created_at'),
            'quality_status': original.get('quality_status', 'valid')
        }), 200

    # 5. Extract Sensor Measurements & Sensor Status
    sensors = data.get('sensor_readings')
    if not sensors or not isinstance(sensors, dict):
        return jsonify({
            'status': 'error',
            'error_code': 'MISSING_READINGS',
            'message': 'sensor_readings dictionary is required.'
        }), 400

    sensor_status = data.get('sensor_status', {})
    overall_quality = 'valid'

    def parse_measurement(key: str, min_val: float, max_val: float):
        nonlocal overall_quality
        raw_status = sensor_status.get(key, 'valid')

        # Normalize status fields
        conn_status = 'connected'
        cal_status = 'calibrated'
        if isinstance(raw_status, dict):
            conn_status = raw_status.get('connection_status', raw_status.get('connection', 'connected'))
            cal_status = raw_status.get('calibration_status', raw_status.get('calibration', 'calibrated'))
        elif isinstance(raw_status, str):
            st = raw_status.lower().strip()
            if st in ('not_configured', 'unconfigured'):
                conn_status = 'not_configured'
            elif st in ('disconnected', 'failed', 'missing'):
                conn_status = st
            elif st in ('uncalibrated', 'factory_default'):
                cal_status = st
            elif st == 'out_of_range':
                pass

        # Check connection status
        if conn_status == 'not_configured':
            return None, 'not_configured'
        if conn_status in ('disconnected', 'missing', 'failed'):
            if overall_quality in ('valid', 'provisional'):
                overall_quality = 'degraded'
            return None, conn_status

        val = sensors.get(key)
        if val is None:
            # If sensor is completely omitted from both readings and status, it is not configured on this node
            if key not in sensor_status and key not in sensors:
                return None, 'not_configured'
            if overall_quality in ('valid', 'provisional'):
                overall_quality = 'degraded'
            return None, 'missing'

        try:
            val_f = float(val)
        except (ValueError, TypeError):
            if overall_quality in ('valid', 'provisional'):
                overall_quality = 'degraded'
            return None, 'invalid_type'

        # Physical range validation
        if val_f < min_val or val_f > max_val:
            overall_quality = 'out_of_range'
            return val_f, 'out_of_range'

        # Calibration integrity check: in-range reading from uncalibrated sensor cannot be marked 'valid'
        if cal_status in ('uncalibrated', 'factory_default'):
            if overall_quality == 'valid':
                overall_quality = 'provisional'
            return round(val_f, 2), cal_status

        return round(val_f, 2), 'valid'

    ph_val, ph_q = parse_measurement('ph', 0.0, 14.0)
    turb_val, turb_q = parse_measurement('turbidity', 0.0, 3000.0)
    temp_val, temp_q = parse_measurement('temperature', -10.0, 60.0)
    humidity_val, _ = parse_measurement('humidity', 0.0, 100.0)
    ec_val, _ = parse_measurement('ec', 0.0, 10000.0)
    wl_val, wl_q = parse_measurement('water_level', 0.0, 100.0)
    do_val, do_q = parse_measurement('do', 0.0, 25.0)

    # Note: Physical sensors on ESP32 cannot directly measure biological or chemical oxygen demand.
    # BOD & COD from edge devices are ignored to preserve data scientific integrity.
    battery_pct = sensors.get('battery_level_pct', sensors.get('battery_pct'))

    record = {
        'station_id': station_id,
        'device_id': device_id,
        'device_message_id': message_id,
        'observed_at': observed_dt.isoformat(),
        'received_at': datetime.now(timezone.utc).isoformat(),
        'ph': ph_val,
        'turbidity': turb_val,
        'temperature': temp_val,
        'humidity': humidity_val,
        'ec': ec_val,
        'water_level': wl_val,
        'do': do_val,
        'bod': None,  # Preserved as NULL for physical edge telemetry
        'cod': None,  # Preserved as NULL for physical edge telemetry
        'provenance': 'real_sensor',
        'status': 'live',
        'quality_status': overall_quality
    }

    # 6. Database Persistence
    res = supabase_insert('sensor_readings', record)
    if not res:
        return jsonify({
            'status': 'error',
            'error_code': 'PERSISTENCE_FAILED',
            'message': 'Failed to insert telemetry into authoritative database.'
        }), 500

    # 7. Device Activity Update (Lifecycle Transition to 'online')
    fw_version = data.get('firmware_version', 'v1.0.0')
    touch_device_activity(device_id, battery_level=battery_pct, firmware_ver=fw_version)

    # 7b. Real-Time Alert Evaluation (Phase 5)
    try:
        rec_for_alert = res[0] if isinstance(res, list) and res else record
        AlertService.evaluate_sensor_observation(rec_for_alert, station_id=station_id)
    except Exception as e:
        print(f"[WARN] AlertService evaluation error on device telemetry: {e}")

    # 8. Telemetry Audit Log Entry
    proc_time_ms = round((time.time() - start_time) * 1000, 2)
    telemetry_log = {
        'device_id': device_id,
        'device_code': device_code,
        'message_id': message_id,
        'sequence_number': seq_num,
        'observed_at': observed_dt.isoformat(),
        'ip_address': request.remote_addr,
        'payload_size_bytes': len(request.data or b''),
        'validation_status': overall_quality,
        'processing_time_ms': proc_time_ms
    }
    supabase_insert('device_telemetry_logs', telemetry_log)

    return jsonify({
        'status': 'success',
        'message': 'Telemetry ingested and verified successfully',
        'device_code': device_code,
        'station_id': station_id,
        'message_id': message_id,
        'sequence_number': seq_num,
        'quality_status': overall_quality,
        'server_timestamp': datetime.now(timezone.utc).isoformat(),
        'processing_time_ms': proc_time_ms
    }), 201


# ============================================================================
# CITIZEN HEALTH STATUS ENDPOINT
# ============================================================================

@sensors_bp.route('/api/citizen/health-status', methods=['GET'])
def get_citizen_health_status():
    """Citizen-facing health status evaluation."""
    reading = get_latest_sensor_reading() or DEFAULT_SENSOR_DATA

    ph   = _validated_sensor(reading, 'ph', 7.4)
    turb = _validated_sensor(reading, 'turbidity', 15.0)
    do_v = _validated_sensor(reading, 'do', 6.8)
    bod  = _validated_sensor(reading, 'bod', 12.0)

    bathing_safe = (6.5 <= ph <= 8.5) and (turb <= 30.0) and (do_v >= 5.0) and (bod <= 20.0)
    drinking_safe = (6.5 <= ph <= 8.5) and (turb <= 5.0) and (do_v >= 6.0) and (bod <= 3.0)

    alerts = []
    if turb > 50.0:
        alerts.append("High turbidity: River water is cloudy; avoid direct contact.")
    if do_v < 4.0:
        alerts.append("Low dissolved oxygen: Aquatic ecosystem under distress.")
    if ph < 6.5 or ph > 8.5:
        alerts.append(f"Abnormal pH ({ph}): Skin irritation possible.")

    return jsonify({
        'status': 'success',
        'station': 'Assi Ghat, Varanasi',
        'evaluated_at': reading.get('created_at') or time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'bathing_safe': bathing_safe,
        'drinking_safe': drinking_safe,
        'water_quality_summary': 'FAIR' if bathing_safe else 'POOR',
        'active_alerts': alerts,
        'parameters': {
            'ph': ph,
            'turbidity_ntu': turb,
            'dissolved_oxygen_mg_l': do_v,
            'bod_mg_l': bod
        },
        'disclaimer': 'Citizen advisory screening only; derived from automated sensors, not statutory microbiological lab analysis.'
    })
