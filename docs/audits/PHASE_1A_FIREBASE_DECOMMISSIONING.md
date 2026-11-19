# PHASE 1A — FIREBASE DECOMMISSIONING REPORT
**Project:** River Sentinel 2.0  
**Status:** Decommissioning Completed (Supabase Authorized Primary)  
**Execution Date:** 2026-11-19  

---

## 1. Executive Summary

During Phase 0, forensic evaluation of the legacy Firebase Realtime Database instance (`riversentinel-ae0b0-default-rtdb`) confirmed an unrecoverable HTTP 423 status:
```json
{
  "error": "The Firebase database 'riversentinel-ae0b0-default-rtdb' has been deactivated."
}
```

Because the database was locked by Google Firebase, no automated REST export of historical data was possible. In Phase 1A, all residual dependencies, network timeouts, and fallback attempts targeting this deactivated instance were purged across the codebase.

---

## 2. Decommissioned Touchpoints

### 2.1 Backend Monolith (`backend/app.py`)
- **Removed**: Firebase Admin SDK initialization attempt (`firebase_admin.initialize_app(...)`), which was printing startup warnings.
- **Removed**: Dead helper functions: `safe_db_push()`, `safe_db_get()`, `safe_db_update()`, `_firebase_rest_url()`.
- **Migrated**: `_get_latest_sensor_from_firebase()` replaced by `get_latest_sensor_reading()`, which queries Supabase directly with safe static fallbacks.
- **Migrated**: `/api/authority/report-summary` rewritten to calculate real statistics (`avg_ph`, `avg_do`, `avg_turbidity`, `avg_water_level`, and report resolution rate) directly from Supabase via PostgreSQL aggregations.
- **Decoupled**: `/api/ai/analyze-image` and `/api/reports/submit` removed dual-write calls to Firebase `analysis_history`.

### 2.2 Telemetry Simulator (`backend/simulate_sensors.py`)
- **Removed**: `push_to_firebase()` and associated Firebase URLs/secrets.
- **Redirected**: All simulated readings now route exclusively to the authenticated Flask backend endpoint (`POST /api/telemetry/simulate`).

### 2.3 USB Serial Bridge (`backend/serial_bridge.py`)
- **Removed**: `push_to_firebase()`.
- **Redirected**: All parsed hardware serial data (`Label: Value`) routes to the authenticated Flask backend endpoint (`POST /api/telemetry/simulate`).

### 2.4 Frontend Configuration Files
- **Removed**: `frontend/src/firebaseConfig.ts` and `frontend/src/services/firebaseConfig.ts` (unimported dead code containing hardcoded credentials).

### 2.5 Dependencies
- **Updated**: `backend/requirements.txt` removed `firebase-admin` and pinned modern, secure versions of `pg8000`, `flask`, `groq`, etc.

---

## 3. Preserved Artifacts

- **Firmware Sketch (`arduino/firebase_sensor_upload.ino`)**:
  As mandated by Phase 1A safety guidelines, this file was left intact in the repository as a historical reference point. It will be replaced during the dedicated Hardware Ingestion Phase (Phase 4) with a modern HTTPS NTP-synchronized telemetry client.
