# River Sentinel 2.0 — Phase 3A Sensor Calibration Framework

## 1. Scientific Calibration Mandate

In accordance with hydrological and environmental measurement standards, raw voltage signals or analog-to-digital converter (ADC) counts cannot be treated as authoritative river quality measurements without traceable calibration.

Furthermore:
- **Biochemical Oxygen Demand (BOD)** and **Chemical Oxygen Demand (COD)** are **NOT** direct physical field sensor measurements. They represent laboratory incubated assays (5-day standard at 20°C for BOD₅) and chemical digestion (potassium dichromate reflux for COD). Physical ESP32 microcontrollers must not fabricate direct real-time BOD/COD readings.
- **CWC Flood Thresholds** at the Varanasi gauge site (70.26m Warning, 71.26m Danger) are referenced to the Great Trigonometrical Survey (GTS) Mean Sea Level (MSL) datum. Ultrasonic or hydrostatic stage sensors mounted on ghat steps measure height above the sensor mounting datum and require a physical topographic benchmark survey before equating their values to CWC MSL flood gauge heights.

---

## 2. Sensor Parameter Calibration Profiles

### 2.1 Hydrogen Ion Potential (pH)
- **Sensor Type:** Glass electrode combination probe with BNC signal amplifier (e.g. Gravity Analog pH Sensor).
- **Interface:** Analog voltage (0.0 – 3.0V).
- **Calibration Protocol:** Two-point buffer calibration:
  - Buffer 1: Neutral buffer solution (pH 7.00 at 25°C).
  - Buffer 2: Acidic buffer solution (pH 4.01) or alkaline buffer solution (pH 9.18).
- **Mathematical Conversion:**
  $$\text{pH} = 7.0 + \frac{V_{\text{measured}} - V_{\text{pH7}}}{\text{Slope}}$$
  *(Where Slope is calibrated in mV/pH unit, typically ~59.16 mV/pH at 25°C).*
- **Calibration Frequency:** Bi-weekly in river deployments due to biofouling.

### 2.2 Turbidity
- **Sensor Type:** Optical nephelometric sensor (infrared 850nm LED and phototransistor).
- **Interface:** Analog voltage (0.0 – 3.0V).
- **Calibration Protocol:** Two-point calibration against Formazin Turbidity Standards:
  - 0 NTU: Deionized distilled water.
  - 400 NTU: Standard Formazin polymer suspension.
- **Conversion Function:** Non-linear polynomial derived from calibration points:
  $$\text{Turbidity (NTU)} = a \cdot V^2 + b \cdot V + c$$
  *(Coefficients $a, b, c$ determined per batch calibration).*

### 2.3 Water Temperature
- **Sensor Type:** Waterproof DS18B20 digital thermal probe.
- **Interface:** 1-Wire Digital Bus (Dallas 1-Wire Protocol).
- **Resolution:** 12-bit (0.0625°C precision).
- **Calibration Protocol:** Zero-point calibration in crushed ice-water bath (0.0°C) and precision laboratory reference bath (25.0°C).

### 2.4 Electrical Conductivity (EC)
- **Sensor Type:** Platinum or stainless-steel two-electrode cell.
- **Interface:** AC excitation circuit (to prevent electrode polarization) with analog envelope detector.
- **Calibration Protocol:** Standard Potassium Chloride (KCl) solutions (1413 µS/cm and 12.88 mS/cm at 25°C) with active temperature compensation:
  $$\text{EC}_{25} = \frac{\text{EC}_{\text{raw}}}{1 + \alpha (T - 25)}$$
  *(Where temperature coefficient $\alpha \approx 0.0191 / ^\circ\text{C}$).*

### 2.5 Water Level / Stage Gauge
- **Sensor Type:** Weatherproof ultrasonic sensor (JSN-SR04T) or hydrostatic pressure transmitter (4-20mA with 250Ω precision burden resistor).
- **Interface:** Digital trigger/echo or 0.6 – 3.0V analog.
- **Datum Conversion:**
  $$\text{Water Level (MSL)} = \text{Sensor Mounting Elevation (MSL)} - \text{Measured Distance to Water Surface}$$
  *(Sensor mounting elevation must be determined by field RTK-GNSS or GTS benchmark levelling).*

### 2.6 Dissolved Oxygen (DO)
- **Sensor Type:** Galvanic or optical fluorescence DO probe.
- **Interface:** Analog millivolt interface.
- **Calibration Protocol:** 100% water-saturated air calibration and zero-oxygen solution (sodium sulfite $\text{Na}_2\text{SO}_3$ 5% solution).

---

## 3. Calibration Metadata Schema

Every calibrated deployment stores calibration verification records in the station and device registry:

| Field | Type | Description |
| :--- | :--- | :--- |
| `sensor_type` | `VARCHAR(30)` | Parameter identifier (`ph`, `turbidity`, etc.) |
| `calibration_date` | `DATE` | Date procedure was executed in lab/field |
| `technician_name` | `VARCHAR(100)` | Name of qualified environmental technician |
| `standard_lot_number`| `VARCHAR(50)` | Chemical buffer batch or lot identifier |
| `calibrated_slope` | `NUMERIC(8,4)` | Calculated transducer transfer slope |
| `zero_offset` | `NUMERIC(8,4)` | Sensor zero voltage offset (mV) |
| `expiry_date` | `DATE` | Scheduled date for recalibration |
| `status` | `VARCHAR(20)` | `valid`, `recalibration_due`, `expired` |
