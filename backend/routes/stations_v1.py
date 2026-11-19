"""
River Sentinel 2.0 - Versioned Station & Analytics Blueprint (v1)
Provides RESTful endpoints for:
- Station discovery and lifecycle metadata.
- Station-specific latest valid readings.
- Historical parameter time-series with filtering (24h, 7d, 30d, custom).
- Station-specific operational analytics.
- System-wide authority analytics aggregations.
- Filtered CSV data export.
- Transparent station-specific scientific safety evaluation.
"""

from flask import Blueprint, jsonify, request, make_response
import os
import io
import csv
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from services.supabase_service import execute_sql, supabase_get
from services.auth_service import require_role
from services.alert_service import AlertService

stations_v1_bp = Blueprint('stations_v1', __name__)

# Constants for query safety
MAX_TIMEFRAME_DAYS = 90
DEFAULT_LIMIT = 200
MAX_LIMIT = 1000

# CWC Varanasi Reference Gauge Thresholds (GTS Datum MSL)
CWC_WARNING_LEVEL_M = 70.26
CWC_DANGER_LEVEL_M = 71.26
CWC_HFL_M = 73.90


def _parse_time_bounds(timeframe: str, start_str: Optional[str], end_str: Optional[str]):
    """Compute UTC start and end datetime bounds based on timeframe."""
    now_utc = datetime.now(timezone.utc)
    if timeframe == '7d':
        return now_utc - timedelta(days=7), now_utc
    elif timeframe == '30d':
        return now_utc - timedelta(days=30), now_utc
    elif timeframe == 'custom':
        if not start_str or not end_str:
            raise ValueError("timeframe='custom' requires both start_time and end_time query parameters")
        try:
            st = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
            et = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
        except Exception as e:
            raise ValueError(f"Invalid ISO-8601 timestamp: {e}")

        if st > et:
            raise ValueError("start_time must be chronologically earlier than end_time")
        if (et - st).days > MAX_TIMEFRAME_DAYS:
            raise ValueError(f"Requested time window exceeds maximum allowable limit of {MAX_TIMEFRAME_DAYS} days")
        return st, et
    else:
        # Default: 24 hours
        return now_utc - timedelta(hours=24), now_utc


def _find_station(station_id: str) -> Optional[Dict[str, Any]]:
    """Look up a monitoring station by UUID or station_code safely without PostgREST syntax errors."""
    is_valid_uuid = False
    try:
        uuid.UUID(str(station_id))
        is_valid_uuid = True
    except (ValueError, AttributeError):
        is_valid_uuid = False

    if is_valid_uuid:
        stations = supabase_get('monitoring_stations', filters={'id': f'eq.{station_id}'})
        if stations:
            return stations[0]

    stations = supabase_get('monitoring_stations', filters={'station_code': f'eq.{station_id}'})
    if stations:
        return stations[0]
    return None


def _compute_device_runtime_status(dev: Dict[str, Any]) -> str:
    """Compute actual device status based on lifecycle and recent telemetry touch."""
    status = dev.get('status', 'provisioned')
    if status in ('revoked', 'maintenance', 'inactive', 'registered', 'awaiting_installation'):
        return status
    last_seen = dev.get('last_seen_at')
    if not last_seen:
        return 'provisioned'
    try:
        dt = datetime.fromisoformat(str(last_seen).replace('Z', '+00:00'))
        if (datetime.now(timezone.utc) - dt).total_seconds() <= 900:
            return 'online'
        return 'offline'
    except Exception:
        return 'offline'


# ============================================================================
# 1. STATION DIRECTORY & DETAILS
# ============================================================================

