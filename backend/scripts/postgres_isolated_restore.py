"""
River Sentinel 2.0 - Native PostgreSQL Isolated Disaster Recovery Engine (Phase 7.1)
Restores and verifies backups against an actual PostgreSQL 15 engine in an isolated namespace.
- Strictly isolated: Operates in dedicated schema 'isolated_restore_test'.
- Zero impact: Never drops or modifies the active development tables in 'public'.
- Tests true PostgreSQL features: Tables, Foreign Keys, Indexes, RLS Policies, Views.
- Measures true Recovery Time Objective (RTO) on live PostgreSQL engine.
"""

import os
import sys
import json
import time
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from services.supabase_service import get_db_connection
from scripts.postgres_backup import generate_postgres_backup, TABLES_INVENTORY

ISOLATED_SCHEMA = "isolated_restore_test"


def split_sql_statements(sql: str) -> List[str]:
    """Split SQL script into statements respecting single quotes, double quotes, and PostgreSQL dollar quotes."""
    statements = []
    current = []
    in_quote = False
    quote_char = None
    in_dollar_quote = False
    dollar_tag = None
    i = 0
    n = len(sql)
    while i < n:
        c = sql[i]
        if in_quote:
            if c == quote_char:
                if i + 1 < n and sql[i + 1] == quote_char:
                    current.append(c)
                    current.append(sql[i + 1])
                    i += 2
                    continue
                else:
                    in_quote = False
            current.append(c)
        elif in_dollar_quote:
            if c == '$' and sql[i:].startswith(dollar_tag):
                current.append(dollar_tag)
                i += len(dollar_tag)
                in_dollar_quote = False
                continue
            current.append(c)
        else:
            if c == '$':
                next_dollar = sql.find('$', i + 1)
                if next_dollar != -1 and (next_dollar - i) <= 30:
                    candidate = sql[i:next_dollar + 1]
                    inner = candidate[1:-1]
                    if all(ch.isalnum() or ch == '_' for ch in inner):
                        in_dollar_quote = True
                        dollar_tag = candidate
                        current.append(dollar_tag)
                        i += len(dollar_tag)
                        continue
            if c in ("'", '"'):
                in_quote = True
                quote_char = c
                current.append(c)
            elif c == ';':
                stmt = "".join(current).strip()
                if stmt:
                    statements.append(stmt)
                current = []
            else:
                current.append(c)
        i += 1
    if current:
        stmt = "".join(current).strip()
        if stmt:
            statements.append(stmt)
    return statements


