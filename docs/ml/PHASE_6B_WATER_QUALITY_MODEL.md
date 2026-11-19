# River Sentinel 2.0 — Phase 6B: Water Quality Model Redevelopment & CPCB Standards Engine

**Project:** River Sentinel 2.0  
**Target River / Location:** Ganga River, Varanasi, Uttar Pradesh, India  
**Date:** 2026-11-19  
**Status:** Validated Deterministic Reference Engine & Experimental Anomaly Screening  
**Branch:** `river-sentinel/phase-1-stabilization`  

---

## 1. Executive Summary & Core Principle

In accordance with Phase 6 instructions:
> *"Do not create a model simply to complete a milestone. Build models only where the real datasets support a meaningful prediction task... Never fabricate training rows, ground-truth labels or accuracy metrics. Do not promise or target an arbitrary validation accuracy such as 85–95%."*

The previous synthetic model (`backend/water_quality_model.pkl`) reported artificial 100% accuracy by memorizing non-overlapping uniform distributions and claiming untreated river water was "potable". 

Phase 6B replaces this with:
1. **Authoritative Standards-Based Deterministic Evaluator:** Implements official Central Pollution Control Board (CPCB) Designated Best Use Class B criteria for outdoor bathing.
2. **Exhaustive Station Alignment of Official CPCB Datasets (2018–2021):** Covers 272 actual sampling events across Varanasi, explicitly separating Ganga mainstem stations from tributaries.
3. **Dataset Sufficiency Gate Finding:** Supervised classification of statutory Class B compliance is **scientifically unviable and deferred** because exactly 0 out of 34 complete sampling events across the Varanasi Ganga stations met all 4 Class B criteria (100% of tested samples violated Total Coliform standards).
4. **Experimental In-Situ IoT Anomaly Detector (`water_quality_anomaly_detector_v1`):** An unsupervised `IsolationForest` model trained on empirical physical-chemical baselines to detect sensor faults, out-of-distribution industrial spills, and water quality shocks.

---

## 2. Preserved Raw CPCB Datasets & Checksums

Official laboratory monitoring datasets from the National Water Data Portal (NWDP / NWIC, Ministry of Jal Shakti) are preserved without modification.

| File Name | Agency / Period | File Size | SHA-256 Checksum |
| :--- | :--- | :--- | :--- |
| `physical_up_1961_2020.csv` | CPCB / 2020 | 570,765 bytes | `b14dc5e3d59a7d307519e164d820a13ccf263f72dc7b919de652f0cf5f66c291` |
| `physical_up_2021_2025.csv` | CPCB / 2021 | 63,519 bytes | `9ed3e9a7c8f30e957d5fa7024692646de6b0b1de4552828074b00f838746f66a` |
| `chemical_up_1961_2020.csv` | CPCB / 2020 | 901,047 bytes | `ad3a143b7b6eccadc8e3381d46f971f458c3aea15ff71bef4e492656f38380df` |
| `chemical_up_2021_2025.csv` | CPCB / 2021 | 352,325 bytes | `f8e2c82a1fad3928271ac9e384f9f99027c12d6b69b1fc3029ce5e07268efd72` |
| `biological_up_1961_2020.csv`| CPCB / 2020 | 557,862 bytes | `2ea5f193d6b7a466d57d299f84207811cba05348c44c05c0d8a2896319a4fb56` |
| `biological_up_2021_2025.csv`| CPCB / 2021 | 218,320 bytes | `02b0a00ca59c5b55f06b790b1c526dd0f0ae0d2c3fb70d43135c133eb220613a` |

---

## 3. Station Separation & Hydrological Contexts

Varanasi monitoring locations belong to distinct hydrological systems and must **never** be aggregated blindly:

```
                  Middle Ganga Basin — Varanasi River Network
                                    
 [Upstream Ganga (Mirzapur)]
          │
          ▼
   (Station 1) Ganga at Varanasi U/S (Assi Ghat)  [Mainstem Baseline]
          │
          ├──── City Ghats (Dashashwamedh, Manikarnika) & Urban Sewage Outfalls
          ▼
   (Station 2) Ganga at Varanasi D/S (Malviya Bridge / Rajghat) [Mainstem Impact]
          │
          ├──── Confluence with Varuna River (Stations 3 & 4: Rameshwar & Pre-Confluence)
          ▼
 [Downstream Ganga (Ghazipur / Bihar)]
```

