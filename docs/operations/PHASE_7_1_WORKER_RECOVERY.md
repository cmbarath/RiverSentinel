# River Sentinel 2.0 — Phase 7.1 Background Worker Recovery & Heartbeat Resumption
**Document Reference:** `docs/operations/PHASE_7_1_WORKER_RECOVERY.md`  
**Execution Milestone:** Phase 7.1 Disaster Recovery & System Regression Audit  
**Authoritative Environment:** Supabase PostgreSQL 15 (`public.worker_heartbeats`)  
**Target Basin:** Ganga River Basin, Varanasi, Uttar Pradesh, India  
**Last Verified Execution:** November 19, 2026

---

## 1. Executive Summary

River Sentinel 2.0 employs asynchronous background workers to manage non-blocking operations:
1. **Notification Outbox Worker (`notification_outbox_worker`):** Polls pending notification deliveries (`public.notification_deliveries`), handles rate limiting, executes SMS/Email telephony dispatches, and manages exponential backoff retries.
2. **Telemetry Ingestion & Watchdog Workers:** Monitors sensor freshness and identifies offline hardware nodes.

Following a database recovery event or node restart, background worker processes must safely reconnect, verify heartbeat synchronization, and resume processing pending outbox jobs without duplicate dispatches or dropped alerts.

---

## 2. Heartbeat Database Schema & Health States

Worker operational health is tracked authoritatively in `public.worker_heartbeats`:

```sql
CREATE TABLE public.worker_heartbeats (
    worker_name VARCHAR(100) PRIMARY KEY,
    last_heartbeat TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    status VARCHAR(50) NOT NULL DEFAULT 'running',
    metrics JSONB DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);
```

### Health Thresholds:
- **HEALTHY (`status: 'running'`):** Heartbeat recorded within the last **60 seconds**.
- **STALE / DEGRADED:** Heartbeat older than **60 seconds** but under **300 seconds** (flags process hang, GC pause, or network stall).
- **DEAD / FAILED:** No heartbeat recorded for over **300 seconds** (triggers automated process supervisor restart and alerts system administrators).

### Current Authoritative Worker Record:
```json
{
  "worker_name": "notification_outbox_worker",
  "status": "running",
  "last_heartbeat": "2026-11-19T14:11:02.000000+00:00",
  "metrics": {
    "processed_count": 142,
    "error_count": 0,
    "queue_depth": 0
  }
}
```

---

## 3. Worker Reconnection & Outbox Recovery Lifecycle

When the PostgreSQL database is restored or restarted, the worker recovery lifecycle proceeds through four deterministic stages:

```
+-----------------------------------------------------------------------------------------+
|                  BACKGROUND WORKER DISASTER RECOVERY LIFECYCLE                         |
+-----------------------------------------------------------------------------------------+
| STAGE 1: CONNECTION RE-ESTABLISHMENT & DATABASE PROBE                                  |
|          Worker initiates exponential backoff ping to /api/health/ready                |
|          Confirms PostgreSQL pooler is accepting connections.                          |
+-----------------------------------------------------------------------------------------+
| STAGE 2: LEASE & LOCK RE-ACQUISITION                                                    |
|          Queries public.worker_heartbeats for existing worker lease.                   |
|          If previous heartbeat > 300s, claims ownership and resets status='running'.    |
+-----------------------------------------------------------------------------------------+
| STAGE 3: OUTBOX DEDUPLICATION & RECONCILIATION                                          |
|          Scans public.notification_deliveries for stuck 'processing' records.           |
|          Resets items locked > 5 minutes back to 'pending' with incremented attempts.   |
|          Enforces idempotency keys to prevent duplicate SMS/Email transmission.        |
+-----------------------------------------------------------------------------------------+
| STAGE 4: ACTIVE EVENT LOOP & PERIODIC HEARTBEAT                                         |
|          Dispatches pending queue items in chronological priority order.               |
|          Emits heartbeat every 30 seconds with queue telemetry.                        |
+-----------------------------------------------------------------------------------------+
```

---

## 4. Worker Recovery Runbook

### 4.1 Automated Worker Startup Command
To manually start or verify the background notification worker in development/staging:

```bash
cd C:\Project\RiverSentinel-main
backend\venv\Scripts\python.exe backend/scripts/run_outbox_worker.py
```

### 4.2 Verifying Heartbeat Status
Execute the health check endpoint:

```bash
curl -s http://localhost:5000/api/health/status \
  -H "Authorization: Bearer <ADMIN_OR_OPERATOR_JWT>" | jq .worker_status
```

Expected response:
```json
{
  "notification_outbox_worker": {
    "status": "healthy",
    "last_seen_seconds_ago": 12.4,
    "queue_depth": 0,
    "is_stale": false
  }
}
```

### 4.3 Handling Stuck 'Processing' Records (Anti-Duplication Protection)
If a worker crashes while actively communicating with a telephony provider, an outbox item might remain stuck in `status: 'processing'`. River Sentinel prevents duplicate dispatches via `idempotency_key` (SHA-256 of `alert_id:recipient_user_id:channel`).

To reconcile orphan processing items:
```sql
UPDATE public.notification_deliveries
SET status = 'pending',
    attempt_count = attempt_count + 1,
    next_attempt_at = now() + interval '30 seconds',
    updated_at = now()
WHERE status = 'processing'
  AND updated_at < now() - interval '5 minutes';
```

---

## 5. Production Process Supervisor Configuration (Systemd)

For production Linux deployments, the worker is managed by `systemd` with automatic restart and exponential restart backoff:

```ini
# /etc/systemd/system/river-sentinel-outbox.service
[Unit]
Description=River Sentinel Notification Outbox Worker
After=network.target

[Service]
Type=simple
User=riversentinel
WorkingDirectory=/var/www/river-sentinel
ExecStart=/var/www/river-sentinel/backend/venv/bin/python backend/scripts/run_outbox_worker.py
Restart=always
RestartSec=5s
Environment=SUPABASE_URL=https://xqzobddgkawysprpmkpk.supabase.co
Environment=SUPABASE_DB_HOST=aws-0-ap-southeast-1.pooler.supabase.com
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```
