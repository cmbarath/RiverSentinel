# River Sentinel 2.0 — Phase 6A: Official Dataset Discovery Report

**Project:** River Sentinel 2.0  
**Target River / Location:** Ganga River, Varanasi, Uttar Pradesh, India  
**Discovery Date:** 2026-11-19  
**Status:** Official Data Portal Discovery & Station Inventory  

---

## 1. Scope & Discovery Methodology

In accordance with Phase 6 requirements, this report documents the discovery, retrieval, and inventory of authoritative, public, and official open government datasets for:
1. **River Water Quality (Physical, Chemical, Biological)** for Varanasi and the middle Ganga basin.
2. **Hydrological River Stages & Flooding (Water Levels, Discharge, Telemetry)** for Varanasi (Rajghat / Malviya Bridge).
3. **Hydro-meteorological Precipitation Data** for Varanasi and its upstream catchment.

Discovery was conducted programmatically using the official CKAN REST APIs of the **National Water Data Portal (NWDP / NWIC, Ministry of Jal Shakti, Government of India)** (`https://nwdp.nwic.gov.in`), complemented by open access portals and CWC published hydrological stages.

---

## 2. National Water Data Portal (NWDP / NWIC) Water Quality Discovery

The National Water Data Portal hosts official monitoring datasets compiled by the **Central Pollution Control Board (CPCB)** and state pollution control boards under the National Water Quality Monitoring Programme (NWMP).

Six comprehensive datasets covering Uttar Pradesh surface water quality were identified, inspected, and downloaded:

### 2.1 Catalog Packages & Direct Resources

| Dataset / Parameter Category | NWDP Package ID | Resource File Name | Resource ID | File Size (Bytes) | SHA-256 Hash |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Physical (1961–2020)** | `c547abaa-fbdc-4f46-b152-dc023be0c75c` | `swq_manual_physical_parameters_cpcb_up_1961_2020.csv` | `3aac0149-d815-42a6-975a-2e5c757256f6` | 570,765 | `606703c6fc9650085ec3e708761a58eb89f6655c6bc8aa4eecb8a1c62f2df37b` |
| **Physical (2021–2025)** | `c547abaa-fbdc-4f46-b152-dc023be0c75c` | `swq_physical_parameter_manual_cpcb_up_2021_2025.csv` | `caf05460-e4bc-498d-85f3-2ed21a595e89` | 63,519 | `9ed3e9a7c8f30e957d5fa7024692646de6b0b1de4552828074b00f838746f66a` |
| **Chemical (1961–2020)** | `d54d7702-d21f-408f-8dc0-2665bde47201` | `swq_manual_chemical_parameters_cpcb_up_1961_2020.csv` | `75c260b7-ab36-4cda-a21b-f6fe22387eb6` | 901,047 | `b21495e80dca0a430adfd98c1aa12e9871168f0cb503046f5c531d27976e1074` |
| **Chemical (2021–2025)** | `d54d7702-d21f-408f-8dc0-2665bde47201` | `swq_chemical_parameter_manual_cpcb_up_2021_2025.csv` | `fb147bf0-f952-4153-84ad-ef5cb39f6517` | 352,325 | `f8e2c82a1fad3928271ac9e384f9f99027c12d6b69b1fc3029ce5e07268efd72` |
| **Biological (1961–2020)**| `e97bcc1b-895e-4eb9-a826-09d52f7b5ca0` | `swq_manual_biological_parameters_cpcb_up_1961_2020.csv` | `4b7b29f0-be59-499a-986a-58635449a08c` | 557,862 | `a9069d3004bbad9dc88701e9d2912a76f28d84425bf784a0c8b090bf3519b7d5` |
| **Biological (2021–2025)**| `e97bcc1b-895e-4eb9-a826-09d52f7b5ca0` | `swq_biological_parameter_manual_cpcb_up_2021_2025.csv` | `31003ead-35e6-488d-84c9-8536a3dd7ab9` | 218,320 | `02b0a00ca59c5b55f06b790b1c526dd0f0ae0d2c3fb70d43135c133eb220613a` |

---

## 3. Station-Level Monitoring Coverage for Varanasi

Analysis of the official CPCB datasets reveals five active monitoring stations in the Varanasi district:

```
                  Middle Ganga Basin — Varanasi River Network
                                    
 [Upstream / Mirzapur]
          │
          ▼
   (Station 1) Ganga at Varanasi U/S (Assi Ghat)  [Latitude: 25.2917, Longitude: 83.0039]
          │
          ├──── Main Ghats (Dashashwamedh, Manikarnika) & Urban Storm/Sewage Drains
          ▼
   (Station 2) Ganga at Varanasi D/S (Malviya Bridge / Rajghat) [Latitude: 25.3211, Longitude: 83.0317]
          │
          ├──── Confluence with Varuna River (Station 3 & 4: Varuna River & Varuna B/C Ganga)
          ▼
 [Downstream / Ghazipur / Patna]
```

### 3.1 Varanasi Station Inventory

