# River Sentinel 2.0 — Phase 6: Machine Learning Experiment Log

**Project:** River Sentinel 2.0  
**Target River / Location:** Ganga River, Varanasi, Uttar Pradesh, India  
**Date:** 2026-11-19  
**Status:** Comprehensive Record of Successful, Experimental, and Deferred Modeling Tasks  
**Branch:** `river-sentinel/phase-1-stabilization`  

---

## 1. Overview & Scientific Experimentation Protocol

In strict alignment with River Sentinel 2.0 principles:
- No model is forced simply to achieve an arbitrary completion milestone.
- All models are evaluated against real baseline comparisons (Persistence, Rolling Averages, Deterministic Standards).
- Unsuccessful or deferred experiments are documented in full detail to preserve empirical truth and prevent architectural regression.

---

## 2. Water Quality Modeling Experiments

### Experiment WQ-1: Synthetic Potability Classification (Legacy Prototype)
- **Model Architecture:** `RandomForestClassifier` (100 trees), `StandardScaler` (5 features).
- **Features:** `[ph, turbidity, temperature, ec, do]`
- **Target:** Synthetic binary potability (`1 = potable, 0 = non-potable`).
- **Data Source:** `backend/train_water_quality_model.py` generating 2,000 synthetic rows via `np.random.uniform`.
- **Reported Metrics:** Accuracy $100\%$, Precision $1.00$, Recall $1.00$, ROC-AUC $1.00$.
- **Outcome: REJECTED & CLASSIFIED INVALID.**
- **Diagnostic Root Cause:** Safe and unsafe intervals were generated with artificial, non-overlapping gaps (e.g. Turbidity safe: $[0.5, 9.9]\text{ NTU}$, unsafe: $[10.0, 500.0]\text{ NTU}$). A single decision tree split achieved 100% accuracy. The model learned zero real-world environmental dynamics and falsely categorized raw surface water as potable.

---

### Experiment WQ-2: Supervised Binary CPCB Class B Classifier
- **Objective:** Train a classifier to predict whether a sample meets official CPCB Class B Designated Best Use criteria for outdoor bathing.
- **Dataset:** 272 aligned CPCB laboratory observations across 5 Varanasi stations (2018–2021).
- **Target:** `is_cpcb_class_b_compliant` (1 if all 4 parameters pass: pH 6.5–8.5, DO $\ge 5\text{ mg/L}$, BOD $\le 3\text{ mg/L}$, Total Coliform $\le 500\text{ MPN/100mL}$).
- **Target Class Distribution:**
  - Ganga U/S Assi Ghat: Compliant = 0, Non-compliant = 23, Partial = 41. (Positive class prevalence: **0%**)
  - Ganga D/S Malviya Bridge: Compliant = 0, Non-compliant = 65. (Positive class prevalence: **0%**)
  - Varuna & Gomti: Compliant = 0, Non-compliant = 129, Partial = 14. (Positive class prevalence: **0%**)
- **Outcome: FORMALLY DEFERRED (DATASET SUFFICIENCY GATE FAILED).**
- **Scientific Reason:** Supervised binary classification cannot be trained when the positive class prevalence in verified ground-truth data is exactly $0\%$. Total Coliform in Ganga at Varanasi consistently exceeds the $500\text{ MPN/100mL}$ standard across all tested samples. Generating synthetic positive labels would violate core project principles.
- **Adopted Solution:** The standards-based **Deterministic Reference Evaluator** (`backend/ml/water_quality/evaluator.py`) is deployed as the authoritative evaluation mechanism.

---

### Experiment WQ-3: Supervised Real-Time 5-Day BOD Regression from IoT Probes
- **Objective:** Predict 5-day Biochemical Oxygen Demand (BOD) directly from minute-level IoT sensor readings ($\text{pH, Turbidity, EC, Temp, DO}$).
- **Outcome: FORMALLY DEFERRED (BIOLOGICAL LATENCY MISMATCH).**
- **Scientific Reason:** BOD is a microbiological assay requiring 5 days of incubation at 20°C to measure oxygen depletion caused by aerobic biochemical decomposition. While optical surrogates exist under controlled laboratory conditions, attempting to predict 5-day BOD from raw in-situ physical sensor telemetry without site-specific spectrographic calibration produces severe spurious correlations. Empirical analysis at Malviya Bridge demonstrates that DO can remain high ($7.30\text{ mg/L}$) due to physical channel reaeration while BOD simultaneously fails ($3.98\text{ mg/L}$) due to upstream organic sewage inflows.

