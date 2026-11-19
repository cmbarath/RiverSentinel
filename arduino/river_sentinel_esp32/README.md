# River Sentinel 2.0 — ESP32 Firmware Guide

## 1. Overview & Architecture

The River Sentinel 2.0 ESP32-WROOM-32 firmware provides an edge computing and telemetry framework designed for long-term deployment along the Ganga River in Varanasi, India.

It features:
- **Dedicated Device Authentication:** Pre-shared keys authenticated over HTTPS (`X-Device-Code`, `X-Device-Token`) verified on the server via constant-time SHA-256 checks.
- **Payload Schema 2.0:** Versioned JSON with sequence numbers, UUID message IDs, and explicit sensor status indicators.
- **SNTP UTC Synchronization:** Automatic synchronization against global NTP pools with timestamp quality fallback.
- **Bounded Offline Buffering:** In-memory queue to retain telemetry during temporary cellular/Wi-Fi outages without flash-write wear.
- **Hardware Abstraction:** Pluggable `ISensor` interfaces preventing fabricated readings from absent probes.

---

## 2. Directory Structure

```
arduino/river_sentinel_esp32/
├── river_sentinel_esp32.ino    # Main firmware entrypoint & state machine
├── config.example.h            # Configuration template (Git-tracked)
├── config.h                    # Local device credentials (Ignored by Git)
├── wifi_manager.h              # Wi-Fi connection & exponential backoff
├── time_sync.h                 # SNTP time synchronization & ISO 8601 formatting
├── device_auth.h               # Token management & redacted identity printing
├── device_status.h             # Heap, uptime, Wi-Fi RSSI, & battery ADC monitoring
├── offline_queue.h             # Bounded circular buffer for offline resilience
├── sensor_manager.h            # Abstract sensor bundle orchestrator
├── telemetry_client.h          # HTTPS REST client for Schema 2.0 ingestion
├── sensor_interfaces/
│   └── ISensor.h               # Abstract sensor base interface
└── README.md                   # Firmware documentation & setup instructions
```

---

## 3. Configuration & Provisioning Setup

1. Copy `config.example.h` to `config.h`:
   ```bash
   cp arduino/river_sentinel_esp32/config.example.h arduino/river_sentinel_esp32/config.h
   ```
2. Run the device provisioning script on the backend to register the device and generate high-entropy tokens:
   ```powershell
   backend\venv\Scripts\python backend/scripts/provision_device.py --provision DEV-ESP32-ASSI-01 "ESP32 Sensor Unit Assi-01" STN-VAR-ASSI-01
   ```
3. Copy the output `DEVICE_TOKEN` into `config.h`.
4. Enter local Wi-Fi SSID and Password.

---

## 4. Hardware Safety & Pin Assignment Notes

> [!WARNING]
> **ESP32 ADC Voltage Limitation:** ESP32 analog pins can strictly tolerate up to 3.3V maximum. Never connect 5V analog sensor signals directly to an ESP32 GPIO. Use precision resistor dividers (e.g. 10kΩ / 20kΩ) or an I2C ADC (ADS1115).

> [!IMPORTANT]
> **Wi-Fi ADC Conflict:** ESP32 `ADC2` channels (GPIO 0, 2, 4, 12-15, 25-27) cannot be used while the Wi-Fi transceiver is transmitting. All analog sensors must be wired to `ADC1` pins (GPIO 32, 33, 34, 35, 36, 39).
