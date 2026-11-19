"""
River Sentinel 2.0 - Serial Bridge Service
Reads telemetry from USB serial connected ESP32-WROOM-32 microcontrollers
and forwards authenticated payloads to the Flask ingestion endpoint.
"""

import serial
import serial.tools.list_ports
import time
import requests
import json
import os
import re
import uuid
import argparse
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:5000').rstrip('/')
SIMULATOR_TOKEN = os.getenv('SIMULATOR_API_TOKEN', 'rs_sim_dev_sec_7a8f9c12')


def find_arduino_port():
    """Auto-detect likely ESP32 / Arduino COM port."""
    ports = list(serial.tools.list_ports.comports())
    print("\n🔍 Scanning for COM ports...")
    if not ports:
        print("❌ No COM ports found!")
        return None

    for i, p in enumerate(ports):
        print(f"  [{i}] {p.device} - {p.description}")

    # Heuristic for USB Serial adapters common in ESP32 (CP2102, CH340, FTDI)
    for p in ports:
        desc = p.description.lower()
        if any(chip in desc for chip in ("cp210", "ch340", "ftdi", "usb serial", "esp32", "arduino")):
            print(f"\n✅ Auto-detected likely ESP32 on {p.device}")
            return p.device

    if ports:
        return ports[0].device
    return None


