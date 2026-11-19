"""
River Sentinel 2.0 - Versioned Alerts & Notifications Blueprint (v1)
Provides:
- Alert listing with multi-dimensional filtering (status, severity, category, station).
- Detailed alert inspection with full audit trail of lifecycle events.
- Role-based alert acknowledgement and resolution.
- Alert rule management for authority administrators.
- In-app notification delivery inbox, unread counts, and mark-as-read actions.
- User notification preference management with explicit SMS consent guardrails.
- Outbox processing trigger for background delivery worker.
"""

from flask import Blueprint, jsonify, request
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from services.supabase_service import execute_sql, supabase_get, supabase_insert
from services.auth_service import require_auth, require_role, optional_auth
from services.alert_service import AlertService
from services.notification_worker import NotificationWorker

alerts_v1_bp = Blueprint('alerts_v1', __name__)


# ============================================================================
# 1. ALERT LISTING & DETAILS
# ============================================================================

@alerts_v1_bp.route('/api/v1/alerts', methods=['GET'])
@optional_auth
def list_system_alerts_v1():
    """
    List alerts with filtering across status, severity, category, and station.
    Public/Citizens see sanitized public alerts (FLOOD, WATER_QUALITY) that are active.
    Authority Admins and Field Officers see all operational alerts.
    """
    user = getattr(request, 'user', None)
    role = getattr(request, 'user_role', 'anonymous')

    status_filter = request.args.get('status', 'active').lower().strip()
    severity_filter = request.args.get('severity', 'all').upper().strip()
    category_filter = request.args.get('category', 'all').upper().strip()
    station_id = request.args.get('station_id')

    try:
        limit = min(int(request.args.get('limit', 100)), 500)
        offset = max(int(request.args.get('offset', 0)), 0)
    except ValueError:
        limit, offset = 100, 0

    sql_conditions = ["1=1"]
    sql_params: Dict[str, Any] = {'limit': limit, 'offset': offset}

    # Role-based visibility
    if role not in ('authority_admin', 'field_officer'):
        # Public / Citizen view: only active public environmental alerts
        sql_conditions.append("a.category IN ('FLOOD', 'WATER_QUALITY')")
        sql_conditions.append("a.status != 'resolved'")
    else:
        # Authority / Field Officer view: apply status filter if specified
        if status_filter != 'all':
            sql_conditions.append("a.status = :status")
            sql_params['status'] = status_filter

    if severity_filter != 'ALL':
        sql_conditions.append("a.severity = :severity")
        sql_params['severity'] = severity_filter

    if category_filter != 'ALL':
        sql_conditions.append("a.category = :category")
        sql_params['category'] = category_filter

    if station_id and station_id != 'all':
        sql_conditions.append("(a.station_id = :sid::uuid OR s.station_code = :sid)")
        sql_params['sid'] = station_id

    where_clause = " AND ".join(sql_conditions)

    count_sql = f"""
        SELECT count(*) 
        FROM public.system_alerts a
        LEFT JOIN public.monitoring_stations s ON s.id = a.station_id
        WHERE {where_clause};
    """
    total_matching = execute_sql(count_sql, sql_params)[0][0]

    select_sql = f"""
        SELECT 
            a.id, a.alert_code, a.category, a.severity, a.title,
            a.description, a.status, a.occurrence_count,
            a.measured_value, a.expected_threshold, a.threshold_unit,
            a.provenance, a.quality_status, a.first_triggered_at, a.last_triggered_at,
            a.acknowledged_at, a.resolved_at, a.resolution_reason,
            s.id AS station_id, s.station_code, s.station_name, s.location_name
        FROM public.system_alerts a
        LEFT JOIN public.monitoring_stations s ON s.id = a.station_id
        WHERE {where_clause}
        ORDER BY 
            CASE a.severity
                WHEN 'CRITICAL' THEN 1
                WHEN 'HIGH' THEN 2
                WHEN 'MEDIUM' THEN 3
                WHEN 'LOW' THEN 4
                ELSE 5
            END,
            a.last_triggered_at DESC
        LIMIT :limit OFFSET :offset;
    """
    rows = execute_sql(select_sql, sql_params)

    alerts = []
    for r in rows:
        alerts.append({
            'id': str(r[0]),
            'alert_code': r[1],
            'category': r[2],
            'severity': r[3],
            'title': r[4],
            'description': r[5],
            'status': r[6],
            'occurrence_count': r[7],
            'measured_value': float(r[8]) if r[8] is not None else None,
            'expected_threshold': float(r[9]) if r[9] is not None else None,
            'threshold_unit': r[10],
            'provenance': r[11],
            'quality_status': r[12],
            'first_triggered_at': r[13].isoformat() if r[13] else None,
            'last_triggered_at': r[14].isoformat() if r[14] else None,
            'acknowledged_at': r[15].isoformat() if r[15] else None,
            'resolved_at': r[16].isoformat() if r[16] else None,
            'resolution_reason': r[17],
            'station': {
                'id': str(r[18]) if r[18] else None,
                'station_code': r[19],
                'station_name': r[20],
                'location_name': r[21]
            } if r[18] else None
        })

    return jsonify({
        'status': 'success',
        'count': len(alerts),
        'total_matching': total_matching,
        'alerts': alerts
    })


