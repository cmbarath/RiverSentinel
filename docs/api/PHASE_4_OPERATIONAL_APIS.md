# River Sentinel 2.0 — Phase 4 Operational REST APIs

This document specifies the versioned station data and analytics APIs implemented under **Phase 4: Operational Application Completion**.

---

## 1. Overview & Architecture

All Phase 4 operational endpoints are organized under the versioned route namespace `/api/v1` and registered via the `stations_v1_bp` blueprint in `backend/routes/stations_v1.py`.

### Design Principles:
1. **Station-Bound Observation Isolation**: Telemetry queries strictly partition and index by `station_id` (UUID) or `station_code`.
2. **Safe SQL Parameterization**: SQL queries utilize bound parameters (`:sid::uuid`, `:start_time`, `:limit`) via `pg8000.native` and PostgreSQL SSL pools.
3. **Transparent Provenance Tracking**: Every observation payload returns its `provenance` (`real_sensor`, `simulated`, or `default`) and `quality_status` (`valid`, `provisional`, `out_of_range`).
4. **DOS & Memory Guardrails**: Hard limits on query bounds (`MAX_TIMEFRAME_DAYS = 90`, `MAX_LIMIT = 1000`).

---

## 2. API Reference Matrix

| Endpoint | Method | Authentication | Description |
| :--- | :--- | :--- | :--- |
| `/api/v1/stations` | `GET` | Public | List all registered monitoring stations with lifecycle, device runtime state, and latest observation |
| `/api/v1/stations/<id>` | `GET` | Public | Station metadata, attached device details, and CWC reference gauge benchmarks |
| `/api/v1/stations/<id>/latest` | `GET` | Public | Single latest valid observation or clean 200 `no_data` response |
| `/api/v1/stations/<id>/readings` | `GET` | Public | Filtered time-series historical observations with statistical summary |
| `/api/v1/stations/<id>/analytics` | `GET` | Public | Total counts, provenance breakdown, quality status distribution, and 24h averages |
| `/api/v1/analytics/overview` | `GET` | `require_role('authority_admin', 'field_officer')` | Live system-wide aggregations across stations, devices, telemetry, reports, and flood risks |
| `/api/v1/export/sensor-data` | `GET` | Public | Stream filtered CSV sensor records with parameter and timeframe filters |
| `/api/v1/stations/<id>/evaluate-safety` | `GET`, `POST` | Public | Scientific water screening against CPCB Class B and BIS IS 10500 benchmarks |

---

## 3. Detailed Endpoint Contracts

### 3.1. Station Directory: `GET /api/v1/stations`
Returns all registered river monitoring stations in Varanasi.

#### Response Example (`200 OK`):
```json
{
  "status": "success",
  "count": 4,
  "stations": [
    {
      "id": "e66507dc-7d0e-4bc7-9cd0-86848fc9b80d",
      "station_code": "STN-VAR-ASSI-01",
      "station_name": "Assi Ghat Monitoring Station",
      "location_name": "Assi Ghat, Varanasi",
      "river_name": "Ganga",
      "latitude": 25.2891,
      "longitude": 83.0067,
      "status": "active",
      "warning_water_level_m": 70.26,
      "danger_water_level_m": 71.26,
      "cwc_reference_gauge_id": "cwc-gauge-varanasi-01",
      "is_online": true,
      "device": {
        "device_code": "DEV-VAR-ASSI-01",
        "device_name": "Assi Ghat Primary ESP32 Node",
        "lifecycle_status": "active",
        "runtime_status": "online",
        "battery_level_pct": 94.0,
        "firmware_version": "v1.2.0-esp32"
      },
      "latest_reading": {
        "id": 40,
        "observed_at": "2026-11-19T02:45:02.817716+00:00",
        "ph": 7.35,
        "turbidity": 4.2,
        "temperature": 23.5,
        "water_level": 68.2,
        "ec": 480.0,
        "do": 7.1,
        "provenance": "real_sensor",
        "quality_status": "valid"
      }
    }
  ]
}
```

---

### 3.2. Historical Time-Series: `GET /api/v1/stations/<station_id>/readings`

#### Query Parameters:
- `timeframe`: `24h` (default), `7d`, `30d`, or `custom`.
- `start_time` / `end_time`: ISO-8601 UTC strings (required when `timeframe=custom`).
- `parameter`: `all` (default), `ph`, `turbidity`, `temperature`, `water_level`, `ec`, `do`.
- `provenance`: `all` (default), `real_sensor`, `simulated`.
- `quality_status`: `all` (default), `valid`, `provisional`, `degraded`, `out_of_range`.
- `limit`: Integer (default 200, max 1000).
- `offset`: Pagination offset (default 0).

