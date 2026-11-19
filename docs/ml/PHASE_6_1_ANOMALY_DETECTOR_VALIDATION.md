# River Sentinel 2.0 — Phase 6.1: Water Quality Anomaly Detector Forensic Re-Evaluation

**Project:** River Sentinel 2.0  
**Target River / Location:** Ganga River, Varanasi, Uttar Pradesh, India  
**Date:** 2026-11-19  
**Status:** Forensic Validation, Root Cause Analysis & Governance Constraints  
**Branch:** `river-sentinel/phase-1-stabilization`  

---

## 1. Executive Summary & Governance Mandate

Phase 6.1 re-evaluated the `water_quality_anomaly_detector_v1` (`sklearn.ensemble.IsolationForest`) to determine why the model achieved only **$27.1\%$ recall** on severe wastewater samples and whether it is safe for operational alerting.

### Core Governance Determinations:
1. **Low Recall Confirmed:** Across 48 verified ground-truth severe wastewater samples from Varuna Before Confluence, the model correctly identified only **13 samples ($27.1\%$)**, missing 35 samples ($72.9\%$).
2. **Diagnostic Root Cause Identified:** The failure is driven by **parameter subspace blindness**. Physical IoT probes measure pH, DO, Turbidity, and Conductivity, but cannot measure dissolved organic matter (BOD) or bacteriological pathogens (Total Coliform). In 73% of severe wastewater samples, physical properties remained within overlapping Ganga bounds while biological contamination was extreme.
3. **Operational Status:** Retained strictly as **`experimental`**.
4. **Alert Engine Quarantine:** The anomaly detector is **strictly prohibited from triggering automatic public pollution alerts or emergency SMS dispatch**. The deterministic CPCB Class B standards engine remains the authoritative operational mechanism.

---

## 2. Re-Evaluation Methodology & Ground Truth Definition

### 2.1 Datasets Analyzed
- **Training Baseline (Ganga Mainstem):** 129 actual CPCB physical-chemical observations across 2018–2021:
  - `Ganga U/S Assi Ghat`: 64 samples
  - `Ganga D/S Malviya Bridge`: 65 samples
- **Evaluation Set (Varuna Confluence):** 48 actual CPCB observations from `River Varuna B/C with River Ganga at Varanasi`.
- **Features Used:** `['ph', 'do_mg_l', 'turbidity_ntu', 'conductivity_us_cm']` scaled via `StandardScaler`.

### 2.2 Ground-Truth Definition of Severe Wastewater
In environmental chemistry, river water is categorized as severe untreated municipal sewage/wastewater if it meets any of the following criteria:
$$\text{BOD} > 10.0\text{ mg/L} \quad \lor \quad \text{Total Coliform} > 50,000\text{ MPN/100mL} \quad \lor \quad \text{DO} < 4.0\text{ mg/L}$$

In the Varuna Confluence record:
- Mean BOD is **$20.57\text{ mg/L}$** (range: $6.8 - 64.0\text{ mg/L}$).
- Mean DO is **$3.29\text{ mg/L}$** (down to $0.50\text{ mg/L}$).
- Mean Total Coliform is **$79,250\text{ MPN/100mL}$** (up to $110,000\text{ MPN}$).
- **Result:** Exactly **48 out of 48 samples ($100\%$)** meet the severe wastewater definition.

---

## 3. Comprehensive Performance Metrics & Confusion Matrix

The model was evaluated by treating Ganga samples as normal baseline inliers ($y = 0$) and Varuna Confluence samples as severe anomalies ($y = 1$):

```
                       Wastewater Detection Confusion Matrix
                       
                                   Actual Baseline    Actual Severe Sewage
                                     (Ganga, n=129)      (Varuna, n=48)
      ┌───────────────────────────┬──────────────────┬────────────────────┐
      │ Predicted Inlier (Normal) │  TN = 118 (91.5%)│   FN = 35 (72.9%)  │
      ├───────────────────────────┼──────────────────┼────────────────────┤
      │ Predicted Anomaly (Alert) │  FP =  11 ( 8.5%)│   TP = 13 (27.1%)  │
      └───────────────────────────┴──────────────────┴────────────────────┘
```

### 3.1 Quantitative Metrics

| Metric | Empirical Score | Interpretation |
| :--- | :--- | :--- |
| **True Positives (TP)** | 13 | Correctly detected severe sewage inflows |
| **False Negatives (FN)** | 35 | Missed severe sewage inflows |
| **False Positives (FP)** | 11 | False alarms on normal Ganga baseline ($8.5\%$, matching $0.08$ prior) |
| **True Negatives (TN)** | 118 | Correct inliers on normal Ganga baseline ($91.5\%$) |
| **Precision** | **$0.5417$** | $54.2\%$ of triggered anomalies represent true severe sewage |
| **Recall (Sensitivity)** | **$0.2708$** | **$27.1\%$** of severe sewage events detected |
| **F1-Score** | **$0.3611$** | Low harmonic balance due to high false negative rate |

