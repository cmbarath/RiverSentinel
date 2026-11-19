# River Sentinel 2.0 — Standard Alert Rules & Regulatory Criteria (Phase 5.1 Hardened)

## 1. Statutory vs. Operational Regulatory Rules

River Sentinel 2.0 strictly distinguishes statutory environmental benchmarks from internal operational riparian screening rules.

| Rule Code | Category | Parameter | Condition | Severity | Statutory? | Origin / Version Metadata | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `RULE-CWC-FLOOD-WARN` | `FLOOD` | `water_level` | `>= 70.26 m` | `HIGH` | **Yes** | CWC Varanasi Reference Datum | Water level reaches CWC Warning Stage (70.26m MSL). Low-lying steps inundated. |
| `RULE-CWC-FLOOD-DANGER` | `FLOOD` | `water_level` | `>= 71.26 m` | `CRITICAL` | **Yes** | CWC Varanasi Reference Datum | Water level reaches CWC Danger Stage (71.26m MSL). Precautionary evacuation required. |
| `RULE-CPCB-PH-RANGE` | `WATER_QUALITY` | `ph` | `< 6.5 OR > 8.5` | `HIGH` | **Yes** | CPCB Class B (Outdoor Bathing) | Surface water pH outside safe statutory range (6.5 - 8.5). Chemical or acidic discharge risk. |
| `RULE-CPCB-DO-MIN` | `WATER_QUALITY` | `do` | `< 5.0 mg/L` | `HIGH` | **Yes** | CPCB Class B (Outdoor Bathing) | Dissolved Oxygen critically depleted (< 5.0 mg/L). Risk to human immersion & aquatic life. |
| `RULE-TURB-HIGH` | `OPERATIONAL_SCREENING` | `turbidity` | `> 100.0 NTU` | `MEDIUM` | **No** | Project Investigation Guideline v2.0 | Non-statutory operational investigation threshold for suspended solids/effluent plume. |
| `RULE-DEV-OFFLINE` | `DEVICE_HEALTH` | `heartbeat_stale_seconds` | `> 900 s` | `HIGH` | Internal | IoT Edge Reliability Spec v1.0 | Active ESP32 node has not transmitted telemetry in 15 minutes. Check LoRa/WiFi/power. |
| `RULE-POLLUTION-NEW` | `POLLUTION_REPORT` | `status` | `eq 'PENDING'` | `HIGH` | Citizen | Citizen Watchdog Workflow | New citizen pollution report filed. UPPCB field triage required. |

---

## 2. Scientific Evaluation Semantics

### 2.1 CPCB Class B Primary Water Quality Criteria for Outdoor Bathing
Official statutory CPCB Class B criteria require all four parameters:
1. **pH**: 6.5 to 8.5
2. **Dissolved Oxygen (DO)**: $\ge 5.0\text{ mg/L}$
3. **Biochemical Oxygen Demand (BOD 5-day 20°C)**: $\le 3.0\text{ mg/L}$
4. **Total Coliform Organisms**: $\le 500\text{ MPN/100 mL}$

**In-Situ Hardware Screening Limitation:**
Real-time electronic edge nodes (ESP32 probes) measure physical and chemical indicators (pH, DO, temperature, conductivity, turbidity). Continuous electronic probes cannot perform 5-day microbiological incubation (BOD) or bacteriological culture (Total Coliform).
Therefore, real-time telemetry assessments are classified as:
- `compliant_for_measured_parameters`: All in-situ electronic parameters (pH, DO) are within limits, with explicit `partial_assessment` disclaimer indicating laboratory microbiological analysis is required for statutory certification.
- `non_compliant_for_measured_parameters`: At least one in-situ measured parameter violates limits.
- `insufficient_data`: Neither pH nor DO is available.

### 2.2 Operational Turbidity Screening (`RULE-TURB-HIGH`)
- **Scientific Clarification**: Turbidity is **not** a statutory CPCB Class B criterion for outdoor bathing. Turbidity is governed separately as an operational riparian clarity guideline (100.0 NTU trigger, 85.0 NTU recovery).
- **Category**: `OPERATIONAL_SCREENING` (distinct from statutory `WATER_QUALITY`).
- **Rule Metadata**: `is_cpcb_statutory = FALSE`, `source_reference = 'Project Investigation Guideline v2.0'`, `rule_version = 2`.
- **Hysteresis Recovery**: Recovery is evaluated at `<= 85.0 NTU` to prevent alert chattering during transient silt surges.

### 2.3 Granular Alert Deduplication Keys
To prevent cross-parameter collision (such as high turbidity overwriting low DO), all deduplication keys are fully qualified:
- **CWC Flood Stage**: `RULE-CWC-FLOOD:{station_id}:water_level`
- **CPCB pH Range**: `RULE-CPCB-PH-RANGE:{station_id}:ph`
- **CPCB Minimum DO**: `RULE-CPCB-DO-MIN:{station_id}:do`
- **Turbidity Screening**: `RULE-TURB-HIGH:{station_id}:turbidity`
- **Device Connectivity**: `RULE-DEV-OFFLINE:{device_id}`
- **Citizen Pollution Report**: `RULE-POLLUTION-NEW:{report_id}`

---

## 3. Dynamic Rule Management (Admin API)

Authority Administrators can inspect, update, or create rules via `/api/v1/alerts/rules`.
All rule modifications retain `rule_version` tracking and log lifecycle transitions in `alert_events`.
