# River Sentinel 2.0 — Phase 6: Model Registry

**Project:** River Sentinel 2.0  
**Target Geography:** Ganga River, Varanasi, Uttar Pradesh, India  
**Date:** 2026-11-19  
**Status:** Cryptographic Model Registry, Versioning & Lifecycle Tracking  
**Branch:** `river-sentinel/phase-1-stabilization`  

---

## 1. Registry Architecture & Status Definitions

River Sentinel 2.0 classifies all machine learning and algorithmic artifacts under four formal operational statuses:

1. **`approved_standards_engine`**: Authoritative, deterministically validated rule engine complying with statutory environmental standards (CPCB Class B, CWC Hydrological Stages).
2. **`experimental`**: Research model trained with causal anti-leakage guarantees and evaluated on held-out temporal data. Used for operational advisory and screening; **strictly prohibited from autonomously triggering public emergency SMS alerts**.
3. **`invalid_legacy_preserved`**: Previous prototype model retained solely for forensic auditing and backward compatibility. Never used for safety-critical decisions.
4. **`deferred`**: Predictive modeling task formally postponed due to failing the Dataset Sufficiency Gate (e.g. 0 positive events in ground truth).

---

## 2. Active Model Inventory

### 2.1 Model Registry Table

| Model Name | Version | Status | Primary Serialized Artifact | Scaler / Preprocessor | Primary Task |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`cpcb_class_b_evaluator_v1`** | `1.0.0` | `approved_standards_engine` | `backend/ml/water_quality/evaluator.py` | None (Rule Engine) | Statutory CPCB Class B compliance screening |
| **`flood_stage_forecaster_v1`** | `1.0.0` | `experimental` | `backend/ml/models/flood_stage_forecaster_v1.pkl` | `flood_stage_scaler_v1.pkl` | 1-Day-Ahead Ganga water level regression ($m$) |
| **`water_quality_anomaly_detector_v1`** | `1.0.0` | `experimental` | `backend/ml/models/water_quality_anomaly_detector_v1.pkl` | `water_quality_scaler_v1.pkl` | In-situ IoT physical sensor anomaly screening |
| **`legacy_flood_model_v0`** | `0.1.0` | `invalid_legacy_preserved` | `backend/flood_model.pkl` | `backend/flood_scaler.pkl` | Preserved legacy binary prototype |
| **`legacy_water_quality_model_v0`** | `0.1.0` | `invalid_legacy_preserved` | `backend/water_quality_model.pkl` | `backend/water_quality_scaler.pkl` | Preserved legacy synthetic prototype |

---

## 3. Detailed Model Specifications

### 3.1 Model: `cpcb_class_b_evaluator_v1`
- **Identifier:** `cpcb_class_b_evaluator_v1`
- **Lifecycle Status:** `approved_standards_engine`
- **Implementation:** Python module `backend/ml/water_quality/evaluator.py`
- **Target Definition:** Record-level assessment against official CPCB Designated Best Use Class B outdoor bathing criteria:
  - `compliant_for_measured_parameters`
  - `non_compliant_for_measured_parameters`
  - `partial_assessment`
  - `insufficient_data`
- **Input Parameters & Statutory Criteria:**
  1. `ph`: $6.5 \le \text{pH} \le 8.5$
  2. `do_mg_l`: $\ge 5.0\text{ mg/L}$
  3. `bod_mg_l`: $\le 3.0\text{ mg/L}$
  4. `total_coliform_mpn_100ml`: $\le 500\text{ MPN/100mL}$
  5. `turbidity_ntu`: Operational screening threshold ($\le 100\text{ NTU}$, non-statutory)
  6. `conductivity_us_cm`: Operational screening threshold ($\le 1500\text{ }\mu\text{S/cm}$, non-statutory)
- **Core Governance Rule:** Full compliance is NEVER declared unless all 4 required parameters are measured and pass.
- **Inference Integration:** Active in `GET /api/water-quality/predict` under key `cpcb_class_b_assessment`.

---

### 3.2 Model: `flood_stage_forecaster_v1`
- **Identifier:** `flood_stage_forecaster_v1`
- **Lifecycle Status:** `experimental`
- **Model Architecture:** `sklearn.ensemble.RandomForestRegressor`
  - Estimators: 100 trees
  - Max Depth: 6 (constrained to prevent leaf memorization)
  - Min Samples Split: 5
