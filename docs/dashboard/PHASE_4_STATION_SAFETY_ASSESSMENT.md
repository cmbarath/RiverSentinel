# River Sentinel 2.0 — Phase 4 Station-Specific Safety Assessment Specification

This document details the scientific screening criteria, regulatory thresholds, and implementation of **SafetyChecker** (`frontend/src/components/dashboard/SafetyChecker.tsx`).

---

## 1. Problem Statement & Audit Findings

The pre-implementation audit revealed critical deficiencies in the legacy safety checker:
1. **Global Reading Decoupling**: It listed 12 ghat names in a dropdown, but changing the selection evaluated the exact same global sensor reading from `useSensorData()`.
2. **Scientifically Irresponsible Potability Claims**:
   - The component checked if `ph >= 6.5 && turbidity < 5 && ec < 500` and declared water "Safe for drinking after filtration."
   - In-situ electronic sensors measure electro-chemical indicators. They CANNOT detect microbiological pathogens (such as Fecal Coliform or Salmonella) or dissolved heavy metals.
   - Declaring raw river water safe for human consumption without certified laboratory culture violates national drinking water standards (BIS IS 10500:2012).

---

## 2. Overhauled Architecture & Regulatory Criteria

The overhauled `SafetyChecker.tsx` queries `GET /api/v1/stations/<station_id>/evaluate-safety`.
The backend dynamically evaluates the single most recent valid observation for the chosen station against Indian regulatory standards:

### 2.1. Religious & Recreational Bathing (CPCB Class B)
Evaluates whether water quality meets the Central Pollution Control Board (CPCB) Primary Water Quality Criteria for Class B (Outdoor Bathing):
- **pH**: Must be between 6.5 and 8.5.
- **Dissolved Oxygen (DO)**: Must be ≥ 5.0 mg/L.
- **Turbidity**: Monitored for surface runoff / silt suspension.

### 2.2. Drinking Water Screening (BIS IS 10500:2012)
- Evaluates in-situ parameters (pH, Turbidity, Electrical Conductivity / TDS benchmark).
- **Mandatory Scientific Disclaimer**:
  *"In-situ electronic probes screen physical and chemical properties only. Raw river water contains bacteriological contaminants (e.g., Fecal Coliform) and must undergo conventional treatment and disinfection per BIS IS 10500:2012 prior to human consumption."*
- Explicitly marks suitability as `TREATMENT_REQUIRED`.

### 2.3. Aquatic Ecology & Dissolved Oxygen Health
- **Healthy**: DO ≥ 5.0 mg/L (Supports Gangetic river dolphins, major Indian carps).
- **Stressed**: 2.0 mg/L ≤ DO < 4.0 mg/L (Biological stress detected).
- **Hypoxic**: DO < 2.0 mg/L (Critical condition; risk of fish kills).

### 2.4. Hardware Health & Anomaly Confidence Score
- Cross-references sensor quality status (`valid`, `provisional`, `out_of_range`).
- Marks stream provenance (`real_sensor` vs `simulated`).
- Computes confidence score (95% for calibrated physical nodes, 70% for synthetic streams).

---

## 3. Empty & Unmonitored Station Handling

When a user selects a station in `planned` lifecycle status with no recorded telemetry packets:
- The UI renders an informative card stating: *"Awaiting Physical Node Deployment: Station is currently in PLANNED lifecycle status. Safety assessments cannot be determined without valid observations."*
- It does NOT fabricate synthetic numbers or display incorrect "Safe" badges.
