# River Sentinel 2.0 — Transactional Notification Outbox & Delivery Subsystem

## 1. Architectural Pattern: Transactional Outbox

To decouple alert generation from network delivery (telephony gateways, push providers, email servers), River Sentinel 2.0 utilizes the **Transactional Outbox Pattern**:

```
+---------------------+
|    ALERT ENGINE     |
+----------+----------+
           | 1. Evaluates observation & triggers alert
           | 2. Inserts alert into public.system_alerts
           | 3. Inserts delivery jobs into public.notification_deliveries (Status: 'queued')
           v
+------------------------------------+
|  TABLE: notification_deliveries    |
+------------------+-----------------+
                   |
                   | 4. Polled / triggered asynchronously
                   v
+------------------------------------+
|        NOTIFICATION WORKER         |
|   - Concurrency: SKIP LOCKED       |
|   - Channel Routing: in_app / sms  |
|   - Rate Limiting: 10 msg/target   |
|   - Exponential Backoff            |
+------------------+-----------------+
                   |
         +---------+---------+
         |                   |
         v                   v
+-----------------+ +-----------------+
| IN-APP DELIVERY | | TELEPHONY (SMS) |
| Immediate mark  | | GSM 160-char    |
| as 'delivered'  | | Mock / HTTP     |
+-----------------+ +-----------------+
```

---

## 2. Notification Channels

### 2.1 In-App Notification Delivery
- **Target Audience**: Authority Administrators, Field Officers, and Citizens opting into in-app alerts.
- **Delivery Model**: Instant database delivery. When the worker claims the delivery job, it immediately marks status as `delivered`.
- **User Experience**:
  - Unread count badge rendered in the navigation header.
  - Interactive inbox in the Profile and Dashboard components.
  - Endpoints:
    - `GET /api/v1/notifications`: List inbox items.
    - `GET /api/v1/notifications/unread-count`: Unread counter.
    - `POST /api/v1/notifications/<delivery_id>/read`: Mark individual notification read.
    - `POST /api/v1/notifications/mark-all-read`: Mark all notifications read.

### 2.2 Telephonic SMS Broadcast
- **Target Audience**: Verified Authority Field Personnel and Citizens residing in high-risk riparian flood zones.
- **Carrier Rules**: Conforms to standard GSM 7-bit single-segment limits (160 characters).
- **Consent Gate**: Under TRAI Telecom Commercial Communications Customer Preference Regulations (TCCCPR, 2018), external cellular messages require:
  1. `sms_enabled = true`
  2. `phone_number_verified = true`
  3. Non-null `consent_timestamp`
  4. Non-simulated telemetry (`provenance == 'real_sensor'`)

---

## 3. Simulation Protection & Safety Rules

> [!IMPORTANT]
> **Strict External Telephony Safeguard**:
> When an alert is derived from simulated telemetry (`provenance == 'simulated'`), notification jobs are enqueued with `status = 'suppressed'`.
> Simulated observations **never** trigger live external cellular transmissions. This guarantees that simulated load tests or training drills never generate public panic or consume real telephony credits.

---

## 4. Worker Mechanics & Exponential Backoff

The background worker (`NotificationWorker.process_outbox_batch`) operates under the following parameters:

- **Batch Size**: 20 jobs per pass.
- **Concurrency Safety**: Queries use `FOR UPDATE SKIP LOCKED` to prevent duplicate claiming across multiple worker processes.
- **Max Attempts**: 3 attempts before moving to `failed`.
- **Backoff Strategy**: Exponential backoff where `delay_seconds = 30 * (2 ** (attempt - 1))`.
  - Attempt 1 failure: retry after 30 seconds.
  - Attempt 2 failure: retry after 60 seconds.
  - Attempt 3 failure: marked permanently as `failed`.
- **Trigger**: Can be invoked on a cron schedule or on-demand via `POST /api/v1/notifications/process-outbox`.