---

### Experiment WQ-4: Physical Sensor Anomaly Detection (`water_quality_anomaly_detector_v1`)
- **Objective:** Provide robust, transparent real-time screening for IoT sensor malfunction, calibration drift, and sudden industrial pollution surges.
- **Model Architecture:** `sklearn.ensemble.IsolationForest` (100 estimators, contamination prior $= 0.08$).
- **Features:** `[ph, do_mg_l, turbidity_ntu, conductivity_us_cm]` scaled via `StandardScaler`.
- **Training Baseline:** 129 physical-chemical observations from Ganga mainstem stations (Assi Ghat & Malviya Bridge).
- **Validation Datasets:**
  - In-Distribution: 129 Ganga baseline samples.
  - Out-of-Distribution: 48 severe urban wastewater samples from Varuna River before confluence.
- **Empirical Results:**
  - Baseline Ganga Anomaly Rate: **$8.5\%$** (matches $0.08$ prior).
  - Out-of-Distribution Anomaly Recall on Varuna Sewage: **$27.1\%$**.
- **Outcome: ACCEPTED (EXPERIMENTAL STATUS).**
- **Registry Artifacts:** `backend/ml/models/water_quality_anomaly_detector_v1.pkl` and `water_quality_scaler_v1.pkl`.

---

## 3. Flood Risk & River Stage Forecasting Experiments

### Experiment FL-1: Rainfall-Heuristic Binary Flood Classifier (Legacy Prototype)
- **Model Architecture:** `RandomForestClassifier` (100 trees), `StandardScaler` (6 features).
- **Features:** `[water_level, discharge, rain_varanasi, rain_upstream, temperature, humidity]`
- **Target:** `flood_label` (1 if rainfall $> 40\text{ mm}$ or discharge $> 8000$ or water level $> 67.5\text{ m}$).
- **Split Method:** Shuffled 80/20 train/test split on 1,095 consecutive daily records (2018–2020).
- **Reported Metrics:** Accuracy $99.54\%$, ROC-AUC $1.00$.
- **Outcome: REJECTED & CLASSIFIED INVALID.**
- **Diagnostic Root Cause:** 
  1. **Temporal Leakage:** Shuffling sequential daily records allowed the model to train on day $t$ and test on days $t-1$ and $t+1$, memorizing autocorrelated conditions.
  2. **Defective Target:** The river water level in the dataset ranged from $64.94\text{ m}$ to $69.63\text{ m}$. The official CWC Warning Stage at Varanasi is **$70.26\text{ m}$**. The river **never once flooded**, yet 683 days ($62.4\%$) were labelled as floods based on normal monsoon baseflows.

---

### Experiment FL-2: Supervised Warning/Danger Flood Event Classifier
- **Objective:** Train a binary classifier to predict when the Ganga River will exceed the CWC Warning Stage ($70.26\text{ m}$) or Danger Stage ($71.26\text{ m}$).
- **Dataset:** 1,095 daily gauge observations (2018–2020).
- **Ground Truth Events:** $\max(\text{water\_level}) = 69.63\text{ m}$. Events $\ge 70.26\text{ m} = \mathbf{0}$.
- **Outcome: FORMALLY DEFERRED (ZERO POSITIVE CASES).**
- **Scientific Reason:** In the 2018–2020 dataset, the river never reached warning stage. A supervised classifier cannot be trained with 0 positive instances without hallucinating decision boundaries.
- **Adopted Solution:** Statutory flood alerts remain strictly bound to deterministic gauge thresholds in `backend/services/alert_service.py`.

---

