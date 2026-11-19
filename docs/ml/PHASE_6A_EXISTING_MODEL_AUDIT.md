# River Sentinel 2.0 — Phase 6A: Existing Machine Learning Model Audit

**Project:** River Sentinel 2.0  
**Target River / Location:** Ganga River, Varanasi, Uttar Pradesh, India  
**Audit Date:** 2026-11-19  
**Status:** Complete Diagnostic Forensic Audit  
**Constraint Compliance:** No existing model artifact or scaler was retrained, overwritten, or replaced.

---

## 1. Executive Summary

This audit performs an exhaustive forensic examination of all machine learning artifacts, training scripts, feature pipelines, and inference routes currently present in the River Sentinel 2.0 codebase.

Two distinct ML pipelines were audited:
1. **Flood Risk Prediction Model** (`backend/flood_model.pkl` and `backend/flood_model/model.pkl`)
2. **Water Quality Potability Model** (`backend/water_quality_model.pkl`)

### Key Diagnostic Findings:
- **Flood Model (False High Accuracy via Temporal Leakage):** The reported 99.54% test accuracy and 1.00 ROC-AUC are statistical artifacts resulting from **random temporal data leakage**. The training pipeline shuffled consecutive daily time-series records (2018–2020) using `train_test_split(..., shuffle=True)`, allowing the model to train on day $t$ and test on days $t-1$ and $t+1$.
- **Flood Target Construction Defect:** The training dataset water levels range strictly between **$64.94\text{ m}$ and $69.63\text{ m}$**. In Varanasi (Rajghat / Malviya Bridge), the official Central Water Commission (CWC) **Warning Stage is $70.26\text{ m}$** and the **Danger Stage is $71.26\text{ m}$**. The river never once reached even the warning stage in the dataset, yet **$683 \text{ out of } 1,095\text{ records (62.4\%)}$** were labelled as `flood_label = 1` based on an artificial rainfall-discharge heuristic.
- **Water Quality Model (Synthetic Artifact):** The 100% reported accuracy and 1.00 ROC-AUC are entirely artificial. The training dataset consists of 2,000 synthetic rows generated from **mutually exclusive, non-overlapping uniform intervals** (e.g., Turbidity safe: $[0.5, 9.9]\text{ NTU}$, unsafe: $[10.0, 500.0]\text{ NTU}$). Any single decision tree split separates the classes perfectly with zero generalization power.
- **Regulatory Target Conflation:** The water quality model purports to predict "potable" drinking water suitability, conflating Bureau of Indian Standards drinking water norms (BIS IS 10500:2012) with raw river water intended for outdoor bathing (CPCB Designated Best Use Class B). Raw river surface water is never potable without conventional treatment and disinfection.

---

## 2. Complete Inventory & Cryptographic Checksums of Existing Artifacts

Every artifact in `backend/` was hashed using SHA-256 and verified for byte size, serialized library versions, and architectural topology.

| Artifact Path | SHA-256 Checksum | Size (Bytes) | Serialized Framework / Class |
| :--- | :--- | :--- | :--- |
| `backend/flood_model.pkl` | `cc9d2b930bf457e20646f0fbafd9e98aecbcc7af6917744a1538b16d0e9c0f0a` | 483,881 | scikit-learn v1.5.0, `RandomForestClassifier` (100 estimators) |
| `backend/flood_scaler.pkl` | `7d225b73471171647cf195c061bd5eaa42dfecb5b964271a17763e592295c695` | 1,095 | scikit-learn v1.5.0, `StandardScaler` (6 features) |
| `backend/water_quality_model.pkl` | `a8b927575aea9de2d3b5288999ad9d3acf39f9183acc1e1ce4195a658accdfab` | 146,633 | scikit-learn v1.5.0, `RandomForestClassifier` (100 estimators) |
| `backend/water_quality_scaler.pkl` | `aa855b948ade01ad7c5695b40228673eedcd30e41ee16351bcc758f51101a11c` | 975 | scikit-learn v1.5.0, `StandardScaler` (5 features) |
| `backend/flood_model/model.pkl` | `07db94e308d385942ef8601b8337658b17fe1bac47e55b469567e796ec12e46c` | 1,295,497 | scikit-learn v1.4.2, `RandomForestClassifier` (100 estimators, 12 features) |
| `backend/flood_model/scaler.pkl` | `d5f5894986a872ae2a5f7207ef0de255c67cf45471e70a1f4d786a2011283c99` | 1,319 | scikit-learn v1.4.2, `StandardScaler` (12 features) |
| `backend/flood_model/features.pkl` | `6efa4c9d0ff7edc9e2dbdbc0a9ddb98fa099d4adfe146b7ddbd936d899867daa` | 221 | Python list (12 feature names) |
| `backend/flood_model/flood_data_with_dynamic_labels.csv` | `9cf91c9a0b7fda8b569550e2192b8f726c6d9d0ae2956d8cc365c6e45633d1c4` | 155,117 | CSV dataset, 1,095 rows x 15 columns |

