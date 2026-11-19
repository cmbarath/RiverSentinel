# River Sentinel 2.0 — Phase 6A: Data Quality & Target Feasibility Report

**Project:** River Sentinel 2.0  
**Target River / Location:** Ganga River, Varanasi, Uttar Pradesh, India  
**Report Date:** 2026-11-19  
**Status:** Quality Assessment, Statistical Profiling & Feasibility Analysis  

---

## 1. Executive Summary

This report evaluates the quality, completeness, sampling frequency, and target feasibility of available environmental datasets for machine learning model development in River Sentinel 2.0.

### Core Feasibility Conclusions:
1. **Water Quality Domain:**
   - Official CPCB water quality data from NWDP provides empirical ground truth for Varanasi (Assi Ghat and Malviya Bridge / Rajghat).
   - **Sampling Frequency Mismatch:** CPCB data represents manual laboratory grab samples taken **once or twice per month**, yielding approximately 65 records per station across 2020–2021. This contrasts with IoT stations which stream physical telemetry **hourly or minutely**.
   - **Parameter Measurability Mismatch:** Biological indicators that govern regulatory compliance (CPCB Class B)—namely **BOD (5-day laboratory incubation)** and **Total Coliform (bacteriological culture)**—cannot be measured directly by low-cost in-situ IoT probes.
   - **Recommendation:** Reframe the water quality model from "potability prediction" to an **Operational Surface Water Quality Screening & Surrogate Model** calibrated against CPCB Class B standards, while maintaining deterministic alert rules for directly measured physical parameters (pH, DO, Turbidity, EC).
2. **Flood Risk Domain:**
   - **Data Insufficiency for Pure Local ML:** Ganga basin hourly telemetry is absent from open REST endpoints on NWDP.
   - The historical dataset (`flood_data_with_dynamic_labels.csv`) spans water levels between $64.94\text{ m}$ and $69.63\text{ m}$, never reaching the official CWC Warning Stage ($70.26\text{ m}$) or Danger Stage ($71.26\text{ m}$).
   - Machine learning models trained on heuristic labels cannot safely replace hydrological hydraulic modeling.
   - **Recommendation:** Formally classify the Random Forest flood prediction endpoint as **experimental and advisory**. Operational flood safety alerts must be strictly bound to official **Central Water Commission (CWC) gauge thresholds** ($70.26\text{ m}$ Warning, $71.26\text{ m}$ Danger).

---

## 2. Statistical Profiling of Official CPCB Varanasi Data (2020–2021)

From the downloaded official NWDP CPCB datasets, empirical records for the two primary Varanasi stations were extracted and analyzed:

### 2.1 Station 1: Ganga at Varanasi Upstream (`ASSIGHAT`)
*Location:* Southern entry of Ganga into Varanasi ($25.2917^\circ\text{N}, 83.0039^\circ\text{E}$). Baseline water quality before passing urban ghats.

| Parameter | Record Count | Min | Mean | Max | CPCB Class B Standard | Compliance Observation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **pH** | 64 | 7.45 | 8.27 | 8.60 | 6.5 – 8.5 | **98.4% Compliant** (mildly alkaline, typical for Ganga baseflow) |
| **Dissolved Oxygen (DO)** | 64 | 6.50 mg/L | 8.32 mg/L | 10.40 mg/L | $\ge 5.0\text{ mg/L}$ | **100% Compliant** (strong reaeration from open river channel) |
| **BOD (5-day, 20°C)** | 64 | 1.70 mg/L | 2.56 mg/L | 6.50 mg/L | $\le 3.0\text{ mg/L}$ | **84.4% Compliant** (occasional monsoon organic wash) |
| **Total Coliform** | 17 | 1,100 | 2,006 | 3,400 | $\le 500\text{ MPN/100mL}$ | **0% Compliant** (exceeds outdoor bathing standard by 2x to 7x) |
| **Turbidity** | 16 | 12.0 NTU | 71.4 NTU | 198.0 NTU | Operational screening | Highly seasonal (high silt in monsoon, low in winter) |
| **Electric Conductivity** | 16 | 242 $\mu\text{S/cm}$ | 411 $\mu\text{S/cm}$ | 512 $\mu\text{S/cm}$ | Screen $< 1500\text{ }\mu\text{S/cm}$ | **100% Compliant** with natural freshwater norms |

### 2.2 Station 2: Ganga at Varanasi Downstream (`MALVIYA BRIDGE / RAJGHAT`)
*Location:* Northern exit of Ganga from Varanasi ($25.3211^\circ\text{N}, 83.0317^\circ\text{E}$). Reflects cumulative pollution from city ghats, crematoria, and untreated nallah drains.

| Parameter | Record Count | Min | Mean | Max | CPCB Class B Standard | Compliance Observation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **pH** | 65 | 7.33 | 8.18 | 8.70 | 6.5 – 8.5 | **96.9% Compliant** |
| **Dissolved Oxygen (DO)** | 65 | 5.80 mg/L | 7.30 mg/L | 9.50 mg/L | $\ge 5.0\text{ mg/L}$ | **100% Compliant** (drops by $\sim 1.0\text{ mg/L}$ relative to Assi Ghat) |
| **BOD (5-day, 20°C)** | 65 | 3.30 mg/L | 3.98 mg/L | 5.80 mg/L | $\le 3.0\text{ mg/L}$ | **0% Compliant** (**Permanently fails** Class B standard due to city effluents!) |
| **Total Coliform** | 17 | 14,000 | 21,412 | 31,000 | $\le 500\text{ MPN/100mL}$ | **0% Compliant** (exceeds limit by **28x to 62x**!) |
| **Turbidity** | 16 | 16.0 NTU | 79.9 NTU | 212.0 NTU | Operational screening | Silt and suspended solids elevated downstream |
| **Electric Conductivity** | 16 | 254 $\mu\text{S/cm}$ | 435 $\mu\text{S/cm}$ | 546 $\mu\text{S/cm}$ | Screen $< 1500\text{ }\mu\text{S/cm}$ | Compliant with mineral freshwater bounds |

