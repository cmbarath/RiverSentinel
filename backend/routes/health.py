"""
River Sentinel 2.0 - Health, Readiness and Operational Diagnostics Blueprint (Phase 7)
Provides:
- Liveness check (/api/health/live): fast, zero-dependency process check.
- Readiness check (/api/health/ready): deep dependency verification (Supabase DB, ML models, Worker).
- Authorized operational diagnostics (/api/health/status): detailed component telemetry for administrators.
"""

from flask import Blueprint, jsonify, request
import os
import time
from datetime import datetime, timezone
from typing import Dict, Any

from services.supabase_service import get_db_connection, execute_sql, SUPABASE_URL
from services.auth_service import extract_bearer_token, verify_supabase_jwt, get_user_profile

health_bp = Blueprint('health', __name__)
START_TIME = time.time()


def _check_db_connectivity() -> Dict[str, Any]:
    """Verify direct PostgreSQL database connectivity and measure round-trip latency."""
    t0 = time.time()
    try:
        con = get_db_connection()
        try:
            res = con.run("SELECT 1;")
            latency_ms = round((time.time() - t0) * 1000, 2)
            if res and res[0][0] == 1:
                return {'connected': True, 'latency_ms': latency_ms}
        finally:
            con.close()
    except Exception as e:
        return {'connected': False, 'error': 'Database unreachable', 'latency_ms': None}
    return {'connected': False, 'error': 'Unexpected response', 'latency_ms': None}


def _check_model_artifacts() -> Dict[str, Any]:
    """Verify presence of registered model artifacts without exposing file paths."""
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    models_dir = os.path.join(backend_dir, 'ml', 'models')

    flood_pkl = os.path.join(models_dir, 'flood_stage_forecaster_v1.pkl')
    flood_meta = os.path.join(models_dir, 'flood_stage_forecaster_v1.json')
    wq_pkl = os.path.join(models_dir, 'water_quality_anomaly_detector_v1.pkl')
    wq_meta = os.path.join(models_dir, 'water_quality_anomaly_detector_v1.json')

    return {
        'flood_forecaster_v1': {
            'ready': os.path.exists(flood_pkl) and os.path.exists(flood_meta),
            'version': '1.1.0',
            'governance_status': 'research_only'
        },
        'water_quality_anomaly_detector_v1': {
            'ready': os.path.exists(wq_pkl) and os.path.exists(wq_meta),
            'version': '1.1.0',
            'governance_status': 'experimental'
        },
        'cpcb_class_b_evaluator': {
            'ready': True,
            'version': '1.0.0',
            'governance_status': 'deterministic_standard'
        }
    }


def _check_worker_heartbeat() -> Dict[str, Any]:
    """Inspect latest worker heartbeat from public.worker_heartbeats."""
    try:
        rows = execute_sql("""
            SELECT worker_name, status, last_heartbeat, metrics
            FROM public.worker_heartbeats
            WHERE worker_name = 'notification_worker'
            LIMIT 1;
        """)
        if rows:
            worker_name, status, last_hb, metrics = rows[0]
            # Check if heartbeat is recent (within 10 minutes)
            is_recent = False
            if last_hb:
                hb_dt = datetime.fromisoformat(str(last_hb).replace('Z', '+00:00'))
                diff = (datetime.now(timezone.utc) - hb_dt).total_seconds()
                is_recent = (diff < 600)

            return {
                'registered': True,
                'status': status,
                'is_active': is_recent,
                'last_heartbeat': str(last_hb)
            }
    except Exception:
        pass
    return {'registered': False, 'status': 'no_heartbeat_recorded', 'is_active': False}


# ============================================================================
# 1. LIVENESS PROBE
# ============================================================================

@health_bp.route('/api/health/live', methods=['GET'])
def liveness_check():
    """
    Lightweight process liveness probe.
    Returns 200 OK as long as the Flask application is running.
    Does NOT fail due to downstream service drops.
    """
    uptime = round(time.time() - START_TIME, 2)
    return jsonify({
        'status': 'alive',
        'service': 'River Sentinel 2.0 API Server',
        'uptime_seconds': uptime,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }), 200


# ============================================================================
# 2. READINESS PROBE
# ============================================================================

@health_bp.route('/api/health/ready', methods=['GET'])
def readiness_check():
    """
    Application readiness probe checking critical dependencies.
    States:
      - 'healthy': Database connected, configuration valid, models present.
      - 'degraded': Database connected, but non-critical optional service is unconfigured/stale.
      - 'unavailable': Critical dependency (Database) unreachable. Returns 503.
    """
    db_health = _check_db_connectivity()
    models_health = _check_model_artifacts()
    worker_health = _check_worker_heartbeat()

    has_groq = bool(os.getenv('GROQ_API_KEY'))
    has_sms = os.getenv('SMS_ENABLED', 'false').lower() in ('true', '1', 'yes')

    # Database is the sole hard requirement for application readiness
    if not db_health['connected']:
        return jsonify({
            'status': 'unavailable',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'database': {'status': 'disconnected', 'error': db_health.get('error')},
            'models': {
                'flood_forecaster_ready': models_health['flood_forecaster_v1']['ready'],
                'anomaly_detector_ready': models_health['water_quality_anomaly_detector_v1']['ready']
            },
            'optional_services': {
                'groq_ai': 'configured' if has_groq else 'unconfigured',
                'sms_gateway': 'enabled' if has_sms else 'disabled'
            }
        }), 503

    # If DB is connected, check for partial degradation
    is_degraded = (
        not models_health['flood_forecaster_v1']['ready'] or
        not models_health['water_quality_anomaly_detector_v1']['ready'] or
        not has_groq
    )

    overall_status = 'degraded' if is_degraded else 'healthy'

    return jsonify({
        'status': overall_status,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'uptime_seconds': round(time.time() - START_TIME, 2),
        'database': {
            'status': 'connected',
            'latency_ms': db_health.get('latency_ms')
        },
        'models': {
            'flood_forecaster_ready': models_health['flood_forecaster_v1']['ready'],
            'anomaly_detector_ready': models_health['water_quality_anomaly_detector_v1']['ready'],
            'cpcb_evaluator_ready': models_health['cpcb_class_b_evaluator']['ready']
        },
        'workers': {
            'notification_worker_active': worker_health['is_active'],
            'notification_worker_status': worker_health['status']
        },
        'optional_services': {
            'groq_ai': 'configured' if has_groq else 'unconfigured',
            'sms_gateway': 'enabled' if has_sms else 'disabled'
        }
    }), 200


