# River Sentinel 2.0 — Phase 7A: System-Wide Reliability Audit
**Audit Date:** November 19, 2026  
**Target Environment:** Varanasi, Ganga River Monitoring  
**Current Git Commit Baseline:** `114fd5762e0c6905a749c1c3f8ccc7ff350f6f64`  
**Development Branch:** `river-sentinel/phase-1-stabilization`  

---

## 1. Executive Summary & Audit Scope

This pre-implementation audit conducts an exhaustive inspection of the River Sentinel 2.0 architecture prior to executing Phase 7 reliability and observability hardening. 

The audit covers:
1. Git repository integrity and branch state.
2. Relational database schema, row counts, migration history, and RLS enforcement.
3. Flask backend application lifecycle, routing, and error management.
4. Next.js 16 frontend build, error handling, and state management.
5. Background worker architecture, outbox processing, and concurrency hazards.
6. IoT telemetry ingestion, sensor reliability, and edge hardware contract compatibility.
7. External service dependencies (Supabase, Groq AI, SMS Gateway, Weather).
8. ML model governance and artifact integrity.
9. Backup and disaster recovery readiness.

---

## 2. Component-by-Component Baseline Audit

### 2.1 Git Repository & Branch Status
- **Current Branch**: `river-sentinel/phase-1-stabilization` (Main branch remains untouched).
- **Current HEAD Commit**: `114fd57` (`feat(ml): complete Phase 6.1 model validation, governance, and operational readiness correction`).
- **Working Tree**: Clean. Zero uncommitted files or untracked changes at audit entry.
- **Remote Isolation**: Remote `origin` remains unpushed; deployments to Vercel/Render remain suppressed.

### 2.2 Relational Database & Migration History
The Supabase PostgreSQL database contains 15 public tables, all with Row Level Security (`rowsecurity = True`):

| Table Name | Live Row Count | Primary Key | Key Indexes & Constraints | RLS Enabled |
| :--- | :---: | :--- | :--- | :---: |
| `profiles` | 1 | `id` (UUID) | `idx_profiles_role` | Yes |
| `monitoring_stations` | 5 | `id` (UUID) | `monitoring_stations_station_code_key`, `idx_stations_status` | Yes |
| `devices` | 6 | `id` (UUID) | `devices_device_code_key`, `idx_devices_station`, `idx_devices_status` | Yes |
| `sensor_readings` | 22 | `id` (UUID) | `uq_sensor_message_id`, `idx_sensor_readings_created`, `idx_sensor_readings_station_created` | Yes |
| `cwc_reference_gauges` | 1 | `id` (UUID) | `cwc_reference_gauges_gauge_code_key` | Yes |
| `station_assignments` | 0 | `id` (UUID) | `station_assignments_station_id_user_id_key`, `idx_assignments_station`, `idx_assignments_user` | Yes |
| `pollution_reports` | 1 | `id` (UUID) | `idx_reports_status`, `idx_reports_created_by` | Yes |
| `system_alerts` | 85 | `id` (UUID) | `system_alerts_alert_code_key`, `idx_system_alerts_status`, `idx_system_alerts_category`, `idx_system_alerts_station`, `idx_system_alerts_active_dedup` | Yes |
| `alert_rules` | 7 | `id` (UUID) | `alert_rules_rule_code_key`, `idx_alert_rules_category`, `idx_alert_rules_station` | Yes |
| `alert_events` | 141 | `id` (UUID) | `idx_alert_events_alert_id` | Yes |
| `notification_deliveries`| 128 | `id` (UUID) | `notification_deliveries_idempotency_key_key`, `idx_notification_deliveries_outbox`, `idx_notification_deliveries_user_in_app` | Yes |
| `notification_preferences`| 1 | `id` (UUID) | `notification_preferences_user_id_key` | Yes |
| `flood_predictions` | 42 | `id` (UUID) | `idx_flood_station_created` | Yes |
| `device_telemetry_logs` | 55 | `id` (UUID) | `idx_telemetry_logs_device`, `idx_telemetry_logs_message` | Yes |
| `public_sensor_telemetry` | View/Table | — | Public sanitized projection | Yes |