@alerts_v1_bp.route('/api/v1/alerts/<alert_id>', methods=['GET'])
@optional_auth
def get_alert_details_v1(alert_id: str):
    """Retrieve detailed alert metadata and historical event audit trail."""
    role = getattr(request, 'user_role', 'anonymous')

    sql = """
        SELECT 
            a.id, a.alert_code, a.category, a.severity, a.title,
            a.description, a.status, a.occurrence_count,
            a.measured_value, a.expected_threshold, a.threshold_unit,
            a.provenance, a.quality_status, a.first_triggered_at, a.last_triggered_at,
            a.acknowledged_by, a.acknowledged_at, a.resolved_by, a.resolved_at,
            a.resolution_reason, a.deduplication_key,
            s.id AS station_id, s.station_code, s.station_name, s.location_name
        FROM public.system_alerts a
        LEFT JOIN public.monitoring_stations s ON s.id = a.station_id
        WHERE a.id = :id::uuid OR a.alert_code = :id
        LIMIT 1;
    """
    rows = execute_sql(sql, {'id': alert_id})
    if not rows:
        return jsonify({'status': 'error', 'error_code': 'NOT_FOUND', 'message': f"Alert '{alert_id}' not found"}), 404

    r = rows[0]
    aid = str(r[0])

    # Fetch audit events
    events_sql = """
        SELECT id, event_type, actor_id, metadata, created_at
        FROM public.alert_events
        WHERE alert_id = :aid::uuid
        ORDER BY created_at DESC;
    """
    ev_rows = execute_sql(events_sql, {'aid': aid})
    events = []
    for ev in ev_rows:
        events.append({
            'id': str(ev[0]),
            'event_type': ev[1],
            'actor_id': str(ev[2]) if ev[2] else None,
            'metadata': ev[3] if isinstance(ev[3], dict) else {},
            'created_at': ev[4].isoformat() if ev[4] else None
        })

    # Fetch delivery dispatch summary if authority
    delivery_summary = None
    if role in ('authority_admin', 'field_officer'):
        deliv_sql = """
            SELECT channel, status, count(*)
            FROM public.notification_deliveries
            WHERE alert_id = :aid::uuid
            GROUP BY channel, status;
        """
        deliv_rows = execute_sql(deliv_sql, {'aid': aid})
        delivery_summary = {}
        for d in deliv_rows:
            ch, st, cnt = d[0], d[1], d[2]
            if ch not in delivery_summary:
                delivery_summary[ch] = {}
            delivery_summary[ch][st] = cnt

    return jsonify({
        'status': 'success',
        'alert': {
            'id': aid,
            'alert_code': r[1],
            'category': r[2],
            'severity': r[3],
            'title': r[4],
            'description': r[5],
            'status': r[6],
            'occurrence_count': r[7],
            'measured_value': float(r[8]) if r[8] is not None else None,
            'expected_threshold': float(r[9]) if r[9] is not None else None,
            'threshold_unit': r[10],
            'provenance': r[11],
            'quality_status': r[12],
            'first_triggered_at': r[13].isoformat() if r[13] else None,
            'last_triggered_at': r[14].isoformat() if r[14] else None,
            'acknowledged_by': str(r[15]) if r[15] else None,
            'acknowledged_at': r[16].isoformat() if r[16] else None,
            'resolved_by': str(r[17]) if r[17] else None,
            'resolved_at': r[18].isoformat() if r[18] else None,
            'resolution_reason': r[19],
            'station': {
                'id': str(r[21]) if r[21] else None,
                'station_code': r[22],
                'station_name': r[23],
                'location_name': r[24]
            } if r[21] else None,
            'events': events,
            'delivery_summary': delivery_summary
        }
    })