- **Artifact Path:** `backend/ml/models/flood_stage_forecaster_v1.pkl`
- **Scaler Path:** `backend/ml/models/flood_stage_scaler_v1.pkl` (`StandardScaler`, 17 features)
- **Target:** Tomorrow's river water level: $y_t = \text{water\_level}_{t+1}$ in metres above MSL.
- **Features (17 Causal Features at Time $t$):**
  `['stage_t', 'stage_lag1', 'stage_lag2', 'stage_delta_1d', 'stage_delta_2d', 'stage_rolling_mean_3d', 'stage_rolling_mean_7d', 'stage_rolling_max_7d', 'rain_local_t', 'rain_local_3d_sum', 'rain_upstream_t', 'rain_upstream_3d_sum', 'discharge_t', 'temp_t', 'humidity_t', 'season_sin', 'season_cos']`
- **Training Period:** 2018-01-07 to 2019-12-31 ($724\text{ days}$)
- **Test Period (Held-Out):** 2020-01-01 to 2020-12-29 ($364\text{ days}$)
- **Performance on Held-Out 2020 Test Set:**
  - Overall MAE: **$0.7970\text{ m}$** (Persistence baseline: $1.0635\text{ m}$ — **$25.1\%$ error reduction**)
  - Overall RMSE: **$0.9809\text{ m}$** (Persistence baseline: $1.3272\text{ m}$)
  - High-Water Period MAE ($\ge 67.5\text{ m}$): **$0.8036\text{ m}$** (Persistence baseline: $1.0606\text{ m}$)
  - Bias: $+0.0237\text{ m}$
- **Known Limitations:**
  - Historical dataset contains zero observations crossing CWC Warning Stage ($70.26\text{ m}$) or Danger Stage ($71.26\text{ m}$).
  - Must never trigger emergency SMS alerts directly. All emergency public warnings derive strictly from official CWC gauge readings.
- **Inference Integration:** Active in `GET /api/flood/predict` under key `stage_forecast`.

---

### 3.3 Model: `water_quality_anomaly_detector_v1`
- **Identifier:** `water_quality_anomaly_detector_v1`
- **Lifecycle Status:** `experimental`
- **Model Architecture:** `sklearn.ensemble.IsolationForest`
  - Estimators: 100 trees
  - Contamination Prior: 0.08
- **Artifact Path:** `backend/ml/models/water_quality_anomaly_detector_v1.pkl`
- **Scaler Path:** `backend/ml/models/water_quality_scaler_v1.pkl` (`StandardScaler`, 4 features)
- **Features (4 In-Situ Physical-Chemical Parameters):**
  `['ph', 'do_mg_l', 'turbidity_ntu', 'conductivity_us_cm']`
- **Training Baseline:** 129 physical-chemical samples from Ganga mainstem stations at Varanasi (Assi Ghat & Malviya Bridge, 2018–2021).
- **Validation Results:**
  - Ganga Baseline Anomaly Detection Rate: $8.5\%$
  - Out-of-Distribution Anomaly Recall on Varuna Sewage: $27.1\%$
- **Known Limitations:**
  - Does not predict bacteriological contamination (Total Coliform) or 5-day BOD.
  - Acts strictly as an operational IoT hardware sanity check and industrial spill screening filter.
- **Inference Integration:** Active in `GET /api/water-quality/predict` under key `physical_screening.anomaly_status`.

---

### 3.4 Preserved Legacy Artifacts (Forensic Tracking)
These files remain untouched in `backend/` with their original SHA-256 checksums:
1. `backend/flood_model.pkl` (`cc9d2b930bf457e20646f0fbafd9e98aecbcc7af6917744a1538b16d0e9c0f0a`): Legacy 6-feature classifier.
2. `backend/flood_scaler.pkl` (`7d225b73471171647cf195c061bd5eaa42dfecb5b964271a17763e592295c695`): Legacy 6-feature scaler.
3. `backend/water_quality_model.pkl` (`a8b927575aea9de2d3b5288999ad9d3acf39f9183acc1e1ce4195a658accdfab`): Legacy synthetic classifier.
4. `backend/water_quality_scaler.pkl` (`aa855b948ade01ad7c5695b40228673eedcd30e41ee16351bcc758f51101a11c`): Legacy synthetic scaler.
