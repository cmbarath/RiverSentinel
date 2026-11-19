# PHASE 0 — MACHINE LEARNING MODEL AUDIT REPORT
**Project:** River Sentinel 2.0  
**Models Audited:** Flood Risk Classifier & Water Quality Potability Classifier  
**Audit Timestamp:** 2026-11-19T05:49:50+05:30  
**Auditor:** Senior Machine Learning & Hydrological Systems Engineer  

---

## 1. Executive Summary

Both machine-learning models in River Sentinel were inspected across their training scripts, datasets, feature engineering, validation methodologies, and active prediction endpoints.

### Summary of Verdicts:
1. **Flood Prediction Model (`flood_model.pkl`)**:
   - **Reported Accuracy**: 99.54% (ROC AUC: 1.0)
   - **Verdict**: **OVERFITTED / FLAWED VALIDATION (TEMPORAL DATA LEAKAGE)**.
   - The reported accuracy is an artifact of random stratified train/test splitting on time-series river hydrological data, combined with synthetic target assignment. In reality, northern India monsoon seasonality is violated in the training data, and the model cannot be considered deployment-ready for operational early warning.
2. **Water Quality Model (`water_quality_model.pkl`)**:
   - **Reported Accuracy**: 100.0% (ROC AUC: 1.0)
   - **Verdict**: **TRIVIAL THRESHOLD MEMORIZATION ON SYNTHETIC DATA**.
   - The dataset was 100% synthetically generated using non-overlapping uniform distributions. The model has not learned complex chemical water quality dynamics; it has merely memorized synthetic threshold cutoffs (e.g., Turbidity < 10 NTU, DO > 5 mg/L).
3. **Model Artifact Duplication**:
   - Three copies of the flood model exist in the repository (`backend/flood_model.pkl`, `backend/flood_model/model.pkl`, `backend/ml_models/flood/model.pkl`).
   - The module `backend/flood_predictor.py` and test script `backend/test_flood_api.py` are orphaned and expect an obsolete 12-feature schema rather than the active 6-feature pipeline.

---

## 2. Flood Prediction Model Audit

### 2.1 Model Specifications
- **Artifacts**: `backend/flood_model.pkl` (483 KB), `backend/flood_scaler.pkl` (1.09 KB)
- **Algorithm**: `RandomForestClassifier(n_estimators=200, max_depth=15, min_samples_split=5, min_samples_leaf=2, class_weight='balanced')`
- **Scikit-Learn Version**: 1.9.1
- **Metadata**: `backend/model_info.json`
- **Training Script**: `backend/train_flood_model.py`
- **Input Features (6 total)**:
  1. `water_level_varanasi` (meters)
  2. `discharge_cumec` ($\text{m}^3/\text{s}$)
  3. `rain_varanasi_mm` ($\text{mm}/\text{hr}$ / daily accumulation)
  4. `rain_upstream_avg_mm` ($\text{mm}/\text{hr}$ / daily accumulation)
  5. `temperature_c` ($^\circ\text{C}$)
  6. `humidity_pct` ($\%$)

### 2.2 Dataset Forensic Analysis
- **Data Source**: `backend/flood_model/flood_data_with_dynamic_labels.csv`
- **Shape**: 1,095 rows $\times$ 15 columns (corresponding to 3 consecutive years of daily records, from 2018-01-01 to 2020-12-30).
- **Target Variable**: `flood_label` ($0 = \text{No Flood}, 1 = \text{Flood}$).
- **Target Distribution**: Class 0: 821 (75.0%), Class 1: 274 (25.0%).

### 2.3 Critical Scientific & Methodological Defects
1. **Severe Temporal Data Leakage**:
   - In `train_flood_model.py` (lines 77–79):
     ```python
     X_train, X_test, y_train, y_test = train_test_split(
         X, y, test_size=0.2, random_state=42, stratify=y
     )
     ```
   - Random shuffling breaks the chronological continuity of daily river discharge and flood wave propagation. Day $t-1$ and day $t+1$ reside in the training set while day $t$ is evaluated in the test set. Because river levels exhibit high serial autocorrelation, the model easily achieves >99% test accuracy simply by interpolating adjacent days.
2. **Hydrological & Meteorological Inconsistencies**:
   - Inspection of row 0 (`01-01-2018`): `rain_varanasi_mm = 94.05 mm`, `water_level_varanasi = 67.71 m`, `flood_label = 1`.
   - In Varanasi, January is dry winter (average monthly rainfall $< 15\text{ mm}$). Monsoon floods occur exclusively between July and September. Having major flood events labelled in early January indicates that the rainfall and flood labels in this dataset were generated via heuristic formulas rather than verified Central Water Commission (CWC) or IMD gauge records.
3. **Unused / Constant Spatial Features in Source CSV**:
   - Columns `basin_area_pct`, `mean_elevation_m`, `mean_slope`, `basin_relief_m`, `flow_accumulation`, `twi`, `network_density` contain constant numbers with zero variance across all 1,095 rows, rendering them useless for single-station prediction.

---

## 3. Water Quality / Potability Model Audit