### 3.2 Anomaly Score Distributions
`IsolationForest` anomaly scores (lower / more negative indicates higher abnormality):
- **Ganga Baseline ($n=129$):** $\text{Mean} = -0.4127$, $\text{Std} = 0.0926$, Range: $[-0.6859, -0.3212]$
- **Varuna Confluence ($n=48$):** $\text{Mean} = -0.5660$, $\text{Std} = 0.0949$, Range: $[-0.7485, -0.4442]$
- While the mean score shifts negative for Varuna (proving the model has some sensitivity to oxygen depression), the distribution overlap between $-0.44$ and $-0.55$ causes the majority of sewage samples to fall inside the normal decision threshold.

---

## 4. Diagnostic Root Cause of Low Recall ($27.1\%$)

Comparing the 13 detected Varuna samples against the 35 missed Varuna samples reveals the exact chemical cause:

| Subgroup | Sample Count | Mean DO | Mean pH | Mean Conductivity | Mean BOD | Mean Total Coliform |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Detected Anomalies** | 13 | **$1.85\text{ mg/L}$** (Anoxic) | $7.58$ | $630.6\text{ }\mu\text{S/cm}$ | $24.8\text{ mg/L}$ | $88,000\text{ MPN}$ |
| **Missed Anomalies** | 35 | **$3.82\text{ mg/L}$** | $7.80$ | $512.0\text{ }\mu\text{S/cm}$ | **$19.0\text{ mg/L}$** | **$76,000\text{ MPN}$** |

### The Root Cause: Parameter Subspace Blindness
1. In the 13 detected samples, organic waste was so overwhelming that Dissolved Oxygen collapsed below $2.0\text{ mg/L}$, creating an extreme physical outlier that `IsolationForest` captured.
2. In the 35 missed samples, surface reaeration kept Dissolved Oxygen between $3.0$ and $4.5\text{ mg/L}$, and water pH remained neutral ($7.6 - 8.0$).
3. Because the IoT probe vector contains **only physical parameters** (`[ph, do, turbidity, ec]`), the vector appeared physically normal, even though biological BOD was $19.0\text{ mg/L}$ ($> 6\times$ statutory limit) and Coliform was $76,000\text{ MPN}$ ($> 150\times$ statutory limit).
4. **Scientific Conclusion:** Low-cost in-situ IoT probes cannot detect biological sewage contamination without severe hypoxia. Physical-only anomaly models must never be trusted for statutory sanitary protection.

---

## 5. Domain Generalization Experiments

### Experiment A: Within-Ganga Temporal Holdout
- **Training Set:** Ganga observations 2018–2019 ($n=48$)
- **Held-Out Test Set:** Ganga observations 2020–2021 ($n=81$)
- **Result:** Test Anomaly Rate was **$43.2\%$**.
- **Cause:** Nationwide industrial lockdowns during 2020 drastically altered river conductivity and clarity, causing a legitimate environmental distribution shift that an unsupervised model flags as anomalous.

### Experiment B: Leave-One-Station-Out (Assi Ghat vs Malviya Bridge)
- **Training Set:** Upstream Ganga at Assi Ghat ($n=64$)
- **Test Set:** Downstream Ganga at Malviya Bridge ($n=65$)
- **Result:** $12.3\%$ of downstream Malviya Bridge samples were flagged as anomalies relative to the upstream baseline, successfully reflecting the downstream impact of urban ghats and nallah outfalls.

---

## 6. Operational Governance & Application Behavior

To prevent experimental models from misleading citizens or municipal authorities:

1. **Status Tag:** Classified as **`experimental`** in `backend/ml/models/water_quality_anomaly_detector_v1.json`.
2. **API Isolation:** In `GET /api/water-quality/predict`, the anomaly output is isolated under `physical_screening`:
   ```json
   {
     "physical_screening": {
       "anomaly_status": "NORMAL",
       "screening_status": "experimental_screening_only",
       "alert_eligible": false,
       "screening_note": "Experimental physical anomaly score. Never represents a confirmed pollution event or biological contamination."
     }
   }
   ```
3. **Alert Prohibition:** Automatic alert engine rules reject anomaly scores. No SMS, WhatsApp, or public dashboard warnings can be generated exclusively by this model.
4. **Primary Authority:** The deterministic standards engine (`cpcb_class_b_evaluator_v1`) remains the sole authority for water quality assessment.
