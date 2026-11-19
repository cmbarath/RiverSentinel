"""
Verify schema and RLS policies on Supabase after Phase 2 migration.
"""
import pg8000.native
from dotenv import dotenv_values

env = dotenv_values('backend/.env')
con = pg8000.native.Connection(
    user=env['SUPABASE_DB_USER'],
    host=env['SUPABASE_DB_HOST'],
    port=int(env['SUPABASE_DB_PORT']),
    password=env['SUPABASE_DB_PASSWORD'],
    database=env['SUPABASE_DB_NAME'],
    ssl_context=True
)

print("--- 1. PUBLIC TABLES ---")
tables = con.run("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    ORDER BY table_name;
""")
for t in tables:
    print(f"Table: {t[0]}")

print("\n--- 2. PUBLIC VIEWS ---")
views = con.run("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_type = 'VIEW'
    ORDER BY table_name;
""")
for v in views:
    print(f"View: {v[0]}")

print("\n--- 3. RLS STATUS ---")
rls = con.run("""
    SELECT relname, relrowsecurity 
    FROM pg_class 
    JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace 
    WHERE pg_namespace.nspname = 'public' AND relkind = 'r'
    ORDER BY relname;
""")
for r in rls:
    print(f"Table: {r[0]}, RLS Enabled: {r[1]}")

print("\n--- 4. RLS POLICIES ---")
policies = con.run("""
    SELECT tablename, policyname, permissive, roles, cmd 
    FROM pg_policies 
    WHERE schemaname = 'public'
    ORDER BY tablename, policyname;
""")
for p in policies:
    print(f"[{p[0]}] {p[1]} -> Cmd: {p[4]}, Roles: {p[3]}")

print("\n--- 5. STORAGE BUCKETS ---")
buckets = con.run("SELECT id, name, public, file_size_limit FROM storage.buckets;")
for b in buckets:
    print(f"Bucket: id={b[0]}, name={b[1]}, public={b[2]}, limit={b[3]}")

con.close()
