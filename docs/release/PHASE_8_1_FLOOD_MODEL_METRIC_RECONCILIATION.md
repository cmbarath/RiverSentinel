# Phase 8.1A: Flood Model Metric Reconciliation Report
## Investigation, Root Cause Analysis & Governance Verification for Hydrological Forecaster

**Milestone:** Phase 8.1A — Flood Model Metric Discrepancy  
**Target Geography:** Ganga River, Varanasi, Uttar Pradesh, India  
**Date:** November 19, 2026  
**Auditor:** Antigravity Data Science & AI Safety Team  

---

## 1. Executive Summary

A discrepancy was identified between the model governance metrics established in Phase 6.1 and those reported in Phase 8 documentation:
- **Phase 6.1 Benchmark Record:** Ridge Regression ($\alpha=10.0$), Test MAE: **0.7882 metres**, RMSE: **0.9719 metres**, $R^2$: **-0.0399**.
- **Phase 8 Documentation Claim:** Ridge Regressor ($\alpha=100.0$), Test MAE: **0.37 metres**.

An empirical investigation was conducted to determine the provenance of the Phase 8 figures, verify the serialized model artifact hashes, reproduce model training, and formally reconcile all documentation and governance artifacts.

### Key Finding:
The active, serialized model artifact in `backend/ml/models/flood_stage_forecaster_v1.pkl` has **never changed since Phase 6.1**. Its internal hyperparameter is $\alpha=10.0$, and its true held-out test MAE is **0.7882 metres**. The `0.37` figure reported in Phase 8 was a documentation transcription error (originating from `0.37s` in the Phase 7.1 disaster recovery manifest).

---

## 2. Artifact Hash & Parameter Verification

The serialized model artifact was inspected directly:

```python
import joblib, hashlib
path = 'backend/ml/models/flood_stage_forecaster_v1.pkl'
model = joblib.load(path)
# SHA-256 Hash: 4b550a876290894dcf79780c788dc43661c9e726a64fdd64265f9c02ab8ff4c1
# Model Type: sklearn.linear_model._ridge.Ridge
# Model Alpha: 10.0
# Coefficients (17 features): [-0.02918, 0.04754, 0.01045, -0.05371, -0.02907, ...]
# Intercept: 67.429019
```

The metadata JSON file (`backend/ml/models/flood_stage_forecaster_v1.json`) confirms:
- **Model Type:** `RidgeRegression (alpha=10.0)`
- **Training Period:** 2018-01-08 to 2019-12-30 (724 days)
- **Held-Out Test Period:** 2020-01-01 to 2020-12-29 (364 days)
- **Reported Metrics:**
  - `mae_m`: `0.7882`
  - `rmse_m`: `0.9719`
  - `r2`: `-0.0399`
  - `bias_m`: `+0.0119`
  - `med_ae_m`: `0.7073`

---

## 3. Empirical Reproduction & Sensitivity Analysis

To investigate whether $\alpha=100.0$ or any alternate split/target could produce an MAE of `0.37 m`, the dataset was re-evaluated under identical conditions using `backend/ml/flood/reassess_forecaster.py`:

### Experiment 1: Regularization Parameter Sensitivity (Held-out Test Year 2020)
| Regularization ($\alpha$) | Test MAE (m) | Test RMSE (m) | Test $R^2$ | Train MAE (m) | Train $R^2$ |
|---|---|---|---|---|---|
| $\alpha = 0.1$ | 0.7891 | 0.9737 | -0.0440 | 0.7209 | 0.0289 |
| $\alpha = 1.0$ | 0.7890 | 0.9735 | -0.0435 | 0.7209 | 0.0289 |
| **$\alpha = 10.0$ (Active)** | **0.7882** | **0.9719** | **-0.0399** | **0.7214** | **0.0286** |
| $\alpha = 50.0$ | 0.7867 | 0.9681 | -0.0319 | 0.7234 | 0.0270 |
| $\alpha = 100.0$ | 0.7859 | 0.9658 | -0.0269 | 0.7252 | 0.0253 |
| $\alpha = 500.0$ | 0.7836 | 0.9598 | -0.0142 | 0.7301 | 0.0182 |
| $\alpha = 1000.0$ | 0.7831 | 0.9577 | -0.0098 | 0.7322 | 0.0140 |

*Result:* Testing $\alpha=100.0$ yields a test MAE of `0.7859 m`, within 2 mm of $\alpha=10.0$. Neither parameter produces `0.37 m`.

### Experiment 2: Target Delta Formulation ($y_{t+1} - y_t$)
Testing whether the target was formulated as 24-hour rate of change:
- $\alpha=10.0$: Test MAE = `0.7883 m`
- $\alpha=100.0$: Test MAE = `0.7903 m`

### Experiment 3: Random Train/Test Splits
Evaluating whether a randomized 80/20 train/test split yielded `0.37 m`:
- `random_state=42`, $\alpha=10.0$: MAE = `0.7609 m`
- `random_state=0`, $\alpha=10.0$: MAE = `0.7209 m`
- `random_state=1`, $\alpha=10.0$: MAE = `0.7127 m`

*Result:* Even random splits on autocorrelated time-series fail to achieve `0.37 m`.

---

## 4. Root Cause Determination

The investigation verified that:
1. **No new training run occurred during Phase 8.** The binary artifact was untouched.
2. **Provenance of `0.37`:** In `docs/operations/PHASE_7_1_RTO_RPO_RESULTS.md`, the operation `Write SQL & generate cryptographic manifest` completed in `0.37s`. During Phase 8 documentation drafting, the number `0.37` was inadvertently transposed into prose as the Ridge Forecaster MAE.
3. **Provenance of `alpha=100.0`:** The Phase 6.1 code explored multiple regularization penalties; $\alpha=100.0$ was mentioned in exploratory notes, but $\alpha=10.0$ was the chosen model saved in `flood_stage_forecaster_v1.pkl`.

---

## 5. Corrective Action & Governance Closure

1. **Documentation Alignment:** Updated `README.md` and `docs/release/PHASE_8_MODEL_GOVERNANCE.md` to restore the true, verified figures:
   - **Algorithm:** `Ridge Regression (alpha=10.0)`
   - **Test MAE:** **`0.7882 metres`**
   - **Test RMSE:** **`0.9719 metres`**
   - **Test $R^2$:** **`-0.0399`**
2. **Operational Classification:** Reaffirmed that the model remains strictly **`research_only`**.
3. **Data Provenance:** The underlying dataset remains formally designated as **semi-synthetic** (containing synthetic dry-month rainfall injections).
4. **Emergency Suppression:** Automated alert triggers from this model remain programmatically suppressed in `routes/predictions.py`.

**Reconciliation Status:** FULLY RESOLVED & RECONCILED
