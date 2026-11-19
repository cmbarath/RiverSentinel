# River Sentinel 2.0 — Hardware Architecture & Sensor Integration Specification

This document details the hardware design, microcontroller pinout, sensor bus architecture, power subsystem, and calibration procedures for River Sentinel 2.0 IoT nodes.

> **DEPLOYMENT STATUS NOTICE:**  
> Physical field mounting on the ghats of Varanasi is **DEFERRED** for the software release candidate milestone. River Sentinel 2.0 operates with complete hardware abstraction: firmware packages are validated in **Bench Diagnostic Mode** (`SENSORS_PHYSICALLY_ATTACHED = false`), sending deterministic telemetry with explicit status tagging to avoid false river warnings.

---

## 1. System Block Diagram

```
+---------------------------------------------------------------------------------+
|                               RIVER SENTINEL IOT NODE                           |
|                                                                                 |
|  +--------------------+         +--------------------------------------------+  |
|  | Solar Panel (10W)  |         |             ESP32-WROOM-32                 |  |
|  +---------+----------+         |   (240MHz Dual-Core, 520KB SRAM, 4MB Flash)|  |
|            |                    |                                            |  |
|            v                    |                                            |  |
|  +--------------------+         |  [ADC1_CH6 / GPIO 34] <--- pH Probe Board  |  |
|  | MPPT / TP4056 BMS  |         |  [ADC1_CH7 / GPIO 35] <--- Turbidity Sensor|  |
|  +---------+----------+         |  [GPIO 4 OneWire]     <--- DS18B20 Temp    |  |
|            |                    |  [GPIO 5 (Trig)]      ---> JSN-SR04T Level |  |
|            v                    |  [GPIO 18 (Echo)]     <--- JSN-SR04T Echo  |  |
|  +--------------------+         |  [ADC1_CH4 / GPIO 32] <--- EC Probe Board  |  |
|  | 2x 18650 Li-Ion    |         |  [ADC1_CH5 / GPIO 33] <--- DO Probe Board  |  |
|  | (3.7V, 5200 mAh)   |         |  [ADC1_CH0 / GPIO 36] <--- Battery Divider |  |
|  +---------+----------+         |  [GPIO 2]             ---> Status LED      |  |
|            |                    +---------------------+----------------------+  |
|            v                                          |                         |
|  +--------------------+                               v                         |
|  | Ultra-Low Dropout  |                       Wi-Fi 802.11 b/g/n                |
|  | 3.3V Regulator     |-----------------> VCC (3.3V Rail)                       |
|  +--------------------+                                                         |
+---------------------------------------------------------------------------------+
```

---

## 2. Pinout & Sensor Interfacing

The ESP32 ADC2 channels are multiplexed with the Wi-Fi subsystem. Therefore, **all analog sensors must exclusively utilize ADC1 channels** (GPIO 32–39) to prevent ADC reading corruption during Wi-Fi transmission.

| Pin | Function / Sensor | Interface Type | Electrical Specification | Purpose |
|---|---|---|---|---|
| **GPIO 34** | pH Sensor Module | Analog Input (ADC1_CH6) | 0.0V – 3.3V (Neutral: ~2.5V) | Measures river pH (CPCB Class B: 6.5–8.5). |
| **GPIO 35** | Optical Turbidity Sensor | Analog Input (ADC1_CH7) | 0.0V – 3.3V (Clear: ~3.0V, Muddy: <1.5V) | Optical scatter measurement in NTU. |
| **GPIO 4** | Water Temperature (DS18B20) | Digital OneWire | 3.3V Logic (4.7kΩ pullup required) | Water thermal monitoring (-10°C to +85°C). |
| **GPIO 5** | Water Level Trigger (JSN-SR04T) | Digital Output | 3.3V Trigger Pulse (10 µs) | Ultrasonic pulse initiation. |
| **GPIO 18** | Water Level Echo (JSN-SR04T) | Digital Input | 3.3V Echo Pulse (divider if 5V sensor) | Measures water stage elevation above MSL. |
| **GPIO 32** | Electrical Conductivity (EC) | Analog Input (ADC1_CH4) | 0.0V – 3.3V | Dissolved solids and ionic concentration. |
| **GPIO 33** | Dissolved Oxygen (DO) | Analog Input (ADC1_CH5) | 0.0V – 3.3V galvanic/optical | Measures dissolved O2 in mg/L (CPCB Class B: >=5.0 mg/L). |
| **GPIO 36** | Battery Voltage Monitor | Analog Input (ADC1_CH0) | 2:1 Resistor Divider (100kΩ / 100kΩ) | Measures Li-Ion pack state of charge. |
| **GPIO 2** | System Status Indicator | Digital Output | Active-High Blue LED | Wi-Fi / transmission state indicator. |