### 3.1 Target Monitoring Stations

| Station Name in Raw Data | Clean System Name | River | Hydrological Context | Total Aligned Events | Complete Class B Samples |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GANGA AT VARANASI U/S (ASSIGHAT) U.P` | Ganga U/S Assi Ghat | Ganga | Mainstem Upstream Baseline | 64 | 17 (26.6%) |
| `GANGA AT VARANASI D/S (MALVIYA BRIDGE) U.P` | Ganga D/S Malviya Bridge | Ganga | Mainstem Downstream Impact | 65 | 17 (26.2%) |
| `RIVER VARUNA AT RAMESHWAR VARANASI` | Varuna at Rameshwar | Varuna | Rural Tributary | 47 | 12 (25.5%) |
| `RIVER VARUNA B/C WITH RIVER GANGA AT VARANASI`| Varuna Before Confluence | Varuna | Urban Tributary (Extreme Sewage) | 48 | 12 (25.0%) |
| `GOMTI AT VARANASI U.P` | Gomti at Varanasi | Gomti | Regional Tributary | 48 | 12 (25.0%) |

### 3.2 Rejected Non-River Monitoring Records
The following sampling stations in Varanasi were identified in raw files and rejected from river water quality modeling:
- `CHANDPUR INDUSTRIAL AREA LAHARTARA VARANASI` (Groundwater / industrial effluent)
- `GOPIGANJ INDUSTRIAL AREA BHADOHI VARANASI U.P` (Industrial drainage)
- `GROUND AROUND STP DINAPUR VARANASI U.P` (STP perimeter borewell)

---

## 4. Laboratory Sample Alignment Procedure

The physical, chemical, and biological files represent separate laboratory analysis streams.
- **Alignment Key:** Strict join on `(Station, Data Acquisition Time)`.
- **Temporal Synchronization:** Chemical and biological records have **100% timestamp matching** (identical collection events). Physical measurements are available on approximately $75\%$ of those dates.
- **Data Glitch Remediation:** Forensic inspection identified shifted rows in `physical_up_1961_2020.csv` during April 2020 (national COVID lockdown), where text like `'Clear'` was recorded in `Electric Conductivity` and `Turbidity` columns. The pipeline converts unparseable strings to `NaN` without corrupting valid numeric rows.
- **Resulting Aligned Dataset:** Stored at `backend/data/processed/varanasi_water_quality_aligned.csv` (272 rows x 20 columns).

---

## 5. Official CPCB Designated Best Use Class B Criteria

Statutory criteria for **Class B (Outdoor Bathing)** from the Central Pollution Control Board ([CPCB Criteria PDF](https://cpcb.nic.in/wqm/Designated_Best_Use_Water_Quality_Criteria.pdf)):

| Parameter | CPCB Class B Requirement | Regulatory Status | Operational Meaning |
| :--- | :--- | :--- | :--- |
| **pH** | **$6.5 - 8.5$** | Mandatory Statutory | Normal aquatic equilibrium |
| **Dissolved Oxygen (DO)** | **$\ge 5.0\text{ mg/L}$** | Mandatory Statutory | Aerobic ecosystem respiration |
| **BOD (5 days at 20°C)** | **$\le 3.0\text{ mg/L}$** | Mandatory Statutory | Organic pollution load |
| **Total Coliform** | **$\le 500\text{ MPN/100 mL}$** | Mandatory Statutory | Bacteriological / fecal hazard |
| **Turbidity** | Non-statutory ($100\text{ NTU}$ screening) | Operational Screening Only | Suspended silt; seasonal indicator |
| **Conductivity** | Non-statutory ($1500\text{ }\mu\text{S/cm}$ screening) | Operational Screening Only | Dissolved mineral ions |

---

## 6. Deterministic Reference Assessment Findings

Executing `backend/ml/water_quality/evaluator.py` against all 272 aligned empirical rows yields unvarnished ground truth:

```
                           Empirical CPCB Class B Compliance Audit
                           
  Station                           Total   Fully Compliant   Non-Compliant   Partial (Missing Coliform)
  ──────────────────────────────────────────────────────────────────────────────────────────────────────
  Ganga U/S Assi Ghat                64      0 (0.0%)         23 (35.9%)      41 (64.1%)
  Ganga D/S Malviya Bridge (Rajghat) 65      0 (0.0%)         65 (100.0%)      0 (0.0%)
  Gomti at Varanasi                  48      0 (0.0%)         46 (95.8%)       2 (4.2%)
  Varuna at Rameshwar                47      0 (0.0%)         35 (74.5%)      12 (25.5%)
  Varuna Before Confluence           48      0 (0.0%)         48 (100.0%)      0 (0.0%)
