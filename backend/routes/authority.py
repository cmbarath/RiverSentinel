"""
Authority Actions & Operations Routes Blueprint
Handles citizen report management, summaries, CSV export, legal notice generation,
monitoring stations, IoT devices, and role-based administrative operations.
"""

from flask import Blueprint, jsonify, request, make_response
import os
import io
import csv
import random
import time
import hashlib
from datetime import datetime
from services.supabase_service import (
    supabase_get, supabase_insert, supabase_update, execute_sql,
    get_sensor_summary, get_reports_summary
)
from services.auth_service import require_auth, require_role, optional_auth
from services.alert_service import AlertService

authority_bp = Blueprint('authority', __name__)

# In-memory alert store for operational alerts
ACTIVE_SYSTEM_ALERTS = []


# ============================================================================
# 1. AUTH & PROFILE ENDPOINTS
# ============================================================================

@authority_bp.route('/api/auth/me', methods=['GET'])
@require_auth
def get_current_user_profile():
    """Return the profile and validated role of the authenticated caller."""
    user = getattr(request, 'user', {})
    profile = getattr(request, 'user_profile', {})
    role = getattr(request, 'user_role', 'citizen')

    return jsonify({
        'status': 'success',
        'user': {
            'id': user.get('id'),
            'email': user.get('email'),
            'created_at': user.get('created_at'),
            'phone': user.get('phone')
        },
        'profile': profile,
        'role': role
    })


# ============================================================================
# 2. MONITORING STATIONS ENDPOINTS
# ============================================================================

@authority_bp.route('/api/stations', methods=['GET'])
def get_monitoring_stations():
    """
    Public endpoint: Retrieve all active Varanasi monitoring stations.
    Accessible anonymously so interactive maps and dashboards can render stations.
    """
    stations = supabase_get('monitoring_stations', order='station_code.asc')
    if stations and isinstance(stations, list):
        return jsonify({
            'status': 'success',
            'count': len(stations),
            'stations': stations
        })

    # Fallback default stations if database empty
    return jsonify({
        'status': 'success',
        'count': 1,
        'stations': [{
            'id': 'stn-assi-fallback',
            'station_code': 'STN-VAR-ASSI-01',
            'station_name': 'Assi Ghat Monitoring Station',
            'river_name': 'Ganga',
            'location_name': 'Assi Ghat, Varanasi, UP, India',
            'latitude': 25.2891,
            'longitude': 83.0067,
            'status': 'planned',
            'warning_water_level_m': 70.26,
            'danger_water_level_m': 71.26
        }]
    })


@authority_bp.route('/api/stations', methods=['POST'])
@require_role('authority_admin')
def create_monitoring_station():
    """Register a new monitoring station (Authority Admin only)."""
    data = request.get_json(silent=True) or {}
    station_code = data.get('station_code')
    station_name = data.get('station_name')
    lat = data.get('latitude')
    lon = data.get('longitude')

    if not station_code or not station_name or lat is None or lon is None:
        return jsonify({'error': 'Bad Request', 'message': 'Missing required fields: station_code, station_name, latitude, longitude'}), 400

    new_station = {
        'station_code': station_code.strip(),
        'station_name': station_name.strip(),
        'river_name': data.get('river_name', 'Ganga'),
        'description': data.get('description', ''),
        'location_name': data.get('location_name', station_name),
        'latitude': float(lat),
        'longitude': float(lon),
        'warning_water_level_m': float(data.get('warning_water_level_m', 70.26)),
        'danger_water_level_m': float(data.get('danger_water_level_m', 71.26)),
        'status': data.get('status', 'planned')
    }

    res = supabase_insert('monitoring_stations', new_station)
    if res:
        return jsonify({'status': 'success', 'message': 'Monitoring station registered', 'station': res[0]}), 201
    return jsonify({'error': 'Internal Server Error', 'message': 'Failed to save station'}), 500


# ============================================================================
# 3. IOT DEVICES MANAGEMENT ENDPOINTS
# ============================================================================