---

## 3. Power Subsystem Architecture

To maintain autonomous operations along the Varanasi ghats:

- **Battery Pack:** Two 18650 Lithium-Ion cells in parallel (3.7V nominal, 5200 mAh capacity).
- **Solar Harvesting:** 10W / 6V monocrystalline solar panel coupled with a TP4056 or CN3791 MPPT charging circuit with over-discharge and short-circuit protection.
- **Voltage Regulation:** AP2112K-3.3 or ME6211 low-dropout (LDO) regulator delivering up to 600mA with quiescent current < 55 µA.
- **Power Budget:**
  - Active sampling & Wi-Fi TX (80mA avg, 250mA peak): ~3 seconds per minute.
  - Deep sleep / Light sleep (optional field extension): ~15 µA.
  - Average power draw: ~4.5 mA (~45 days autonomy on zero sunlight).

---

## 4. Calibration & Quality Assurance Procedures

### 4.1 pH Sensor 2-Point / 3-Point Calibration
1. Rinse probe thoroughly with deionized (DI) water.
2. Immerse in standard pH 7.00 buffer solution at 25°C. Adjust potentiometer until voltage reads 2.50V (or record ADC value $V_{offset}$).
3. Immerse in standard pH 4.01 buffer solution. Record voltage ($V_{acid}$).
4. Calculate slope:
   $$m = \frac{4.01 - 7.00}{V_{acid} - 2.50}$$
5. Apply calibration constants in `config.h`.

### 4.2 Optical Turbidity Calibration
1. Immerse in pure DI water (0 NTU reference). Record clear water voltage ($V_{clear} \approx 3.0\text{V}$).
2. Immerse in 400 NTU Formazin standard suspension. Record voltage ($V_{400}$).
3. Compute quadratic/linear calibration transfer curve for the sensor conditioning circuit.

### 4.3 Ultrasonic Elevation Offset (MSL Conversion)
To convert ultrasonic sensor distance to CWC Varanasi Gauge height (Meters above Mean Sea Level):
$$\text{Water Level (m MSL)} = H_{sensor\_datum} - \frac{d_{measured}}{100}$$
Where $H_{sensor\_datum}$ is the surveyed elevation of the sensor mounting bracket (e.g., 73.50m MSL at Assi Ghat).

---

## 5. Phase 3B Physical Hardware Roadmap

When transitioning from bench testing to live river deployment:

1. **Enclosure:** IP68 weatherproof polycarbonate junction box with waterproof PG7 cable glands.
2. **Sensor Sheath:** Stainless steel 316 perforated stilling well to protect probes against Ganga river silt, debris, and monsoon currents.
3. **Mounting:** Stainless steel bracket mounted to reinforced masonry pillars above high flood level (73.0m MSL) at Assi Ghat and Dashashwamedh Ghat.
4. **Firmware Mode:** Set `#define SENSORS_PHYSICALLY_ATTACHED true` in `config.h` and flash using the Arduino package in `firmware/esp32/arduino/RiverSentinelESP32/`.