```

### Detailed Parameter-Level Realities:
1. **Downstream Ganga (Malviya Bridge):**
   - **BOD Failure:** 65 out of 65 samples ($100\%$) violated the $3.0\text{ mg/L}$ limit ($\text{mean} = 3.98\text{ mg/L}$, min $3.30$, max $5.80\text{ mg/L}$).
   - **Total Coliform Failure:** 17 out of 17 samples ($100\%$) violated the $500\text{ MPN}$ limit ($\text{mean} = 21,412\text{ MPN/100mL}$, exceeding standards by $> 40\times$).
   - **pH Violations:** 4 individual samples had $\text{pH} > 8.5$ (dates: 2019-12-02, 2020-01-02, 2020-04-16, 2020-05-07).
   - **DO Compliance:** Dissolved Oxygen met the $\ge 5.0\text{ mg/L}$ standard in 65/65 samples ($\text{mean} = 7.30\text{ mg/L}$).
2. **Upstream Ganga (Assi Ghat):**
   - **BOD:** Compliant in 58/64 samples ($\text{mean} = 2.56\text{ mg/L}$). Only 6 samples exceeded $3.0\text{ mg/L}$.
   - **Total Coliform:** 17 out of 17 samples violated the $500\text{ MPN}$ limit ($\text{mean} = 2,006\text{ MPN/100mL}$).
   - **pH Violations:** 3 individual samples exceeded $\text{pH} 8.5$ (dates: 2020-11-02, 2020-12-01, 2021-05-18).
3. **Core Scientific Rule Enforced:**
   - A sample is categorized as `partial_assessment` when measured parameters pass but required biological indicators (BOD or Total Coliform) are missing.
   - **Full compliance (`compliant_for_measured_parameters`) is NEVER declared unless all 4 statutory parameters are measured and pass.**
   - As a result, fully compliant samples across all Varanasi Ganga stations: **0 out of 129 samples**.

---

## 7. Dataset Sufficiency Gate & Real ML Tasks

### 7.1 Dataset Sufficiency Gate Evaluation
- **Total Complete Class B Observations:** 17 samples for Assi Ghat, 17 samples for Malviya Bridge.
- **Class Balance:** Class B Positive = 0, Class B Negative = 34.
- **Sampling Cadence:** Bi-weekly to monthly laboratory grab samples.
- **Physical Sensor Mismatch:** Real-time IoT probes measure physical parameters ($\text{pH, DO, Turbidity, EC, Temp}$), but **cannot measure 5-day incubation BOD or bacterial cultures**.
- **Conclusion:** Training a supervised classifier to predict statutory Class B compliance or 5-day BOD from sparse monthly samples is statistically invalid and **formally deferred**.

### 7.2 Experimental ML Implementation: Physical Sensor Anomaly Detection
To provide valuable real-time operational utility for IoT deployments without fabricating biological predictions, we implemented `water_quality_anomaly_detector_v1`:
- **Model Type:** `sklearn.ensemble.IsolationForest`
- **Features:** `[ph, do_mg_l, turbidity_ntu, conductivity_us_cm]`
- **Training Baseline:** Empirical distribution of Ganga mainstem stations (Assi Ghat & Malviya Bridge).
- **Contamination Prior:** $0.08$
- **Benchmark Performance:**
  - Ganga Baseline Anomaly Rate: $8.5\%$
  - Out-of-Distribution Recall on Varuna Sewage Effluent: $27.1\%$ physical-chemical anomaly detection rate.
- **Role:** Screens incoming IoT telemetry for physical sensor malfunctions, calibration drift, or sudden toxic industrial discharges.
