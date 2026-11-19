# River Sentinel 2.0 — Phase 7: Background Worker Architecture & Runbook
**Document Date:** November 19, 2026  
**Module:** Background Processing, Outbox Queue & Worker Lifecycle  
**Target Environment:** Varanasi, Ganga River Monitoring  

---

## 1. Architectural Overview

River Sentinel 2.0 utilizes a PostgreSQL-backed Transactional Outbox pattern implemented in [backend/services/notification_worker.py](file:///c:/Project/RiverSentinel-main/backend/services/notification_worker.py). 

This design avoids introducing heavy distributed queue infrastructure (such as Redis, Celery, or RabbitMQ) while fulfilling critical enterprise guarantees:
1. **Zero Message Loss**: Outbox records are committed in the same database transaction as alert events.
2. **Concurrency Safety**: Multi-worker contention is prevented using PostgreSQL atomic row locking (`FOR UPDATE SKIP LOCKED`).
3. **Stuck Job Recovery**: If a worker crashes mid-delivery, abandoned `processing` jobs are automatically recovered.
4. **Bounded Backoff**: Retries scale exponentially up to a 1-hour cap.
5. **Dead-Letter Handling**: Permanent failures are isolated and never retried indefinitely.
6. **Worker Observability**: Process heartbeat, metrics, and state are persisted to `public.worker_heartbeats`.

---

## 2. Worker Lifecycle & Execution Modes

The worker can be operated via CLI commands or triggered programmatically.

### 2.1 Single Batch Execution (`--once`)
Processes a single batch of up to 20 pending deliveries and exits:
```bash
backend/venv/Scripts/python.exe backend/services/notification_worker.py --once
```

### 2.2 Continuous Daemon Mode (`--daemon`)
Runs an independent background daemon process with configurable polling cadence:
```bash
backend/venv/Scripts/python.exe backend/services/notification_worker.py --daemon --interval 5 --batch-size 20
```

### 2.3 Stuck-Job Recovery Sweep Only (`--recover-stuck`)
Performs a sweep of stuck jobs without processing outbox messages:
```bash
backend/venv/Scripts/python.exe backend/services/notification_worker.py --recover-stuck
```

---

## 3. Concurrency Control & Job Claiming

Workers atomically transition pending jobs from `queued` to `processing`:

```sql
UPDATE public.notification_deliveries
SET status = 'processing',
    updated_at = :now
WHERE id IN (
    SELECT id FROM public.notification_deliveries
    WHERE status IN ('queued', 'failed')
      AND attempt_count < max_attempts
      AND next_attempt_at <= :now
    ORDER BY created_at ASC
    LIMIT :limit
    FOR UPDATE SKIP LOCKED
)
RETURNING id, alert_id, recipient_user_id, recipient_phone, channel, provider, attempt_count, max_attempts, message_payload;
```

`FOR UPDATE SKIP LOCKED` guarantees that concurrent worker processes will never claim the same delivery record, eliminating duplicate SMS dispatches and race conditions.

---

## 4. Stuck-Job Recovery Mechanism

If a worker terminates unexpectedly (e.g. OOM killer, power failure, host restart) while processing a claimed batch, the delivery records remain with `status = 'processing'`.

The recovery sweep runs automatically before every outbox batch:
1. Identifies all records where `status = 'processing'` and `updated_at < (now - interval '5 minutes')`.
2. If `attempt_count >= max_attempts`: marks `status = 'failed'`, `last_error_code = 'STUCK_JOB_TIMEOUT'`.
3. If `attempt_count < max_attempts`: resets `status = 'queued'`, increments `attempt_count`, schedules immediate retry, and logs recovery.

---

## 5. Bounded Exponential Backoff & Failure Handling

When a transient provider error occurs (e.g., cellular network gateway busy):
- Retry interval formula:
  $$\text{backoff\_seconds} = \min(2^{\text{attempt}} \times 15\text{s}, 3600\text{s})$$
- Attempt 1: 30 seconds
- Attempt 2: 60 seconds
- Attempt 3: 120 seconds
- Max Cap: 3,600 seconds (1 hour).

### Permanent Failure Classification:
Deliveries are immediately marked as `failed` without retrying if:
- `attempt_count >= max_attempts` (default: 3).
- Recipient phone number is invalid or unparseable (`INVALID_PHONE`).
- Recipient has revoked SMS consent (`UNREGISTERED_RECIPIENT`).
- Cellular SMS Gateway is disabled in environment (`GATEWAY_UNCONFIGURED`).

---

## 6. Worker Observability & Graceful Shutdown

### Heartbeat Tracking (`public.worker_heartbeats`)
Every worker run records a heartbeat with metrics into PostgreSQL:
- `worker_name`: `'notification_worker'`
- `status`: `'running'`, `'idle'`, or `'stopped'`
- `last_heartbeat`: UTC timestamp
- `metrics`: JSON object containing processed, delivered, accepted, failed, and recovered counts.

### Graceful Signal Handling:
The worker traps `SIGINT` (Ctrl+C) and `SIGTERM`. When a shutdown signal is intercepted:
1. Flags `_SHUTDOWN_REQUESTED = True`.
2. Completes the currently in-flight claimed batch to prevent data corruption.
3. Updates `public.worker_heartbeats` with `status = 'stopped'`.
4. Terminates cleanly with zero stranded jobs.
