"""
Migration Runner for River Sentinel 2.0
Executes version-controlled SQL migrations against Supabase PostgreSQL.
"""
import sys
import os
import pg8000.native
from dotenv import dotenv_values

def run_migration_file(file_path: str):
    env = dotenv_values('backend/.env')
    host = env.get('SUPABASE_DB_HOST')
    port = int(env.get('SUPABASE_DB_PORT', 5432))
    user = env.get('SUPABASE_DB_USER')
    password = env.get('SUPABASE_DB_PASSWORD')
    database = env.get('SUPABASE_DB_NAME', 'postgres')

    if not all([host, user, password]):
        print("[ERROR] Missing database connection credentials in backend/.env")
        sys.exit(1)

    if not os.path.exists(file_path):
        print(f"[ERROR] Migration file not found: {file_path}")
        sys.exit(1)

    print(f"[INFO] Connecting to Supabase DB at {host}:{port}...")
    con = pg8000.native.Connection(
        user=user,
        host=host,
        port=port,
        password=password,
        database=database,
        ssl_context=True
    )

    with open(file_path, 'r', encoding='utf-8') as f:
        sql = f.read()

    print(f"[INFO] Executing migration: {os.path.basename(file_path)} ({len(sql)} bytes)...")
    try:
        con.run(sql)
        print(f"[SUCCESS] Migration {os.path.basename(file_path)} applied successfully!")
    except Exception as e:
        print(f"[FAILED] Error applying migration: {e}")
        con.close()
        sys.exit(1)

    con.close()

if __name__ == '__main__':
    migration_file = sys.argv[1] if len(sys.argv) > 1 else 'supabase/migrations/20261119000001_phase2_relational_schema_and_security.sql'
    run_migration_file(migration_file)
