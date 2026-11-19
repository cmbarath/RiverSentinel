# River Sentinel 2.0 — Phase 3A.1 Firmware Verification
**ESP32-WROOM-32 Compilation, Strict HTTPS Validation & Sensor Quality Architecture**

---

## 1. Toolchain & Compilation Environment

Firmware compilation verification was performed using PlatformIO Core against the official Espressif 32 development platform:

- **Build Orchestrator:** PlatformIO Core 6.2.0
- **Platform:** Espressif 32 (v8.0.0)
- **Framework:** Arduino ESP32 Core (v3.3.12 / framework-arduinoespressif32)
- **Toolchain:** `xtensa-esp-elf` GCC 14.2.0
- **Target Microcontroller:** ESP32-WROOM-32 (`esp32dev`)
- **Flash Configuration:** 4MB Flash, QIO mode, 80MHz
- **CPU Clock:** 240MHz dual-core Xtensa LX6

### Compilation Outcome
```
CONFIGURATION: https://docs.platformio.org/page/boards/espressif32/esp32dev.html
PLATFORM: Espressif 32 (8.0.0) > Espressif ESP32 Dev Module
HARDWARE: ESP32 240MHz, 320KB RAM, 4MB Flash
RAM:   [==        ]  15.1% (used 49,544 bytes from 327,680 bytes)
Flash: [========  ]  79.6% (used 1,043,903 bytes from 1,310,720 bytes)
Building .pio\build\esp32dev\firmware.bin
esptool v5.4.0
Creating ESP32 image...
Merged 3 ELF sections.
Successfully created ESP32 image.
======================== [SUCCESS] Took 284.53 seconds ========================
```

---

## 2. HTTPS Certificate Validation & Trust Architecture

### 2.1 Elimination of Insecure Bypasses
The firmware contains **zero certificate validation bypasses**. `setInsecure()` is strictly forbidden and nowhere present in the codebase.

### 2.2 Strict Certificate Trust Strategy
In `arduino/river_sentinel_esp32/telemetry_client.h`:
1. **Root CA Enrollment:** The client loads the official standard root certificate (`ISRG Root X1` for Let's Encrypt / modern cloud endpoints) via `secureClient.setCACert(ROOT_CA_CERT)` declared in `config.h`.
2. **NTP Clock Synchronization Preflight:**
   X.509 certificate validation requires verifying `notBefore` and `notAfter` validity periods. If an ESP32 has not yet synchronized its internal Real-Time Clock (RTC) via SNTP, its clock sits at epoch (1970), which would cause either false certificate rejection or insecure clock bypasses.
   
   The telemetry client enforces strict clock preflight:
   ```cpp
   time_t now = time(nullptr);
   if (now < 1700000000) { // Timestamp prior to Nov 2023 indicates uninitialized clock
       Serial.println(F("[TLS] ❌ Error: NTP time not synchronized. Refusing TLS connection without valid clock to prevent expired/invalid certificate acceptance."));
       return -2; // Signals caller to queue message until clock sync completes
   }
   ```
3. **Diagnostic Sanitization:** In the event of a TLS handshake failure, the client logs only sanitized numerical status codes without exposing API tokens, request headers, or confidential configuration parameters.

---

## 3. Sensor Quality & Calibration Demarcation

Broad physical bounds checks (e.g. pH 0–14) are basic plausibility filters, not proof of measurement validity. In-situ river sensors drift significantly and require explicit calibration states.

### 3.1 Four-Dimensional Sensor Evaluation

Every reading evaluated by `POST /api/v1/telemetry/ingest` is classified across four distinct dimensions:

```
+-------------------------------------------------------------------------+
|                         INGESTION EVALUATION                            |
+---------------------+-------------------+-------------------+-----------+
| 1. Range Status     | 2. Connection     | 3. Calibration    | 4. Quality|
| - in_range          | - connected       | - calibrated      | - valid   |
| - out_of_range      | - disconnected    | - uncalibrated    | - provis. |
|                     | - missing         | - factory_default | - degraded|
|                     | - not_configured  |                   | - out_of_r|
+---------------------+-------------------+-------------------+-----------+
```

### 3.2 Degradation & Provisional Rules
1. **Uncalibrated Sensor Rule:** If a sensor value falls within physical bounds (e.g. pH 7.25) but its calibration status is `uncalibrated` or `factory_default`, the reading **CANNOT be tagged as `valid`**. The backend records the value with sensor quality `'uncalibrated'` and downgrades overall reading quality to `'provisional'`.
2. **Disconnected Probe Rule:** If an attached probe fails to report or sends `disconnected`, the reading is recorded as `NULL` (never 0.0), and overall quality becomes `'degraded'`.
3. **Unconfigured Probe Rule:** If a probe is marked `not_configured` (e.g. optional EC or dissolved oxygen probe not physically wired to the node), its value is recorded as `NULL` and does **not** degrade overall river reading quality.
4. **BOD/COD Scientific Integrity Rule:** In-situ electrochemical probes cannot directly measure Biochemical or Chemical Oxygen Demand. All BOD/COD fields submitted from edge devices are stored as `NULL` in `sensor_readings` to prevent synthetic or unverified estimates from being treated as lab-certified measurements.

---

## 4. Hardware Pinout & Peripheral Safety Rules

For deployment to physical ESP32 boards (Phase 3B):
- **Analog Sensor Routing:** Must use **ADC1 channels only** (GPIO 32, 33, 34, 35, 36, 39). ADC2 channels are multiplexed with the Wi-Fi baseband and cannot sample while Wi-Fi is transmitting.
- **Input Voltage Dividers:** ESP32 ADC inputs have an absolute maximum rating of 3.3V (operational linear range 0.1V – 3.1V with 11dB attenuation). 5V sensors (such as DF-Robot analog turbidity) must use precision resistive voltage dividers ($10\text{k}\Omega / 20\text{k}\Omega$) or op-amp buffers.
- **Non-Invention Rule:** No physical measurement is fabricated or claimed as online until physical sensor probes are installed, calibrated with standard buffer solutions (pH 4.01/7.00/10.01), and verified over hardware Wi-Fi.