- **Storage Bucket**: `pollution-evidence` (Private, `public = False`, objects count: 0).
- **Migration Sequence**:
  - `20261119000000_phase1a_security_remediation.sql`
  - `20261119000001_phase2_relational_schema_and_security.sql`
  - `20261119000002_phase3a_cwc_and_device_lifecycle.sql`
  - `20261119000003_phase5_alerts_and_notifications.sql`
  - `20261119000004_phase5_1_alert_hardening.sql`

### 2.3 Flask Application Startup & Health Architecture
- **Application Structure**: Factory pattern in `backend/app.py` registering 6 blueprints (`sensors_bp`, `predictions_bp`, `ai_bp`, `authority_bp`, `stations_v1_bp`, `alerts_v1_bp`).
- **Deficiencies Identified**:
  1. Single `/api/health` endpoint: Merely inspects presence of environment variables (`bool(os.getenv('SUPABASE_URL'))`), returning 200 even when database connections drop or fail completely.
  2. Missing `/api/health/live`: No dedicated lightweight liveness probe for process supervision.
  3. Missing `/api/health/ready`: No deep readiness probe checking database connectivity, required model artifacts, and background worker status.
  4. Missing operator status endpoint: No authenticated operational status dashboard for internal components.

### 2.4 Structured Logging & Error Handling
- **Current State**: Unstructured `print()` statements scattered throughout routes and services.
- **Deficiencies Identified**:
  1. No correlation ID (`X-Correlation-ID`) or request ID (`X-Request-ID`) propagation.
  2. No latency or duration metrics per HTTP response.
  3. Default Flask unhandled exception handler can leak internal error traces on 500 responses.
  4. No centralized audit log format (JSON structured log) for operational monitoring.
  5. Sensitive data exposure risk: Token and payload logging must be strictly sanitized.

### 2.5 Background Worker Reliability
- **Current State**: `NotificationWorker` in `backend/services/notification_worker.py` processes outbox batches.
- **Deficiencies Identified**:
  1. Trigger mechanism: Triggered via HTTP `POST /api/v1/notifications/process-outbox` or one-shot command line. No resilient continuous daemon worker.
  2. Stuck `processing` jobs: If a worker process terminates during execution, rows claimed with `status = 'processing'` remain locked indefinitely because there is no stuck-job timeout/reclaim logic.
  3. Worker heartbeat: No worker registration table or heartbeat recording in PostgreSQL.
  4. Graceful shutdown: No SIGINT/SIGTERM handlers to finish inflight deliveries before process exit.

### 2.6 Sensor Telemetry & Reliability
- **Current State**:
  - Simulator endpoint: `/api/telemetry/simulate` (`provenance: 'simulated'`, device_id NULL).
  - Physical edge endpoint: `/api/v1/telemetry/ingest` (schema 2.0, SHA-256 token validation, message idempotency).
- **Deficiencies Identified**:
  1. Timestamp validation: Ingest accepts arbitrary past timestamps without upper/lower drift guards.
  2. Fallback masking: `_validated_sensor()` in `routes/sensors.py` falls back to default constants (e.g. 28.0°C, 68.5m) when values are out of range or missing, risking treating disconnected or failing hardware as normal readings.
  3. Stale data detection: No automated API field indicating time elapsed since last physical observation or flagging stale sensor telemetry.
  4. Missing parameter reporting: No structured indication of which parameters are absent in a given transmission.

### 2.7 Database Performance & Indexes
- **Deficiencies Identified**:
  1. `notification_deliveries`: `idx_notification_deliveries_outbox` exists on `(status, next_attempt_at)`, but queries recovering stuck jobs require an index on `(status, updated_at)`.
  2. `sensor_readings`: Missing an index on `(station_id, created_at DESC)` combining `quality_status` for high-frequency filtering.
  3. `alert_events`: Missing index on `(created_at DESC)` for chronological audit trail queries.
  4. Unbounded queries: `get_reports_summary()` queries 200 rows without pagination.