def _compute_device_lifecycle(device: dict) -> str:
    """Compute active/offline state without fabricating physical connectivity."""
    status = device.get('status', 'provisioned')
    if status in ('revoked', 'maintenance', 'inactive', 'registered', 'awaiting_installation'):
        return status
    last_seen = device.get('last_seen_at')
    if not last_seen:
        return 'provisioned'  # Provisioned with credentials, awaiting initial physical telemetry
    try:
        last_dt = datetime.fromisoformat(str(last_seen).replace('Z', '+00:00'))
        # Active telemetry window: 15 minutes (900 seconds)
        if (datetime.now(timezone.utc) - last_dt).total_seconds() <= 900:
            return 'online'
        return 'offline'
    except Exception:
        return 'offline'


@authority_bp.route('/api/devices', methods=['GET'])
@require_role('authority_admin', 'field_officer')
def list_devices():
    """List registered IoT devices (Authority Admin & Field Officers only)."""
    devices = supabase_get('devices', order='device_code.asc')
    sanitized = []
    for d in (devices or []):
        dev_copy = dict(d)
        # Never leak credential hash over API
        dev_copy.pop('credential_hash', None)
        dev_copy['display_status'] = _compute_device_lifecycle(d)
        sanitized.append(dev_copy)

    return jsonify({
        'status': 'success',
        'count': len(sanitized),
        'devices': sanitized
    })


@authority_bp.route('/api/devices', methods=['POST'])
@require_role('authority_admin')
def register_device():
    """Register and provision a new IoT sensor device (Authority Admin only)."""
    data = request.get_json(silent=True) or {}
    device_code = data.get('device_code')
    device_name = data.get('device_name')
    station_id = data.get('station_id')
    raw_token = data.get('token')

    if not device_code or not device_name or not raw_token:
        return jsonify({'error': 'Bad Request', 'message': 'Missing required fields: device_code, device_name, token'}), 400

    from services.device_auth_service import hash_device_token, is_valid_token_format
    if not is_valid_token_format(raw_token):
        return jsonify({
            'error': 'Bad Request',
            'message': 'Token format invalid. Must begin with rs_dev_ and contain 24 random bytes (48 hex chars).'
        }), 400

    token_hash = hash_device_token(raw_token)

    new_device = {
        'device_code': device_code.strip(),
        'device_name': device_name.strip(),
        'station_id': station_id if station_id else None,
        'device_type': data.get('device_type', 'ESP32-WROOM-32'),
        'firmware_version': data.get('firmware_version', 'v2.0.0-phase3a'),
        'credential_hash': token_hash,
        'status': data.get('status', 'provisioned'),
        'battery_level_pct': None,
        'last_seen_at': None
    }

    res = supabase_insert('devices', new_device)
    if res:
        dev_out = dict(res[0])
        dev_out.pop('credential_hash', None)
        dev_out['display_status'] = 'provisioned'
        return jsonify({
            'status': 'success',
            'message': 'IoT Device registered successfully',
            'device': dev_out
        }), 201
    return jsonify({'error': 'Internal Server Error', 'message': 'Failed to register device'}), 500


# ============================================================================
# 4. POLLUTION REPORTS & INCIDENTS (CITIZEN & AUTHORITY)
# ============================================================================

@authority_bp.route('/api/authority/reports', methods=['GET'])
@require_role('authority_admin', 'field_officer')
def get_reports():
    """
    Retrieve pollution reports from Supabase.
    Strictly protected: Accessible only to verified authority_admin and field_officer.
    """
    try:
        sb_reports = supabase_get('pollution_reports', order='created_at.desc', limit=50)
        if sb_reports and isinstance(sb_reports, list):
            formatted = []
            for row in sb_reports:
                ts = int(time.time() * 1000)
                if row.get('created_at'):
                    try:
                        ts = int(datetime.fromisoformat(row['created_at'].replace('Z', '+00:00')).timestamp() * 1000)
                    except Exception:
                        pass
                formatted.append({
                    'id': str(row.get('id', '')),
                    'location': row.get('location_name', 'Ganga River'),
                    'reporter': row.get('reporter', 'Citizen User'),
                    'pollution_level': row.get('pollution_level', 'Moderate'),
                    'status': row.get('status', 'PENDING'),
                    'timestamp': ts,
                    'assessment': row.get('assessment', '') or row.get('description', ''),
                    'confidence': 85.0,
                    'pollutants': row.get('pollutants', []),
                    'storage_path': row.get('storage_path'),
                    'created_by': row.get('created_by'),
                    'station_id': row.get('station_id')
                })
            return jsonify(formatted)
    except Exception as e:
        print(f"[ERROR] Failed to fetch reports from Supabase: {e}")

    return jsonify([])