### 3.1 Model Specifications
- **Artifacts**: `backend/water_quality_model.pkl` (146 KB), `backend/water_quality_scaler.pkl` (975 bytes)
- **Algorithm**: `RandomForestClassifier(n_estimators=200, random_state=42)`
- **Scikit-Learn Version**: 1.9.1
- **Metadata**: `backend/water_quality_model_info.json`
- **Training Script**: `backend/train_water_quality_model.py`
- **Input Features (5 total)**:
  1. `ph`: Range 0–14 (dimensionless)
  2. `turbidity`: Nephelometric Turbidity Units (NTU)
  3. `temperature`: Water temperature ($^\circ\text{C}$)
  4. `ec`: Electrical Conductivity ($\mu\text{S}/\text{cm}$)
  5. `do`: Dissolved Oxygen ($\text{mg}/\text{L}$)

### 3.2 Dataset Forensic Analysis
- **Data Source**: Purely synthetic generation inside `train_water_quality_model.py` (lines 43–66).
- **Generation Logic**:
  ```python
  # Safe samples (Class 1, N=1200):
  turbidity_safe = np.random.uniform(0.5, 9.9, N_SAFE)    # NTU < 10
  ec_safe        = np.random.uniform(50.0, 499.9, N_SAFE) # µS/cm < 500
  do_safe        = np.random.uniform(5.1, 12.0, N_SAFE)   # mg/L > 5

  # Unsafe samples (Class 0, N=800):
  turbidity_unsafe = np.random.uniform(10.0, 500.0, N_UNSAFE) # NTU >= 10
  ec_unsafe        = np.random.uniform(500.0, 3000.0, N_UNSAFE) # µS/cm >= 500
  do_unsafe        = np.random.uniform(0.0, 4.9, N_UNSAFE)   # mg/L <= 4.9
  ```

### 3.3 Critical Scientific & Methodological Defects
1. **Zero-Overlap Artificial Distributions**:
   - Because safe and unsafe samples were created with completely disjoint bounds (`turbidity < 10` vs `turbidity >= 10`, `do > 5.0` vs `do <= 4.9`), there is zero boundary ambiguity.
   - Any machine-learning classifier (or a 2-line `if/else` statement) achieves **100.0% accuracy** on such data.
   - The model has not learned microbiological contamination, biological oxygen demand (BOD) correlations, heavy metal risks, or seasonal organic matter behavior.
2. **Conflating Drinking Water Potability with River Health**:
   - In natural river ecosystems, river water is almost never directly potable without treatment (Class C/D surface water by CPCB standards). Labelling river water as "Potable: 1" based purely on physical sensor thresholds is scientifically invalid and legally misleading for public citizens.
   - In Phase 1 stabilization, a prominent public disclaimer was added to `WaterQuality.tsx`. In Phase 8, this must transition to standard **CPCB Water Quality Index (WQI)** or Designated Best Use classification.

---

## 4. Orphaned & Duplicate ML Code Analysis

1. **`backend/flood_predictor.py`**:
   - Contains an older standalone `FloodPredictor` class.
   - References `backend/ml_models/flood/` (the older 1.2 MB unpruned model).
   - Attempts to calculate discharge using a simplified Manning equation.
   - **Status**: Not imported or executed by `backend/app.py`. Redundant code path.
2. **`backend/test_flood_api.py`**:
   - Sends a 12-feature JSON body containing GIS features (`mean_elevation_m`, `mean_slope`, `flow_accumulation`) to `/api/flood/predict`.
   - Fails because `/api/flood/predict` in `backend/app.py` expects the 6 active sensor features.
   - **Status**: Out of sync with active schema.
3. **Duplicate Pickles**:
   - `backend/flood_model.pkl` (Active, 483 KB)
   - `backend/flood_model/model.pkl` (Duplicate, 1.29 MB)
   - `backend/ml_models/flood/model.pkl` (Duplicate, 1.29 MB)
   - **Action**: Clean up obsolete duplicate pickle files in Phase 1 to keep repository size lean and eliminate ambiguity.

---

## 5. Machine Learning Rebuilding Roadmap (Phase 8 Plan)

To transition these models from academic demonstration artifacts to dependable environmental screening tools:

### Step 1: Real-World Hydrological Data Ingestion
- Acquire verified daily water level and discharge data for Varanasi (Ganga River) from official CWC bulletins or open hydrology archives.
- Implement a **chronological / rolling-origin split** (e.g., Train on 2018–2021, Validate on 2022, Test on 2023–2024). Zero random shuffling.

### Step 2: CPCB Water Quality Index (WQI) Classification
- Replace the binary "potable / unsafe" classification with the **Central Pollution Control Board (CPCB) Designated Best Use Criteria**:
  - Class A: Drinking water without conventional treatment after disinfection.
  - Class B: Outdoor bathing.
  - Class C: Drinking water with conventional treatment.
  - Class D: Propagation of wildlife and fisheries.
  - Class E: Irrigation, industrial cooling, and controlled waste disposal.
- Ground training labels in actual UP Pollution Control Board (UPPCB) lab reports or National Water Quality Monitoring Programme (NWMP) station records for Assi Ghat, Dashashwamedh, and Rajghat.

### Step 3: Probabilistic Calibration & Performance Reporting
- Calibrate model probabilities using Platt scaling or isotonic regression.
- Report Precision, Recall, F1, PR-AUC, and class-wise false negative rates rather than inflated raw accuracy scores.