# ============================================================================
# 2. ALERT ACTIONS: ACKNOWLEDGE & RESOLVE
# ============================================================================

@alerts_v1_bp.route('/api/v1/alerts/<alert_id>/acknowledge', methods=['POST'])
@require_role('authority_admin', 'field_officer')
def acknowledge_alert_v1(alert_id: str):
    """Acknowledge an active operational alert."""
    data = request.get_json(silent=True) or {}
    notes = data.get('notes', '')
    user_id = str(request.user['id'])
    user_role = request.user_role

    try:
        res = AlertService.acknowledge_alert(alert_id=alert_id, user_id=user_id, user_role=user_role, notes=notes)
        return jsonify(res), 200
    except PermissionError as pe:
        return jsonify({'status': 'error', 'error_code': 'FORBIDDEN', 'message': str(pe)}), 403
    except ValueError as ve:
        return jsonify({'status': 'error', 'error_code': 'BAD_REQUEST', 'message': str(ve)}), 400


@alerts_v1_bp.route('/api/v1/alerts/<alert_id>/resolve', methods=['POST'])
@require_role('authority_admin', 'field_officer')
def resolve_alert_v1(alert_id: str):
    """Resolve an alert with a descriptive resolution reason."""
    data = request.get_json(silent=True) or {}
    reason = data.get('reason', '')
    user_id = str(request.user['id'])
    user_role = request.user_role

    try:
        res = AlertService.resolve_alert(alert_id=alert_id, user_id=user_id, user_role=user_role, reason=reason)
        return jsonify(res), 200
    except PermissionError as pe:
        return jsonify({'status': 'error', 'error_code': 'FORBIDDEN', 'message': str(pe)}), 403
    except ValueError as ve:
        return jsonify({'status': 'error', 'error_code': 'BAD_REQUEST', 'message': str(ve)}), 400


# ============================================================================
# 3. ALERT RULES MANAGEMENT
# ============================================================================

@alerts_v1_bp.route('/api/v1/alerts/rules', methods=['GET'])
@require_role('authority_admin', 'field_officer')
def list_alert_rules_v1():
    """List configured threshold rules."""
    rules = supabase_get('alert_rules', order='category.asc,rule_code.asc')
    return jsonify({
        'status': 'success',
        'count': len(rules or []),
        'rules': rules or []
    })


@alerts_v1_bp.route('/api/v1/alerts/rules', methods=['POST'])
@require_role('authority_admin')
def create_or_update_alert_rule_v1():
    """Create or update an alert rule (restricted to authority administrators)."""
    data = request.get_json(silent=True) or {}
    rule_code = data.get('rule_code')
    name = data.get('name')
    category = data.get('category')
    parameter = data.get('parameter')
    operator = data.get('operator')
    threshold_val = data.get('threshold_value')

    if not all([rule_code, name, category, parameter, operator]):
        return jsonify({
            'status': 'error',
            'error_code': 'BAD_REQUEST',
            'message': 'rule_code, name, category, parameter, and operator are mandatory fields.'
        }), 400

    now_iso = datetime.now(timezone.utc).isoformat()
    record = {
        'rule_code': rule_code,
        'name': name,
        'description': data.get('description', ''),
        'category': category,
        'station_id': data.get('station_id'),
        'parameter': parameter,
        'operator': operator,
        'threshold_value': threshold_val,
        'threshold_unit': data.get('threshold_unit', ''),
        'severity': data.get('severity', 'MEDIUM'),
        'enabled': data.get('enabled', True),
        'cooldown_seconds': data.get('cooldown_seconds', 900),
        'created_by': request.user['id'],
        'updated_at': now_iso
    }

    res = supabase_insert('alert_rules', record)
    return jsonify({
        'status': 'success',
        'message': f"Alert rule '{rule_code}' saved successfully.",
        'rule': res[0] if res else record
    }), 201


