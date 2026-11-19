# River Sentinel 2.0 — Phase 6.1: Master Model Operational Status & Safety Matrix

**Project:** River Sentinel 2.0  
**Target River / Location:** Ganga River, Varanasi, Uttar Pradesh, India  
**Date:** 2026-11-19  
**Status:** Canonical Operational Status & Alert Eligibility Matrix  
**Branch:** `river-sentinel/phase-1-stabilization`  

---

## 1. Master Operational Status & Safety Matrix

Every analytical model and algorithm in River Sentinel 2.0 is assigned a strict lifecycle classification and alert governance policy:

| Model Identifier | Model Category | Version | Canonical Operational Status | Public Alert / SMS Eligible? | Primary Data Provenance | Authoritative Scope |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`cpcb_class_b_evaluator_v1`** | Deterministic Standards Engine | `1.0.0` | **`approved_standards_engine`** | **YES (Statutory Rules Only)** | Official CPCB / MoEFCC Criteria | Statutory outdoor bathing compliance screening |
| **`cwc_gauge_stage_engine_v1`** | Deterministic Hydrological Engine | `1.0.0` | **`approved_standards_engine`** | **YES (CWC Warning/Danger Only)** | Official CWC Stage Benchmarks | Emergency flood warning ($70.26\text{ m}$ Warning, $71.26\text{ m}$ Danger) |
| **`flood_stage_forecaster_v1`** | Ridge Regression ($\alpha=10.0$) | `1.1.0` | **`research_only`** | **NO (STRICTLY PROHIBITED)** | Semi-synthetic simulation series | 24-hour advisory river stage trend estimation |
| **`water_quality_anomaly_detector_v1`** | `IsolationForest` (Unsupervised) | `1.1.0` | **`experimental`** | **NO (STRICTLY PROHIBITED)** | Empirical CPCB Ganga baseline | In-situ IoT sensor sanity screening & spill detection |
| **`legacy_flood_classifier_v0`** | Random Forest Classifier | `0.1.0` | **`retired_baseline`** | **NO (PROHIBITED)** | Shuffled daily prototype series | Preserved legacy baseline for forensic audit only |
| **`legacy_water_quality_classifier_v0`** | Random Forest Classifier | `0.1.0` | **`retired_baseline`** | **NO (PROHIBITED)** | Disjoint uniform synthetic intervals | Preserved legacy baseline for forensic audit only |

---

## 2. Model Operational Specifications & Governance Rules

### 2.1 `cpcb_class_b_evaluator_v1`
- **Architecture:** Rule-based standards engine in `backend/ml/water_quality/evaluator.py`.
- **Status:** **`approved_standards_engine`** (Production Approved).
- **Core Role:** Evaluates aligned water quality records against official Central Pollution Control Board (CPCB) Designated Best Use Class B outdoor bathing criteria:
  - $\text{pH}: 6.5 - 8.5$
  - $\text{DO}: \ge 5.0\text{ mg/L}$
  - $\text{BOD}: \le 3.0\text{ mg/L}$
  - $\text{Total Coliform}: \le 500\text{ MPN/100mL}$
- **Operational Rule:** Full compliance is NEVER declared if any required parameter is missing. Turbidity is evaluated independently as an operational screening threshold ($\le 100\text{ NTU}$), not as a statutory criterion.
- **Alert Eligibility:** Eligible for municipal and authority water quality alerts when statutory parameters exceed legal limits.

---

### 2.2 `flood_stage_forecaster_v1`
- **Architecture:** Ridge Regression ($\alpha=10.0$) using 17 causal features strictly at time $t$.
- **Status:** **`research_only`** (Scientific Research Advisory Only).
- **Artifact:** `backend/ml/models/flood_stage_forecaster_v1.pkl` & `flood_stage_scaler_v1.pkl`.
- **Performance:** Achieves an MAE of **$0.7882\text{ m}$** and RMSE of **$0.9719\text{ m}$** on the held-out 2020 test year, outperforming the Persistence Baseline ($1.0635\text{ m}$) by $25.9\%$.
- **Data Provenance:** Historical series derived from prototype simulation containing synthetic rainfall injection across dry months.
- **Strict Governance Constraints:**
  1. **Zero Public Alert Eligibility:** Forecasted stages must **NEVER** trigger emergency public alerts, automated evacuation notices, or SMS messages.
  2. **No Gauge Conflation:** API responses must explicitly state `is_official_cwc_gauge: false` and `prediction_status: 'research_only'`.
  3. **Analytical Boundary Labeling:** Stage $\ge 67.5\text{ m}$ is explicitly designated as an **analytical subset boundary**, never as a statutory flood warning.
  4. **Emergency Primacy:** Official flood warnings derive exclusively from verified physical gauge levels crossing CWC statutory stages ($70.26\text{ m}$ Warning, $71.26\text{ m}$ Danger).

