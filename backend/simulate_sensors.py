import time
import random
import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

FIREBASE_URL = os.getenv('FIREBASE_DATABASE_URL')
FIREBASE_SECRET = os.getenv('FIREBASE_SECRET')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')

if not FIREBASE_URL and not SUPABASE_URL:
    print("[ERROR] Neither FIREBASE_DATABASE_URL nor SUPABASE_URL found in .env")
    exit(1)

print(f"🌊 Starting River Sentinel Sensor Simulation...")
if SUPABASE_URL:
    print(f"  -> Supabase target: {SUPABASE_URL}")
if FIREBASE_URL:
    print(f"  -> Firebase target: {FIREBASE_URL}")

def generate_sensor_data():
    """Generate realistic fluctuating sensor data"""
    timestamp = int(time.time() * 1000)
    
    data = {
        "ph": round(random.uniform(6.5, 8.5), 2),
        "turbidity": round(random.uniform(5.0, 150.0), 1),
        "temperature": round(random.uniform(22.0, 32.0), 1),
        "humidity": round(random.uniform(40.0, 85.0), 1),
        "ec": round(random.uniform(300, 800), 0),
        "water_level": round(random.uniform(65.0, 72.0), 2),
        "bod": round(random.uniform(2.0, 40.0), 1),
        "cod": round(random.uniform(10.0, 180.0), 1),
        "do": round(random.uniform(4.0, 9.0), 1),
        "timestamp": timestamp,
        "source": "simulated",
        "status": "live",
        "provenance": "simulated",
        "latitude": 25.3176,
        "longitude": 82.9739
    }
    
    if data['water_level'] > 70:
        data['turbidity'] += random.uniform(50, 100)
    
    return data

def push_to_supabase(data):
    """Push reading to Supabase sensor_readings table"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False
    try:
        url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/sensor_readings"
        headers = {
            'apikey': SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}',
            'Content-Type': 'application/json'
        }
        payload = {
            "ph": data.get("ph"),
            "turbidity": data.get("turbidity"),
            "temperature": data.get("temperature"),
            "humidity": data.get("humidity"),
            "ec": data.get("ec"),
            "water_level": data.get("water_level"),
            "bod": data.get("bod"),
            "cod": data.get("cod"),
            "do": data.get("do"),
            "provenance": data.get("provenance", "simulated"),
            "status": data.get("status", "live"),
            "latitude": data.get("latitude", 25.3176),
            "longitude": data.get("longitude", 82.9739)
        }
        res = requests.post(url, headers=headers, json=payload, timeout=5)
        return res.status_code in (200, 201)
    except Exception as e:
        print(f"[ERROR] Supabase push failed: {e}")
        return False

def push_to_firebase(data):
    """Push data to Firebase using REST API"""
    if not FIREBASE_URL:
        return False
    try:
        url = FIREBASE_URL.rstrip('/')
        auth_query = f"?auth={FIREBASE_SECRET}" if FIREBASE_SECRET else ""
        key = str(data['timestamp'])
        update_url = f"{url}/sensor_data/{key}.json{auth_query}"
        
        response = requests.put(update_url, json=data, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"[ERROR] Firebase push failed: {e}")
        return False

def run_simulation_step():
    data = generate_sensor_data()
    sb_ok = push_to_supabase(data)
    fb_ok = push_to_firebase(data)
    status_parts = []
    if SUPABASE_URL:
        status_parts.append(f"Supabase: {'✅' if sb_ok else '❌'}")
    if FIREBASE_URL:
        status_parts.append(f"Firebase: {'✅' if fb_ok else '❌'}")
    status_str = " | ".join(status_parts)
    print(f"[{status_str}] pH={data['ph']} | WL={data['water_level']}m | Temp={data['temperature']}°C | DO={data['do']}mg/L")

if __name__ == '__main__':
    try:
        while True:
            run_simulation_step()
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n🛑 Simulation stopped.")
