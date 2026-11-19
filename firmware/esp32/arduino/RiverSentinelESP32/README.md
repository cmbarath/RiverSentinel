# River Sentinel 2.0 — ESP32 Arduino IDE Firmware Package

This directory contains the standalone Arduino IDE sketch for River Sentinel 2.0 IoT telemetry nodes, designed for the **ESP32-WROOM-32** microcontroller.

> **IMPORTANT OPERATIONAL NOTICE — NO-SENSOR SAFETY GUARDRAIL:**  
> Physical field installation of river sensors is intentionally **deferred** to Phase 3B. River Sentinel 2.0 is currently in a production-hosted software release candidate state. This sketch operates in **Bench Diagnostic Mode** by default (`SENSORS_PHYSICALLY_ATTACHED = false`).
> 
> **CRITICAL BEHAVIOR:** In Bench Diagnostic Mode, telemetry transmission to `/api/v1/telemetry/ingest` is **STRICTLY SUPPRESSED**. Benchmark diagnostic frames are logged solely to the local Serial Monitor and are NEVER stored or transmitted as genuine physical river sensor observations. Never fabricate live sensor telemetry.


---

## 1. Hardware Requirements

- **Microcontroller:** ESP32-WROOM-32 (38-pin DevKit, NodeMCU-32S, or compatible)
- **Power Supply:** 5V USB via Micro-USB / Type-C or regulated 3.7V LiPo
- **Future Physical Sensor Bus (Deferred):**
  - Analog pH Probe (ADC1_CH6 / GPIO 34)
  - Analog Turbidity Sensor (ADC1_CH7 / GPIO 35)
  - DS18B20 Digital Temperature Sensor (GPIO 4 with 4.7kΩ pullup)
  - Ultrasonic Water Level Sensor HC-SR04 / JSN-SR04T (Trig: GPIO 5, Echo: GPIO 18)
  - Electrical Conductivity Probe (ADC1_CH4 / GPIO 32)
  - Dissolved Oxygen Probe (ADC1_CH5 / GPIO 33)
  - Battery Voltage Divider (ADC1_CH0 / GPIO 36)

---

## 2. Arduino IDE Setup Instructions

