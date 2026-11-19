# River Sentinel 2.0 — Phase 7: Structured Logging & Observability Runbook
**Document Date:** November 19, 2026  
**Module:** Logging, Tracing & Operational Monitoring  
**Target Environment:** Varanasi, Ganga River Monitoring  

---

## 1. Structured Logging Architecture

River Sentinel 2.0 implements end-to-end request tracing and structured JSON logging across all backend services via [backend/services/logging_service.py](file:///c:/Project/RiverSentinel-main/backend/services/logging_service.py).

### 1.1 Traceability Headers
Every HTTP transaction passing through the Flask backend includes two correlation headers:
- `X-Correlation-ID`: Cross-service transaction tracking identifier. Extracted from incoming client headers or generated as a UUID4 string.
- `X-Request-ID`: Unique single-hop request identifier (`req-<hex>`).

Both headers are injected into Flask's `g` request context and returned in all HTTP response headers, ensuring users, edge hardware, and administrators can correlate client issues with server logs.

---

## 2. Structured JSON Log Schema

All request completions, background worker executions, and system events emit single-line JSON log objects:

```json
{
  "timestamp": "2026-11-19 18:50:50,537",
  "level": "INFO",
  "logger": "river_sentinel",
  "message": "GET /api/health/live 200 (0.0ms)",
  "correlation_id": "e11a2297-f6cb-4e7e-90ea-e76f7e94b954",
  "request_id": "req-310dccd78912",
  "route": "/api/health/live",
  "method": "GET",
  "status_code": 200,
  "duration_ms": 0.0,
  "client_ip": "127.0.0.1"
}
```

### Log Levels:
- `INFO`: Normal operational requests (HTTP 200–399) and worker batch processing.
- `WARNING`: Client errors (HTTP 400–499), throttled outbox requests, or rate-limited AI calls.
- `ERROR`: Server-side failures (HTTP 500+), unhandled exceptions, or database disconnects.

---

## 3. Data Sanitization & Credential Protection

The logging pipeline applies automatic, recursive dictionary sanitization (`sanitize_dict`) before any payload is logged or written:
1. **Redacted Key Patterns**: Any key containing `token`, `password`, `secret`, `key`, `auth`, `jwt`, `device_token`, `authorization`, `bearer`, `cookie`, or `evidence` is replaced with `[REDACTED]`.
2. **Binary & Image Redaction**: Uploaded base64 images or multipart file streams are strictly suppressed from logs.
3. **Truncation Guard**: String payloads exceeding 500 characters are truncated with `... [TRUNCATED]` to prevent log exhaustion.

---

## 4. Log Rotation & Retention Policies

- **Log File Location**: `backend/logs/app.log` (Excluded from git tracking via `.gitignore`).
- **Rotation Strategy**: `RotatingFileHandler` triggers rotation when `app.log` reaches **10 Megabytes** (`10 * 1024 * 1024` bytes).
- **Retention Count**: Keeps **5 rotated backups** (`app.log.1` through `app.log.5`), limiting maximum local disk usage to 60 MB.
- **Retention Schedule**:
  - Application operational logs: 30 days active retention.
  - Telemetry audit logs (`device_telemetry_logs` table): 90 days.
  - Security and incident audit logs (`alert_events` table): Permanent statutory retention.

---

## 5. Global Error Classification & User-Facing Masking

Unhandled exceptions are intercepted by Flask error handlers:
- Operators receive detailed tracebacks in `backend/logs/app.log`.
- Public/Citizen clients receive sanitized JSON:

```json
{
  "status": "error",
  "error": "Internal Server Error",
  "error_code": "INTERNAL_SERVER_ERROR",
  "message": "An unexpected error occurred. Please quote the correlation ID for assistance.",
  "correlation_id": "c7e723de-a65d-4f38-9b4d-146c82894def"
}
```
No database connection parameters, SQL queries, or internal stack traces are disclosed.
