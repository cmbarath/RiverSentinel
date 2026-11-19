# PHASE 1A — BACKEND MODULARIZATION & ARCHITECTURE CHANGES
**Project:** River Sentinel 2.0  
**Phase:** Phase 1A Stabilization  
**Execution Date:** 2026-11-19  

---

## 1. Modular Blueprint Architecture

To eliminate the 1,180-line monolithic structure of `backend/app.py`, the backend was refactored into a clean Flask Application Factory using modular Blueprints and dedicated services.

```
backend/
├── app.py                     # Entrypoint & create_app() application factory
├── requirements.txt           # Pinned production dependencies (Firebase removed)
├── simulate_sensors.py        # Authenticated telemetry simulator client
├── serial_bridge.py           # USB serial hardware bridge (routes to backend)
├── services/
│   ├── __init__.py
│   └── supabase_service.py    # Centralized PostgREST persistence & queries
└── routes/
    ├── __init__.py
    ├── sensors.py             # Latest readings, ingestion, citizen health status
    ├── predictions.py         # Flood & water quality ML models, weather API
    ├── ai.py                  # Groq Qwen 3.8 27B chatbot & vision analysis
    └── authority.py           # Reports, summary, CSV export, alerts, notices
```

---

## 2. Service Layer: `backend/services/supabase_service.py`

This module centralizes all communication with Supabase using server-side credentials (`SUPABASE_SERVICE_ROLE_KEY`):
- `supabase_insert(table_name, record)`: Generic authenticated insertion with `return=representation`.
- `supabase_get(table_name, ...)`: Parameterized query builder supporting column selection, ordering, and limits.
- `supabase_update(table_name, filter_param, record)`: Generic row patching.
- `get_latest_sensor_reading()`: Single authoritative fetch for `/api/sensors/latest` and ML inference.
- `get_sensor_summary()`: Live computation of average pH, DO, turbidity, and water level across the latest 50 readings.
- `get_reports_summary()`: Live computation of citizen report resolution rates.

---

## 3. Route Blueprints & API Contracts

### 3.1 `backend/routes/sensors.py` (`sensors_bp`)
- `GET /api/sensors/latest`: Returns live telemetry with provenance metadata (`real`, `simulated`, `default`).
- `POST /api/telemetry/simulate` (alias: `POST /api/v1/telemetry/ingest`): Authenticates incoming telemetry via `X-Simulator-Token` and persists valid readings into Supabase `sensor_readings`.
- `GET /api/citizen/health-status`: Computes bathing and drinking safety assessments with citizen advisories.

### 3.2 `backend/routes/predictions.py` (`predictions_bp`)
- `GET, POST /api/flood/predict`: Ingests sensor readings and weather, runs canonical 6-feature Random Forest model, logs risk to `flood_predictions`, and returns probability and explanatory factors.
- `GET, POST /api/water-quality/predict`: Evaluates water potability screening and calculates heuristic river quality score with laboratory disclaimer.
- `GET /api/weather`: Fetches live Varanasi meteorological data from Open-Meteo.

### 3.3 `backend/routes/ai.py` (`ai_bp`)
- `POST /api/ai/chat`: Multilingual conversational interface powered by Groq Qwen 3.8 27B.
- `POST /api/ai/analyze-image`: Multimodal vision assessment of uploaded river pollution photos; automatically logs findings to Supabase `pollution_reports`.

### 3.4 `backend/routes/authority.py` (`authority_bp`)
- `GET /api/authority/reports`: Returns recent citizen reports from Supabase.
- `POST /api/authority/reports/update`: Updates report status (`VERIFIED`, `REJECTED`, etc.) in Supabase.
- `POST /api/reports/submit`: Ingests citizen pollution reports into Supabase.
- `GET /api/authority/report-summary`: Returns live aggregated system analytics.
- `GET /api/authority/export-data`: Streams legitimate CSV export of real database sensor records.
- `POST /api/authority/send-sms`: Simulates SMS dispatches (explicitly marked as simulation).
- `POST /api/authority/trigger-alert`: Activates system-wide warning alerts.
- `POST /api/authority/generate-notice`: Generates formal legal notice templates.

---

## 4. Backward Compatibility Verification

All existing frontend API paths (`/api/sensors/latest`, `/api/ai/chat`, `/api/flood/predict`, `/api/water-quality/predict`, `/api/authority/reports`, etc.) were retained with identical JSON schemas. No frontend changes were required to maintain full operational parity.