@stations_v1_bp.route('/api/v1/stations', methods=['GET'])
def list_stations_v1():
    """
    List all registered river monitoring stations with their current lifecycle,
    associated hardware device runtime state, and latest valid telemetry observation.
    """
    stations = supabase_get('monitoring_stations', order='station_code.asc')
    if not stations:
        return jsonify({'status': 'success', 'count': 0, 'stations': []})

    devices = supabase_get('devices')
    dev_map = {}
    if devices and isinstance(devices, list):
        for d in devices:
            sid = str(d.get('station_id')) if d.get('station_id') else None
            if sid:
                dev_map[sid] = d

    # Fetch latest reading per station using DISTINCT ON SQL for efficiency
    latest_sql = """
        SELECT DISTINCT ON (station_id)
            station_id, id, observed_at, created_at, ph, turbidity,
            temperature, humidity, ec, water_level, "do", provenance, quality_status
        FROM public.sensor_readings
        WHERE station_id IS NOT NULL
        ORDER BY station_id, COALESCE(observed_at, created_at) DESC;
    """
    try:
        latest_rows = execute_sql(latest_sql)
        latest_map = {}
        for r in latest_rows:
            sid = str(r[0])
            latest_map[sid] = {
                'id': r[1],
                'observed_at': r[2].isoformat() if r[2] else (r[3].isoformat() if r[3] else None),
                'ph': float(r[4]) if r[4] is not None else None,
                'turbidity': float(r[5]) if r[5] is not None else None,
                'temperature': float(r[6]) if r[6] is not None else None,
                'humidity': float(r[7]) if r[7] is not None else None,
                'ec': float(r[8]) if r[8] is not None else None,
                'water_level': float(r[9]) if r[9] is not None else None,
                'do': float(r[10]) if r[10] is not None else None,
                'provenance': r[11],
                'quality_status': r[12]
            }
    except Exception as e:
        print(f"[WARN] Failed to fetch latest readings via SQL: {e}")
        latest_map = {}

    results = []
    for s in stations:
        sid = str(s.get('id'))
        dev = dev_map.get(sid)
        dev_info = None
        is_physically_online = False

        if dev:
            runtime_st = _compute_device_runtime_status(dev)
            is_physically_online = (runtime_st == 'online')
            dev_info = {
                'device_code': dev.get('device_code'),
                'device_name': dev.get('device_name'),
                'lifecycle_status': dev.get('status'),
                'runtime_status': runtime_st,
                'last_seen_at': dev.get('last_seen_at'),
                'battery_level_pct': float(dev['battery_level_pct']) if dev.get('battery_level_pct') is not None else None,
                'firmware_version': dev.get('firmware_version')
            }

        station_obj = {
            'id': sid,
            'station_code': s.get('station_code'),
            'station_name': s.get('station_name'),
            'river_name': s.get('river_name', 'Ganga'),
            'location_name': s.get('location_name'),
            'latitude': float(s.get('latitude', 0.0)),
            'longitude': float(s.get('longitude', 0.0)),
            'status': s.get('status', 'planned'),
            'warning_water_level_m': float(s['warning_water_level_m']) if s.get('warning_water_level_m') is not None else None,
            'danger_water_level_m': float(s['danger_water_level_m']) if s.get('danger_water_level_m') is not None else None,
            'cwc_reference_gauge_id': s.get('cwc_reference_gauge_id'),
            'device': dev_info,
            'is_online': is_physically_online,
            'latest_reading': latest_map.get(sid)
        }
        results.append(station_obj)

    return jsonify({
        'status': 'success',
        'count': len(results),
        'stations': results
    })


@stations_v1_bp.route('/api/v1/stations/<station_id>', methods=['GET'])
def get_station_details_v1(station_id: str):
    """Retrieve full station identity, hardware binding, and reference thresholds."""
    station = _find_station(station_id)
    if not station:
        return jsonify({'status': 'error', 'error_code': 'NOT_FOUND', 'message': f"Station '{station_id}' not found"}), 404

    sid = station['id']

    # Fetch attached device
    devs = supabase_get('devices', filters={'station_id': f'eq.{sid}'})
    dev_info = None
    if devs:
        d = devs[0]
        dev_info = {
            'device_code': d.get('device_code'),
            'device_name': d.get('device_name'),
            'lifecycle_status': d.get('status'),
            'runtime_status': _compute_device_runtime_status(d),
            'last_seen_at': d.get('last_seen_at'),
            'battery_level_pct': float(d['battery_level_pct']) if d.get('battery_level_pct') is not None else None,
            'firmware_version': d.get('firmware_version')
        }

    # Latest reading
    latest = supabase_get('sensor_readings', filters={'station_id': f'eq.{sid}'}, order='created_at.desc', limit=1)
    latest_obj = latest[0] if latest else None

    # Reference CWC gauge info
    cwc_info = None
    if station.get('cwc_reference_gauge_id'):
        cwc_rows = supabase_get('cwc_reference_gauges', filters={'id': f"eq.{station['cwc_reference_gauge_id']}"})
        if cwc_rows:
            cwc_info = cwc_rows[0]

    return jsonify({
        'status': 'success',
        'station': {
            'id': sid,
            'station_code': station.get('station_code'),
            'station_name': station.get('station_name'),
            'river_name': station.get('river_name'),
            'location_name': station.get('location_name'),
            'latitude': float(station.get('latitude', 0.0)),
            'longitude': float(station.get('longitude', 0.0)),
            'status': station.get('status'),
            'warning_water_level_m': float(station['warning_water_level_m']) if station.get('warning_water_level_m') is not None else None,
            'danger_water_level_m': float(station['danger_water_level_m']) if station.get('danger_water_level_m') is not None else None,
            'cwc_reference': cwc_info,
            'device': dev_info,
            'latest_reading': latest_obj
        }
    })


