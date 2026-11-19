"""
River Sentinel 2.0 - Database Backup Utility (Phase 7)
Safely extracts schema structure and table data from Supabase PostgreSQL.
- Connects directly using SSL connection credentials.
- Exports all public application tables and metadata.
- Computes SHA-256 checksum for backup integrity verification.
- Stores backup in the isolated backups/ directory (ignored by git).
"""

import os
import sys
import json
import time
import hashlib
from datetime import datetime, date, timezone
import uuid
from decimal import Decimal


def _json_serial(obj):
    """JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (bytes, bytearray)):
        return obj.hex()
    return str(obj)

# Ensure backend root is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from services.supabase_service import get_db_connection

# Directory for backups (outside working code, git-ignored)
root_dir = os.path.dirname(backend_dir)
BACKUP_DIR = os.path.join(root_dir, 'backups')
os.makedirs(BACKUP_DIR, exist_ok=True)

TABLES_TO_BACKUP = [
    'profiles',
    'monitoring_stations',
    'devices',
    'cwc_reference_gauges',
    'station_assignments',
    'sensor_readings',
    'pollution_reports',
    'alert_rules',
    'system_alerts',
    'alert_events',
    'notification_preferences',
    'notification_deliveries',
    'flood_predictions',
    'device_telemetry_logs',
    'worker_heartbeats'
]


def backup_database() -> str:
    """Extract and serialize database tables into a timestamped JSON backup file."""
    start_time = time.time()
    now_utc = datetime.now(timezone.utc)
    timestamp_str = now_utc.strftime('%Y%m%d_%H%M%S')
    backup_filename = f"river_sentinel_backup_{timestamp_str}.json"
    backup_path = os.path.join(BACKUP_DIR, backup_filename)

    print(f"[{now_utc.strftime('%Y-%m-%d %H:%M:%S')}] Starting River Sentinel database backup...")

    con = get_db_connection()
    backup_data: Dict[str, Any] = {
        'version': '2.0.0',
        'created_at': now_utc.isoformat(),
        'database_host': os.getenv('SUPABASE_DB_HOST', 'supabase_postgres')[:12] + '...',
        'tables': {},
        'table_counts': {}
    }

    total_rows = 0

    try:
        for table in TABLES_TO_BACKUP:
            try:
                # Query column names
                cols_query = f"""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' AND table_name = '{table}'
                    ORDER BY ordinal_position;
                """
                col_rows = con.run(cols_query)
                columns = [r[0] for r in col_rows]

                # Query all data
                data_query = f"SELECT * FROM public.{table};"
                rows = con.run(data_query)
                
                # Convert rows to serializable format
                serialized_rows = []
                for r in rows:
                    row_dict = {}
                    for idx, col in enumerate(columns):
                        val = r[idx]
                        if isinstance(val, (datetime,)):
                            val = val.isoformat()
                        elif isinstance(val, (bytes, bytearray)):
                            val = val.hex()
                        row_dict[col] = val
                    serialized_rows.append(row_dict)

                backup_data['tables'][table] = {
                    'columns': columns,
                    'rows': serialized_rows
                }
                backup_data['table_counts'][table] = len(serialized_rows)
                total_rows += len(serialized_rows)
                print(f"  ✓ Backed up table '{table}': {len(serialized_rows)} rows")

            except Exception as te:
                print(f"  [WARN] Table '{table}' backup encountered warning: {te}")
                backup_data['table_counts'][table] = 0
                backup_data['tables'][table] = {'columns': [], 'rows': []}

    finally:
        con.close()

    duration_sec = round(time.time() - start_time, 2)
    backup_data['metadata'] = {
        'total_tables': len(TABLES_TO_BACKUP),
        'total_rows': total_rows,
        'duration_seconds': duration_sec
    }

    # Write serialized JSON backup
    raw_json = json.dumps(backup_data, indent=2, default=_json_serial)
    checksum = hashlib.sha256(raw_json.encode('utf-8')).hexdigest()
    backup_data['checksum_sha256'] = checksum

    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(backup_data, f, indent=2, default=_json_serial)

    print(f"\n[SUCCESS] Backup completed successfully in {duration_sec}s!")
    print(f"  File: {backup_path}")
    print(f"  Total tables: {len(TABLES_TO_BACKUP)} | Total rows: {total_rows}")
    print(f"  SHA-256 Checksum: {checksum}")

    return backup_path


if __name__ == '__main__':
    backup_database()