### Experiment FL-3: Continuous 1-Day-Ahead River Stage Regressor (`flood_stage_forecaster_v1`)
- **Objective:** Forecast tomorrow's river stage in metres MSL: $y_t = \text{water\_level}_{t+1}$.
- **Features (17 Causal Features at Time $t$):**
  - Current & lagged stages: `stage_t`, `stage_lag1`, `stage_lag2`
  - Momentum: `stage_delta_1d`, `stage_delta_2d`
  - Rolling windows: `rolling_mean_3d`, `rolling_mean_7d`, `rolling_max_7d`
  - Cumulative rainfall: `rain_local_t`, `rain_local_3d_sum`, `rain_upstream_t`, `rain_upstream_3d_sum`
  - Hydraulics & Meteorology: `discharge_t`, `temp_t`, `humidity_t`
  - Seasonality: `season_sin`, `season_cos`
  - **Zero future leakage.**
- **Strict Temporal Split:**
  - Training: 2018-01-07 to 2019-12-31 ($724\text{ days}$)
  - Held-out Test: 2020-01-01 to 2020-12-29 ($364\text{ days}$)
  - High-Water Test Days ($\ge 67.5\text{ m}$): $176\text{ days } (48.4\%)$

#### Benchmark Comparison on Held-Out Test Year 2020:

| Model Architecture | Overall MAE ($m$) | Overall RMSE ($m$) | Bias ($m$) | $R^2$ Score | High-Water MAE ($m$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Persistence Baseline ($\hat{y}_{t+1} = y_t$)** | $1.0635$ | $1.3272$ | $-0.0040$ | $-0.9389$ | $1.0606$ |
| **Rolling 3-Day Mean Baseline** | $0.9114$ | $1.1249$ | $-0.0036$ | $-0.3930$ | $0.8952$ |
| **Ridge Regression ($\alpha=10.0$)** | **$0.7882$** | **$0.9719$** | $+0.0119$ | $-0.0399$ | **$0.8003$** |
| **Random Forest Regressor** | **$0.7970$** | **$0.9809$** | $+0.0237$ | $-0.0591$ | **$0.8036$** |
| **HistGradientBoosting Regressor** | $0.8330$ | $1.0360$ | $+0.0545$ | $-0.1815$ | $0.8206$ |

- **Outcome: ACCEPTED (EXPERIMENTAL STATUS).**
- **Analysis:**
  - Both Ridge Regression ($0.7882\text{ m}$) and Random Forest ($0.7970\text{ m}$) beat the Persistence Baseline ($1.0635\text{ m}$) by **$25.1\% - 25.9\%$**.
  - During high-water stages ($\ge 67.5\text{ m}$), Random Forest predicts rising and falling hydrograph limbs with an MAE of $0.8036\text{ m}$.
  - The model is serialized as `backend/ml/models/flood_stage_forecaster_v1.pkl` with explicit metadata stating it is an experimental advisory forecast.

---

## 4. Summary Matrix of All Experiments

| Experiment ID | Domain | Intended Task | Outcome | Primary Justification | Production Deployment |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **WQ-1** | Water Quality | Potability Classification | **REJECTED** | Disjoint uniform synthetic data; false 100% accuracy | None |
| **WQ-2** | Water Quality | Statutory Class B Binary ML | **DEFERRED** | Insufficient data; 0 positive instances in real records | Deterministic Evaluator |
| **WQ-3** | Water Quality | Real-time 5-day BOD Regression | **DEFERRED** | Physical-biological latency mismatch | Laboratory Testing |
| **WQ-4** | Water Quality | In-Situ Physical Anomaly Detection | **ACCEPTED** | Unsupervised screening on empirical baseline | `water_quality_anomaly_detector_v1` |
| **FL-1** | Flood Risk | Rainfall-Heuristic Binary Flood ML | **REJECTED** | Temporal leakage; river never crossed warning stage | None |
| **FL-2** | Flood Risk | Warning/Danger Event Classification | **DEFERRED** | 0 warning/danger events in historical dataset | Deterministic CWC Stage Engine |
| **FL-3** | Flood Risk | 1-Day-Ahead Stage Regression | **ACCEPTED** | Beats persistence by 25.1% on held-out 2020 test year | `flood_stage_forecaster_v1` |