def execute_isolated_postgresql_restore() -> Dict[str, Any]:
    """
    Restore the PostgreSQL backup into an isolated schema on the live PostgreSQL cluster,
    verify all database and security integrity, measure RTO, and safely clean up.
    """
    total_start_time = time.time()
    now_utc = datetime.now(timezone.utc)
    print(f"[{now_utc.strftime('%Y-%m-%d %H:%M:%S')}] Commencing Native PostgreSQL Isolated Restore Test...")
    print(f"  Target Isolated Schema: {ISOLATED_SCHEMA}")

    # Step 1: Generate native SQL dump configured specifically for isolated schema
    t0_backup = time.time()
    sql_path, manifest_path, manifest = generate_postgres_backup(target_schema_override=ISOLATED_SCHEMA)
    backup_gen_duration = round(time.time() - t0_backup, 3)

    with open(sql_path, 'r', encoding='utf-8') as f:
        sql_script = f.read()

    expected_tables = manifest['tables']
    total_expected_rows = manifest['total_rows']

    con = get_db_connection()
    t_restore_start = time.time()
    
    report: Dict[str, Any] = {
        'isolated_schema': ISOLATED_SCHEMA,
        'source_project_id': manifest['project_id'],
        'execution_timestamp': now_utc.isoformat(),
        'backup_generation_duration_seconds': backup_gen_duration,
        'sql_dump_size_kb': round(os.path.getsize(sql_path) / 1024, 1),
        'sql_dump_checksum': manifest['sql_dump_sha256'],
        'tables_verified': {},
        'table_discrepancies': [],
        'indexes_verified': 0,
        'constraints_verified': 0,
        'rls_policies_verified': 0,
        'views_verified': 0,
        'foreign_key_integrity': 'UNKNOWN',
        'sample_queries': {},
        'status': 'FAILED'
    }

    try:
        # Step 2: Clean isolated schema to ensure pristine testing environment
        print(f"  Resetting isolated schema '{ISOLATED_SCHEMA}'...")
        con.run(f"DROP SCHEMA IF EXISTS {ISOLATED_SCHEMA} CASCADE;")
        con.run(f"CREATE SCHEMA {ISOLATED_SCHEMA};")

        # Step 3: Execute the SQL restoration script
        print(f"  Executing restoration statements on PostgreSQL engine...")
        t_exec_start = time.time()
        
        # Split statements carefully: DDL, inserts, constraints
        statements = split_sql_statements(sql_script)
        for stmt in statements:
            # Skip pure comments
            lines = [l for l in stmt.split('\n') if not l.strip().startswith('--')]
            clean_stmt = "\n".join(lines).strip()
            if not clean_stmt:
                continue
            con.run(clean_stmt)

        restore_exec_duration = round(time.time() - t_exec_start, 3)
        print(f"  Restoration statements executed in {restore_exec_duration}s.")

        # Step 4: Verification of Database Integrity
        print(f"  Verifying table counts, structures, and indexes in '{ISOLATED_SCHEMA}'...")
        t_verify_start = time.time()

        # 4.1 Tables & Row Counts
        for table in TABLES_INVENTORY:
            try:
                cnt_res = con.run(f'SELECT count(*) FROM {ISOLATED_SCHEMA}."{table}";')
                actual_cnt = cnt_res[0][0] if cnt_res else 0
                expected_cnt = expected_tables.get(table, {}).get('row_count', 0)
                
                report['tables_verified'][table] = {
                    'expected_rows': expected_cnt,
                    'restored_rows': actual_cnt,
                    'match': (actual_cnt == expected_cnt)
                }

                if actual_cnt != expected_cnt:
                    report['table_discrepancies'].append({
                        'table': table, 'expected': expected_cnt, 'actual': actual_cnt
                    })
            except Exception as e:
                report['table_discrepancies'].append({
                    'table': table, 'error': str(e)
                })

        # 4.2 Indexes Verification
        idx_res = con.run(f"""
            SELECT count(*) FROM pg_indexes 
            WHERE schemaname = '{ISOLATED_SCHEMA}';
        """)
        report['indexes_verified'] = idx_res[0][0] if idx_res else 0

        # 4.3 Constraints Verification (PK, Unique, FK)
        con_res = con.run(f"""
            SELECT count(*) FROM pg_constraint 
            WHERE connamespace = '{ISOLATED_SCHEMA}'::regnamespace;
        """)
        report['constraints_verified'] = con_res[0][0] if con_res else 0

        # 4.4 RLS Verification
        rls_res = con.run(f"""
            SELECT tablename, rowsecurity FROM pg_tables 
            WHERE schemaname = '{ISOLATED_SCHEMA}';
        """)
        all_rls_enabled = all(r[1] for r in rls_res) if rls_res else False
        report['all_tables_rls_enabled'] = all_rls_enabled

        # Policies count
        pol_res = con.run(f"""
            SELECT count(*) FROM pg_policies 
            WHERE schemaname = '{ISOLATED_SCHEMA}';
        """)
        report['rls_policies_verified'] = pol_res[0][0] if pol_res else 0

        # 4.5 Foreign Key Relational Traversal
        fk_check_res = con.run(f"""
            SELECT count(*) 
            FROM {ISOLATED_SCHEMA}.devices d
            LEFT JOIN {ISOLATED_SCHEMA}.monitoring_stations s ON d.station_id = s.id
            WHERE s.id IS NULL AND d.station_id IS NOT NULL;
        """)
        orphaned_devices = fk_check_res[0][0] if fk_check_res else 0
        report['foreign_key_integrity'] = 'PASSED' if (orphaned_devices == 0) else 'FAILED'

        # 4.6 Views Verification
        try:
            view_res = con.run(f"SELECT count(*) FROM {ISOLATED_SCHEMA}.public_sensor_telemetry;")
            report['views_verified'] = 1
            report['sample_queries']['view_count'] = view_res[0][0] if view_res else 0
        except Exception:
            report['views_verified'] = 0

        # 4.7 Sample Data Query
        sample_sensor = con.run(f"""
            SELECT ph, turbidity, water_level, created_at 
            FROM {ISOLATED_SCHEMA}.sensor_readings 
            ORDER BY created_at DESC LIMIT 1;
        """)
        if sample_sensor:
            report['sample_queries']['latest_sensor_reading'] = {
                'ph': str(sample_sensor[0][0]),
                'turbidity': str(sample_sensor[0][1]),
                'water_level': str(sample_sensor[0][2]),
                'created_at': str(sample_sensor[0][3])
            }

        verification_duration = round(time.time() - t_verify_start, 3)

        # Step 5: Teardown Isolated Schema (Leave zero residue)
        print(f"  Tearing down isolated test schema '{ISOLATED_SCHEMA}'...")
        con.run(f"DROP SCHEMA IF EXISTS {ISOLATED_SCHEMA} CASCADE;")

        total_rto_duration = round(time.time() - t_restore_start, 3)
        overall_duration = round(time.time() - total_start_time, 3)

        report['rto_measurement'] = {
            'restore_execution_seconds': restore_exec_duration,
            'integrity_verification_seconds': verification_duration,
            'total_rto_seconds': total_rto_duration,
            'overall_end_to_end_seconds': overall_duration
        }

        is_success = (
            len(report['table_discrepancies']) == 0 and
            report['foreign_key_integrity'] == 'PASSED' and
            report['all_tables_rls_enabled'] is True and
            report['indexes_verified'] > 0
        )

        report['status'] = 'SUCCESS' if is_success else 'FAILED'

        # Persist verification report to backups directory
        report_filename = f"river_sentinel_restore_report_{now_utc.strftime('%Y%m%d_%H%M%S')}.json"
        report_path = os.path.join(BACKUP_DIR, report_filename)
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)

        print(f"\n[{'SUCCESS' if is_success else 'FAILURE'}] PostgreSQL Isolated Restore Verification Complete!")
        print(f"  Total Tables Restored: {len(report['tables_verified'])}")
        print(f"  Total Rows Restored: {sum([t['restored_rows'] for t in report['tables_verified'].values()])}")
        print(f"  Discrepancies: {len(report['table_discrepancies'])}")
        print(f"  Indexes Restored: {report['indexes_verified']}")
        print(f"  Constraints Restored: {report['constraints_verified']}")
        print(f"  RLS Policies Restored: {report['rls_policies_verified']}")
        print(f"  Foreign Key Traversal: {report['foreign_key_integrity']}")
        print(f"  Total Measured PostgreSQL RTO: {total_rto_duration} seconds")
        print(f"  Report written to: {report_path}")

        return report

    finally:
        con.close()


if __name__ == '__main__':
    execute_isolated_postgresql_restore()
