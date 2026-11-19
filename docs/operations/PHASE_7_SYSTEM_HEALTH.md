# River Sentinel 2.0 — Phase 7: Application Health & Readiness Specification
**Document Date:** November 19, 2026  
**Module:** Health, Diagnostics & Liveness Architecture  
**Target Environment:** Varanasi, Ganga River Monitoring  

---

## 1. Architectural Overview

River Sentinel 2.0 decouples operational health into distinct conceptual tiers:
1. **Liveness (`/api/health/live`)**: Indicates whether the Flask application server is responsive and accepting network connections. It never fails due to downstream external service outages.
2. **Readiness (`/api/health/ready`)**: Deep probe verifying whether the service is capable of serving traffic safely. Validates Supabase PostgreSQL connectivity, model artifacts, and background worker status.
3. **Operational Diagnostics (`/api/health/status`)**: Authenticated endpoint for system operators and administrators providing detailed metrics across all subsystems (Database, Storage, AI, Inference, Alerts, Telemetry, Workers).

---

## 2. Liveness Endpoint Specification

### `GET /api/health/live`
- **Access**: Public / Anonymous.
- **Purpose**: Container and supervisor liveness checking.
- **Latency**: `< 1 ms`.
- **Failure Conditions**: Only fails if Flask process has terminated or deadlocked.

#### Sample Response (HTTP 200 OK):
```json
{
  "service": "River Sentinel 2.0 API Server",
  "status": "alive",
  "timestamp": "2026-11-19T13:20:00.000000+00:00",
  "uptime_seconds": 1240.5
}
```

---

## 3. Readiness Endpoint Specification

### `GET /api/health/ready`
- **Access**: Public / Anonymous (Strict zero credential leakage).
- **Purpose**: Kubernetes/traffic routing readiness probe.
- **Evaluated Dependencies**:
  - Direct PostgreSQL database ping (`SELECT 1;`) and latency measurement.
  - Presence of versioned ML model artifacts (`flood_stage_forecaster_v1.pkl`, `water_quality_anomaly_detector_v1.pkl`).
  - Background worker heartbeat freshness (within 10-minute window).
  - Optional provider configurations (Groq AI, SMS Gateway).

#### State Machine:
- **`healthy` (HTTP 200)**: Database is connected with latency `< 1000ms`, required model artifacts are loaded, and core services are operational.
- **`degraded` (HTTP 200)**: Database is connected, but an optional provider (Groq API, SMS Gateway) is disabled or unconfigured, or a non-critical model is in fallback mode.
- **`unavailable` (HTTP 503)**: Database connectivity is broken or times out. Traffic must be redirected or queued.

#### Sample Response (HTTP 200 OK — Healthy):
```json
{
  "database": {
    "latency_ms": 422.58,
    "status": "connected"
  },
  "models": {
    "anomaly_detector_ready": true,
    "cpcb_evaluator_ready": true,
    "flood_forecaster_ready": true
  },
  "optional_services": {
    "groq_ai": "configured",
    "sms_gateway": "disabled"
  },
  "status": "healthy",
  "timestamp": "2026-11-19T13:20:02.625102+00:00",
  "uptime_seconds": 1242.0,
  "workers": {
    "notification_worker_active": true,
    "notification_worker_status": "running"
  }
}
```

#### Security Guardrails:
- Database hostnames, credentials, and connection strings are strictly redacted.
- No internal tracebacks or environment variable contents are exposed.

---

## 4. Authorized Operational Diagnostics

### `GET /api/health/status`
- **Access**: Restricted. Requires:
  - Header `X-Worker-Secret` matching `WORKER_API_SECRET`, OR
  - Supabase Bearer token for a user with role `authority_admin`.
- **Anonymous Access**: Rejects with `HTTP 403 Forbidden`.

#### Sample Response (HTTP 200 OK):
```json
{
  "status": "success",
  "server_timestamp": "2026-11-19T13:20:14.000000+00:00",
  "uptime_seconds": 1254.3,
  "database": {
    "provider": "Supabase PostgreSQL",
    "status": "connected",
    "latency_ms": 422.58,
    "total_sensor_readings": 23
  },
  "storage": {
    "bucket": "pollution-evidence",
    "access": "private_rls"
  },
  "groq_ai": {
    "configured": true,
    "model": "qwen/qwen3.8-27b"
  },
  "flood_inference": {
    "model_version": "flood_stage_forecaster_v1",
    "algorithm": "Ridge Regression",
    "status": "research_only",
    "alert_eligible": false,
    "artifact_ready": true
  },
  "water_quality_evaluation": {
    "standards_evaluator": "CPCB Class B Primary Water Quality Criteria",
    "anomaly_detector": "IsolationForest v1",
    "screening_status": "experimental_screening_only",
    "alert_eligible": false,
    "artifact_ready": true
  },
  "alert_engine": {
    "status": "operational",
    "active_incidents": 16
  },
  "notification_worker": {
    "heartbeat": {
      "registered": true,
      "status": "running",
      "is_active": true,
      "last_heartbeat": "2026-11-19 13:19:26.515646+00:00"
    },
    "outbox_metrics": {
      "queued": 0,
      "processing": 0,
      "failed": 28,
      "delivered": 50,
      "accepted": 50,
      "stuck_processing": 0
    }
  },
  "telephony": {
    "sms_enabled": false,
    "provider": "mock",
    "sender_id": "RIVSEN"
  }
}
```
