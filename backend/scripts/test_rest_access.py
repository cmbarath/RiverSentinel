"""
Test PostgREST endpoints with anonymous key to verify RLS privacy protections.
"""
import requests
from dotenv import dotenv_values

env = dotenv_values('backend/.env')
supabase_url = env.get('SUPABASE_URL')
anon_key = env.get('SUPABASE_KEY')

anon_headers = {
    'apikey': anon_key,
    'Authorization': f'Bearer {anon_key}'
}

print(f"Testing PostgREST at {supabase_url} with anon key...")

# 1. Test pollution_reports (Must NOT return raw rows to anonymous)
res_reports = requests.get(f"{supabase_url}/rest/v1/pollution_reports", headers=anon_headers)
print(f"GET /rest/v1/pollution_reports (anon): Status {res_reports.status_code}, Body: {res_reports.text}")

# 2. Test public_sensor_telemetry
res_telemetry = requests.get(f"{supabase_url}/rest/v1/public_sensor_telemetry?limit=2", headers=anon_headers)
print(f"GET /rest/v1/public_sensor_telemetry (anon): Status {res_telemetry.status_code}, Count: {len(res_telemetry.json()) if res_telemetry.status_code == 200 else res_telemetry.text}")

# 3. Test monitoring_stations
res_stations = requests.get(f"{supabase_url}/rest/v1/monitoring_stations", headers=anon_headers)
print(f"GET /rest/v1/monitoring_stations (anon): Status {res_stations.status_code}, Count: {len(res_stations.json()) if res_stations.status_code == 200 else res_stations.text}")
