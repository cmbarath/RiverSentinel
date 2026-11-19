# RIVER SENTINEL 2.0 — MASTER IMPLEMENTATION ROADMAP
**Document Version:** 2.0.0  
**Baseline Date:** 2026-11-19  
**Execution Strategy:** Sequential, Phase-Gated, Test-Driven Delivery  

---

## 1. Roadmap Overview & Execution Principles

This roadmap guides the controlled evolution of River Sentinel from its stabilized forensic baseline into a complete, secure, hardware-ready river monitoring platform.

### Immutable Principles:
1. **Zero Big-Bang Overhauls**: Each phase delivers self-contained, testable improvements without breaking existing working features.
2. **Branch Discipline**: All work is performed and verified on `river-sentinel/phase-1-stabilization`. The local `main` branch remains untouched at `223c7dc` until formal acceptance.
3. **Strict Credential Protection**: No secrets, device tokens, or private keys in Git commits, client bundles, or documentation.
4. **No Premature Deployment**: No deployments to Vercel, Render, or public cloud until Phase 12 verification is complete.
5. **Phase-Gated Approval**: Every phase stops upon completion to present test results and receive explicit approval before progressing.

---

## 2. Phase-by-Phase Execution Plan

```mermaid
flowchart LR
    P0["Phase 0: System Audit (Current)"] --> P1["Phase 1: Foundation & Stability"]
    P1 --> P2["Phase 2: Database & Security"]
    P2 --> P3["Phase 3: Firebase Decommission"]
    P3 --> P4["Phase 4: Hardware IoT Ingestion"]
    P4 --> P5["Phase 5: Backend Modularization"]
    P5 --> P6["Phase 6: Real Frontend & Maps"]
    P6 --> P7["Phase 7: Alert Engine"]
    P7 --> P8["Phase 8: ML Rebuilding & WQI"]
    P8 --> P9["Phase 9: Reliability & Monitoring"]
    P9 --> P10["Phase 10: Security Hardening"]
    P10 --> P11["Phase 11: End-to-End Testing"]
    P11 --> P12["Phase 12: Production Readiness"]
```

---

### PHASE 1 — FOUNDATION AND PROJECT STABILITY
*Objective: Clean technical debt, standardize configuration, modularize backend, and eliminate dead code without altering public API contracts.*

- **Task 1.1: Git & Workspace Baseline**:
  - Verify clean working tree and active development branch.
  - Tag verified Phase 0 baseline commit.
- **Task 1.2: Secret Hygiene & Dead File Removal**:
  - Remove unused `frontend/src/firebaseConfig.ts` and `frontend/src/services/firebaseConfig.ts` containing exposed project credentials.
  - Remove duplicate model artifacts (`backend/ml_models/flood/model.pkl`, `backend/flood_model/model.pkl`).
  - Archive or harmonize orphaned `backend/flood_predictor.py` and `backend/test_flood_api.py`.
- **Task 1.3: Configuration Standardization**:
  - Create complete `.env.example` templates for both `backend/` and `frontend/` documenting all required variables with clear comments.
  - Standardize environment variable keys across Node and Python.
- **Task 1.4: Backend Blueprint Modularization**:
  - Refactor monolithic `backend/app.py` into a clean Flask Application Factory (`create_app()`) using Flask Blueprints:
    - `api/sensors.py` (Telemetry endpoints)
    - `api/predictions.py` (Flood & Water Quality ML routes)
    - `api/ai.py` (Groq chat & vision endpoints)
    - `api/authority.py` (Reports, notices, alerts, analytics)
    - `services/supabase_service.py` (Centralized Supabase connector)
  - Ensure 100% backward compatibility for all existing frontend API calls.
- **Task 1.5: Verification & Checkpoint**:
  - Run all 13 backend test cases in `test_model_predictions.py`.
  - Verify Next.js production build (`npm run build`) and linting (`npm run lint`).
  - Commit Phase 1 deliverable with clean commit message on development branch.

---

### PHASE 2 — DATABASE ARCHITECTURE AND SUPABASE SECURITY
*Objective: Implement version-controlled migrations, revoke dangerous permissions, and build the 10 target entities.*

- **Task 2.1: Supabase CLI & Migration Setup**:
  - Initialize `supabase/` project structure (`config.toml`, `migrations/`).
  - Baseline existing hosted schema into `supabase/migrations/20261119000000_baseline.sql`.
- **Task 2.2: Privilege Hardening**:
  - Revoke `TRUNCATE`, `DELETE`, `TRIGGER`, `REFERENCES` from `anon` and `authenticated` roles on all tables.
  - Restrict `anon` strictly to authorized `SELECT` queries.
- **Task 2.3: Entity Creation & Relational Constraints**:
  - Author and apply additive migrations for `profiles`, `monitoring_stations`, `devices`, `system_alerts`, `water_quality_predictions`, `maintenance_logs`.
  - Add foreign keys (`station_id`, `device_id`) and performance indexes on `created_at`, `observed_at`.
