# River Sentinel 2.0 — Transactional Notification Outbox & Delivery Subsystem (Phase 5.1 Hardened)

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
|   - Outbox Guard: 1-50 batch limit |
|   - Rate Limiting: 2s cooldown     |
|   - Exponential Backoff            |
+------------------+-----------------+
                   |
         +---------+---------+
         |                   |
         v                   v
+-----------------+ +-----------------+
| IN-APP DELIVERY | | TELEPHONY (SMS) |
| Immediate mark  | | GSM 160 / UCS-2 |
| as 'delivered'  | | Status:         |
|                 | | 'accepted'      |
+-----------------+ +--------+--------+
                             |
                             | Carrier DLR Callback (Async Webhook)
                             v
                    +-----------------+
                    | FINAL DELIVERY  |
                    | Status:         |
                    | 'delivered'     |
                    +-----------------+
```

---

## 2. Delivery Status Accuracy Lifecycle

River Sentinel 2.0 enforces a strict distinction between gateway transmission acceptance and actual handset delivery:

```
[queued] ---> [processing] ---> [accepted] (Provider HTTP 200) ---> [delivered] (Carrier DLR Callback)
                                    |
                                    +---> [failed] (Carrier DLR Bounce / Expired)
```

1. **`queued`**: Alert created; delivery record waiting in outbox table with `next_attempt_at <= now()`.
2. **`processing`**: Atomically claimed by worker using `FOR UPDATE SKIP LOCKED`.
3. **`accepted`**: Provider successfully received and acknowledged the SMS request (HTTP 200). `accepted_at` timestamp is recorded, `provider_message_id` is stored, and `delivered_at` **remains NULL**.
4. **`delivered`**: Terminal delivery confirmed via asynchronous Delivery Receipt (DLR) webhook callback from the carrier. `delivered_at` and `provider_callback_received_at` timestamps are recorded.
5. **`failed`**: Delivery failed permanently (invalid phone number, unregistered DLT template, or carrier bounce).
6. **`suppressed`**: SMS delivery was suppressed to prevent external costs or confusion (e.g. simulated telemetry alert).

---

## 3. Worker Authorization & Execution Guards

The outbox processor endpoint `POST /api/v1/notifications/process-outbox` is strictly secured:
- **Authorization**:
  - Internal backend cron workers pass `X-Worker-Secret: <WORKER_API_SECRET>`.
  - Authorized human operators must hold the `authority_admin` JWT role.
  - Ordinary citizens and field officers receive **HTTP 403 Forbidden**.
- **Bounded Batch Size**: The `limit` query parameter is bounded between 1 and 50 (defaults to 20).
- **Execution Rate Limiting**: Enforces a minimum cooldown of 2 seconds between batch invocations (returning HTTP 429 when throttled).

---

## 4. Carrier Delivery Receipt (DLR) Webhook

External telephony providers push real-time handset delivery status to:
`POST /api/v1/notifications/callback/sms`

- **Webhook Authentication**: Verified using `X-SMS-Webhook-Token`.
- **Payload Acceptance**: Compatible with standard carrier callbacks (`provider_message_id`, `delivery_status`, `error_code`, `error_message`).
- **Replay Attack Prevention**: If a notification delivery record is already in a terminal state (`delivered`, `failed`, `cancelled`), subsequent duplicate callbacks are safely ignored (`status: 'ignored'`) without mutating state.
