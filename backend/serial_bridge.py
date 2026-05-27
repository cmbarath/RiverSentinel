
import serial
import serial.tools.list_ports
import time
import requests
import json
import os
import re
import argparse
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

FIREBASE_URL = os.getenv('FIREBASE_DATABASE_URL')
FIREBASE_SECRET = os.getenv('FIREBASE_SECRET')

if not FIREBASE_URL or not FIREBASE_SECRET:
    print("❌ Error: Missing Firebase configuration in .env")
    input("Press Enter to exit...")
    exit(1)

def find_arduino_port():
    """Auto-detect likely Arduino port"""
    ports = list(serial.tools.list_ports.comports())
    
    print("\n🔍 Scanning for COM ports...")
    
    if not ports:
        print("❌ No COM ports found!")
        return None
        
    for i, p in enumerate(ports):
        print(f"  [{i}] {p.device} - {p.description}")
        
    # Heuristic: Pick the one with 'Arduino' or 'USB Serial' in description
    likely_port = None
    for p in ports:
        if "Arduino" in p.description or "USB Serial" in p.description or "CH340" in p.description or "CP210" in p.description:
            likely_port = p.device
            break
            
    if likely_port:
        print(f"\n✅ Auto-detected likely Arduino on {likely_port}")
        # Non-interactive mode preference
        return likely_port
            
    # If no likely port found, return the last one as a fallback or None
    if ports:
        return ports[0].device
        
    return None

def parse_line(line, current_data):
    """Parse a line from Serial Monitor and update current data dict"""
    line = line.strip()
    
    # Handle the start of a new data block
    if "------ SENSOR DATA ------" in line:
        return "NEW_BLOCK"
        
    # Regex to match "Label: Value" format
    match = re.search(r"([^:]+):\s*([\d\.-]+)", line)
    if match:
        label = match.group(1).strip().lower().replace(" ", "_")
        value = float(match.group(2))
        
        # Map labels to Firebase keys
        key_map = {
            "ph": "ph",
            "turbidity": "turbidity",
            "temperature": "temperature",
            "humidity": "humidity",
            "ec": "ec",
            "water_level": "water_level",
            "bod": "bod",
            "cod": "cod",
            "do": "do",
            "dissolved_oxygen": "do"
        }
        
        if label in key_map:
            current_data[key_map[label]] = value
            return "UPDATED"
            
    return "IGNORED"

def push_to_firebase(data):
    """Push data to Firebase using REST API"""
    try:
        # Add timestamp
        data['timestamp'] = int(time.time() * 1000)
        data['status'] = 'live'
        
        # Use timestamp as key
        key = str(data['timestamp'])
        update_url = f"{FIREBASE_URL}/sensor_data/{key}.json?auth={FIREBASE_SECRET}"
        
        response = requests.put(update_url, json=data)
        
        if response.status_code == 200:
            print(f"🚀 Sent to Firebase: pH={data.get('ph', '?')} | WL={data.get('water_level', '?')}m | Temp={data.get('temperature', '?')}°C")
            return True
        else:
            print(f"❌ Failed to push: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='River Sentinel Serial Bridge')
    parser.add_argument('--port', help='Serial port (e.g. COM3)')
    parser.add_argument('--baud', type=int, default=115200, help='Baud rate')
    args = parser.parse_args()

    print("🌊 River Sentinel - Serial Bridge")
    print("---------------------------------")
    
    port = args.port
    if not port:
        port = find_arduino_port()
    
    if not port:
        print("❌ No port selected/found. Exiting.")
        return

    baud_rate = args.baud
    
    try:
        ser = serial.Serial(port, baud_rate, timeout=1)
        print(f"\n✅ Connected to {port} at {baud_rate} baud")
        print("Waiting for data... (Press Ctrl+C to stop)")
        
        current_data = {}
        last_push_time = 0
        
        while True:
            if ser.in_waiting > 0:
                try:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if not line: continue
                    
                    # print(f"Raw: {line}") # Debug
                    
                    result = parse_line(line, current_data)
                    
                    if result == "NEW_BLOCK":
                        # If we have data from the previous block, push it now
                        if len(current_data) > 3: 
                            push_to_firebase(current_data)
                            current_data = {} # Reset for next block
                            
                    # Timeout push
                    if len(current_data) > 5 and (time.time() - last_push_time > 5):
                         push_to_firebase(current_data)
                         last_push_time = time.time()
                         current_data = {}
                         
                except Exception as e:
                    print(f"⚠️ Error reading line: {e}")
                    
            time.sleep(0.01)
            
    except serial.SerialException as e:
        print(f"\n❌ Serial Error: {e}")
        print("Tip: Make sure the Arduino Serial Monitor is CLOSED.")
    except KeyboardInterrupt:
        print("\n🛑 Bridge stopped.")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()

if __name__ == "__main__":
    main()
