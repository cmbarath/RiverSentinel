"""
Sensors & Telemetry Routes Blueprint
Handles live sensor telemetry retrieval, citizen health status, and authenticated telemetry ingestion.
"""

from flask import Blueprint, jsonify, request
import os
import time
from services.supabase_service import get_latest_sensor_reading, supabase_insert

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
        'temperature_error': temperature_error,
        'water_level_error': water_level_error
    })


@sensors_bp.route('/api/telemetry/simulate', methods=['POST'])
@sensors_bp.route('/api/v1/telemetry/ingest', methods=['POST'])
def ingest_telemetry():
    """
    Authenticated telemetry ingestion endpoint for simulator and IoT edge devices.
    Requires X-Simulator-Token or X-Device-Token header.
    """
    token = request.headers.get('X-Simulator-Token') or request.headers.get('X-Device-Token') or ''
    expected_token = os.getenv('SIMULATOR_API_TOKEN', 'rs_sim_dev_sec_7a8f9c12')

    if not token or token != expected_token:
        return jsonify({
            'status': 'error',
            'message': 'Unauthorized: Invalid or missing telemetry token'
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
            'provenance': data.get('provenance', 'simulated'),
            'status': data.get('status', 'live'),
            'latitude': float(data.get('latitude', 25.3176)),
            'longitude': float(data.get('longitude', 82.9739))
        }
        if data.get('station_id'):
            record['station_id'] = data.get('station_id')
        if data.get('device_id'):
            record['device_id'] = data.get('device_id')
        if data.get('quality_status'):
            record['quality_status'] = data.get('quality_status')

        res = supabase_insert('sensor_readings', record)
        if res:
            return jsonify({
                'status': 'success',
                'message': 'Telemetry persisted successfully',
                'data': record
            }), 201
        else:
            return jsonify({'status': 'error', 'message': 'Database persistence failed'}), 500

    except (ValueError, TypeError) as ve:
        return jsonify({'status': 'error', 'message': f'Data format error: {ve}'}), 400


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