class SerialBridge:
    def __init__(self, port: str, baud: int, device_code: str, device_token: str, simulate_mode: bool = False):
        self.port = port
        self.baud = baud
        self.device_code = device_code
        self.device_token = device_token
        self.simulate_mode = simulate_mode
        self.sequence_number = 1

    def send_production_telemetry(self, sensor_readings: dict, sensor_status: dict = None):
        """Submit authenticated telemetry to /api/v1/telemetry/ingest."""
        url = f"{BACKEND_URL}/api/v1/telemetry/ingest"
        headers = {
            'Content-Type': 'application/json',
            'X-Device-Code': self.device_code,
            'X-Device-Token': self.device_token
        }
        payload = {
            'schema_version': '2.0',
            'device_code': self.device_code,
            'message_id': str(uuid.uuid4()),
            'sequence_number': self.sequence_number,
            'observed_at': datetime.now(timezone.utc).isoformat(),
            'firmware_version': 'v1.0.0-serial-bridge',
            'sensor_readings': sensor_readings,
            'sensor_status': sensor_status or {}
        }
        self.sequence_number += 1

        try:
            res = requests.post(url, headers=headers, json=payload, timeout=5)
            if res.status_code == 201:
                print(f"🚀 [PRODUCTION HTTP 201] Telemetry ingested for {self.device_code} | Seq={self.sequence_number-1} | Readings={sensor_readings}")
                return True
            else:
                print(f"❌ [HTTP {res.status_code}] Ingestion failed: {res.text[:120]}")
                return False
        except requests.exceptions.ConnectionError:
            print(f"⚠️ Backend offline at {BACKEND_URL}. Verify Flask is running on port 5000.")
            return False
        except Exception as e:
            print(f"❌ Telemetry push exception: {e}")
            return False

    def send_simulator_telemetry(self, sensor_readings: dict):
        """Submit development simulation reading to /api/telemetry/simulate."""
        url = f"{BACKEND_URL}/api/telemetry/simulate"
        headers = {
            'Content-Type': 'application/json',
            'X-Simulator-Token': SIMULATOR_TOKEN
        }
        payload = {
            **sensor_readings,
            'provenance': 'simulated',
            'status': 'live'
        }
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=5)
            if res.status_code in (200, 201):
                print(f"🧪 [SIMULATOR HTTP {res.status_code}] Simulated telemetry pushed: {sensor_readings}")
                return True
            else:
                print(f"❌ Simulator push failed ({res.status_code}): {res.text[:120]}")
                return False
        except Exception as e:
            print(f"❌ Simulator push exception: {e}")
            return False

    def parse_line(self, line: str, current_data: dict):
        line = line.strip()
        # Direct JSON stream support
        if line.startswith('{') and line.endswith('}'):
            try:
                parsed = json.loads(line)
                if 'sensor_readings' in parsed:
                    return 'JSON_FULL', parsed
                return 'JSON_READINGS', parsed
            except json.JSONDecodeError:
                pass

        if "------ SENSOR DATA ------" in line:
            return "NEW_BLOCK", None

        match = re.search(r"([^:]+):\s*([\d\.-]+)", line)
        if match:
            label = match.group(1).strip().lower().replace(" ", "_")
            try:
                value = float(match.group(2))
                key_map = {
                    "ph": "ph", "turbidity": "turbidity", "temperature": "temperature",
                    "humidity": "humidity", "ec": "ec", "water_level": "water_level",
                    "do": "do", "dissolved_oxygen": "do", "battery": "battery_pct"
                }
                if label in key_map:
                    current_data[key_map[label]] = value
                    return "UPDATED", None
            except ValueError:
                pass

        return "IGNORED", None

    def start(self):
        print(f"\n📡 Opening Serial Port {self.port} at {self.baud} baud...")
        print(f"   Mode: {'Simulated Ingestion' if self.simulate_mode else 'Physical Device Ingestion'}")
        print(f"   Target: {self.device_code if not self.simulate_mode else 'Telemetry Simulator'}")

        try:
            ser = serial.Serial(self.port, self.baud, timeout=1)
            print("✅ Serial connection established. Listening for telemetry...\n")
            current_data = {}
            last_push = time.time()

            while True:
                if ser.in_waiting > 0:
                    try:
                        raw_line = ser.readline().decode('utf-8', errors='ignore').strip()
                        if not raw_line:
                            continue

                        status, parsed_obj = self.parse_line(raw_line, current_data)

                        if status == 'JSON_FULL':
                            if self.simulate_mode:
                                self.send_simulator_telemetry(parsed_obj.get('sensor_readings', {}))
                            else:
                                self.send_production_telemetry(parsed_obj.get('sensor_readings', {}), parsed_obj.get('sensor_status'))
                            current_data = {}

                        elif status == 'JSON_READINGS':
                            if self.simulate_mode:
                                self.send_simulator_telemetry(parsed_obj)
                            else:
                                self.send_production_telemetry(parsed_obj)
                            current_data = {}

                        elif status == 'NEW_BLOCK' and len(current_data) >= 3:
                            if self.simulate_mode:
                                self.send_simulator_telemetry(current_data)
                            else:
                                self.send_production_telemetry(current_data)
                            current_data = {}

                        # Periodic flush for key-value streams
                        if len(current_data) >= 4 and (time.time() - last_push > 4):
                            if self.simulate_mode:
                                self.send_simulator_telemetry(current_data)
                            else:
                                self.send_production_telemetry(current_data)
                            last_push = time.time()
                            current_data = {}

                    except Exception as e:
                        print(f"⚠️ Error processing serial line: {e}")

                time.sleep(0.01)

        except serial.SerialException as e:
            print(f"\n❌ Serial Exception: {e}")
        except KeyboardInterrupt:
            print("\n🛑 Serial bridge stopped by operator.")
        finally:
            if 'ser' in locals() and ser.is_open:
                ser.close()


def main():
    parser = argparse.ArgumentParser(description="River Sentinel 2.0 Serial Bridge")
    parser.add_argument('--port', help="Serial port (e.g. COM3 or /dev/ttyUSB0)")
    parser.add_argument('--baud', type=int, default=115200, help="Baud rate (default: 115200)")
    parser.add_argument('--device-code', default="DEV-ESP32-ASSI-01", help="Target device code")
    parser.add_argument('--device-token', default="", help="Device pre-shared key token")
    parser.add_argument('--simulate', action='store_true', help="Route to simulator endpoint instead of production ingest")
    args = parser.parse_args()

    port = args.port or find_arduino_port()
    if not port:
        print("❌ No serial port available. Exiting.")
        sys.exit(1)

    bridge = SerialBridge(
        port=port,
        baud=args.baud,
        device_code=args.device_code,
        device_token=args.device_token,
        simulate_mode=args.simulate
    )
    bridge.start()


if __name__ == '__main__':
    main()