# ============================================================================
# 4. IN-APP NOTIFICATIONS & USER INBOX
# ============================================================================

@alerts_v1_bp.route('/api/v1/notifications', methods=['GET'])
@require_auth
def get_user_notifications_v1():
    """Retrieve in-app notifications for the authenticated caller."""
    uid = str(request.user['id'])

    try:
        limit = min(int(request.args.get('limit', 50)), 100)
        offset = max(int(request.args.get('offset', 0)), 0)
    except ValueError:
        limit, offset = 50, 0

    unread_only = request.args.get('unread_only', 'false').lower() == 'true'

    sql = f"""
        SELECT 
            nd.id, nd.alert_id, nd.status, nd.message_payload,
            nd.read_at, nd.created_at,
            a.alert_code, a.category, a.severity, a.status AS alert_status,
            s.station_name, s.location_name
        FROM public.notification_deliveries nd
        JOIN public.system_alerts a ON a.id = nd.alert_id
        LEFT JOIN public.monitoring_stations s ON s.id = a.station_id
        WHERE nd.recipient_user_id = :uid::uuid
          AND nd.channel = 'in_app'
          {'AND nd.read_at IS NULL' if unread_only else ''}
        ORDER BY nd.created_at DESC
        LIMIT :limit OFFSET :offset;
    """
    rows = execute_sql(sql, {'uid': uid, 'limit': limit, 'offset': offset})

    items = []
    for r in rows:
        payload = r[3] if isinstance(r[3], dict) else {}
        items.append({
            'delivery_id': str(r[0]),
            'alert_id': str(r[1]),
            'delivery_status': r[2],
            'title': payload.get('title', 'System Notification'),
            'description': payload.get('description', ''),
            'is_read': r[4] is not None,
            'read_at': r[4].isoformat() if r[4] else None,
            'created_at': r[5].isoformat() if r[5] else None,
            'alert_code': r[6],
            'category': r[7],
            'severity': r[8],
            'alert_status': r[9],
            'station_name': r[10] or 'Varanasi Corridor',
            'location_name': r[11] or 'Ganga River'
        })

    unread_count_sql = """
        SELECT count(*) 
        FROM public.notification_deliveries
        WHERE recipient_user_id = :uid::uuid AND channel = 'in_app' AND read_at IS NULL;
    """
    unread_count = execute_sql(unread_count_sql, {'uid': uid})[0][0]

    return jsonify({
        'status': 'success',
        'unread_count': unread_count,
        'count': len(items),
        'notifications': items
    })


@alerts_v1_bp.route('/api/v1/notifications/unread-count', methods=['GET'])
@require_auth
def get_unread_notification_count():
    """Retrieve unread notification count for the authenticated user badge."""
    uid = str(request.user['id'])
    count = execute_sql("""
        SELECT count(*) FROM public.notification_deliveries
        WHERE recipient_user_id = :uid::uuid AND channel = 'in_app' AND read_at IS NULL;
    """, {'uid': uid})[0][0]
    return jsonify({'status': 'success', 'unread_count': count})


@alerts_v1_bp.route('/api/v1/notifications/<delivery_id>/read', methods=['POST'])
@require_auth
def mark_notification_read(delivery_id: str):
    """Mark a single in-app notification delivery as read."""
    uid = str(request.user['id'])
    now_iso = datetime.now(timezone.utc).isoformat()
    res = execute_sql("""
        UPDATE public.notification_deliveries
        SET read_at = :now, updated_at = :now
        WHERE id = :id::uuid AND recipient_user_id = :uid::uuid AND channel = 'in_app'
        RETURNING id;
    """, {'id': delivery_id, 'uid': uid, 'now': now_iso})

    if not res:
        return jsonify({'status': 'error', 'error_code': 'NOT_FOUND', 'message': 'Notification not found'}), 404
    return jsonify({'status': 'success', 'message': 'Notification marked as read.'})


@alerts_v1_bp.route('/api/v1/notifications/mark-all-read', methods=['POST'])
@require_auth
def mark_all_notifications_read():
    """Mark all in-app notifications as read for current user."""
    uid = str(request.user['id'])
    now_iso = datetime.now(timezone.utc).isoformat()
    execute_sql("""
        UPDATE public.notification_deliveries
        SET read_at = :now, updated_at = :now
        WHERE recipient_user_id = :uid::uuid AND channel = 'in_app' AND read_at IS NULL;
    """, {'uid': uid, 'now': now_iso})
    return jsonify({'status': 'success', 'message': 'All notifications marked as read.'})