#### Response Example (`200 OK`):
```json
{
  "status": "success",
  "station_id": "e66507dc-7d0e-4bc7-9cd0-86848fc9b80d",
  "station_code": "STN-VAR-ASSI-01",
  "station_name": "Assi Ghat Monitoring Station",
  "timeframe": "24h",
  "parameter": "all",
  "count": 7,
  "total_matching": 7,
  "start_time": "2026-11-18T03:20:35.643776+00:00",
  "end_time": "2026-11-19T03:20:35.643776+00:00",
  "provenance_counts": {
    "real": 1,
    "simulated": 6
  },
  "provenance_breakdown": {
    "real_sensor": 1,
    "simulated": 6
  },
  "summary": {
    "ph": { "min": 7.0, "max": 7.95, "avg": 7.48, "sample_count": 7 },
    "turbidity": { "min": 10.0, "max": 149.3, "avg": 42.0, "sample_count": 6 },
    "temperature": { "min": 25.0, "max": 29.9, "avg": 27.25, "sample_count": 6 },
    "water_level": { "min": 66.0, "max": 69.76, "avg": 67.45, "sample_count": 6 },
    "ec": { "min": 400.0, "max": 598.0, "avg": 487.33, "sample_count": 6 },
    "do": { "min": 6.8, "max": 8.7, "avg": 7.55, "sample_count": 6 }
  },
  "readings": [
    {
      "id": 40,
      "timestamp": "2026-11-19T02:45:02.817716+00:00",
      "ph": 7.35,
      "turbidity": null,
      "temperature": null,
      "water_level": null,
      "ec": null,
      "do": null,
      "provenance": "real_sensor",
      "quality_status": "valid"
    }
  ]
}
```

---

### 3.3. Authority Overview: `GET /api/v1/analytics/overview`
Requires valid Supabase Auth JWT in `Authorization: Bearer <token>` belonging to `authority_admin` or `field_officer`.

#### Response Example (`200 OK`):
```json
{
  "status": "success",
  "generated_at": "2026-11-19T03:20:25.252389+00:00",
  "stations": {
    "total": 4,
    "active": 2,
    "planned": 1,
    "installed": 1,
    "by_status": { "active": 2, "planned": 1, "installed": 1 }
  },
  "devices": {
    "total": 4,
    "active_online": 1,
    "online_active": 1,
    "offline": 2,
    "provisioned": 1,
    "by_status": { "online": 1, "offline": 2, "provisioned": 1 }
  },
  "readings": {
    "total": 16,
    "real_sensor": 1,
    "simulated": 15,
    "last_24h": 16
  },
  "telemetry": {
    "total_readings": 16,
    "readings_last_24h": 16,
    "real_sensor_count": 1,
    "simulated_count": 15,
    "by_provenance": { "real_sensor": 1, "simulated": 15 }
  },
  "pollution_reports": {
    "total": 6,
    "submitted": 2,
    "investigating": 1,
    "resolved": 2,
    "rejected": 1,
    "resolution_rate_pct": 33.3,
    "by_status": { "submitted": 2, "investigating": 1, "resolved": 2, "rejected": 1 }
  },
  "flood_risk": {
    "latest_predictions_count": 20,
    "risk_level_counts": { "LOW": 16, "HIGH": 4 },
    "by_severity": { "LOW": 16, "HIGH": 4 }
  },
  "cwc_reference_gauge": {
    "site": "Varanasi (Ganga River)",
    "warning_level_m": 70.26,
    "danger_level_m": 71.26,
    "highest_flood_level_m": 73.90
  }
}
```

---

### 3.4. Scientific Safety Screening: `GET /api/v1/stations/<id>/evaluate-safety`
Transparently screens the latest valid telemetry packet for the station against regulatory water standards.

#### Response Example (`200 OK`):
```json
{
  "status": "success",
  "station_code": "STN-VAR-ASSI-01",
  "station_name": "Assi Ghat Monitoring Station",
  "observation_timestamp": "2026-11-19T02:45:02.817716+00:00",
  "provenance": "real_sensor",
  "quality_status": "valid",
  "confidence_level": "HIGH",
  "parameters": {
    "ph": 7.35,
    "turbidity_ntu": 4.2,
    "temperature_c": 23.5,
    "water_level_m": 68.2,
    "ec_us_cm": 480.0,
    "do_mg_l": 7.1
  },
  "bathing_water_screening": {
    "cpcb_class": "Class B (Outdoor Bathing)",
    "suitability": "SUITABLE",
    "verdict": "SAFE",
    "criteria": {
      "ph": { "value": 7.35, "requirement": "6.5 to 8.5", "passed": true },
      "dissolved_oxygen": { "value": 7.1, "requirement": ">= 5.0 mg/L", "passed": true }
    },
    "notes": "In-situ parameters are within CPCB Class B limits for religious and recreational bathing."
  },
  "drinking_water_screening": {
    "standard": "Bureau of Indian Standards (BIS IS 10500:2012)",
    "suitability_level": "TREATMENT_REQUIRED",
    "bis_is10500_compliance": {
      "ph": { "value": 7.35, "acceptable_limit": "6.5 - 8.5", "status": "PASS" },
      "turbidity": { "value": 4.2, "acceptable_limit": "1 NTU", "permissible_limit": "5 NTU", "status": "PASS" },
      "tds_ec": { "value": 480.0, "benchmark": "<= 1000 uS/cm", "status": "PASS" }
    },
    "disclaimer": "In-situ electronic probes screen physical and chemical properties only. Raw river water contains bacteriological contaminants (e.g., Fecal Coliform) and must undergo conventional treatment and disinfection per BIS IS 10500:2012 prior to human consumption."
  },
  "ecological_screening": {
    "status": "HEALTHY",
    "do_reading_mg_l": 7.1,
    "description": "Adequate for aquatic biomes."
  },
  "sensor_anomaly_screening": {
    "anomalies_detected": [],
    "is_simulated": false,
    "confidence_score": 0.95
  },
  "scientific_disclaimer": "Screening is based exclusively on in-situ electronic probe readings. Bacteriological pathogens (Fecal Coliform, E. Coli) and chemical toxins require laboratory testing. Never consume untreated river water based solely on automated sensor readings."
}
```