---

### 2.3 `water_quality_anomaly_detector_v1`
- **Architecture:** `IsolationForest` (100 estimators, contamination prior $= 0.08$) using 4 physical parameters (`[ph, do, turbidity, ec]`).
- **Status:** **`experimental`** (Experimental Physical Screening Only).
- **Artifact:** `backend/ml/models/water_quality_anomaly_detector_v1.pkl` & `water_quality_scaler_v1.pkl`.
- **Performance:** Detects $8.5\%$ anomalies on Ganga baseline; achieves **$27.1\%$ recall** on severe untreated urban sewage (Varuna Confluence).
- **Known Limitation:** Blind to bacteriological pathogens (Total Coliform) and dissolved organic matter (BOD) when surface aeration prevents severe hypoxia ($\text{DO} > 2.0\text{ mg/L}$).
- **Strict Governance Constraints:**
  1. **Zero Public Alert Eligibility:** Anomaly scores must **NEVER** trigger automated pollution alerts or citizen notifications.
  2. **Screening Isolation:** Output is isolated in API responses under `physical_screening` with `alert_eligible: false`.
  3. **Display Integrity:** Dashboards must label anomaly outputs as "Experimental Physical Sensor Screening", never as "Confirmed Biological Contamination".

---

### 2.4 Retired Legacy Baselines (`legacy_flood_classifier_v0` & `legacy_water_quality_classifier_v0`)
- **Status:** **`retired_baseline`** (Retired from Production).
- **Artifacts:** `backend/flood_model.pkl`, `backend/flood_scaler.pkl`, `backend/water_quality_model.pkl`, `backend/water_quality_scaler.pkl`.
- **Audit Findings:** The legacy flood model used an invalid random train/test split on time series and an artificial rainfall heuristic; the legacy water quality model used disjoint uniform distributions and falsely categorized raw river water as potable.
- **Preservation Policy:** Retained in the repository with intact SHA-256 checksums to preserve forensic reproducibility and backward compatibility, but permanently retired from decision-making.

---

## 3. Dashboard Integration & Safety Rules

To ensure complete user safety and prevent misinformation:

```
                            Dashboard Data Representation
                            
  Frontend Component             Data Source                        Display Rules
  ──────────────────────────────────────────────────────────────────────────────────────────────────────────
  AuthorityAlerts.tsx            alert_service.py                   Statutory CPCB/CWC deterministic alerts ONLY.
                                                                    Zero experimental ML alert generation.
                                                                    
  WeatherAndFlood.tsx            GET /api/flood/predict             Displays 1-day forecasted stage with:
                                                                    - Explicit "Research Advisory Only" badge.
                                                                    - CWC Warning (70.26m) reference level.
                                                                    - Data provenance disclaimer.
                                                                    
  WaterQuality.tsx               GET /api/water-quality/predict     Displays CPCB Class B assessment with:
                                                                    - Explicit "Outdoor Bathing" criteria.
                                                                    - Non-potable surface water warning.
                                                                    - Experimental physical anomaly indicator.
```

### Prohibited Application Behaviors:
- **No Artificial Confidence Percentages:** Models must not return fabricated "99.9% confidence" figures.
- **No Automatic Emergency SMS:** No worker or endpoint may dispatch telephony SMS or WhatsApp messages based on `flood_stage_forecaster_v1` or `water_quality_anomaly_detector_v1`.
- **No Fake Sensor Interpolation:** In the absence of live physical hardware, endpoints must transparently report simulation or missing-data statuses.