### Step 1: Install Arduino IDE
Download and install [Arduino IDE 2.3+](https://www.arduino.cc/en/software).

### Step 2: Install ESP32 Board Core
1. Open Arduino IDE and navigate to **File → Preferences**.
2. In **Additional boards manager URLs**, add:
   ```text
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
3. Open **Tools → Board → Boards Manager**, search for `esp32` by Espressif Systems, and click **Install** (version 2.0.14 or later).

### Step 3: Configure Target Board
From the **Tools** menu, select:
- **Board:** `ESP32 Dev Module`
- **CPU Frequency:** `240MHz (WiFi/BT)`
- **Flash Frequency:** `80MHz`
- **Flash Mode:** `QIO`
- **Flash Size:** `4MB (32Mb)`
- **Partition Scheme:** `Default 4MB with spiffs (1.2MB APP/1.5MB SPIFFS)`
- **Upload Speed:** `921600` (or `115200` if flashing fails)
- **Port:** Select the COM port corresponding to your CP2102/CH340 USB-UART bridge.

---

## 3. Configuration

1. In this directory, copy `config.example.h` to `config.h`:
   ```bash
   cp config.example.h config.h
   ```
2. Open `config.h` in Arduino IDE or any text editor.
3. Configure your local Wi-Fi credentials:
   ```c
   #define WIFI_SSID     "Your-WiFi-SSID"
   #define WIFI_PASSWORD "Your-WiFi-Password"
   ```
4. Set your River Sentinel backend host:
   - For Render production:
     ```c
     #define BACKEND_HOST    "river-sentinel-backend.onrender.com"
     #define BACKEND_PORT    443
     #define USE_TLS         true
     #define INGEST_ENDPOINT "/api/v1/telemetry/ingest"
     ```
   - For local development:
     ```c
     #define BACKEND_HOST    "192.168.1.100"  // Your PC's LAN IP
     #define BACKEND_PORT    5000
     #define USE_TLS         false
     #define INGEST_ENDPOINT "/api/v1/telemetry/ingest"
     ```
5. Set your device identification:
   ```c
   #define DEVICE_CODE  "DEV-ESP32-ASSI-01"
   #define DEVICE_TOKEN "rs_dev_assi01_replace_with_actual_token"
   ```

---

## 4. Flashing and Verification

1. Connect the ESP32 to your computer via USB.
2. In Arduino IDE, click **Verify** (checkmark icon) to compile.
3. Click **Upload** (arrow icon) to flash the firmware.
4. Open the **Serial Monitor** at **115200 baud**.
5. You should observe (in Bench Diagnostic Mode with `SENSORS_PHYSICALLY_ATTACHED = false`):
   ```text
   🌊 River Sentinel 2.0 - ESP32 Telemetry Node (Arduino)
   ========================================================
   [Auth] Identity Verification:
     - Station Device Code: DEV-ESP32-ASSI-01
     - Device Auth Token:  rs_d...[REDACTED]...oken
   [System] Firmware Version: 2.1.0-arduino
   [System] Hardware Mode:   BENCH DIAGNOSTIC SIMULATION
   [Wi-Fi] Connecting to SSID '...'... ✓ Connected! IP: 192.168.1.150
   [NTP] Synchronizing UTC time... ✓ UTC synchronized: 2026-11-19T22:50:00Z
   [Sample] Telemetry Frame seq #1 | 2026-11-19T22:50:00Z
     - pH: 7.80 (bench_simulation) | Turbidity: 18.50 NTU (bench_simulation)
     - Temp: 24.20 C (bench_simulation) | Water Level: 67.20 m (bench_simulation)
     - EC: 380.0 uS/cm | DO: 7.40 mg/L | Battery: 98.0%
   [SAFETY GUARDRAIL] SENSORS_PHYSICALLY_ATTACHED == false
   [SAFETY GUARDRAIL] Telemetry transmission to /api/v1/telemetry/ingest suppressed.
   [SAFETY GUARDRAIL] Benchmark diagnostics are logged to Serial only. Database integrity protected.
   ```

---

## 5. Security & Ingestion Contract Reference

- **Endpoint:** `POST /api/v1/telemetry/ingest`
- **Authentication Headers:**
  - `X-Device-Code`: Registered hardware identifier (e.g. `DEV-ESP32-ASSI-01`).
  - `X-Device-Token`: Pre-shared credential verified by constant-time SHA-256 on the backend.
- **Idempotency:** Each frame generates an RFC 4122 UUID v4 `message_id` using the ESP32 hardware TRNG. Duplicates sent during network retries are safely deduplicated by the backend database.
- **Offline Queue Volatility & Fault Tolerance:**
  - If Wi-Fi or backend connectivity drops while physical sensors are active (`SENSORS_PHYSICALLY_ATTACHED = true`), readings are buffered in a bounded circular SRAM queue (up to 50 frames) and drained automatically once connectivity is restored.
  - **RAM vs Flash Architecture:** The ring buffer is allocated in volatile ESP32 SRAM (`QueuedReading offlineBuffer[50]`). Buffer contents **DO NOT** survive an ESP32 power loss, brownout, or reboot. Persistent Flash/NVS/SD card storage is intentionally deferred to Phase 3B.
- **Toolchain / Compilation:**
  - Tested for compilation via Arduino IDE 2.3+ with `esp32 by Espressif Systems` core.
  - If using CLI, requires `arduino-cli compile --fqbn esp32:esp32:esp32 RiverSentinelESP32.ino`. If `arduino-cli` is not installed on the host OS, Arduino IDE 2.x is the recommended official compiler interface.
