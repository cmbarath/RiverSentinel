# River Sentinel 2.0 — Phase 6: Dataset Manifest & Provenance Registry

**Project:** River Sentinel 2.0  
**Target River / Location:** Ganga River, Varanasi, Uttar Pradesh, India  
**Date:** 2026-11-19  
**Status:** Cryptographic Manifest, Station Mapping & Pipeline Provenance  
**Branch:** `river-sentinel/phase-1-stabilization`  

---

## 1. Raw Datasets Manifest & Checksums

All raw datasets are cataloged with source URLs, sizes in bytes, and cryptographic SHA-256 checksums:

| Dataset Identifier | File Name | Source / Agency | Size (Bytes) | SHA-256 Checksum |
| :--- | :--- | :--- | :--- | :--- |
| `cpcb_phys_1961_2020` | `physical_up_1961_2020.csv` | NWDP / CPCB (Package `c547abaa`) | 570,765 | `b14dc5e3d59a7d307519e164d820a13ccf263f72dc7b919de652f0cf5f66c291` |
| `cpcb_phys_2021_2025` | `physical_up_2021_2025.csv` | NWDP / CPCB (Package `c547abaa`) | 63,519 | `9ed3e9a7c8f30e957d5fa7024692646de6b0b1de4552828074b00f838746f66a` |
| `cpcb_chem_1961_2020` | `chemical_up_1961_2020.csv` | NWDP / CPCB (Package `d54d7702`) | 901,047 | `ad3a143b7b6eccadc8e3381d46f971f458c3aea15ff71bef4e492656f38380df` |
| `cpcb_chem_2021_2025` | `chemical_up_2021_2025.csv` | NWDP / CPCB (Package `d54d7702`) | 352,325 | `f8e2c82a1fad3928271ac9e384f9f99027c12d6b69b1fc3029ce5e07268efd72` |
| `cpcb_bio_1961_2020` | `biological_up_1961_2020.csv` | NWDP / CPCB (Package `e97bcc1b`) | 557,862 | `2ea5f193d6b7a466d57d299f84207811cba05348c44c05c0d8a2896319a4fb56` |
| `cpcb_bio_2021_2025` | `biological_up_2021_2025.csv` | NWDP / CPCB (Package `e97bcc1b`) | 218,320 | `02b0a00ca59c5b55f06b790b1c526dd0f0ae0d2c3fb70d43135c133eb220613a` |
| `flood_daily_sim` | `flood_data_with_dynamic_labels.csv` | Prototype Local Simulation Series | 155,117 | `9cf91c9a0b7fda8b569550e2192b8f726c6d9d0ae2956d8cc365c6e45633d1c4` |

---

## 2. Processed Datasets Manifest

| Processed File Name | Path in Repository | Row Count | Column Count | Generating Script |
| :--- | :--- | :--- | :--- | :--- |
| `varanasi_water_quality_aligned.csv` | `backend/data/processed/` | 272 | 20 | `backend/ml/water_quality/alignment.py` |

---

## 3. Station Mapping & Hydrological Hierarchy

The pipeline strictly maps original station strings into standardized clean names, explicit river identifiers, and station roles:

