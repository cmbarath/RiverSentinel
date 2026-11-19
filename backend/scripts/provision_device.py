"""
Device Provisioning & Key Management CLI for River Sentinel 2.0
Allows administrators to provision new ESP32 devices, rotate credentials,
and revoke compromised hardware tokens.
"""

import sys
import os
import argparse
import pg8000.native
from dotenv import dotenv_values

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from services.device_auth_service import generate_device_token, hash_device_token

def get_db():
    env = dotenv_values(os.path.join(backend_dir, '.env'))
    return pg8000.native.Connection(
        user=env['SUPABASE_DB_USER'],
        host=env['SUPABASE_DB_HOST'],
        port=int(env['SUPABASE_DB_PORT']),
        password=env['SUPABASE_DB_PASSWORD'],
        database=env['SUPABASE_DB_NAME'],
        ssl_context=True
    )

def list_devices():
    con = get_db()
    rows = con.run("""
        SELECT d.device_code, d.device_name, d.status, s.station_code, s.station_name, d.firmware_version, d.last_seen_at
        FROM public.devices d
        LEFT JOIN public.monitoring_stations s ON d.station_id = s.id
        ORDER BY d.device_code;
    """)
    print("\n--- REGISTERED RIVER SENTINEL DEVICES ---")
    for r in rows:
        print(f"[{r[0]}] {r[1]} | Status: {r[2]} | Station: {r[3]} ({r[4]}) | FW: {r[5]} | LastSeen: {r[6]}")
    con.close()

def provision_device(device_code: str, device_name: str, station_code: str):
    con = get_db()
    # Find station
    stations = con.run("SELECT id, station_name FROM public.monitoring_stations WHERE station_code = :code;", code=station_code)
    if not stations:
        print(f"[ERROR] Station {station_code} not found.")
        con.close()
        return

    station_id = stations[0][0]
    token = generate_device_token()
    token_hash = hash_device_token(token)

    con.run("""
        INSERT INTO public.devices (
            device_code, device_name, station_id, device_type,
            firmware_version, credential_hash, status
        ) VALUES (
            :dcode, :dname, :sid::uuid, 'ESP32-WROOM-32',
            'v1.0.0-framework', :hash, 'provisioned'
        )
        ON CONFLICT (device_code) DO UPDATE SET
            station_id = EXCLUDED.station_id,
            credential_hash = EXCLUDED.credential_hash,
            status = 'provisioned',
            updated_at = now();
    """, dcode=device_code, dname=device_name, sid=station_id, hash=token_hash)

    print("\n" + "=" * 65)
    print("DEVICE PROVISIONED SUCCESSFULLY")
    print("=" * 65)
    print(f"Device Code:     {device_code}")
    print(f"Device Name:     {device_name}")
    print(f"Station Code:    {station_code} ({stations[0][1]})")
    print(f"Lifecycle State: provisioned")
    print(f"Credential Hash: {token_hash[:20]}...")
    print("-" * 65)
    print("⚠️  ONE-TIME PRE-SHARED KEY (STORE IN ESP32 config.h NOW):")
    print(f"   DEVICE_TOKEN = {token}")
    print("-" * 65)
    print("This secret will NEVER be displayed again or stored in plaintext.")
    print("=" * 65 + "\n")
    con.close()

def rotate_device_token(device_code: str):
    con = get_db()
    dev = con.run("SELECT id, device_name, status FROM public.devices WHERE device_code = :code;", code=device_code)
    if not dev:
        print(f"[ERROR] Device {device_code} not found.")
        con.close()
        return

    token = generate_device_token()
    token_hash = hash_device_token(token)

    con.run("""
        UPDATE public.devices
        SET credential_hash = :hash, updated_at = now()
        WHERE device_code = :code;
    """, hash=token_hash, code=device_code)

    print("\n" + "=" * 65)
    print(f"CREDENTIAL ROTATED FOR {device_code}")
    print("=" * 65)
    print("⚠️  NEW ONE-TIME PRE-SHARED KEY (UPDATE IN ESP32 config.h):")
    print(f"   DEVICE_TOKEN = {token}")
    print("=" * 65 + "\n")
    con.close()

def revoke_device(device_code: str):
    con = get_db()
    con.run("UPDATE public.devices SET status = 'revoked', updated_at = now() WHERE device_code = :code;", code=device_code)
    print(f"[REVOKED] Device {device_code} has been marked REVOKED. Telemetry will be rejected.")
    con.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="River Sentinel 2.0 Device Provisioning")
    parser.add_argument('--list', action='store_true', help="List all registered devices")
    parser.add_argument('--provision', nargs=3, metavar=('CODE', 'NAME', 'STATION_CODE'), help="Provision new device")
    parser.add_argument('--rotate', metavar='CODE', help="Rotate device credential")
    parser.add_argument('--revoke', metavar='CODE', help="Revoke device access")

    args = parser.parse_args()

    if args.list:
        list_devices()
    elif args.provision:
        provision_device(args.provision[0], args.provision[1], args.provision[2])
    elif args.rotate:
        rotate_device_token(args.rotate)
    elif args.revoke:
        revoke_device(args.revoke)
    else:
        list_devices()