# ============================================================================
# 3. AUTHORIZED OPERATIONAL STATUS (ADMINISTRATIVE / MONITORING)
# ============================================================================

@health_bp.route('/api/health/status', methods=['GET'])
def operational_status():
    """
    Deep operational diagnostics for authenticated administrators and system monitors.
    Requires role 'authority_admin' or valid 'X-Worker-Secret'.
    """
    worker_secret = request.headers.get('X-Worker-Secret')
    expected_secret = os.getenv('WORKER_API_SECRET', 'test_worker_secret_key_varanasi')
    authorized = False

    if worker_secret and worker_secret == expected_secret:
        authorized = True

    if not authorized:
        token = extract_bearer_token()
        if token:
            user = verify_supabase_jwt(token)
            if user:
                profile = get_user_profile(user['id'])
                if profile and profile.get('role') == 'authority_admin':
                    authorized = True

    if not authorized:
        return jsonify({
            'status': 'error',
            'error': 'Forbidden',
            'message': 'Operational status diagnostics require authority_admin role or system worker secret.'
        }), 403

    db_health = _check_db_connectivity()
    models_health = _check_model_artifacts()
    worker_health = _check_worker_heartbeat()

    # Query internal operational counts
    outbox_stats = {'queued': 0, 'processing': 0, 'failed': 0, 'delivered': 0, 'accepted': 0, 'stuck_processing': 0}
    active_alerts_count = 0
    reading_counts = 0

    if db_health['connected']:
        try:
            # Outbox deliveries breakdown
            outbox_rows = execute_sql("""
                SELECT status, count(*) 
                FROM public.notification_deliveries 
                GROUP BY status;
            """)
            for st, cnt in outbox_rows:
                if st in outbox_stats:
                    outbox_stats[st] = cnt

            # Check for stuck processing rows (> 5 min)
            stuck_rows = execute_sql("""
                SELECT count(*) 
                FROM public.notification_deliveries 
                WHERE status = 'processing' 
                  AND updated_at < (now() - interval '5 minutes');
            """)
            if stuck_rows:
                outbox_stats['stuck_processing'] = stuck_rows[0][0]

            # Active alerts count
            alert_rows = execute_sql("SELECT count(*) FROM public.system_alerts WHERE status = 'active';")
            if alert_rows:
                active_alerts_count = alert_rows[0][0]

            # Sensor readings count
            sensor_rows = execute_sql("SELECT count(*) FROM public.sensor_readings;")
            if sensor_rows:
                reading_counts = sensor_rows[0][0]
        except Exception:
            pass

    return jsonify({
        'status': 'success',
        'server_timestamp': datetime.now(timezone.utc).isoformat(),
        'uptime_seconds': round(time.time() - START_TIME, 2),
        'database': {
            'provider': 'Supabase PostgreSQL',
            'status': 'connected' if db_health['connected'] else 'disconnected',
            'latency_ms': db_health.get('latency_ms'),
            'total_sensor_readings': reading_counts
        },
        'storage': {
            'bucket': 'pollution-evidence',
            'access': 'private_rls'
        },
        'groq_ai': {
            'configured': bool(os.getenv('GROQ_API_KEY')),
            'model': 'qwen/qwen3.8-27b'
        },
        'flood_inference': {
            'model_version': 'flood_stage_forecaster_v1',
            'algorithm': 'Ridge Regression',
            'status': 'research_only',
            'alert_eligible': False,
            'artifact_ready': models_health['flood_forecaster_v1']['ready']
        },
        'water_quality_evaluation': {
            'standards_evaluator': 'CPCB Class B Primary Water Quality Criteria',
            'anomaly_detector': 'IsolationForest v1',
            'screening_status': 'experimental_screening_only',
            'alert_eligible': False,
            'artifact_ready': models_health['water_quality_anomaly_detector_v1']['ready']
        },
        'alert_engine': {
            'status': 'operational',
            'active_incidents': active_alerts_count
        },
        'notification_worker': {
            'heartbeat': worker_health,
            'outbox_metrics': outbox_stats
        },
        'telephony': {
            'sms_enabled': os.getenv('SMS_ENABLED', 'false').lower() in ('true', '1', 'yes'),
            'provider': os.getenv('SMS_PROVIDER', 'mock'),
            'sender_id': os.getenv('SMS_SENDER_ID', 'RIVSEN')
        }
    }), 200
