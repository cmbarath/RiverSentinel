
import time
import random
import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

FIREBASE_URL = os.getenv('FIREBASE_DATABASE_URL')
FIREBASE_SECRET = os.getenv('FIREBASE_SECRET')

if not FIREBASE_URL or not FIREBASE_SECRET:
    print("❌ Error: Missing Firebase configuration in .env")
    print("Please ensure FIREBASE_DATABASE_URL and FIREBASE_SECRET are set.")
    exit(1)

print(f"🌊 Starting River Sentinel Sensor Simulation...")
print(f"target: {FIREBASE_URL}")

def generate_sensor_data():
    """Generate realistic fluctuating sensor data"""
    timestamp = int(time.time() * 1000)
    
    # Base values with random fluctuation
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
        "status": "live"  # This flag tells frontend it's live data
    }
    
    # Add some correlation (e.g. high turbidity often with high water level)
    if data['water_level'] > 70:
        data['turbidity'] += random.uniform(50, 100)
    
    return data

def push_to_firebase(data):
    """Push data to Firebase using REST API"""
    try:
        url = f"{FIREBASE_URL}/sensor_data.json?auth={FIREBASE_SECRET}"
        
        # We push to a new node with timestamp as key (or let Firebase generate one)
        # For simplicity and to not fill up DB, we can also just update a 'latest' node
        # But 'sensor_data' in app.py seems to read the latest from a list/dict
        
        # Strategy: Push to a list so history is preserved (optional) or just set 'current'
        # The app.py uses `latest_key = max(sensor_snapshot.keys())`, so it expects a dictionary of readings
        
        # We'll use the timestamp as the key
        key = str(data['timestamp'])
        update_url = f"{FIREBASE_URL}/sensor_data/{key}.json?auth={FIREBASE_SECRET}"
        
        response = requests.put(update_url, json=data)
        
        if response.status_code == 200:
            print(f"✅ Data pushed: pH={data['ph']} | WL={data['water_level']}m | Temp={data['temperature']}°C")
            return True
        else:
            print(f"❌ Failed to push: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False

# Main loop
try:
    while True:
        sensor_data = generate_sensor_data()
        push_to_firebase(sensor_data)
        
        # Wait for 5 seconds
        time.sleep(5)
        
except KeyboardInterrupt:
    print("\n🛑 Simulation stopped.")