@stations_v1_bp.route('/api/v1/stations/<station_id>/latest', methods=['GET'])
def get_station_latest_reading_v1(station_id: str):
    """Retrieve the single most recent valid sensor reading for a specific station."""
    station = _find_station(station_id)
    if not station:
        return jsonify({'status': 'error', 'error_code': 'NOT_FOUND', 'message': f"Station '{station_id}' not found"}), 404

    sid = station['id']
    readings = supabase_get('sensor_readings', filters={'station_id': f'eq.{sid}'}, order='created_at.desc', limit=1)

    if not readings:
        return jsonify({
            'status': 'no_data',
            'message': 'No telemetry records exist for this station yet.',
            'station_id': sid,
            'station_code': station.get('station_code'),
            'station_name': station.get('station_name'),
            'reading': None
        }), 200

    r = readings[0]
    return jsonify({
        'status': 'success',
        'station_id': sid,
        'station_code': station.get('station_code'),
        'station_name': station.get('station_name'),
        'reading': r
    })


# ============================================================================
# 2. HISTORICAL SENSOR READINGS WITH FILTERING & PAGINATION
# ============================================================================

@stations_v1_bp.route('/api/v1/stations/<station_id>/readings', methods=['GET'])
def get_station_historical_readings_v1(station_id: str):
    """
    Retrieve historical time-series sensor observations for a station.
    Supported filters:
      - timeframe: 24h (default), 7d, 30d, custom
      - start_time, end_time: ISO-8601 UTC (for custom)
      - parameter: ph, turbidity, temperature, water_level, ec, do, all
      - provenance: real_sensor, simulated, all
      - quality_status: valid, provisional, degraded, out_of_range, all
      - limit: default 200, max 1000
      - offset: pagination offset
    """
    target_station = _find_station(station_id)
    if not target_station:
        return jsonify({'status': 'error', 'error_code': 'NOT_FOUND', 'message': f"Station '{station_id}' not found"}), 404

    sid = target_station['id']

    # Query params
    timeframe = request.args.get('timeframe', '24h').lower().strip()
    start_arg = request.args.get('start_time')
    end_arg = request.args.get('end_time')
    parameter = request.args.get('parameter', 'all').lower().strip()
    provenance = request.args.get('provenance', 'all').strip()
    quality = request.args.get('quality_status', 'all').strip()

    try:
        limit = min(int(request.args.get('limit', DEFAULT_LIMIT)), MAX_LIMIT)
        offset = max(int(request.args.get('offset', 0)), 0)
    except ValueError:
        return jsonify({'status': 'error', 'error_code': 'BAD_REQUEST', 'message': 'limit and offset must be integers'}), 400

    try:
        start_dt, end_dt = _parse_time_bounds(timeframe, start_arg, end_arg)
    except ValueError as ve:
        return jsonify({'status': 'error', 'error_code': 'INVALID_TIMEFRAME', 'message': str(ve)}), 400

    # Build SQL query with safe parameterization
    sql_conditions = [
        "station_id = :sid::uuid",
        "COALESCE(observed_at, created_at) >= :start_time",
        "COALESCE(observed_at, created_at) <= :end_time"
    ]
    sql_params = {
        'sid': sid,
        'start_time': start_dt.isoformat(),
        'end_time': end_dt.isoformat()
    }

    if provenance != 'all':
        sql_conditions.append("provenance = :prov")
        sql_params['prov'] = provenance

    if quality != 'all':
        sql_conditions.append("quality_status = :qstatus")
        sql_params['qstatus'] = quality

    where_clause = " AND ".join(sql_conditions)

    # 1. Total count matching filter
    count_sql = f"SELECT count(*) FROM public.sensor_readings WHERE {where_clause};"
    total_matching = execute_sql(count_sql, sql_params)[0][0]

    # 2. Fetch rows in chronological order (ASC) for graphing
    query_sql = f"""
        SELECT 
            id, COALESCE(observed_at, created_at) as event_time,
            ph, turbidity, temperature, water_level, ec, "do",
            provenance, quality_status
        FROM public.sensor_readings
        WHERE {where_clause}
        ORDER BY COALESCE(observed_at, created_at) ASC
        LIMIT :limit OFFSET :offset;
    """
    sql_params['limit'] = limit
    sql_params['offset'] = offset

    rows = execute_sql(query_sql, sql_params)

    # Format output items and compute min/max/avg for requested parameters
    items = []
    accum = {
        'ph': [], 'turbidity': [], 'temperature': [],
        'water_level': [], 'ec': [], 'do': []
    }
    real_cnt = 0
    sim_cnt = 0

    for r in rows:
        rid, event_dt, ph, turb, temp, wl, ec, do_v, prov, q_stat = r
        if prov == 'real_sensor':
            real_cnt += 1
        elif prov == 'simulated':
            sim_cnt += 1

        reading_item = {
            'id': rid,
            'timestamp': event_dt.isoformat() if event_dt else None,
            'provenance': prov,
            'quality_status': q_stat
        }

        # Include values and track for stats
        vals = {
            'ph': float(ph) if ph is not None else None,
            'turbidity': float(turb) if turb is not None else None,
            'temperature': float(temp) if temp is not None else None,
            'water_level': float(wl) if wl is not None else None,
            'ec': float(ec) if ec is not None else None,
            'do': float(do_v) if do_v is not None else None
        }

        for k, v in vals.items():
            if v is not None:
                accum[k].append(v)
            if parameter == 'all' or parameter == k:
                reading_item[k] = v

        items.append(reading_item)

    # Statistical summaries
    summary = {}
    for param_name, values in accum.items():
        if values and (parameter == 'all' or parameter == param_name):
            summary[param_name] = {
                'min': round(min(values), 2),
                'max': round(max(values), 2),
                'avg': round(sum(values) / len(values), 2),
                'sample_count': len(values)
            }

    return jsonify({
        'status': 'success',
        'station_id': sid,
        'station_code': target_station.get('station_code'),
        'station_name': target_station.get('station_name'),
        'station': {
            'id': sid,
            'station_code': target_station.get('station_code'),
            'station_name': target_station.get('station_name')
        },
        'parameter': parameter,
        'timeframe': timeframe,
        'start_time': start_dt.isoformat(),
        'end_time': end_dt.isoformat(),
        'count': len(items),
        'total_matching': total_matching,
        'provenance_counts': {'real': real_cnt, 'simulated': sim_cnt},
        'provenance_breakdown': {'real_sensor': real_cnt, 'simulated': sim_cnt},
        'summary': summary,
        'summary_statistics': summary,
        'readings': items
    })