@authority_bp.route('/api/authority/reports/update', methods=['POST'])
@require_role('authority_admin', 'field_officer')
def update_report_status():
    """Update report workflow status in Supabase (Admins & Field Officers)."""
    data       = request.get_json(silent=True) or {}
    report_id  = data.get('reportId')
    new_status = data.get('status')

    if not report_id or not new_status:
        return jsonify({'status': 'error', 'message': 'Missing reportId or status'}), 400

    filter_param = f"id=eq.{report_id}"
    supabase_update('pollution_reports', filter_param, {
        'status': new_status,
        'updated_at': datetime.now().isoformat()
    })

    return jsonify({
        'status':    'success',
        'message':   f"Report marked as {new_status.lower()}",
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })


@authority_bp.route('/api/citizen/my-reports', methods=['GET'])
@require_auth
def get_my_citizen_reports():
    """Retrieve pollution reports created by the authenticated citizen."""
    user = getattr(request, 'user', {})
    user_id = user.get('id')

    reports = supabase_get('pollution_reports', filters={'created_by': f'eq.{user_id}'}, order='created_at.desc')
    return jsonify({
        'status': 'success',
        'reports': reports or []
    })


@authority_bp.route('/api/reports/submit', methods=['POST'])
@optional_auth
def submit_full_report():
    """
    Submit citizen pollution report to Supabase.
    Attaches authenticated user UUID if logged in, along with optional storage_path and station_id.
    """
    data = request.get_json(silent=True) or {}
    user = getattr(request, 'user', None)

    created_by = user.get('id') if user else data.get('created_by')
    reporter_name = data.get('reporter')
    if not reporter_name and user:
        reporter_name = user.get('email', 'Citizen User')
    elif not reporter_name:
        reporter_name = 'Citizen User'

    record = {
        'pollution_level': data.get('pollution_level', 'Moderate'),
        'pollutants': data.get('pollutants', []),
        'assessment': data.get('assessment', ''),
        'description': data.get('description', ''),
        'location_name': data.get('location', data.get('location_name', 'Ganga River, Varanasi')),
        'reporter': reporter_name,
        'status': 'PENDING',
        'storage_path': data.get('storage_path'),
        'created_by': created_by,
        'station_id': data.get('station_id')
    }

    res = supabase_insert('pollution_reports', record)
    if res:
        # Phase 5: Trigger authority review alert for new pollution report
        try:
            AlertService.evaluate_new_pollution_report(res[0])
        except Exception as e:
            print(f"[WARN] AlertService evaluation error on pollution report: {e}")

        return jsonify({
            'status': 'success',
            'message': 'Report submitted successfully',
            'report': res[0]
        }), 201
    return jsonify({'status': 'error', 'message': 'Failed to save report'}), 500


# ============================================================================
# 5. SUMMARIES, CSV EXPORT, ALERTS & NOTICES
# ============================================================================

@authority_bp.route('/api/authority/report-summary', methods=['GET'])
@require_role('authority_admin', 'field_officer')
def get_report_summary():
    """Return live aggregate statistics computed from Supabase."""
    sensor_stats = get_sensor_summary()
    report_stats = get_reports_summary()

    # Query real database active alerts
    try:
        active_cnt_rows = execute_sql("SELECT count(*) FROM public.system_alerts WHERE status != 'resolved';")
        active_alerts_count = active_cnt_rows[0][0] if active_cnt_rows else len(ACTIVE_SYSTEM_ALERTS)
    except Exception:
        active_alerts_count = len(ACTIVE_SYSTEM_ALERTS)

    return jsonify({
        'status':         'success',
        'sensor_summary': sensor_stats,
        'report_summary': report_stats,
        'active_alerts':  active_alerts_count,
        'generated_at':   datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'agency':         'UP Pollution Control Board (VARANASI)'
    })


