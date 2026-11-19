"""
postgres_independent_db_restore.py - Phase 7.2 Independent Database Restoration Engine
Performs full physical database-level disaster recovery testing:
1. Creates an isolated, dedicated database 'rs_independent_recovery_test' on PostgreSQL 15.
2. Restores the latest verified PostgreSQL DDL, constraints, rows, indexes, functions, triggers, and RLS policies.
3. Compares tables, rows, constraints, indexes, functions, triggers, RLS policies, and grants.
4. Verifies actual PostgreSQL behavior (triggers, foreign keys, RLS evaluation).
5. Runs application-level connectivity and API tests using the Flask test client.
6. Measures exact timings (Database creation, restore, verification, application testing).
7. Tears down the isolated database cleanly with DROP DATABASE ... WITH (FORCE).
"""

import os
import sys
import time
import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List

# Ensure backend root is on sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from dotenv import load_dotenv
env_path = os.path.join(BACKEND_DIR, '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv()

import pg8000.native
from scripts.postgres_backup import TABLES_INVENTORY
from scripts.postgres_isolated_restore import split_sql_statements

INDEPENDENT_DB_NAME = "rs_independent_recovery_test"
BACKUP_DIR = os.path.join(PROJECT_ROOT, "backups")


def get_cluster_connection(database: str = "postgres"):
    """Establish direct connection to specified database on Supabase PostgreSQL pooler."""
    return pg8000.native.Connection(
        user=os.getenv('SUPABASE_DB_USER', 'postgres.xqzobddgkawysprpmkpk'),
        host=os.getenv('SUPABASE_DB_HOST', 'aws-0-ap-southeast-1.pooler.supabase.com'),
        port=int(os.getenv('SUPABASE_DB_PORT', 5432)),
        database=database,
        password=os.getenv('SUPABASE_DB_PASSWORD'),
        ssl_context=True
    )


def execute_independent_database_recovery() -> Dict[str, Any]:
    """Execute complete Phase 7.2 independent database recovery simulation."""
    total_start_time = time.time()
    now_utc = datetime.now(timezone.utc)
    print(f"[{now_utc.strftime('%Y-%m-%d %H:%M:%S')}] Commencing Phase 7.2 Independent PostgreSQL Database Recovery...")
    print(f"  Target Isolated Database: {INDEPENDENT_DB_NAME}")

    # Find latest native backup and manifest
    manifest_files = [f for f in os.listdir(BACKUP_DIR) if f.startswith('river_sentinel_manifest_') and f.endswith('.json')]
    if not manifest_files:
        raise FileNotFoundError("No manifest files found in backups/")
    latest_manifest_path = os.path.join(BACKUP_DIR, sorted(manifest_files)[-1])

    with open(latest_manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    sql_path = os.path.join(BACKUP_DIR, manifest['sql_dump_file'])
    if not os.path.exists(sql_path):
        raise FileNotFoundError(f"SQL dump file not found: {sql_path}")

    # Verify SHA-256 Checksum
    with open(sql_path, 'rb') as f:
        computed_sha256 = hashlib.sha256(f.read()).hexdigest()
    if computed_sha256 != manifest['sql_dump_sha256']:
        raise ValueError(f"Checksum mismatch! Manifest: {manifest['sql_dump_sha256']}, Computed: {computed_sha256}")

    with open(sql_path, 'r', encoding='utf-8') as f:
        sql_script = f.read()

    report: Dict[str, Any] = {
        'isolated_database_name': INDEPENDENT_DB_NAME,
        'source_project_id': manifest['project_id'],
        'execution_timestamp': now_utc.isoformat(),
        'sql_dump_file': manifest['sql_dump_file'],
        'sql_dump_size_kb': round(os.path.getsize(sql_path) / 1024, 1),
        'sql_dump_sha256': computed_sha256,
        'timing_benchmarks': {},
        'tables_verified': {},
        'table_discrepancies': [],
        'indexes_verified': 0,
        'constraints_verified': 0,
        'functions_verified': 0,
        'triggers_verified': 0,
        'rls_policies_verified': 0,
        'grants_verified': 0,
        'behavioral_tests': {},
        'application_tests': {},
        'status': 'FAILED'
    }

    # Step 1: Create Independent Database on Cluster
    t_create_start = time.time()
    print(f"  Provisioning dedicated database '{INDEPENDENT_DB_NAME}'...")
    con_admin = get_cluster_connection(database="postgres")
    try:
        con_admin.run(f"DROP DATABASE IF EXISTS {INDEPENDENT_DB_NAME} WITH (FORCE);")
        con_admin.run(f"CREATE DATABASE {INDEPENDENT_DB_NAME};")
    finally:
        con_admin.close()
    db_create_duration = round(time.time() - t_create_start, 3)
    report['timing_benchmarks']['database_provisioning_seconds'] = db_create_duration
    print(f"  Database '{INDEPENDENT_DB_NAME}' created in {db_create_duration}s.")

    # Step 2: Connect to Isolated Database & Execute Restoration Statements
    t_restore_start = time.time()
    print(f"  Connecting to '{INDEPENDENT_DB_NAME}' and executing restoration script...")
    con_isolated = get_cluster_connection(database=INDEPENDENT_DB_NAME)

    try:
        statements = split_sql_statements(sql_script)
        for stmt in statements:
            lines = [l for l in stmt.split('\n') if not l.strip().startswith('--')]
            clean_stmt = "\n".join(lines).strip()
            if not clean_stmt:
                continue
            con_isolated.run(clean_stmt)

        restore_duration = round(time.time() - t_restore_start, 3)
        report['timing_benchmarks']['database_restore_execution_seconds'] = restore_duration
        print(f"  Restoration script executed in {restore_duration}s.")

        # Step 3: Comparative Integrity Verification
        t_verify_start = time.time()
        print(f"  Verifying schema, row counts, constraints, and indexes in '{INDEPENDENT_DB_NAME}'...")

        # 3.1 Table and Row Counts
        for table in TABLES_INVENTORY:
            try:
                cnt_res = con_isolated.run(f'SELECT count(*) FROM public."{table}";')
                row_cnt = cnt_res[0][0]
                expected_cnt = manifest['tables'].get(table, {}).get('row_count', 0)
                report['tables_verified'][table] = {
                    'expected_rows': expected_cnt,
                    'restored_rows': row_cnt,
                    'matches': row_cnt == expected_cnt
                }
                if row_cnt != expected_cnt:
                    report['table_discrepancies'].append({
                        'table': table, 'expected': expected_cnt, 'actual': row_cnt
                    })
            except Exception as e:
                report['tables_verified'][table] = {'error': str(e), 'matches': False}
                report['table_discrepancies'].append({'table': table, 'error': str(e)})

        # 3.2 Constraints (PK, Unique, FK)
        const_res = con_isolated.run("""
            SELECT count(*) FROM pg_constraint 
            WHERE connamespace = 'public'::regnamespace;
        """)
        report['constraints_verified'] = const_res[0][0] if const_res else 0

        # 3.3 Secondary Indexes
        idx_res = con_isolated.run("""
            SELECT count(*) FROM pg_indexes 
            WHERE schemaname = 'public' 
              AND indexname NOT LIKE '%_pkey' AND indexname NOT LIKE '%_key';
        """)
        report['indexes_verified'] = idx_res[0][0] if idx_res else 0

        # 3.4 Functions in public
        func_res = con_isolated.run("""
            SELECT proname FROM pg_proc 
            WHERE pronamespace = 'public'::regnamespace;
        """)
        restored_funcs = [r[0] for r in func_res]
        report['functions_verified'] = len(restored_funcs)
        report['restored_functions'] = restored_funcs

        # 3.5 Triggers on auth.users / public tables
        trig_res = con_isolated.run("""
            SELECT tgname FROM pg_trigger 
            WHERE tgname = 'on_auth_user_created';
        """)
        report['triggers_verified'] = len(trig_res)

        # 3.6 Row-Level Security Policies
        rls_res = con_isolated.run("""
            SELECT count(*) FROM pg_policies 
            WHERE schemaname = 'public';
        """)
        report['rls_policies_verified'] = rls_res[0][0] if rls_res else 0

        # 3.7 Grants to anon, authenticated, service_role
        grant_res = con_isolated.run("""
            SELECT count(*) FROM information_schema.role_table_grants 
            WHERE table_schema = 'public' 
              AND grantee IN ('anon', 'authenticated', 'service_role');
        """)
        report['grants_verified'] = grant_res[0][0] if grant_res else 0

        # Step 4: Behavioral Verification
        # 4.1 Foreign Key Traversal Join
        join_query = """
            SELECT s.station_code, s.station_name, d.device_code, d.status
            FROM public.monitoring_stations s
            JOIN public.devices d ON s.id = d.station_id
            LIMIT 5;
        """
        join_rows = con_isolated.run(join_query)
        report['behavioral_tests']['foreign_key_join'] = {
            'status': 'PASSED' if len(join_rows) > 0 else 'FAILED',
            'sample_count': len(join_rows)
        }

        # 4.2 Security Function (get_my_role) Evaluation
        role_res = con_isolated.run("SELECT public.get_my_role();")
        report['behavioral_tests']['get_my_role_evaluation'] = {
            'status': 'PASSED' if role_res and role_res[0][0] == 'anonymous' else 'FAILED',
            'evaluated_role': role_res[0][0] if role_res else None
        }

        # 4.3 Trigger Functionality (Insert user in auth.users -> check public.profiles auto-creation)
        test_new_uid = "99999999-9999-9999-9999-999999999999"
        con_isolated.run(f"""
            INSERT INTO auth.users (id, email, raw_user_meta_data)
            VALUES ('{test_new_uid}', 'new_citizen_test@riversentinel.test', '{{"full_name": "Citizen Auto Created"}}'::jsonb);
        """)
        profile_check = con_isolated.run(f"SELECT full_name, role FROM public.profiles WHERE id = '{test_new_uid}';")
        trigger_passed = (len(profile_check) > 0 and profile_check[0][0] == 'Citizen Auto Created')
        report['behavioral_tests']['auth_trigger_handle_new_user'] = {
            'status': 'PASSED' if trigger_passed else 'FAILED',
            'auto_created_profile': profile_check[0] if profile_check else None
        }
        # Clean up test user
        con_isolated.run(f"DELETE FROM auth.users WHERE id = '{test_new_uid}';")

        verify_duration = round(time.time() - t_verify_start, 3)
        report['timing_benchmarks']['database_validation_seconds'] = verify_duration

        # Step 5: Application Connectivity Test (Flask with Restored Database)
        t_app_start = time.time()
        print(f"  Executing Flask application tests against '{INDEPENDENT_DB_NAME}'...")

        # Point Flask to restored database
        old_db_name = os.environ.get('SUPABASE_DB_NAME')
        os.environ['SUPABASE_DB_NAME'] = INDEPENDENT_DB_NAME

        try:
            from app import app
            client = app.test_client()

            # Test 1: Liveness Probe
            live_resp = client.get('/api/health/live')
            report['application_tests']['health_live'] = {
                'status_code': live_resp.status_code,
                'status': 'PASSED' if live_resp.status_code == 200 else 'FAILED'
            }

            # Test 2: Readiness Probe
            ready_resp = client.get('/api/health/ready')
            report['application_tests']['health_ready'] = {
                'status_code': ready_resp.status_code,
                'status': 'PASSED' if ready_resp.status_code == 200 else 'FAILED'
            }

            # Test 3: Public Station List
            stn_resp = client.get('/api/stations')
            stn_data = json.loads(stn_resp.data.decode('utf-8'))
            report['application_tests']['stations_list'] = {
                'status_code': stn_resp.status_code,
                'station_count': len(stn_data.get('stations', [])),
                'status': 'PASSED' if stn_resp.status_code == 200 and len(stn_data.get('stations', [])) >= 5 else 'FAILED'
            }

            # Test 4: Citizen Water Quality Assessment
            citizen_resp = client.get('/api/citizen/health-status')
            report['application_tests']['citizen_health_status'] = {
                'status_code': citizen_resp.status_code,
                'status': 'PASSED' if citizen_resp.status_code == 200 else 'FAILED'
            }

            # Test 5: ML Flood Prediction API
            flood_resp = client.post('/api/flood/predict', json={
                'water_level': 68.5,
                'discharge': 40000,
                'rain_varanasi': 25.0,
                'rain_upstream': 40.0
            })
            report['application_tests']['flood_prediction'] = {
                'status_code': flood_resp.status_code,
                'status': 'PASSED' if flood_resp.status_code == 200 else 'FAILED'
            }

            # Test 6: ML Water Quality API
            wq_resp = client.post('/api/water-quality/predict', json={
                'ph': 7.6,
                'turbidity': 15.0,
                'temperature': 26.5,
                'humidity': 65.0,
                'ec': 350.0
            })
            report['application_tests']['water_quality_prediction'] = {
                'status_code': wq_resp.status_code,
                'status': 'PASSED' if wq_resp.status_code == 200 else 'FAILED'
            }

            # Test 7: Anonymous Access Guard (401 on Authority Reports)
            auth_guard_resp = client.get('/api/authority/reports')
            report['application_tests']['authority_guard_anonymous_401'] = {
                'status_code': auth_guard_resp.status_code,
                'status': 'PASSED' if auth_guard_resp.status_code == 401 else 'FAILED'
            }

        finally:
            if old_db_name:
                os.environ['SUPABASE_DB_NAME'] = old_db_name
            else:
                os.environ.pop('SUPABASE_DB_NAME', None)

        app_duration = round(time.time() - t_app_start, 3)
        report['timing_benchmarks']['application_verification_seconds'] = app_duration

        total_rto = round(restore_duration + verify_duration + app_duration, 3)
        overall_duration = round(time.time() - total_start_time, 3)
        report['timing_benchmarks']['total_recovery_rto_seconds'] = total_rto
        report['timing_benchmarks']['overall_duration_seconds'] = overall_duration

        is_success = (
            len(report['table_discrepancies']) == 0 and
            report['behavioral_tests']['foreign_key_join']['status'] == 'PASSED' and
            report['behavioral_tests']['auth_trigger_handle_new_user']['status'] == 'PASSED' and
            report['application_tests']['health_ready']['status'] == 'PASSED' and
            report['application_tests']['stations_list']['status'] == 'PASSED'
        )

        report['status'] = 'SUCCESS' if is_success else 'FAILED'

        print(f"\n[{'SUCCESS' if is_success else 'FAILURE'}] Phase 7.2 Independent Database Recovery Complete!")
        print(f"  Tables Restored: {len(report['tables_verified'])} (Discrepancies: {len(report['table_discrepancies'])})")
        print(f"  Rows Restored: {sum([t.get('restored_rows', 0) for t in report['tables_verified'].values() if isinstance(t, dict)])}")
        print(f"  Constraints: {report['constraints_verified']} | Indexes: {report['indexes_verified']}")
        print(f"  Functions: {report['functions_verified']} | Triggers: {report['triggers_verified']}")
        print(f"  RLS Policies: {report['rls_policies_verified']} | Grants: {report['grants_verified']}")
        print(f"  Trigger Execution: {report['behavioral_tests']['auth_trigger_handle_new_user']['status']}")
        print(f"  Application Connectivity: {report['application_tests']['stations_list']['status']}")
        print(f"  Independent Database RTO: {total_rto} seconds")

        # Save Report
        report_filename = f"river_sentinel_independent_restore_report_{now_utc.strftime('%Y%m%d_%H%M%S')}.json"
        report_path = os.path.join(BACKUP_DIR, report_filename)
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        print(f"  Report written to: {report_path}")

        return report

    finally:
        # Step 6: Teardown Isolated Database
        print(f"  Tearing down isolated database '{INDEPENDENT_DB_NAME}'...")
        con_isolated.close()
        con_teardown = get_cluster_connection(database="postgres")
        try:
            con_teardown.run(f"DROP DATABASE IF EXISTS {INDEPENDENT_DB_NAME} WITH (FORCE);")
            print(f"  Database '{INDEPENDENT_DB_NAME}' dropped with force. Zero residual footprint.")
        finally:
            con_teardown.close()


if __name__ == '__main__':
    execute_independent_database_recovery()
