# River Sentinel 2.0 — Phase 3A Hardware Configuration Matrix

## 1. Physical Sensor Configuration Matrix

The table below documents the candidate and framework specifications for sensors planned for physical deployment on the ESP32-WROOM-32 edge node.

| Sensor Type | Candidate Model | Electrical Interface | Supply Voltage | Signal Voltage | Target GPIO | Measurement Range | Unit | Calibration Method | Driver Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Microcontroller** | ESP32-WROOM-32 | 3.3V Logic / USB-UART | 5.0V USB / 3.7V Li-Ion | 3.3V Max | N/A | N/A | N/A | Internal 1.1V Vref calibration | **Configured & Tested** |
| **Water Temperature** | DS18B20 (Waterproof) | 1-Wire Digital Bus | 3.0V – 5.5V | 3.3V (4.7kΩ pullup) | **GPIO 4** | -55 to +125 | °C | 2-point ice / precision bath | Abstract Framework (`ISensor`) |
| **pH Probe** | Analog pH Pro (DFRobot / E-201-C) | Analog (High-Z BNC amp) | 5.0V (VCC) | 0.0V – 3.0V (via divider) | **GPIO 32 (ADC1)** | 0.0 – 14.0 | pH units | 2-point buffer (pH 7.00 & 4.01) | Abstract Framework (`ISensor`) |
| **Turbidity Sensor** | Optical Turbidity (TS-300B) | Analog phototransistor | 5.0V (VCC) | 0.0V – 2.5V (within 3.3V) | **GPIO 35 (ADC1)** | 0 – 3000 | NTU | Formazin 0 NTU & 400 NTU | Abstract Framework (`ISensor`) |
| **Electrical Cond. (EC)** | DFRobot Gravity Analog EC | AC Excitation Analog | 3.3V – 5.0V | 0.0V – 3.0V | **GPIO 33 (ADC1)** | 0 – 10000 | µS/cm | KCl 1413 µS/cm standard | Abstract Framework (`ISensor`) |
| **Water Stage Level** | JSN-SR04T-2.0 Waterproof Ultrasonic | Digital Pulse (Trig/Echo) | 5.0V (VCC) | Echo: 3.3V (via divider) | **Trig: 5, Echo: 18** | 0.20 – 6.00 | m | Fixed datum tape verification | Abstract Framework (`ISensor`) |
| **Battery Monitor** | 100kΩ / 100kΩ Resistor Divider | Analog DC Divider | 3.7V – 4.2V | 1.85V – 2.10V | **GPIO 34 (ADC1)** | 0.0 – 100.0 | % | Multimeter voltage baseline | **Implemented (`DeviceStatus`)** |
| **BOD / COD** | Laboratory Reference Assay | Manual Lab Entry | N/A | N/A | N/A | BOD: 0–500, COD: 0–1000 | mg/L | Standard Methods 5210B / 5220B | **Lab / Manual Ingestion Only** |

---

## 2. Critical Electrical & Wiring Safety Guardrails

### 2.1 ADC Input Voltage Limitations
- **Maximum Tolerable Input:** 3.3V DC.
- Any 5V analog sensor output **must** transit through a precision resistive divider (e.g. $R_1 = 10\text{k}\Omega$, $R_2 = 20\text{k}\Omega$) or an external I2C analog-to-digital converter (ADS1115).
- Applying 5V directly to any ESP32 GPIO will permanently damage the silicon.

### 2.2 Wi-Fi vs. ADC Channel Contention
- ESP32 microcontrollers have two ADC peripherals: `ADC1` (8 channels) and `ADC2` (10 channels).
- **Hard Silicon Constraint:** `ADC2` is shared with the Wi-Fi transceiver. When the Wi-Fi stack transmits or scans, any read to `ADC2` returns corrupt data or fails.
- **Rule:** All analog river sensors must be connected strictly to `ADC1` pins:
  - GPIO 32 (ADC1_CH4)
  - GPIO 33 (ADC1_CH5)
  - GPIO 34 (ADC1_CH6 - Input only)
  - GPIO 35 (ADC1_CH7 - Input only)
  - GPIO 36 / SENSOR_VP (ADC1_CH0 - Input only)
  - GPIO 39 / SENSOR_VN (ADC1_CH3 - Input only)

### 2.3 Environmental Enclosure & Waterproofing
- River deployments at Varanasi ghats experience high monsoon humidity (up to 95%), seasonal submersion, and extreme summer ambient temperatures (up to 46°C).
- Enclosures must meet IP67 / NEMA 4X ingress protection standards.
- Conformal coating (silicone or acrylic) must be applied to all exposed PCBs.
- Cable glands (PG7 / PG9) with EPDM rubber seals must be used for probe entries.
