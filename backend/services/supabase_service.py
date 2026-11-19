"""
Supabase Database Service for River Sentinel 2.0
Centralizes all PostgreSQL / PostgREST operations via server-side credentials.
"""

import os
import requests
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from dotenv import load_dotenv

# Ensure backend/.env is reliably loaded even when invoked standalone
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_env_path = os.path.join(_backend_dir, '.env')
if os.path.exists(_env_path):
    load_dotenv(_env_path)
else:
    load_dotenv()

# Load environment
SUPABASE_URL = os.getenv('SUPABASE_URL', '').rstrip('/')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_KEY')


def get_db_connection():
    """Establish direct SSL connection to Supabase PostgreSQL database."""
    import pg8000.native
    return pg8000.native.Connection(
        user=os.getenv('SUPABASE_DB_USER', 'postgres'),
        host=os.getenv('SUPABASE_DB_HOST'),
        port=int(os.getenv('SUPABASE_DB_PORT', 5432)),
        password=os.getenv('SUPABASE_DB_PASSWORD'),
        database=os.getenv('SUPABASE_DB_NAME', 'postgres'),
        ssl_context=True
    )


def execute_sql(query: str, params: Optional[Dict[str, Any]] = None) -> List[List[Any]]:
    """Execute parameterized SQL query directly on the PostgreSQL database."""
    con = get_db_connection()
    try:
        if params:
            return con.run(query, **params)
        return con.run(query)
    finally:
        con.close()


def get_headers(use_service_role: bool = True) -> Optional[Dict[str, str]]:
    """Generate authenticated headers for Supabase PostgREST API."""
    key = (SUPABASE_SERVICE_KEY if use_service_role else None) or SUPABASE_ANON_KEY
    if not key:
        return None
    return {
        'apikey': key,
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json'
    }


def supabase_insert(table_name: str, record: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """Insert a record into a Supabase table using server-side service role with retry."""
    if not SUPABASE_URL:
        return None
    headers = get_headers(use_service_role=True)
    if not headers:
        return None
    url = f"{SUPABASE_URL}/rest/v1/{table_name}"
    post_headers = {**headers, 'Prefer': 'return=representation'}

    for attempt in range(3):
        try:
            res = requests.post(url, headers=post_headers, json=record, timeout=5.0)
            if res.status_code in (200, 201):
                return res.json()
            print(f"[ERROR] Supabase insert to {table_name} returned {res.status_code}: {res.text[:200]}")
            return None
        except Exception as e:
            if attempt == 2:
                print(f"[ERROR] Supabase insert exception ({table_name}): {e}")
            time.sleep(0.2)
    return None


def supabase_get(table_name: str, select: str = "*", order: Optional[str] = None,
                 limit: Optional[int] = None, filters: Optional[Dict[str, str]] = None) -> Optional[List[Dict[str, Any]]]:
    """Query records from a Supabase table with retry on transient SSL/network drops."""
    if not SUPABASE_URL:
        return None
    headers = get_headers(use_service_role=True)
    if not headers:
        return None

    query_parts = [f"select={select}"]
    if order:
        query_parts.append(f"order={order}")
    if limit:
        query_parts.append(f"limit={limit}")
    if filters:
        for col, condition in filters.items():
            query_parts.append(f"{col}={condition}")

    query_str = "&".join(query_parts)
    url = f"{SUPABASE_URL}/rest/v1/{table_name}?{query_str}"

    for attempt in range(3):
        try:
            res = requests.get(url, headers=headers, timeout=5.0)
            if res.status_code == 200:
                return res.json()
            print(f"[ERROR] Supabase query on {table_name} returned {res.status_code}: {res.text[:200]}")
            return None
        except Exception as e:
            if attempt == 2:
                print(f"[ERROR] Supabase query exception ({table_name}): {e}")
            time.sleep(0.2)
    return None


def supabase_update(table_name: str, filter_param: str, record: Dict[str, Any]) -> bool:
    """Update records in a Supabase table matching the filter_param with retry."""
    if not SUPABASE_URL:
        return False
    headers = get_headers(use_service_role=True)
    if not headers:
        return False
    url = f"{SUPABASE_URL}/rest/v1/{table_name}?{filter_param}"

    for attempt in range(3):
        try:
            res = requests.patch(url, headers=headers, json=record, timeout=5.0)
            return res.status_code in (200, 204)
        except Exception as e:
            if attempt == 2:
                print(f"[ERROR] Supabase update exception ({table_name}): {e}")
            time.sleep(0.2)
    return False


def get_latest_sensor_reading() -> Optional[Dict[str, Any]]:
    """Retrieve the single most recent sensor reading from Supabase."""
    rows = supabase_get('sensor_readings', order='created_at.desc', limit=1)
    if rows and isinstance(rows, list) and len(rows) > 0:
        return rows[0]
    return None


def get_sensor_summary() -> Dict[str, Any]:
    """Calculate statistical averages from recent sensor readings."""
    default_stats = {
        'avg_ph': 7.4,
        'avg_do': 6.8,
        'avg_turbidity': 14.5,
        'avg_water_level': 67.5,
        'trend': 'STABLE',
        'sample_count': 0
    }
    rows = supabase_get('sensor_readings', order='created_at.desc', limit=50)
    if not rows or not isinstance(rows, list):
        return default_stats
    
    phs = [float(r['ph']) for r in rows if r.get('ph') is not None]
    dos = [float(r['do']) for r in rows if r.get('do') is not None]
    turbs = [float(r['turbidity']) for r in rows if r.get('turbidity') is not None]
    wls = [float(r['water_level']) for r in rows if r.get('water_level') is not None]

    if not phs:
        return default_stats

    return {
        'avg_ph': round(sum(phs) / len(phs), 2),
        'avg_do': round(sum(dos) / len(dos), 2) if dos else 6.8,
        'avg_turbidity': round(sum(turbs) / len(turbs), 1) if turbs else 14.5,
        'avg_water_level': round(sum(wls) / len(wls), 2) if wls else 67.5,
        'trend': 'RISING' if len(wls) >= 2 and wls[0] > wls[-1] else 'STABLE',
        'sample_count': len(rows)
    }


def get_reports_summary() -> Dict[str, Any]:
    """Calculate summary statistics from pollution reports."""
    default_stats = {
        'total': 0,
        'verified': 0,
        'rejected': 0,
        'pending': 0,
        'resolution_rate': 0.0
    }
    rows = supabase_get('pollution_reports', order='created_at.desc', limit=200)
    if not rows or not isinstance(rows, list):
        return default_stats

    stats = {'total': len(rows), 'verified': 0, 'rejected': 0, 'pending': 0}
    for r in rows:
        st = str(r.get('status', 'PENDING')).upper()
        if st == 'VERIFIED':
            stats['verified'] += 1
        elif st == 'REJECTED':
            stats['rejected'] += 1
        else:
            stats['pending'] += 1

    total = stats['total']
    stats['resolution_rate'] = round(
        (stats['verified'] + stats['rejected']) / total * 100, 1
    ) if total > 0 else 0.0

    return stats