- **Task 2.4: Supabase Auth Integration**:
  - Configure Supabase Auth handlers. Create database trigger `on_auth_user_created` to automatically provision a `profiles` record.
  - Enforce role integrity: Public signups default to role `'citizen'`. Authority roles can only be granted via administrative migration or verified admin flow.
- **Task 2.5: Supabase Storage Configuration**:
  - Create private storage bucket `pollution-evidence`.
  - Configure RLS policies allowing authenticated users to upload and view their own evidence, with signed URLs for authority inspection.

---

### PHASE 3 — FIREBASE RETIREMENT & CLEAN CUTOVER
*Objective: Safely decommission the deactivated Firebase instance and transition 100% of data reads and writes to Supabase.*

- **Task 3.1: Remove Firebase Fallback Logic**:
  - Remove dead Firebase Realtime Database connection attempts from `app.py`, `simulate_sensors.py`, and `serial_bridge.py`.
  - Eliminate Firebase-related timeout delays during server startup and request processing.
- **Task 3.2: Update Analytics & Summaries**:
  - Migrate `/api/authority/report-summary` to query Supabase `sensor_readings` and `pollution_reports` directly using PostgreSQL aggregations (`AVG()`, `COUNT()`).
- **Task 3.3: Dependency Cleanup**:
  - Remove `firebase-admin` from `backend/requirements.txt` and `firebase` npm packages from `frontend/package.json`.
  - Verify clean cutover with automated API integration tests.

---

### PHASE 4 — HARDWARE-READY IoT ARCHITECTURE
*Objective: Build the authenticated telemetry ingestion pipeline and upgrade firmware and simulator to match physical ESP32 requirements.*

- **Task 4.1: Telemetry Ingestion Endpoint (`POST /api/v1/telemetry/ingest`)**:
  - Implement token-based device authentication against `devices.credential_hash`.
  - Enforce payload validation, physical measurement range bounds, and message deduplication (`message_id`).
  - Separate device observation time (`observed_at`) from server arrival time (`received_at`).
- **Task 4.2: Hardware Telemetry Simulator Upgrade**:
  - Upgrade `backend/simulate_sensors.py` to authenticate against the new ingestion endpoint using pre-provisioned station and device credentials.
  - Implement realistic multi-station simulation (Assi Ghat, Dashashwamedh, Manikarnika).
  - Add failure scenarios: sensor disconnection (-127°C error), turbidity spikes, low DO.
- **Task 4.3: ESP32 Firmware Starter Implementation**:
  - Overhaul `arduino/firebase_sensor_upload.ino` into `firmware/esp32_telemetry_client.ino`:
    - Switch to secure HTTPS POST to River Sentinel backend.
    - Synchronize UTC time via NTP (`configTime`).
    - Implement non-blocking sensor acquisition and offline ring-buffer with flash-wear prevention.
    - Use credential configuration header (`config.h.example`).

---

### PHASE 5 — BACKEND API COMPLETION & REFINEMENT
*Objective: Complete all operational endpoints for stations, devices, alerts, and analytics.*

- **Task 5.1: Monitoring Station & Device Management**:
  - Implement endpoints for listing, viewing, registering, and deactivating stations and devices (`/api/stations`, `/api/devices`).
- **Task 5.2: Real Historical Telemetry Queries**:
  - Implement time-filtered queries (`/api/sensors/history?station=X&range=24h|7d|30d`) with downsampling for chart performance.
- **Task 5.3: Authority Alert Endpoints**:
  - Implement alert acknowledgement and resolution endpoints (`POST /api/alerts/<id>/acknowledge`, `POST /api/alerts/<id>/resolve`).
- **Task 5.4: Legitimate CSV Export**:
  - Replace synthetic `random.uniform()` generator in `/api/authority/export-data` with streaming export of verified database sensor readings.

---

### PHASE 6 — FRONTEND EXPERIENCE & DYNAMIC MAPS
*Objective: Replace all frontend mock components with live Supabase and Flask integrations.*

- **Task 6.1: Real Supabase Authentication UI**:
  - Wire `/login` and `/signup` to Supabase Auth (`supabase.auth.signInWithPassword`, `supabase.auth.signUp`).
  - Implement Next.js middleware (`middleware.ts`) to protect `/authority-dashboard` (requiring authority role) and `/citizen-dashboard`.
- **Task 6.2: Dynamic Station & Telemetry Map**:
  - Update `InteractiveMap.tsx` to fetch registered stations and latest sensor telemetry from the backend.
  - Display live status markers (Safe / Caution / Critical) based on actual parameter readings.
- **Task 6.3: Real Historical Trends Charting**:
  - Connect `HistoricalTrends.tsx` to `/api/sensors/history`.
  - Wire timeframe dropdown (`24 Hours`, `7 Days`, `30 Days`) to dynamic state; calculate real statistical averages (pH, turbidity, DO).
- **Task 6.4: Live Authority Analytics**:
  - Wire `AuthorityAnalytics.tsx` to real station aggregates and report resolution rates from Supabase.
