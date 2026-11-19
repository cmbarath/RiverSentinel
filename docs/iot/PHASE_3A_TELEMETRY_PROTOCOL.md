# River Sentinel 2.0 — Phase 3A Telemetry Protocol Specification

## 1. Overview & Transport Protocol

The River Sentinel 2.0 IoT Telemetry Protocol defines the communication contract between physical edge microcontrollers (ESP32-WROOM-32) and the River Sentinel Flask backend.

- **Transport:** HTTPS (TLS 1.2 / 1.3)
- **Method:** `POST`
- **Endpoint:** `/api/v1/telemetry/ingest`
- **Encoding:** UTF-8 JSON (`Content-Type: application/json`)
- **Port:** 443 (Production HTTPS), 5000 (Development HTTP)

---

## 2. Authentication Headers

Every telemetry submission from a physical hardware node must present device identification and its high-entropy pre-shared key:

| Header | Description | Example |
| :--- | :--- | :--- |
| `X-Device-Code` | Registered hardware device identifier | `DEV-ESP32-ASSI-01` |
| `X-Device-Token` | High-entropy pre-shared secret token | `rs_dev_7a8f9c12b3e4...` |

*(If headers cannot be set by constrained legacy clients, `device_code` and `device_token` may be passed inside the top-level JSON payload).*

The server verifies the token against the device's stored SHA-256 digest in `public.devices.credential_hash` using constant-time comparison (`hmac.compare_digest`).

---

## 3. Telemetry Payload Schema (Version 2.0)

```json
{
  "schema_version": "2.0",
  "device_code": "DEV-ESP32-ASSI-01",
  "message_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "sequence_number": 42,
  "observed_at": "2026-11-19T07:15:30.000Z",
  "firmware_version": "v2.0.0-phase3a",
  "sensor_readings": {
    "ph": 7.42,
    "turbidity": 18.5,
    "temperature": 26.2,
    "humidity": 65.0,
    "ec": 490.0,
    "water_level": 68.35,
    "do": 6.85,
    "battery_pct": 94.2
  },
  "sensor_status": {
    "ph": "valid",
    "turbidity": "valid",
    "temperature": "valid",
    "humidity": "valid",
    "ec": "valid",
    "water_level": "valid",
    "do": "valid"
  },
  "calibration_status": {
    "ph_calibrated_at": "2026-11-01",
    "do_calibrated_at": "2026-11-01"
  }
}
```

### Field Definitions:

1. `schema_version` (string, required): Must strictly be `"2.0"`.
2. `device_code` (string, required): Must match the registered device code in `public.devices`.
3. `message_id` (string UUID v4, required): Unique identifier generated per measurement cycle. Reused identical `message_id` submissions are rejected with **HTTP 409 Conflict**.
4. `sequence_number` (integer $\ge 1$, required): Monotonically increasing message counter.
5. `observed_at` (string ISO 8601 UTC, required): Timestamp when the sensor reading was captured by the node.
6. `sensor_readings` (object, required):
   - `ph` (float, 0.0 – 14.0)
   - `turbidity` (float NTU, 0.0 – 3000.0)
   - `temperature` (float °C, -10.0 – 60.0)
   - `humidity` (float %, 0.0 – 100.0)
   - `ec` (float µS/cm, 0.0 – 10000.0)
   - `water_level` (float m, 0.0 – 100.0)
   - `do` (float mg/L, 0.0 – 25.0)
   - `battery_pct` (float %, 0.0 – 100.0)
7. `sensor_status` (object, optional): Quality indicator per probe (`valid`, `out_of_range`, `disconnected`, `uncalibrated`, `not_configured`).

---

## 4. API Response Specifications

### Success Response (HTTP 201 Created)
```json
{
  "status": "success",
  "message": "Telemetry ingested and verified successfully",
  "device_code": "DEV-ESP32-ASSI-01",
  "station_id": "e66507dc-7d0e-4bc7-9cd0-86848fc9b80d",
  "message_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "sequence_number": 42,
  "quality_status": "valid",
  "server_timestamp": "2026-11-19T07:15:30.852Z",
  "processing_time_ms": 14.2
}
```

### Authentication Failure (HTTP 401 Unauthorized)
```json
{
  "status": "error",
  "error_code": "AUTHENTICATION_FAILED",
  "message": "Authentication failed"
}
```

### Duplicate Message Acknowledged (HTTP 200 OK)
```json
{
  "status": "success",
  "duplicate": true,
  "message": "Message a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d was already processed and persisted.",
  "reading_id": "550e8400-e29b-41d4-a716-446655440000",
  "persisted_at": "2026-11-19T07:15:30.852Z",
  "quality_status": "valid"
}
```

---

## 5. Security & Isolation Rules

1. **Server-Derived Station ID:** The server derives `station_id` from the registered `devices` table. Any `station_id` supplied by the client is deliberately ignored to prevent rogue station spoofing.
2. **Simulator Isolation:** The simulator endpoint (`POST /api/telemetry/simulate`) requires a separate `X-Simulator-Token` and hardcodes `provenance = 'simulated'` with `device_id = NULL`. It cannot authenticate to `/api/v1/telemetry/ingest` or mark physical hardware as online.