---

## 3. Deep Forensic Audit: Flood Risk Forecasting Pipeline

### 3.1 Model Architecture & Parameters
- **Serialized File:** `backend/flood_model.pkl`
- **Class:** `sklearn.ensemble.RandomForestClassifier`
- **Estimators (`n_estimators`):** 100 trees
- **Max Depth:** `None` (trees grown until leaves are pure)
- **Min Samples Split:** 2
- **Class Weights:** `None`
- **Trained Feature Count:** 6 features
- **Features (`backend/flood_scaler.pkl`):**
  1. `water_level`
  2. `discharge`
  3. `rain_varanasi`
  4. `rain_upstream`
  5. `temperature`
  6. `humidity`

### 3.2 Dataset Provenance & Target Construction
The model was trained by `backend/train_flood_model.py` using `backend/flood_model/flood_data_with_dynamic_labels.csv`.
- **Row Count:** 1,095 consecutive daily records spanning 2018-01-01 to 2020-12-30.
- **Reported Test Metrics:** Accuracy 99.54%, Precision 1.00, Recall 0.99, F1 1.00, ROC-AUC 1.00.

#### Critical Defect 1: Temporal Data Leakage via Shuffled Split
The training script executes:
```python
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y, test_size=0.2, random_state=42, stratify=y
)
```
- In hydrological time series, consecutive daily observations have strong autocorrelation ($\text{lag-1 autocorrelation} > 0.95$).
- Randomly shuffling 1,095 consecutive days places day $t$ in the training set and days $t-1$ and $t+1$ in the test set.
- The decision trees simply memorize local temporal neighborhoods. In a true out-of-time walk-forward or temporal split (e.g. train 2018–2019, test 2020), performance collapses.

#### Critical Defect 2: Target Construction vs Hydrological Reality
- In the CSV dataset, water levels are strictly within:
  $$\min(\text{water\_level}) = 64.94\text{ m}, \quad \max(\text{water\_level}) = 69.63\text{ m}, \quad \text{mean} = 67.43\text{ m}$$
- Official Central Water Commission (CWC) stages for Ganga at Varanasi (Malviya Bridge / Rajghat station):
  - **Zero Gauge:** $57.91\text{ m}$ above MSL
  - **Warning Stage:** $70.26\text{ m}$ above MSL
  - **Danger Stage:** $71.26\text{ m}$ above MSL
  - **High Flood Level (HFL):** $73.90\text{ m}$ (recorded 1978-09-09)
- **The actual river level in this dataset NEVER reached $70.26\text{ m}$ (Warning Stage)**. The maximum recorded water level was $69.63\text{ m}$, which is $0.63\text{ m}$ below the warning threshold.
- Despite no actual hydrological flood occurring in the record, **$683 \text{ out of } 1,095\text{ days (62.4\%)}$** were labelled as `flood_label = 1`.
- The target was synthetically generated in `generate_dataset.py` using an arbitrary compound formula:
  $$\text{synthetic\_flood} = (\text{rain\_varanasi} > 40) \lor (\text{discharge} > 8000) \lor (\text{water\_level} > 67.5)$$
- Labeling days with $67.5\text{ m}$ water level as "floods" falsely categorizes normal monsoon baseflows as emergency flooding.

#### Critical Defect 3: Constant Features in 12-Feature Model Variant
In `backend/flood_model/model.pkl` (the legacy 12-feature model), 6 of the 12 features are completely invariant with zero standard deviation:
1. `mean_elevation_m` ($= 76.0$)
2. `mean_slope` ($= 1.2$)
3. `basin_relief_m` ($= 24.0$)
4. `flow_accumulation` ($= 14500.0$)
5. `twi` ($= 8.4$)
6. `network_density` ($= 0.65$)
These columns provide zero predictive variance and serve only to bloat model topology.

---

## 4. Deep Forensic Audit: Water Quality Prediction Pipeline

### 4.1 Model Architecture & Parameters
- **Serialized File:** `backend/water_quality_model.pkl`
- **Class:** `sklearn.ensemble.RandomForestClassifier`
- **Estimators (`n_estimators`):** 100 trees
- **Max Depth:** `None`
- **Trained Feature Count:** 5 features
- **Features (`backend/water_quality_scaler.pkl`):**
  1. `ph`
  2. `turbidity`
  3. `temperature`
  4. `ec`
  5. `do`

### 4.2 Synthetic Data Generation & Artificial Separation
The model was trained by `backend/train_water_quality_model.py`.
- **Total Samples:** 2,000 synthetic rows (1,200 "safe" / potable, 800 "unsafe" / non-potable).
- **Reported Test Metrics:** Accuracy 100.00%, Precision 1.00, Recall 1.00, F1 1.00, ROC-AUC 1.00.

