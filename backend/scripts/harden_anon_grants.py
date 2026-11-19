"""
Harden anon grants on sensitive tables.
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

statements = [
    "REVOKE ALL ON public.profiles FROM anon;",
    "REVOKE ALL ON public.devices FROM anon;",
    "REVOKE ALL ON public.station_assignments FROM anon;",
    "NOTIFY pgrst, 'reload schema';"
]

for s in statements:
    con.run(s)

con.close()
print("Successfully revoked all anon grants on profiles, devices, station_assignments!")
