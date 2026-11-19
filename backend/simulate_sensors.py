"""
River Sentinel 2.0 - Telemetry Simulator
Generates fluctuating sensor telemetry for Ganga river monitoring and posts to
the authenticated backend ingestion endpoint (/api/telemetry/simulate).
"""

import time
import random
import requests
import json
import os
from dotenv import load_dotenv

# Load environment
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:5000').rstrip('/')
SIMULATOR_TOKEN = os.getenv('SIMULATOR_API_TOKEN', 'rs_sim_dev_sec_7a8f9c12')

print("🌊 Starting River Sentinel Sensor Simulation...")
print(f"  -> Ingestion Target: {BACKEND_URL}/api/telemetry/simulate")
print(f"  -> Simulator Auth: {'Configured' if SIMULATOR_TOKEN else 'Missing'}")


def generate_sensor_data():
    """Generate realistic fluctuating sensor measurements for Assi Ghat, Varanasi."""
    timestamp = int(time.time() * 1000)

    data = {
        "ph": round(random.uniform(6.8, 8.4), 2),
        "turbidity": round(random.uniform(8.0, 120.0), 1),
        "temperature": round(random.uniform(22.0, 31.0), 1),
        "humidity": round(random.uniform(45.0, 85.0), 1),
        "ec": round(random.uniform(320, 780), 0),
        "water_level": round(random.uniform(65.5, 71.5), 2),
        "bod": round(random.uniform(4.0, 35.0), 1),
        "cod": round(random.uniform(15.0, 160.0), 1),
        "do": round(random.uniform(4.5, 8.8), 1),
        "timestamp": timestamp,
        "source": "simulated",
        "status": "live",
        "provenance": "simulated",
        "latitude": 25.3176,
        "longitude": 82.9739
    }

    # Cross-parameter physical correlation
    if data['water_level'] > 70.0:
        data['turbidity'] += random.uniform(30, 80)
        data['do'] -= random.uniform(0.5, 1.5)

    return data


def push_to_backend(data):
    """Post reading to the authenticated Flask telemetry ingestion endpoint."""
    url = f"{BACKEND_URL}/api/telemetry/simulate"
    headers = {
        'Content-Type': 'application/json',
        'X-Simulator-Token': SIMULATOR_TOKEN
    }
    try:
        res = requests.post(url, headers=headers, json=data, timeout=5)
        if res.status_code in (200, 201):
            return True, res.status_code
        else:
            print(f"[ERROR] Ingestion failed ({res.status_code}): {res.text[:150]}")
            return False, res.status_code
    except requests.exceptions.ConnectionError:
        print("[ERROR] Connection refused - Is the Flask backend running on port 5000?")
        return False, 0
    except Exception as e:
        print(f"[ERROR] Telemetry push error: {e}")
        return False, 0


def run_simulation_step():
    data = generate_sensor_data()
    success, code = push_to_backend(data)
    status_icon = '✅' if success else '❌'
    print(f"[{status_icon} Backend (HTTP {code})] pH={data['ph']} | WL={data['water_level']}m | Temp={data['temperature']}°C | DO={data['do']}mg/L")
    return success


if __name__ == '__main__':
    try:
        while True:
            run_simulation_step()
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n🛑 Simulation stopped.")