### 2.8 AI Provider & External Gateway Resilience
- **Current State**: Groq integration (`qwen/qwen3.8-27b`) in `backend/routes/ai.py`.
- **Deficiencies Identified**:
  1. No explicit HTTP/client timeout on Groq completions (socket could hang indefinitely).
  2. Rate limit (HTTP 429) errors return generic 500 failures instead of user-friendly queue/quota notices.
  3. Image analysis writes directly to `pollution_reports` without explicit metadata tagging it as an automated visual screening.
  4. SMS gateway fallback: When SMS provider fails or is unconfigured, system properly marks outbox rows as failed, but needs worker-level retry boundary enforcement.

### 2.9 ML Model Governance Integrity
- **Current State**:
  - `flood_stage_forecaster_v1.pkl` (Ridge Regression, SHA-256: `4b550a87...`)
  - `water_quality_anomaly_detector_v1.pkl` (IsolationForest, SHA-256: `79c0cb13...`)
  - Deterministic CPCB Class B standards evaluator.
  - Retired legacy models preserved.
- **Requirement**: Zero promotion of experimental models; strict preservation of research status; graceful handling if model files are missing or unreadable.

---

## 3. Risk Matrix & Prioritized Remediation Plan

| Risk ID | Severity | Category | Description | Phase 7 Remediation |
| :--- | :---: | :--- | :--- | :--- |
| **R-01** | High | Health Checks | False healthy status when database is disconnected. | Implement `/api/health/live`, deep `/api/health/ready`, and authorized `/api/health/status`. |
| **R-02** | High | Workers | Stuck `processing` jobs remain abandoned if worker crashes. | Add stuck-job sweep (`processing` > 5 min -> requeue), daemon loop, and heartbeat logging. |
| **R-03** | Medium | Observability | Unstructured print statements; no correlation IDs; leaky 500 errors. | Structured JSON logging middleware, request correlation IDs, sanitized error handlers. |
| **R-04** | Medium | Telemetry | Out-of-bounds fallback constants mask disconnected hardware. | Explicit quality tagging (`quality_status = 'sensor_fault'`), timestamp validation, stale data metrics. |
| **R-05** | Medium | Database | Missing indexes on outbox recovery and event timelines; unindexed scans. | Migration `20261119000005_phase7_performance_indexes.sql` with targeted composite indexes. |
| **R-06** | Medium | Resilience | Unbounded Groq API calls with no client timeout or 429 rate limit guard. | Explicit 8s client timeout, retry backoff, graceful fallback messaging, clear visual screening tag. |
| **R-07** | High | Disaster Recovery | No verified backup and restore procedure tested against an isolated environment. | Automated backup script, isolated restore test, documented RPO/RTO targets vs measured recovery. |
| **R-08** | Medium | Frontend | Potential duplicate report submissions on rapid clicking; unhandled degradation. | Idempotency token / submit button disabling, explicit backend offline alert banner. |

---

## 4. Phase 7 Execution Sequence

1. **Phase 7B**: Deploy Liveness (`/api/health/live`), Readiness (`/api/health/ready`), and Authorized Service Status (`/api/health/status`).
2. **Phase 7C**: Implement structured logging middleware with correlation IDs, latency tracking, error classification, and sanitized error handlers.
3. **Phase 7D**: Refactor background worker architecture with daemon mode, graceful shutdown, stuck `processing` job recovery, and worker heartbeat.
4. **Phase 7E**: Enhance sensor data reliability with timestamp drift validation, stale reading detection, and explicit sensor fault tagging.
5. **Phase 7F**: Apply database index migration (`20261119000005`), query optimization, and formalize data retention/archival policies.
6. **Phase 7G**: Develop backup & disaster recovery tooling and execute an isolated restoration verification test.
7. **Phase 7H**: Harden frontend error boundaries, loading states, submission idempotency, and offline indicators.
8. **Phase 7I**: Harden Groq AI and SMS integrations with bounded timeouts, rate limit resilience, and screening provenance.
9. **Phase 7J**: Verify ML model governance, checksums, and missing-file fallback handling.
10. **Phase 7K & 7L**: Perform security regression audits and end-to-end integration tests (Workflows A–E).
11. **Phase 7M**: Complete all operational and documentation deliverables.