#### Critical Defect 1: Disjoint Parameter Distributions
The training script generates synthetic data using `np.random.uniform` over non-overlapping intervals:

| Feature | "Safe" Class (Potable = 1) | "Unsafe" Class (Potable = 0) | Gap Between Distributions |
| :--- | :--- | :--- | :--- |
| **pH** | $[6.5, 8.5]$ | $[0.0, 6.4] \cup [8.6, 14.0]$ | $0.1\text{ pH units}$ |
| **Turbidity (NTU)** | $[0.5, 9.9]$ | $[10.0, 500.0]$ | $0.1\text{ NTU}$ |
| **EC ($\mu\text{S/cm}$)** | $[50.0, 499.9]$ | $[500.0, 3000.0]$ | $0.1\text{ }\mu\text{S/cm}$ |
| **DO (mg/L)** | $[5.1, 12.0]$ | $[0.0, 4.9]$ | $0.2\text{ mg/L}$ |
| **Temperature ($^\circ\text{C}$)** | $[15.0, 30.0]$ | $[5.0, 45.0]$ | Overlapping |

Because safe and unsafe intervals are strictly disjoint, a single tree split on `turbidity <= 9.95` or `do >= 5.0` achieves 100% training and test accuracy. The model did not learn environmental patterns; it merely memorized hardcoded rectangular bounds.

#### Critical Defect 2: Statutory and Scientific Misalignment
- The script and UI label `potable = 1` as "Water is safe for direct consumption with basic filtration."
- In Indian regulatory law:
  - **BIS IS 10500:2012** regulates drinking water (e.g. Turbidity $< 1\text{ NTU}$, Total Coliform = 0).
  - **CPCB Designated Best Use Class B** regulates outdoor bathing (pH 6.5–8.5, DO $\ge 5\text{ mg/L}$, BOD $\le 3\text{ mg/L}$, Total Coliform $\le 500\text{ MPN/100mL}$).
- The model ignores BOD and Coliform completely (the primary biological contaminants of river water) and misleads users by classifying untreated river water as "potable".

---

## 5. Inference Contract Analysis (`backend/routes/predictions.py`)

The API routes in `backend/routes/predictions.py` interface directly with the serialized models:

### 5.1 `/api/flood/predict`
- **Method:** `GET`, `POST`
- **Input Parsing:**
  Extracts `water_level`, `discharge`, `rain_varanasi`, `rain_upstream`, `temperature`, `humidity` from latest Supabase reading or JSON POST overrides.
- **Discharge Fallback:**
  If discharge is missing, computes an uncalibrated empirical formula:
  $$\text{discharge} = 25.0 \times 50.0 \times \max(0, \text{water\_level} - 58.0)^{1.3}$$
- **Feature Vector:**
  Passed as a 2D array of 6 floats in exact scaler order:
  `[[water_level, discharge, rain_varanasi, rain_upstream, temperature, humidity]]`
- **Audit Persistence:** Successfully logs predictions into the Supabase table `flood_predictions`.
- **Contract Integrity:** Feature order matches `backend/flood_scaler.pkl`. However, because the underlying model was trained on an invalid target and leaky splits, the returned probability is statistically unreliable.

### 5.2 `/api/water-quality/predict`
- **Method:** `GET`, `POST`
- **Input Parsing:**
  Extracts `ph`, `turbidity`, `temperature`, `ec`, `do` from latest reading or JSON POST overrides.
- **Feature Vector:**
  Passed as a 2D array of 5 floats in exact scaler order:
  `[[ph, turbidity, temperature, ec, do]]`
- **Heuristic Blending:**
  The route calculates a separate rule-based score ($100 - \sum \text{penalties}$) alongside the model prediction. The rule-based penalties for pH, DO, and Turbidity often conflict with the binary ML output.
- **Contract Integrity:** Feature order matches `backend/water_quality_scaler.pkl`.

---

## 6. Audit Verdict and Architectural Recommendations

1. **Flood Model Verdict: FAILED SCIENTIFIC INTEGRITY**
   - Must NOT be used for operational safety-critical flood warnings.
   - The prompt mandate requires: keep flood ML classification experimental; do not fabricate fake alerts; anchor statutory river monitoring to official CWC hydrological gauge thresholds ($70.26\text{ m}$ Warning, $71.26\text{ m}$ Danger).
2. **Water Quality Model Verdict: FAILED SCIENTIFIC INTEGRITY**
   - The synthetic model must be replaced or re-framed as an operational screening tool.
   - Real CPCB water quality observations should be used for empirical baseline calibration.
   - Clarify in all outputs that the model evaluates surface water quality / bathing suitability (CPCB Class B), NEVER potability or direct drinking safety.