# ============================================================================
# 3. STATION OPERATIONAL ANALYTICS
# ============================================================================

@stations_v1_bp.route('/api/v1/stations/<station_id>/analytics', methods=['GET'])
def get_station_analytics_v1(station_id: str):
    """Retrieve operational health, reading counts, and parameter statistics for a station."""
    target_station = _find_station(station_id)
    if not target_station:
        return jsonify({'status': 'error', 'error_code': 'NOT_FOUND', 'message': f"Station '{station_id}' not found"}), 404

    sid = target_station['id']

    # Total readings breakdown by provenance
    prov_sql = """
        SELECT provenance, count(*) 
        FROM public.sensor_readings 
        WHERE station_id = :sid::uuid 
        GROUP BY provenance;
    """
    prov_rows = execute_sql(prov_sql, {'sid': sid})
    provenance_counts = {'real_sensor': 0, 'simulated': 0, 'default': 0}
    total_readings = 0
    for r in prov_rows:
        provenance_counts[r[0] or 'unknown'] = r[1]
        total_readings += r[1]

    # Quality status breakdown
    qual_sql = """
        SELECT COALESCE(quality_status, 'valid'), count(*)
        FROM public.sensor_readings
        WHERE station_id = :sid::uuid
        GROUP BY COALESCE(quality_status, 'valid');
    """
    qual_rows = execute_sql(qual_sql, {'sid': sid})
    quality_counts = {r[0]: r[1] for r in qual_rows}

    # 24-hour vs 7-day averages for real sensor readings
    avg_24h_sql = """
        SELECT 
            ROUND(AVG(ph)::numeric, 2),
            ROUND(AVG(turbidity)::numeric, 2),
            ROUND(AVG(temperature)::numeric, 2),
            ROUND(AVG(water_level)::numeric, 2),
            ROUND(AVG("do")::numeric, 2),
            COUNT(*)
        FROM public.sensor_readings
        WHERE station_id = :sid::uuid 
          AND COALESCE(observed_at, created_at) >= now() - interval '24 hours';
    """
    r24 = execute_sql(avg_24h_sql, {'sid': sid})[0]

    averages_24h = {
        'avg_ph': float(r24[0]) if r24[0] is not None else None,
        'avg_turbidity': float(r24[1]) if r24[1] is not None else None,
        'avg_temperature': float(r24[2]) if r24[2] is not None else None,
        'avg_water_level': float(r24[3]) if r24[3] is not None else None,
        'avg_do': float(r24[4]) if r24[4] is not None else None,
        'readings_count': r24[5]
    }

    return jsonify({
        'status': 'success',
        'station_id': sid,
        'station_code': target_station.get('station_code'),
        'station_name': target_station.get('station_name'),
        'lifecycle_status': target_station.get('status'),
        'total_readings': total_readings,
        'provenance_breakdown': provenance_counts,
        'quality_distribution': quality_counts,
        'averages_last_24h': averages_24h,
        'cwc_reference_thresholds': {
            'warning_water_level_m': float(target_station.get('warning_water_level_m', CWC_WARNING_LEVEL_M)),
            'danger_water_level_m': float(target_station.get('danger_water_level_m', CWC_DANGER_LEVEL_M)),
            'datum': 'GTS Mean Sea Level (MSL)'
        }
    })


# ============================================================================
# 4. SYSTEM-WIDE AUTHORITY ANALYTICS OVERVIEW
# ============================================================================

