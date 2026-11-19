"""
Authority Actions & Operations Routes Blueprint
Handles citizen report management, summaries, legitimate CSV export, legal notice generation, and alert triggers.
"""

from flask import Blueprint, jsonify, request, make_response
import os
import io
import csv
import random
import time
from datetime import datetime
from services.supabase_service import (
    supabase_get, supabase_insert, supabase_update,
    get_sensor_summary, get_reports_summary
)

authority_bp = Blueprint('authority', __name__)

# In-memory alert store for operational alerts
ACTIVE_SYSTEM_ALERTS = []


@authority_bp.route('/api/authority/reports', methods=['GET'])
def get_reports():
    """Retrieve pollution reports from Supabase."""
    mock_reports = [
        {'id': 'mock_1', 'location': 'Dashashwamedh Steps', 'reporter': 'Aviral S.',
         'pollution_level': 'High', 'status': 'PENDING',
         'timestamp': int(time.time() * 1000),
         'assessment': 'Visible oil slicks near boat landing.'},
        {'id': 'mock_2', 'location': 'Assi Ghat', 'reporter': 'Priya V.',
         'pollution_level': 'Moderate', 'status': 'VERIFIED',
         'timestamp': int(time.time() * 1000) - 3600000,
         'assessment': 'Plastic waste at riverbank.'}
    ]

    try:
        sb_reports = supabase_get('pollution_reports', order='created_at.desc', limit=50)
        if sb_reports and isinstance(sb_reports, list) and len(sb_reports) > 0:
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
                    'reporter': row.get('reporter', 'Citizen AI'),
                    'pollution_level': row.get('pollution_level', 'Moderate'),
                    'status': row.get('status', 'PENDING'),
                    'timestamp': ts,
                    'assessment': row.get('assessment', '') or row.get('description', ''),
                    'confidence': 85.0,
                    'pollutants': row.get('pollutants', [])
                })
            return jsonify(formatted)
    except Exception as e:
        print(f"[ERROR] Failed to fetch reports from Supabase: {e}")

    return jsonify(mock_reports)


@authority_bp.route('/api/authority/reports/update', methods=['POST'])
def update_report_status():
    """Update report workflow status in Supabase."""
    data       = request.get_json(silent=True) or {}
    report_id  = data.get('reportId')
    new_status = data.get('status')

    if not report_id or not new_status:
        return jsonify({'status': 'error', 'message': 'Missing reportId or status'}), 400

    if str(report_id).isdigit():
        supabase_update('pollution_reports', f"id=eq.{report_id}", {'status': new_status})

    return jsonify({
        'status':    'success',
        'message':   f"Report marked as {new_status.lower()}",
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })


@authority_bp.route('/api/reports/submit', methods=['POST'])
def submit_full_report():
    """Submit citizen pollution report to Supabase."""
    data = request.get_json(silent=True) or {}

    record = {
        'pollution_level': data.get('pollution_level', 'Moderate'),
        'pollutants': data.get('pollutants', []),
        'assessment': data.get('assessment', ''),
        'description': data.get('description', ''),
        'location_name': data.get('location', data.get('location_name', 'Ganga River')),
        'reporter': data.get('reporter', 'Citizen User'),
        'status': 'PENDING'
    }

    res = supabase_insert('pollution_reports', record)
    if res:
        return jsonify({'status': 'success', 'message': 'Report submitted successfully'}), 201
    return jsonify({'status': 'error', 'message': 'Failed to save report'}), 500


@authority_bp.route('/api/authority/report-summary', methods=['GET'])
def get_report_summary():
    """Return live aggregate statistics computed from Supabase."""
    sensor_stats = get_sensor_summary()
    report_stats = get_reports_summary()

    return jsonify({
        'status':         'success',
        'sensor_summary': sensor_stats,
        'report_summary': report_stats,
        'active_alerts':  len(ACTIVE_SYSTEM_ALERTS),
        'generated_at':   datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'agency':         'UP Pollution Control Board (VARANASI)'
    })


@authority_bp.route('/api/authority/export-data', methods=['GET'])
def export_sensor_data():
    """Export verified sensor telemetry from Supabase as a CSV file."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'ID', 'Timestamp_UTC', 'Station', 'pH', 'Turbidity_NTU',
        'Temperature_C', 'Water_Level_M', 'DO_mg_L', 'BOD_mg_L',
        'COD_mg_L', 'Provenance', 'Status'
    ])

    rows = supabase_get('sensor_readings', order='created_at.desc', limit=500)
    if rows and isinstance(rows, list):
        for r in rows:
            writer.writerow([
                r.get('id', ''),
                r.get('created_at', ''),
                'Assi Ghat',
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
        # Fallback single header row
        writer.writerow(['No database records available'])

    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=RiverSentinel_Telemetry_Export.csv'
    response.headers['Content-Type'] = 'text/csv'
    return response


@authority_bp.route('/api/authority/send-sms', methods=['POST'])
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