| Station Name in Dataset | Agency | River / Waterbody | Available Records (2020–2021) | Key Monitored Parameters |
| :--- | :--- | :--- | :--- | :--- |
| **`GANGA AT VARANASI U/S (ASSIGHAT) U.P`** | CPCB / UPPCB | Ganga (Upstream baseline) | 65 Chem, 64 Bio, 46 Phys | pH, DO, BOD, COD, Fecal/Total Coliform, EC, Turbidity, Temp, Nitrates |
| **`GANGA AT VARANASI D/S (MALVIYA BRIDGE) U.P`** | CPCB / UPPCB | Ganga (Downstream impact) | 65 Chem, 65 Bio, 47 Phys | pH, DO, BOD, COD, Fecal/Total Coliform, EC, Turbidity, Temp, Nitrates |
| **`RIVER VARUNA AT RAMESHWAR VARANASI`** | UPPCB | Varuna River (Tributary) | 47 Chem, 47 Bio, 38 Phys | pH, DO, BOD, COD, Coliform, EC, Turbidity |
| **`RIVER VARUNA B/C WITH RIVER GANGA AT VARANASI`** | UPPCB | Varuna River (Pre-confluence) | 48 Chem, 48 Bio, 39 Phys | pH, DO, BOD, COD, Coliform, EC, Turbidity |
| **`GOMTI AT VARANASI U.P`** | UPPCB | Gomti River | 48 Chem, 48 Bio, 39 Phys | pH, DO, BOD, COD, Coliform, EC, Turbidity |

---

## 4. Central Water Commission (CWC) Hydrological Data Discovery

### 4.1 CWC Real-Time Telemetry Search on NWDP
The NWDP CKAN package `river-water-level-telemetry-hourly-central-water-commission-cwc` was queried for automated real-time telemetry.
- **Total Resources in Package:** 58 resources.
- **Basins Covered:** Subernarekha, Brahmani-Baitarani, Mahanadi, Godavari, Krishna, Pennar, Cauvery, East Flowing Rivers, Tapi, Narmada, Mahi, Sabarmati, West Flowing Rivers.
- **Finding:** **ZERO resources for the Ganga Basin** are published in the NWDP hourly telemetry package. Automated telemetry for the Ganga basin is restricted from general open REST export on NWDP due to interstate and international hydrological sensitivities.

### 4.2 Official Hydrological Benchmark Stages for Varanasi (Rajghat / Malviya Bridge)
Authoritative hydrological stages for Varanasi are published in official **Central Water Commission Flood Bulletins**:

| Stage Designation | Gauge Height (m above MSL) | Hydrological & Operational Meaning |
| :--- | :--- | :--- |
| **Zero Gauge Level** | **$57.91\text{ m}$** | Datum level for the Malviya Bridge gauge plate |
| **Normal Dry Season Level** | **$64.00 - 66.00\text{ m}$** | Low-flow riverbed exposure; ghat steps fully dry |
| **Monsoon Baseflow** | **$66.00 - 69.50\text{ m}$** | Moderate river swell; lower ghat steps inundated |
| **CWC Warning Stage** | **$70.26\text{ m}$** | Flood alert issued to district administration; lower ghats submerged |
| **CWC Danger Stage** | **$71.26\text{ m}$** | High flood danger; riverfront evacuation; water enters riverside buildings |
| **High Flood Level (HFL)** | **$73.90\text{ m}$** | All-time historical peak recorded on 1978-09-09 |

---

## 5. Supplementary Hydro-Meteorological Sources

1. **Open-Meteo Historical Reanalysis & Live API (`https://api.open-meteo.com`):**
   - Implemented in `backend/routes/predictions.py` (`/api/weather`).
   - Provides hourly temperature, relative humidity, precipitation ($mm$), and wind speed for Varanasi ($25.3176^\circ\text{N}, 82.9739^\circ\text{E}$).
2. **Indian Meteorological Department (IMD) Daily Gridded Precipitation:**
   - 0.25° x 0.25° daily gridded rainfall datasets (useful for basin-level catchment integration across upstream Uttar Pradesh and Uttarakhand).

---

## 6. Summary of Dataset Coverage

| Domain | Source | Station Coverage | Temporal Range | Cadence | Readiness for ML |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Water Quality** | NWDP / CPCB | Assi Ghat, Malviya Bridge (Rajghat) | 2020–2021 | Bi-weekly / Monthly grab samples | **Adequate for baseline screening & statistical benchmarking; insufficient for deep time-series ML without synthetic augmentation.** |
| **River Water Level** | CWC / NWDP | Malviya Bridge (Rajghat) | Gauge thresholds (Warning: 70.26m, Danger: 71.26m) | Continuous gauge (telemetry not in NWDP) | **Must use deterministic CWC thresholds. Pure ML forecasting without upstream hydro-telemetry is unreliable.** |
| **Precipitation & Weather** | Open-Meteo / IMD | Varanasi & Middle Ganga | Continuous hourly / reanalysis | Hourly / Daily | **Ready and operational via `/api/weather`.** |