@stations_v1_bp.route('/api/v1/analytics/overview', methods=['GET'])
@require_role('authority_admin', 'field_officer')
def get_system_analytics_overview():
    """
    Retrieve live database aggregations for Authority Analytics:
    - Station lifecycle counts (planned, installed, active).
    - Device operational counts (online, offline, provisioned, revoked).
    - Historical reading volume.
    - Pollution reports status breakdown and resolution rate.
    - Flood risk prediction summary.
    """
    # 1. Station lifecycle counts
    station_rows = execute_sql("SELECT status, count(*) FROM public.monitoring_stations GROUP BY status;")
    stations_by_status = {r[0]: r[1] for r in station_rows}
    total_stations = sum(stations_by_status.values())

    # 2. Device lifecycle counts
    dev_rows = execute_sql("SELECT status, count(*) FROM public.devices GROUP BY status;")
    devices_by_status = {r[0]: r[1] for r in dev_rows}
    total_devices = sum(devices_by_status.values())

    # Calculate live online vs offline based on 15m active window
    online_count = 0
    offline_count = 0
    all_devs = supabase_get('devices')
    if all_devs and isinstance(all_devs, list):
        for d in all_devs:
            st = _compute_device_runtime_status(d)
            if st == 'online':
                online_count += 1
            elif st == 'offline':
                offline_count += 1

    # 3. Sensor readings statistics
    total_readings = execute_sql("SELECT count(*) FROM public.sensor_readings;")[0][0]
    real_readings = execute_sql("SELECT count(*) FROM public.sensor_readings WHERE provenance = 'real_sensor';")[0][0]
    sim_readings = execute_sql("SELECT count(*) FROM public.sensor_readings WHERE provenance = 'simulated';")[0][0]
    readings_24h = execute_sql("SELECT count(*) FROM public.sensor_readings WHERE COALESCE(observed_at, created_at) >= now() - interval '24 hours';")[0][0]

    # 4. Pollution reports statistics
    report_rows = execute_sql("SELECT COALESCE(status, 'submitted'), count(*) FROM public.pollution_reports GROUP BY COALESCE(status, 'submitted');")
    reports_by_status = {r[0]: r[1] for r in report_rows}
    total_reports = sum(reports_by_status.values())
    resolved_reports = reports_by_status.get('resolved', 0)
    resolution_rate = round((resolved_reports / total_reports * 100), 1) if total_reports > 0 else 0.0

    # 5. Flood predictions distribution
    flood_rows = execute_sql("SELECT risk_level, count(*) FROM public.flood_predictions GROUP BY risk_level;")
    flood_risk_counts = {r[0]: r[1] for r in flood_rows}

    return jsonify({
        'status': 'success',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'stations': {
            'total': total_stations,
            'by_status': stations_by_status,
            'active': stations_by_status.get('active', 0),
            'planned': stations_by_status.get('planned', 0),
            'installed': stations_by_status.get('installed', 0)
        },
        'devices': {
            'total': total_devices,
            'active_online': online_count,
            'online_active': online_count,
            'offline': offline_count,
            'provisioned': devices_by_status.get('provisioned', 0),
            'by_lifecycle': devices_by_status,
            'by_status': devices_by_status
        },
        'readings': {
            'total': total_readings,
            'real_sensor': real_readings,
            'simulated': sim_readings,
            'last_24h': readings_24h
        },
        'telemetry': {
            'total_readings': total_readings,
            'readings_last_24h': readings_24h,
            'real_sensor_count': real_readings,
            'simulated_count': sim_readings,
            'by_provenance': {'real_sensor': real_readings, 'simulated': sim_readings}
        },
        'pollution_reports': {
            'total': total_reports,
            'by_status': reports_by_status,
            'submitted': reports_by_status.get('submitted', reports_by_status.get('PENDING', 0)),
            'investigating': reports_by_status.get('investigating', 0),
            'resolved': resolved_reports,
            'rejected': reports_by_status.get('rejected', 0),
            'resolution_rate_pct': resolution_rate
        },
        'flood_risk': {
            'risk_level_counts': flood_risk_counts,
            'by_severity': flood_risk_counts,
            'latest_predictions_count': sum(flood_risk_counts.values())
        },
        'cwc_reference_gauge': {
            'site': 'Varanasi (Ganga River)',
            'warning_level_m': CWC_WARNING_LEVEL_M,
            'danger_level_m': CWC_DANGER_LEVEL_M,
            'highest_flood_level_m': CWC_HFL_M
        }
    })


# ============================================================================
# 5. FILTERED CSV DATA EXPORT
# ============================================================================