| Raw Station String | Clean Name | River | Hydrological Hierarchy | Latitude | Longitude |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GANGA AT VARANASI U/S (ASSIGHAT) U.P` | Ganga U/S Assi Ghat | Ganga | Mainstem River (Upstream Baseline) | 25.2917 | 83.0039 |
| `GANGA AT VARANASI D/S (MALVIYA BRIDGE) U.P` | Ganga D/S Malviya Bridge | Ganga | Mainstem River (Downstream Impact) | 25.3211 | 83.0317 |
| `RIVER VARUNA AT RAMESHWAR VARANASI` | Varuna at Rameshwar | Varuna | Rural Tributary | 25.3850 | 82.8800 |
| `RIVER VARUNA B/C WITH RIVER GANGA AT VARANASI`| Varuna Before Confluence | Varuna | Urban Tributary (Sewage Inflow) | 25.3350 | 83.0450 |
| `GOMTI AT VARANASI U.P` | Gomti at Varanasi | Gomti | Regional Tributary | 25.5000 | 83.1500 |

---

## 4. Parameter & Unit Standard Mapping

All measurements in processed files are converted and typed into standard engineering and scientific units:

| Standard Column Name | Raw Source Parameter | Measurement Unit | CPCB Class B Standard | Operational Role |
| :--- | :--- | :--- | :--- | :--- |
| `ph` | Potential of Hydrogen (pH) | Dimensionless | $6.5 - 8.5$ | Statutory Standard |
| `do_mg_l` | Dissolved oxygen (mg/L) | $\text{mg/L}$ | $\ge 5.0\text{ mg/L}$ | Statutory Standard |
| `bod_mg_l` | Biochemical Oxygen Demand | $\text{mg/L}$ (5 days at 20°C) | $\le 3.0\text{ mg/L}$ | Statutory Standard |
| `total_coliform_mpn_100ml` | Total Coliform | $\text{MPN/100mL}$ | $\le 500\text{ MPN/100mL}$ | Statutory Standard |
| `fecal_coliform_mpn_100ml` | Fecal Coliform | $\text{MPN/100mL}$ | $\le 500\text{ MPN/100mL}$ (desirable) | Secondary Indicator |
| `turbidity_ntu` | Turbidity (NTU) | $\text{NTU}$ | Non-statutory | Screening ($\le 100\text{ NTU}$) |
| `conductivity_us_cm` | Electric Conductivity | $\mu\text{S/cm}$ | Non-statutory | Screening ($\le 1500\text{ }\mu\text{S/cm}$) |
| `temperature_c` | Temperature (ºC) | $^\circ\text{C}$ | Ambient | Physical State |
| `water_level_varanasi` | Stage gauge height | $\text{metres MSL}$ | Warning $70.26\text{ m}$, Danger $71.26\text{ m}$ | Hydrological Stage |
| `discharge_cumec` | River discharge | $\text{m}^3/\text{s}$ ($\text{cumec}$) | Historical flow | Hydraulic Volume |
| `rain_varanasi_mm` | Local rainfall | $\text{mm}$ | Weather state | Storm Runoff |

---

## 5. Sample Alignment & Missingness Audit

### 5.1 Sample Alignment Completeness
Across the 5 Varanasi river stations:
- **Chemical & Biological Alignment:** Exactly $100\%$ of sampling timestamps match.
- **Physical Alignment:** Available for $73.5\%$ of sampling events (189 of 257 dates).
- **Class B Completeness:** Total Coliform was monitored on 17 dates at Ganga stations (quarterly/seasonal schedule), while pH, DO, and BOD were monitored monthly (64–65 dates).

### 5.2 Station-by-Station Parameter Completeness

| Station | Total Events | pH Count | DO Count | BOD Count | Coliform Count | Turbidity Count | EC Count | Complete Class B |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Ganga U/S Assi Ghat** | 64 | 64 (100%) | 64 (100%) | 64 (100%) | 17 (26.6%) | 16 (25.0%) | 16 (25.0%) | 17 (26.6%) |
| **Ganga D/S Malviya Bridge** | 65 | 65 (100%) | 65 (100%) | 65 (100%) | 17 (26.2%) | 16 (24.6%) | 16 (24.6%) | 17 (26.2%) |
| **Varuna at Rameshwar** | 47 | 47 (100%) | 46 (97.9%) | 47 (100%) | 12 (25.5%) | 11 (23.4%) | 11 (23.4%) | 12 (25.5%) |
| **Varuna Before Confluence** | 48 | 48 (100%) | 47 (97.9%) | 48 (100%) | 12 (25.0%) | 11 (22.9%) | 11 (22.9%) | 12 (25.0%) |
| **Gomti at Varanasi** | 48 | 48 (100%) | 48 (100%) | 48 (100%) | 12 (25.0%) | 11 (22.9%) | 11 (22.9%) | 12 (25.0%) |

---

## 6. Rejected Rows & Industrial Monitoring Stations

The following 24 observations from non-river monitoring sites in Varanasi were identified in the raw CPCB files and explicitly excluded:
1. `CHANDPUR INDUSTRIAL AREA LAHARTARA VARANASI` (8 rows): Industrial area drainage.
2. `GOPIGANJ INDUSTRIAL AREA BHADOHI VARANASI U.P` (8 rows): Industrial cluster runoff.
3. `GROUND AROUND STP DINAPUR VARANASI U.P` (8 rows): STP perimeter groundwater monitoring.

---

## 7. Environment-Independent Reproduction Instructions

To reproduce the processed dataset from scratch in any clean environment:

```bash
# 1. Download raw CPCB datasets from official NWDP portal and verify SHA-256 hashes
python backend/ml/download_cpcb_raw.py

# 2. Execute station filtering, alignment, cleaning, and metadata generation
python backend/ml/water_quality/alignment.py

# 3. Execute deterministic evaluation and statistical reporting
python backend/ml/water_quality/evaluator.py

# 4. Train and benchmark the experimental flood stage forecaster
python backend/ml/flood/forecaster.py

# 5. Train and benchmark the experimental physical anomaly detector
python backend/ml/water_quality/anomaly_detector.py
```
All outputs are deterministically reproducible without external dependencies.
