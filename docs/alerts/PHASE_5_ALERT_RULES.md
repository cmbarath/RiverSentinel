# River Sentinel 2.0 — Standard Alert Rules & Regulatory Criteria

## 1. Seeded Statutory Alert Rules

The database comes pre-configured with 7 official regulatory alert rules:

| Rule Code | Category | Parameter | Condition | Severity | Regulatory Origin | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `RULE-CWC-FLOOD-WARN` | `FLOOD` | `water_level` | `>= 70.26 m` | `HIGH` | CWC Varanasi Datum | Water level reaches or exceeds CWC Warning Stage (70.26m MSL). Low-lying steps inundated. |
| `RULE-CWC-FLOOD-DANGER` | `FLOOD` | `water_level` | `>= 71.26 m` | `CRITICAL` | CWC Varanasi Datum | Water level reaches or exceeds CWC Danger Stage (71.26m MSL). Precautionary evacuation required. |
| `RULE-CPCB-PH-RANGE` | `WATER_QUALITY` | `ph` | `< 6.5 OR > 8.5` | `HIGH` | CPCB Class B (Bathing) | Surface water pH outside safe statutory range (6.5 - 8.5). Chemical or acidic discharge risk. |
| `RULE-CPCB-DO-MIN` | `WATER_QUALITY` | `do` | `< 5.0 mg/L` | `HIGH` | CPCB Class B (Bathing) | Dissolved Oxygen critically depleted (< 5.0 mg/L). Risk to aquatic biodiversity. |
| `RULE-TURB-HIGH` | `WATER_QUALITY` | `turbidity` | `> 100 NTU` | `MEDIUM` | CPCB/BIS IS 10500 | Excessive sediment load or sewage effluent discharge detected. |
| `RULE-DEV-OFFLINE` | `DEVICE_HEALTH` | `heartbeat_stale_seconds` | `> 900 s` | `HIGH` | IoT Edge Reliability Spec | Active ESP32 node has not transmitted telemetry in 15 minutes. Check power or LoRa/WiFi gateway. |
| `RULE-POLLUTION-NEW` | `POLLUTION_REPORT` | `status` | `eq 'PENDING'` | `HIGH` | Citizen Watchdog Workflow | New citizen pollution report filed. UPPCB field triage required. |

---

## 2. Rule Evaluation Semantics

### 2.1 CWC Hydrological Flood Screening
- Flood thresholds are GTS MSL (Mean Sea Level) elevations.
- Evaluation occurs **only** when `station.cwc_reference_gauge_id` is present.
- A water level `>= 71.26m` creates or escalates an existing alert to `CRITICAL`.
- A water level `>= 70.26m` and `< 71.26m` creates or maintains a `HIGH` alert.
- Hysteresis recovery occurs when water level recedes below `warning_threshold - 0.15m` (e.g. `<= 70.11m`).

### 2.2 CPCB Class B Water Quality Screening
- **pH**: Values `< 6.5` indicate industrial acidic runoff or organic decomposition; values `> 8.5` indicate alkaline industrial wastewater or toxic algae blooms.
  - Recovery condition: `6.6 <= ph <= 8.4`.
- **Dissolved Oxygen (DO)**: Values `< 5.0 mg/L` violate the minimum bathing requirement. Severe hypoxia (`< 2.0 mg/L`) is escalated in alert descriptions.
  - Recovery condition: `do >= 5.2 mg/L`.
- **Turbidity**: Values `> 100 NTU` exceed riparian clarity standards.
  - Recovery condition: `turbidity <= 90 NTU`.

### 2.3 Hardware Health Screening
- Applies **strictly** to devices with lifecycle state `active`.
- Provisioned devices awaiting initial deployment (`status == 'provisioned'`) are **not** flagged as offline outages.
- If an active device with prior transmissions exceeds `900` seconds since `last_seen_at`, `RULE-DEV-OFFLINE` triggers.
- Once telemetry is received within `900` seconds, the offline alert is resolved automatically.

---

## 3. Dynamic Rule Management (Admin API)

Authority Administrators can create or update rules via the versioned API:

```http
POST /api/v1/alerts/rules
Authorization: Bearer <authority_jwt>
Content-Type: application/json

{
    "rule_code": "RULE-CUSTOM-TEMP-MAX",
    "name": "High Water Temperature Warning",
    "category": "WATER_QUALITY",
    "parameter": "temperature",
    "operator": ">",
    "threshold_value": 35.0,
    "threshold_unit": "°C",
    "severity": "MEDIUM",
    "cooldown_seconds": 1800,
    "enabled": true
}
```