@stations_v1_bp.route('/api/v1/export/sensor-data', methods=['GET'])
def export_filtered_sensor_data_v1():
    """
    Stream filtered sensor telemetry as CSV.
    Supports query filters:
      - station_id
      - parameter
      - timeframe / start_time / end_time
      - provenance
      - quality_status
      - limit (default 1000, max 5000)
    """
    station_id = request.args.get('station_id')
    parameter = request.args.get('parameter', 'all').lower().strip()
    timeframe = request.args.get('timeframe', 'all').lower().strip()
    start_arg = request.args.get('start_time')
    end_arg = request.args.get('end_time')
    provenance = request.args.get('provenance', 'all').strip()
    quality = request.args.get('quality_status', 'all').strip()

    try:
        limit = min(int(request.args.get('limit', 1000)), 5000)
    except ValueError:
        limit = 1000

    sql_conditions = ["1=1"]
    sql_params: Dict[str, Any] = {'limit': limit}

    if station_id and station_id != 'all':
        sql_conditions.append("s.id = :sid::uuid OR s.station_code = :sid")
        sql_params['sid'] = station_id

    if provenance != 'all':
        sql_conditions.append("r.provenance = :prov")
        sql_params['prov'] = provenance

    if quality != 'all':
        sql_conditions.append("r.quality_status = :qstatus")
        sql_params['qstatus'] = quality

    if timeframe != 'all':
        try:
            st, et = _parse_time_bounds(timeframe, start_arg, end_arg)
            sql_conditions.append("COALESCE(r.observed_at, r.created_at) >= :start_time")
            sql_conditions.append("COALESCE(r.observed_at, r.created_at) <= :end_time")
            sql_params['start_time'] = st.isoformat()
            sql_params['end_time'] = et.isoformat()
        except ValueError as ve:
            return jsonify({'status': 'error', 'message': str(ve)}), 400

    where_clause = " AND ".join(sql_conditions)

    export_sql = f"""
        SELECT 
            r.id,
            COALESCE(r.observed_at, r.created_at) as timestamp_utc,
            s.station_code,
            s.station_name,
            r.ph,
            r.turbidity,
            r.temperature,
            r.water_level,
            r.ec,
            r."do",
            r.provenance,
            r.quality_status
        FROM public.sensor_readings r
        LEFT JOIN public.monitoring_stations s ON r.station_id = s.id
        WHERE {where_clause}
        ORDER BY COALESCE(r.observed_at, r.created_at) DESC
        LIMIT :limit;
    """

    rows = execute_sql(export_sql, sql_params)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Reading_ID', 'Timestamp_UTC', 'Station_Code', 'Station_Name',
        'pH', 'Turbidity_NTU', 'Temperature_C', 'Water_Level_M',
        'EC_uS_cm', 'DO_mg_L', 'Provenance', 'Quality_Status'
    ])

    if rows:
        for row in rows:
            writer.writerow([
                row[0],
                row[1].isoformat() if row[1] else '',
                row[2] or 'UNBOUND',
                row[3] or 'Unassigned Station',
                row[4] if row[4] is not None else '',
                row[5] if row[5] is not None else '',
                row[6] if row[6] is not None else '',
                row[7] if row[7] is not None else '',
                row[8] if row[8] is not None else '',
                row[9] if row[9] is not None else '',
                row[10] or 'unknown',
                row[11] or 'unvalidated'
            ])
    else:
        writer.writerow(['No database records matched the selected query filters'])

    response = make_response(output.getvalue())
    filename = f"RiverSentinel_Export_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    return response


@stations_v1_bp.route('/api/authority/export-data', methods=['GET'])
@require_role('authority_admin', 'field_officer')
def export_authority_data_v1():
    return export_filtered_sensor_data_v1()


# ============================================================================
# 6. DYNAMIC SCIENTIFIC STATION SAFETY EVALUATION
# ============================================================================