@authority_bp.route('/api/authority/export-data', methods=['GET'])
@require_role('authority_admin', 'field_officer')
def export_sensor_data():
    """Export verified sensor telemetry from Supabase as a CSV file."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'ID', 'Timestamp_UTC', 'Station_ID', 'pH', 'Turbidity_NTU',
        'Temperature_C', 'Water_Level_M', 'DO_mg_L', 'BOD_mg_L',
        'COD_mg_L', 'Provenance', 'Status'
    ])

    rows = supabase_get('sensor_readings', order='created_at.desc', limit=500)
    if rows and isinstance(rows, list):
        for r in rows:
            writer.writerow([
                r.get('id', ''),
                r.get('created_at', ''),
                r.get('station_id', 'STN-VAR-ASSI-01'),
                r.get('ph', ''),
                r.get('turbidity', ''),
                r.get('temperature', ''),
                r.get('water_level', ''),
                r.get('do', ''),
                r.get('bod', ''),
                r.get('cod', ''),
                r.get('provenance', 'real'),
                r.get('status', 'live')
            ])
    else:
        writer.writerow(['No database records available'])

    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=RiverSentinel_Telemetry_Export.csv'
    response.headers['Content-Type'] = 'text/csv'
    return response


@authority_bp.route('/api/authority/send-sms', methods=['POST'])
@require_role('authority_admin')
def send_emergency_sms():
    """Simulated emergency SMS broadcast."""
    data = request.get_json(silent=True) or {}
    message = data.get('message', "EMERGENCY: River water levels rising. Stay away from ghat areas.")
    mock_targets = ["+91 987XXXXX21", "+91 882XXXXX45", "+91 701XXXXX89"]
    time.sleep(0.5)

    return jsonify({
        'status':     'success',
        'message':    'Emergency SMS broadcast simulated successfully',
        'recipients': len(mock_targets),
        'timestamp':  datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'note':       'Simulated test dispatch; physical SMS gateway not configured.'
    })


@authority_bp.route('/api/authority/trigger-alert', methods=['POST'])
@require_role('authority_admin')
def trigger_alert():
    """Trigger system-wide environmental alert."""
    data     = request.get_json(silent=True) or {}
    a_type   = data.get('type', 'FLOOD')
    severity = data.get('severity', 'CRITICAL')

    alert_obj = {
        'id': f"alert_{int(time.time())}",
        'type': a_type,
        'severity': severity,
        'title': f"{severity} {a_type} WARNING",
        'message': f"System-wide {a_type.lower()} alert activated. Take immediate precautions.",
        'timestamp': int(time.time() * 1000),
        'active': True
    }
    ACTIVE_SYSTEM_ALERTS.append(alert_obj)

    return jsonify({
        'status':    'success',
        'message':   f"{severity} {a_type} alert triggered successfully",
        'alert':     alert_obj,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })


@authority_bp.route('/api/authority/generate-notice', methods=['POST'])
@require_role('authority_admin')
def generate_legal_notice():
    """Generate legal notice document template."""
    notice_id = f"RS-NOT-2026-{random.randint(1000, 9999)}"
    content = f"""RIVER SENTINEL – AUTHORITY LEGAL NOTICE
Code: {notice_id}
Date: {datetime.now().strftime("%B %d, %Y")}

TO: INDUSTRIAL COMPLIANCE DIVISION / LOCAL BODIES
SUBJECT: ENVIRONMENTAL VIOLATION NOTICE

Notice is hereby given based on automated monitoring from RiverSentinel Station: Assi Ghat, Varanasi.
Recorded parameters indicate non-compliance with statutory surface water standards.
Corrective action must be initiated within 48 hours of receipt.
"""
    return jsonify({
        'status':    'success',
        'notice_id': notice_id,
        'content':   content,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