---

## 3. Data Quality Issues & Preprocessing Requirements

### 3.1 Water Quality Data Deficiencies
1. **Sparseness of Physical Observations (Turbidity and EC):**
   In CPCB datasets, complete biological and chemical samples were collected bi-weekly (64–65 rows), but turbidity and conductivity were recorded only 16 times per station over the 2-year period.
2. **Missing Sensor-to-Lab Mapping:**
   An IoT device measures:
   $$\{ \text{pH}, \text{Turbidity}, \text{Temperature}, \text{Conductivity}, \text{Dissolved Oxygen} \}$$
   It cannot measure BOD or Fecal/Total Coliform.
   The downstream data proves that **DO and pH can meet statutory Class B standards while BOD and Coliform simultaneously violate them completely** (as at Malviya Bridge, where mean DO is $7.3\text{ mg/L}$ [compliant] but mean BOD is $3.98\text{ mg/L}$ [violating] and Coliform is $21,412\text{ MPN/100mL}$ [violating]).
3. **Target Redefinition Requirement:**
   - **Old Target (Flawed):** "Potable" (safe to drink with basic filtration). Completely invalid for raw Ganga water.
   - **Correct Target:** **"CPCB Class B Outdoor Bathing Suitability"** or a multi-level **Water Quality Index (WQI)**.
   - For real-time IoT inference, provide an operational index based on measured parameters, clearly separating physical parameter screening from statutory biological laboratory tests.

### 3.2 Flood Prediction Data Deficiencies
1. **Hydrological Inundation Absence:**
   The training dataset contains no instance of river stage crossing the official Warning Stage ($70.26\text{ m}$) or Danger Stage ($71.26\text{ m}$).
2. **Discharge Estimation Sensitivity:**
   In `backend/routes/predictions.py`, if discharge is not provided, the route estimates:
   $$\text{discharge} = 25.0 \times 50.0 \times \max(0, \text{water\_level} - 58.0)^{1.3}$$
   This empirical rating curve is sensitive to small changes in water level:
   - At $67.5\text{ m}$: $\text{discharge} = 1250 \times (9.5)^{1.3} \approx 23,450\text{ cumec}$
   - Normal dry season discharge in Ganga at Varanasi is typically $1,000 - 3,000\text{ cumec}$; monsoon flood peak exceeds $15,000 - 25,000\text{ cumec}$. The formula overestimates baseflow discharge significantly.
3. **Temporal Split Mandate:**
   Any future evaluation of flood prediction models must use **temporal walk-forward splits** (e.g. Train on Years 1–2, Test on Year 3) rather than random shuffled splits to prevent false optimism.

---

## 4. Evaluation of Model Feasibility

| Pipeline | Intended Task | Feasibility with Available Data | Recommended Architectural Treatment |
| :--- | :--- | :--- | :--- |
| **Water Quality ML Model** | Predict bathing safety / Class B compliance from IoT sensor inputs | **FEASIBLE with Empirical Calibration** | Replace disjoint synthetic intervals with realistic empirical distributions derived from CPCB Varanasi monitoring. Predict CPCB Class B compliance or Water Quality Index (WQI). Never claim drinking water potability. |
| **Water Quality Heuristics** | Direct threshold alerts (pH, DO, Turbidity, EC) | **HIGHLY RELIABLE (Deterministic)** | Retain existing deterministic rules in `alert_service.py` based on CPCB Class B (pH 6.5–8.5, DO $\ge 5\text{ mg/L}$) and operational screening (Turbidity, EC). |
| **Flood ML Model** | Predict river flood inundation from local sensor telemetry | **EXPERIMENTAL ONLY** | Pure ML without upstream catchment gauge data cannot reliably predict Ganga floods. Retain model as experimental advisory; anchor all user-facing flood alerts to official CWC hydrological warning/danger stages. |
| **Flood Deterministic Gauge** | River stage early warning ($70.26\text{ m}$ Warning, $71.26\text{ m}$ Danger) | **AUTHORITATIVE & ACCURATE** | Implement deterministic CWC stage checks at $70.26\text{ m}$ and $71.26\text{ m}$ as primary alert triggers. |

---

## 5. Next Steps for Phase 6 Redevelopment

Having completed the forensic audit and dataset discovery, the recommended progression for model redevelopment (Phase 6B / 6C) is:

1. **Water Quality Model Redevelopment:**
   - Retrain `water_quality_model.pkl` and `water_quality_scaler.pkl` using a realistic distribution based on actual CPCB Varanasi data (pH $7.0 - 8.8$, DO $4.0 - 10.5\text{ mg/L}$, Turbidity $10 - 250\text{ NTU}$, EC $200 - 600\text{ }\mu\text{S/cm}$, Temp $15 - 35^\circ\text{C}$).
   - Evaluate with a realistic train/test split. Acknowledge realistic accuracy ($85-95\%$) rather than artificial $100\%$.
   - Align API contract to return `cpcb_class_b_compliant`, `water_quality_index`, and clear non-potable disclaimers.
2. **Flood Model Redevelopment:**
   - Correct the target definition and rating curve in `train_flood_model.py`.
   - Implement temporal out-of-time evaluation (e.g., train 2018–2019, test 2020).
   - Document realistic model performance with honest metrics, clearly disclaiming that official flood warnings derive from CWC gauge levels.
3. **Verification & Regression Testing:**
   - Execute all existing test suites to verify backward compatibility of API responses.