- **Task 6.5: Clean UI States**:
  - Ensure every component includes proper loading skeletons, error handling, empty states, and data freshness timestamps.

---

### PHASE 7 — ALERT & NOTIFICATION ENGINE
*Objective: Build an automated, deduplicated alerting system for environmental anomalies and device failures.*

- **Task 7.1: Threshold Evaluation Rules**:
  - Implement background/inline rule evaluation:
    - High flood risk (water level $\ge$ 71.26 m or flood prob $\ge$ 70%).
    - Severe water pollution (DO $\le$ 3.0 mg/L or turbidity $\ge$ 150 NTU).
    - Device heartbeat timeout (device last seen $> 15\text{ minutes}$).
- **Task 7.2: Alert Deduplication & Persistence**:
  - Prevent flooding authorities with duplicate alerts for an ongoing condition.
  - Store alerts in `system_alerts` table with active flag.
- **Task 7.3: Authority Alert UI**:
  - Real-time alert badges in dashboard; one-click acknowledgement and resolution logging.

---

### PHASE 8 — MACHINE LEARNING REBUILD & SCIENTIFIC GROUNDING
*Objective: Rebuild models with temporal integrity and CPCB standard alignment.*

- **Task 8.1: Flood Model Temporal Retraining**:
  - Implement chronological train/test split (zero random shuffling).
  - Train and evaluate Random Forest and Gradient Boosting baselines on actual sequential records.
  - Report precision, recall, false-negative rate, and calibrated risk probabilities.
- **Task 8.2: Water Quality Transition to CPCB WQI**:
  - Shift from binary potability to Central Pollution Control Board (CPCB) Designated Best Use classification (Classes A–E).
  - Integrate UPPCB / CPCB monitoring data for Varanasi ghats.
  - Provide transparent rule-based and ML screening assessments with explicit laboratory disclaimers.

---

### PHASE 9 — DATA RELIABILITY, QUALITY & OBSERVABILITY
*Objective: Ensure data integrity across the ingestion pipeline.*

- **Task 9.1: Range & Anomaly Validation**:
  - Flag sensor spikes, calibration drift, and frozen sensor values.
- **Task 9.2: System Health & Observability**:
  - Implement comprehensive `/api/health` endpoint reporting database latency, active devices, and model inference metrics.

---

### PHASE 10 — SECURITY HARDENING
*Objective: Comprehensive application and infrastructure security enforcement.*

- **Task 10.1: JWT Verification & CORS Hardening**:
  - Validate Supabase JWT tokens on all protected Flask endpoints.
  - Configure strict CORS allowlisting for the Next.js frontend origin.
- **Task 10.2: Rate Limiting & Upload Hardening**:
  - Implement IP and device rate limiting using Flask-Limiter.
  - Validate image uploads by MIME type, file signature, and size ($\le 5\text{ MB}$).

---

### PHASE 11 — END-TO-END TESTING & INTEGRATION
*Objective: Comprehensive automated testing covering edge devices to UI.*

- **Task 11.1: Backend & API Test Suite**:
  - Pytest suite covering auth, ingestion, ML inference, and alert generation.
- **Task 11.2: End-to-End IoT Simulation Test**:
  - Multi-station simulation run verifying: ESP32 $\to$ Ingest $\to$ Supabase $\to$ Realtime Dashboard $\to$ Alert Trigger.

---

### PHASE 12 — PRODUCTION READINESS & DOCUMENTATION
*Objective: Final deployment checklist and operational runbooks.*

- **Task 12.1: Final Runbooks & Schemas**:
  - Produce operator documentation, sensor calibration guide, and disaster recovery runbook.
- **Task 12.2: Deployment Readiness Gate**:
  - Final review against all 20 Master Acceptance Criteria. Maintain application on local development until user explicitly authorizes cloud deployment.

---

## 3. Master Risk Register

| Risk ID | Category | Risk Description | Severity | Likelihood | Mitigation Strategy |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **RSK-01** | Database | Open `anon` permissions allow unauthorized writes or truncation | **Critical** | High | Revoke `ALL` from `anon` in Phase 2; enforce strict RLS and JWT verification. |
| **RSK-02** | Security | Mock frontend login allows unauthorized access to authority controls | **Critical** | High | Integrate Supabase Auth and server-side role checks in Phase 2 & 6. |
| **RSK-03** | Cloud | Deactivated Firebase RTDB causes timeouts and application errors | **High** | Certain | Fully cut over to Supabase in Phase 2 & 3; remove all Firebase references. |
| **RSK-04** | ML | Inflated ML accuracy claims mislead public on real flood/potability risks | **High** | High | Retrain models with temporal splits in Phase 8; maintain clear public screening disclaimers. |
| **RSK-05** | Hardware | Physical ESP32 unable to communicate with backend | **High** | Medium | Design standard HTTPS telemetry contract (`/api/v1/telemetry/ingest`) tested via simulator first in Phase 4. |