# ============================================================================
# 5. USER NOTIFICATION PREFERENCES
# ============================================================================

@alerts_v1_bp.route('/api/v1/notifications/preferences', methods=['GET', 'POST'])
@require_auth
def user_notification_preferences():
    """
    Manage user notification preferences (in_app, email, sms).
    SMS opt-in strictly requires verified phone number and explicit consent.
    """
    uid = str(request.user['id'])

    if request.method == 'GET':
        rows = execute_sql("""
            SELECT in_app_enabled, email_enabled, sms_enabled,
                   preferred_severities, preferred_categories,
                   phone_number_verified, email_verified, consent_timestamp
            FROM public.notification_preferences
            WHERE user_id = :uid::uuid;
        """, {'uid': uid})

        if not rows:
            return jsonify({
                'status': 'success',
                'preferences': {
                    'in_app_enabled': True,
                    'email_enabled': False,
                    'sms_enabled': False,
                    'preferred_severities': ['CRITICAL', 'HIGH'],
                    'preferred_categories': ['FLOOD', 'WATER_QUALITY', 'POLLUTION_REPORT'],
                    'phone_number_verified': False,
                    'email_verified': False,
                    'consent_timestamp': None
                }
            })

        r = rows[0]
        return jsonify({
            'status': 'success',
            'preferences': {
                'in_app_enabled': r[0],
                'email_enabled': r[1],
                'sms_enabled': r[2],
                'preferred_severities': r[3],
                'preferred_categories': r[4],
                'phone_number_verified': r[5],
                'email_verified': r[6],
                'consent_timestamp': r[7].isoformat() if r[7] else None
            }
        })

    # POST - Update preferences
    data = request.get_json(silent=True) or {}
    in_app = data.get('in_app_enabled', True)
    email_en = data.get('email_enabled', False)
    sms_en = data.get('sms_enabled', False)
    severities = data.get('preferred_severities', ['CRITICAL', 'HIGH'])
    categories = data.get('preferred_categories', ['FLOOD', 'WATER_QUALITY', 'POLLUTION_REPORT'])

    now_iso = datetime.now(timezone.utc).isoformat()
    consent_ts = now_iso if sms_en else None

    # Upsert preferences
    execute_sql("""
        INSERT INTO public.notification_preferences (
            user_id, in_app_enabled, email_enabled, sms_enabled,
            preferred_severities, preferred_categories,
            consent_timestamp, updated_at
        ) VALUES (
            :uid::uuid, :in_app, :email_en, :sms_en,
            :sevs::text[], :cats::text[],
            :consent, :now
        )
        ON CONFLICT (user_id) DO UPDATE SET
            in_app_enabled = EXCLUDED.in_app_enabled,
            email_enabled = EXCLUDED.email_enabled,
            sms_enabled = EXCLUDED.sms_enabled,
            preferred_severities = EXCLUDED.preferred_severities,
            preferred_categories = EXCLUDED.preferred_categories,
            consent_timestamp = COALESCE(EXCLUDED.consent_timestamp, notification_preferences.consent_timestamp),
            updated_at = EXCLUDED.updated_at;
    """, {
        'uid': uid,
        'in_app': in_app,
        'email_en': email_en,
        'sms_en': sms_en,
        'sevs': severities,
        'cats': categories,
        'consent': consent_ts,
        'now': now_iso
    })

    return jsonify({
        'status': 'success',
        'message': 'Notification preferences updated successfully.'
    })


# ============================================================================
# 6. NOTIFICATION OUTBOX WORKER PROCESSOR TRIGGER
# ============================================================================

@alerts_v1_bp.route('/api/v1/notifications/process-outbox', methods=['POST'])
@require_role('authority_admin')
def process_outbox_trigger():
    """Trigger processing of pending outbox notifications."""
    limit = int(request.args.get('limit', 20))
    stats = NotificationWorker.process_outbox_batch(batch_size=limit)
    return jsonify({
        'status': 'success',
        'summary': stats
    })
