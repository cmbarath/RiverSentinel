# River Sentinel 2.0 — Phase 3A.1 Retry Reliability & Offline Queue
**Idempotent HTTP 200 Telemetry Contract & Bounded Circular Offline Buffer**

---

## 1. Network Failure Modes in River IoT Deployments

Field deployments along the Ganga River ghats in Varanasi face transient cellular and Wi-Fi disconnects:
- **Packet Loss During Upstream Transmit:** Node transmits payload, but backend never receives it.
- **Packet Loss During Downstream ACK:** Backend receives, validates, and persists payload to Supabase, but the ACK response is lost due to an antenna drop or cellular tower handover.
- **Microcontroller Brownout / Reset:** ESP32 resets while awaiting acknowledgment, prompting a reboot and immediate queue retransmission.

Without an idempotent retry contract, retrying unacknowledged messages would either:
1. Generate duplicate sensor rows in the database, distorting statistical averages and historical trends.
2. Throw an unhandled HTTP 409 conflict that confuses firmware clients into discarding unsent buffered readings.

---

## 2. Standardized Idempotent Ingestion Contract

The production telemetry ingestion route (`POST /api/v1/telemetry/ingest`) enforces a strict idempotency contract using the client's `message_id` (UUID v4):

### 2.1 First Submission (HTTP 201 Created)
When a telemetry payload is received for the first time:
1. Validates device credentials and message schema.
2. Performs range and calibration quality evaluations.
3. Inserts record into `public.sensor_readings`.
4. Updates device `last_seen_at` and battery levels in `public.devices`.
5. Logs request to `public.device_telemetry_logs`.
6. Returns **HTTP 201 Created** with the persisted `reading_id`.

```json
{
  "status": "success",
  "message": "Telemetry ingested and verified successfully",
  "reading_id": 41,
  "device_code": "DEV-ESP32-ASSI-01",
  "message_id": "c1a932bb-564f-4d64-8848-8df0e78c801e",
  "sequence_number": 42,
  "quality_status": "valid",
  "server_timestamp": "2026-11-19T02:45:00.000Z"
}
```

### 2.2 Repeated Submission / Network Retry (HTTP 200 OK)
If an identical `message_id` is submitted again:
1. Authenticates device credentials.
2. Checks `public.sensor_readings` for matching `device_message_id`.
3. Detects existing record.
4. **Does NOT insert a second database row.**
5. Returns **HTTP 200 OK** with `duplicate: true`, the original `reading_id`, and initial persistence timestamp.

```json
{
  "status": "success",
  "duplicate": true,
  "message": "Message c1a932bb-564f-4d64-8848-8df0e78c801e was already processed and persisted.",
  "reading_id": 41,
  "persisted_at": "2026-11-19T02:45:00.000Z",
  "quality_status": "valid"
}
```

---

## 3. ESP32 Offline Queue Architecture

The firmware implements a static circular ring buffer (`arduino/river_sentinel_esp32/offline_queue.h`) stored in RAM to buffer readings during network dropouts:

```
[ Head ] -> [ Message 1 ] -> [ Message 2 ] -> ... -> [ Tail ]
   ^                                                     |
   |_____________________________________________________|
```

### 3.1 Queue Operations
- **`enqueue(msgId, seq, payload)`:** Adds message at tail. If buffer is full (`_count == _capacity`), the oldest unacknowledged message is dropped (`_head` advanced) to prevent memory exhaustion on constrained microcontrollers.
- **`peek(outMsg)`:** Inspects message at head without dequeuing.
- **`dequeue()`:** Frees message at head upon receiving a valid server acknowledgment.

### 3.2 Firmware Acknowledgment Semantics

In `river_sentinel_esp32.ino`, the transmission loop verifies acknowledgment status:

```cpp
int res = telemetryClient.sendTelemetry(qMsg.jsonPayload);
bool isAck = (res == 201 || res == 200 || res == 409);

if (isAck) {
    // Backend successfully received or previously recorded the reading
    offlineQueue.dequeue();
    Serial.println(F("[Queue] Message acknowledged by server. Popped from buffer."));
} else {
    // Genuine server error (500, 502, 503) or network timeout (-1, -2)
    // Retain message in buffer for subsequent retry cycle
    Serial.println(F("[Queue] Transmission failed. Retaining message in queue."));
    break;
}
```

### 3.3 Genuine Error vs Acknowledgment Matrix

| HTTP / Network Code | Interpretation | Offline Queue Action |
| :--- | :--- | :--- |
| **HTTP 201** | Successfully created | Dequeue (`pop`) |
| **HTTP 200** | Duplicate acknowledged | Dequeue (`pop`) |
| **HTTP 409** | Legacy conflict acknowledged | Dequeue (`pop`) |
| **HTTP 401 / 403** | Auth failed / Revoked | Retain & log critical alert |
| **HTTP 5xx** | Server error / DB failure | **Retain in queue** |
| **HTTP 429** | Rate limited | **Retain in queue** |
| **Return -1 / -2** | Wi-Fi / DNS / TLS failed | **Retain in queue** |