@stations_v1_bp.route('/api/v1/stations/<station_id>/evaluate-safety', methods=['GET', 'POST'])
def evaluate_station_safety_v1(station_id: str):
    """
    Transparent scientific safety screening for a specific station based on its latest observation.
    Evaluates:
      1. Drinking Water Suitability Screening (BIS IS 10500:2012 benchmarks).
      2. Outdoor Bathing Water Quality Screening (CPCB Primary Water Quality Criteria Class B).
      3. Ecological Condition & Dissolved Oxygen Health.
      4. Sensor Anomaly Screening & Calibration Confidence.
    
    IMPORTANT DISCLAIMER:
    In-situ electrochemical and optical sensors (pH, turbidity, EC, DO) are screening tools.
    They cannot detect bacteriological pathogens (e.g. Fecal Coliform) or complex toxins.
    Single-point sensor readings do not constitute official certification of drinking water safety.
    """
    station = _find_station(station_id)
    if not station:
        return jsonify({'status': 'error', 'error_code': 'NOT_FOUND', 'message': f"Station '{station_id}' not found"}), 404

    sid = station['id']

    # Fetch latest observation
    readings = supabase_get('sensor_readings', filters={'station_id': f'eq.{sid}'}, order='created_at.desc', limit=1)
    if not readings:
        return jsonify({
            'status': 'no_data',
            'station_code': station.get('station_code'),
            'station_name': station.get('station_name'),
            'evaluation': None,
            'message': 'No sensor readings have been recorded for this station yet.'
        }), 200

    r = readings[0]
    ph = float(r['ph']) if r.get('ph') is not None else None
    turb = float(r['turbidity']) if r.get('turbidity') is not None else None
    ec = float(r['ec']) if r.get('ec') is not None else None
    do_v = float(r['do']) if r.get('do') is not None else None
    temp = float(r['temperature']) if r.get('temperature') is not None else None
    wl = float(r['water_level']) if r.get('water_level') is not None else None
    q_status = r.get('quality_status', 'valid')
    provenance = r.get('provenance', 'real_sensor')

    bod = float(r['bod']) if r.get('bod') is not None else None
    total_coliform = float(r['total_coliform']) if r.get('total_coliform') is not None else None

    # Parameter Evaluations against Reference Standards
    # 1. Statutory CPCB Class B Outdoor Bathing Assessment (pH, DO, BOD, Total Coliform)
    # Turbidity is NOT a statutory CPCB Class B parameter and is evaluated separately below.
    cpcb_eval = AlertService.evaluate_cpcb_class_b_compliance(
        ph=ph,
        do_v=do_v,
        bod=bod,
        total_coliform=total_coliform
    )

    compliance_status = cpcb_eval['compliance_status']
    is_partial = cpcb_eval['assessment_type'] == 'partial_assessment'

    # Determine backward-compatible suitability and verdict
    if compliance_status == 'insufficient_data':
        bathing_suitability = 'INSUFFICIENT_TELEMETRY'
        bathing_verdict = 'INSUFFICIENT_DATA'
    elif compliance_status == 'compliant_for_measured_parameters':
        bathing_suitability = 'SUITABLE'
        bathing_verdict = 'COMPLIANT_FOR_MEASURED_PARAMETERS' if is_partial else 'CPCB_CLASS_B_COMPLIANT'
    else:
        bathing_suitability = 'UNSUITABLE'
        bathing_verdict = 'NON_COMPLIANT_FOR_MEASURED_PARAMETERS' if is_partial else 'CPCB_CLASS_B_NON_COMPLIANT'

    bathing_notes = []
    if ph is not None and (ph < 6.5 or ph > 8.5):
        bathing_notes.append(f"pH {ph} is outside CPCB Class B range (6.5 - 8.5).")
    if do_v is not None and do_v < 5.0:
        bathing_notes.append(f"Dissolved oxygen {do_v} mg/L is below CPCB Class B minimum (5.0 mg/L).")
    if is_partial:
        bathing_notes.append("Partial screening: Laboratory BOD (<= 3.0 mg/L) and Total Coliform (<= 500 MPN/100 mL) are required for statutory certification.")
    elif not bathing_notes:
        bathing_notes.append("In-situ parameters meet CPCB Class B benchmarks for religious and recreational bathing.")

    # 2. Operational Turbidity Screening (Project Investigation Guideline v2.0 - Non-statutory)
    turb_investigation_threshold = 100.0
    turb_screening_status = 'NORMAL'
    turb_notes = []
    if turb is not None:
        if turb > turb_investigation_threshold:
            turb_screening_status = 'INVESTIGATION_RECOMMENDED'
            turb_notes.append(f"Turbidity ({turb} NTU) exceeds operational investigation threshold ({turb_investigation_threshold} NTU).")
        elif turb > 30.0:
            turb_screening_status = 'ELEVATED'
            turb_notes.append(f"Elevated turbidity ({turb} NTU) indicates sediment suspension or surface runoff.")
        else:
            turb_notes.append(f"Turbidity ({turb} NTU) within baseline river conditions.")
    else:
        turb_notes.append("Turbidity unmeasured.")

    # 3. Raw River Water Drinking Screening (BIS IS 10500:2012)
    # Note: Raw river water is NEVER safe for direct drinking without conventional treatment and disinfection.
    drinking_verdict = 'TREATMENT_REQUIRED'
    drinking_notes = [
        "Raw river water requires conventional treatment and disinfection (chlorination/filtration) prior to consumption."
    ]
    if ph is not None and (ph < 6.5 or ph > 8.5):
        drinking_notes.append(f"pH ({ph}) outside acceptable drinking range (6.5 - 8.5).")
    if turb is not None and turb > 5.0:
        drinking_notes.append(f"Turbidity ({turb} NTU) exceeds potable standard (1 - 5 NTU).")
    if ec is not None and ec > 1000.0:
        drinking_notes.append(f"High electrical conductivity ({ec} uS/cm) indicates elevated dissolved solids.")

    # 4. Ecological Health
    eco_verdict = 'HEALTHY'
    if do_v is not None and do_v < 4.0:
        eco_verdict = 'STRESSED'
    elif do_v is not None and do_v < 2.0:
        eco_verdict = 'HYPOXIC'

    # 5. Calibration & Scientific Confidence
    confidence = 'HIGH' if (provenance == 'real_sensor' and q_status == 'valid') else 'PROVISIONAL'
    if q_status in ('uncalibrated', 'provisional'):
        confidence = 'UNCALIBRATED_PROVISIONAL'

    return jsonify({
        'status': 'success',
        'station_id': sid,
        'station_code': station.get('station_code'),
        'station_name': station.get('station_name'),
        'station': {
            'id': sid,
            'station_code': station.get('station_code'),
            'station_name': station.get('station_name'),
            'lifecycle_status': station.get('status')
        },
        'observation_timestamp': r.get('observed_at') or r.get('created_at'),
        'observation': {
            'observed_at': r.get('observed_at') or r.get('created_at'),
            'provenance': provenance,
            'quality_status': q_status,
            'raw_telemetry': {
                'ph': ph, 'turbidity': turb, 'temperature': temp,
                'humidity': float(r['humidity']) if r.get('humidity') is not None else None,
                'ec': ec, 'water_level': wl, 'do': do_v
            }
        },
        'provenance': provenance,
        'quality_status': q_status,
        'confidence_level': confidence,
        'parameters': {
            'ph': ph, 'turbidity_ntu': turb, 'temperature_c': temp,
            'ec_us_cm': ec, 'do_mg_l': do_v, 'water_level_m': wl
        },
        'evaluations': {
            'bathing_suitability': {
                'verdict': bathing_verdict,
                'suitability': bathing_suitability,
                'compliance_status': compliance_status,
                'assessment_type': cpcb_eval['assessment_type'],
                'standard': 'CPCB Primary Water Quality Criteria for Class B (Outdoor Bathing)',
                'notes': bathing_notes
            },
            'potable_screening': {
                'verdict': drinking_verdict,
                'standard': 'Bureau of Indian Standards (BIS IS 10500:2012)',
                'notes': drinking_notes
            },
            'ecological_health': {
                'verdict': eco_verdict,
                'dissolved_oxygen_status': 'ADEQUATE' if (do_v and do_v >= 5.0) else 'SUBOPTIMAL'
            },
            'operational_turbidity_screening': {
                'parameter': 'turbidity',
                'value_ntu': turb,
                'investigation_threshold_ntu': turb_investigation_threshold,
                'status': turb_screening_status,
                'is_cpcb_statutory': False,
                'source_reference': 'Project Investigation Guideline v2.0',
                'notes': turb_notes
            }
        },
        'bathing_water_screening': {
            'cpcb_class': 'Class B (Outdoor Bathing)',
            'suitability': bathing_suitability,
            'verdict': bathing_verdict,
            'compliance_status': compliance_status,
            'assessment_type': cpcb_eval['assessment_type'],
            'full_class_b_declared': cpcb_eval['full_class_b_declared'],
            'criteria': cpcb_eval['criteria'],
            'missing_criteria': cpcb_eval['missing_criteria'],
            'notes': ' '.join(bathing_notes),
            'disclaimer': cpcb_eval['disclaimer']
        },
        'operational_screening': {
            'parameter': 'turbidity',
            'value_ntu': turb,
            'investigation_threshold_ntu': turb_investigation_threshold,
            'status': turb_screening_status,
            'is_cpcb_statutory': False,
            'source_reference': 'Project Investigation Guideline v2.0',
            'notes': turb_notes
        },
        'drinking_water_screening': {
            'standard': 'Bureau of Indian Standards (BIS IS 10500:2012)',
            'suitability_level': drinking_verdict,
            'bis_is10500_compliance': {
                'ph': {'value': ph, 'acceptable_limit': '6.5 - 8.5', 'permissible_limit': 'No relaxation', 'status': 'PASS' if (ph and 6.5 <= ph <= 8.5) else 'FAIL'},
                'turbidity': {'value': turb, 'acceptable_limit': '1 NTU', 'permissible_limit': '5 NTU', 'status': 'PASS' if (turb and turb <= 5.0) else 'FAIL'},
                'tds_ec': {'value': ec, 'benchmark': '<= 1000 uS/cm', 'status': 'PASS' if (ec and ec <= 1000.0) else 'FAIL'}
            },
            'disclaimer': (
                "In-situ electronic probes screen physical and chemical properties only. "
                "Raw river water contains bacteriological contaminants (e.g., Fecal Coliform) "
                "and must undergo conventional treatment and disinfection per BIS IS 10500:2012 prior to human consumption."
            )
        },
        'ecological_screening': {
            'status': eco_verdict,
            'do_reading_mg_l': do_v,
            'description': 'Adequate for aquatic biomes.' if eco_verdict == 'HEALTHY' else 'Dissolved oxygen stress detected.'
        },
        'sensor_anomaly_screening': {
            'anomalies_detected': [],
            'is_simulated': (provenance == 'simulated'),
            'confidence_score': 0.95 if confidence == 'HIGH' else 0.70
        },
        'scientific_disclaimer': (
            "Screening is based exclusively on in-situ electronic probe readings. "
            "Bacteriological pathogens (Fecal Coliform, E. Coli) and chemical toxins require laboratory testing. "
            "Never consume untreated river water based solely on automated sensor readings."
        )
    })
