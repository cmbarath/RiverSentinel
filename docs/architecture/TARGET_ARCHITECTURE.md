# TARGET SYSTEM ARCHITECTURE (TO-BE)
**Project:** River Sentinel 2.0  
**Design Phase:** Master Engineering Specification  
**Status:** Approved Architectural Target  

---

## 1. Vision & Core Principles

River Sentinel 2.0 is designed as an end-to-end, hardware-ready, enterprise-grade river monitoring platform.

### Core Architectural Principles:
1. **Single Authoritative Data Store**: Supabase PostgreSQL serves as the authoritative source of truth. All Firebase dependencies are decommissioned.
2. **Modular Layered Architecture**: The monolithic Flask script is refactored into distinct blueprints, services, database repositories, and ML inference pipelines.
3. **Hardware-First Telemetry Contract**: Ingestion from simulated and physical ESP32 devices passes through an authenticated, versioned, idempotent telemetry ingestion API (`/api/v1/telemetry/ingest`).
4. **Security by Default**: Supabase Auth with JWT verification, role-based authorization (`citizen`, `field_officer`, `authority_admin`), and strict Row-Level Security (RLS) policies.
5. **Private Object Storage**: Large binary payloads (pollution photos, reports) are stored in private Supabase Storage buckets, referenced via UUIDs and accessed through signed URLs.

---

## 2. Target Architectural Diagram

```mermaid
flowchart TD
    subgraph EdgeTier ["Hardware & Edge Telemetry Tier"]
        ESP32["ESP32 Microcontroller (Wi-Fi + HTTPS)"]
        Simulator["Hardware Simulator (Multi-Station)"]
        Sensors["Hardware Sensors (pH, Turbidity, Temp, DO, EC, Level)"]
        Sensors --> ESP32
    end

    subgraph IngestionAuth ["Device Ingestion & Security"]
        DeviceAuth["Device Token / HMAC Verification"]
        RateLimiter["Ingestion Rate Limiting & Deduping"]
    end

    subgraph BackendServices ["Modular Flask Backend Architecture"]
        IngestRouter["/api/v1/telemetry/ingest"]
        StationSvc["Station & Device Management Service"]
        AlertEngine["Alert & Notification Engine"]
        MLService["ML Inference Service (Flood & Water Quality)"]
        AIService["AI Service (Groq Chat & Vision)"]
        AuthMiddleware["Supabase JWT Auth & Role Guard"]
    end

    subgraph DatabaseTier ["Authoritative Supabase PostgreSQL Tier"]
        DBProfiles["profiles (Role-based)"]
        DBStations["monitoring_stations (Ghats)"]
        DBDevices["devices (ESP32 Credentials & Status)"]
        DBReadings["sensor_readings (Partitioned / Indexed)"]
        DBReports["pollution_reports (Workflow-tracked)"]
        DBFlood["flood_predictions (Versioned & Provenance)"]
        DBWQ["water_quality_predictions (CPCB WQI)"]
        DBAlerts["system_alerts (Deduplicated & Acknowledged)"]
        DBStorage["storage.buckets (Private pollution-evidence)"]
    end

    subgraph ClientTier ["Next.js 16 Presentation Tier"]
        CitizenApp["Citizen Portal (Public Water Safety, Reports, Chatbot)"]
        AuthorityApp["Authority Operations (Ghat Map, Device Status, Alerts)"]
    end

    %% Edge to Ingestion
    ESP32 -->|HTTPS POST JSON + Token| IngestRouter
    Simulator -->|HTTPS POST JSON + Token| IngestRouter
    IngestRouter --> DeviceAuth --> RateLimiter

    %% Ingestion to Backend & DB
    RateLimiter --> IngestRouter
    IngestRouter --> DBReadings
    IngestRouter --> AlertEngine
    AlertEngine --> DBAlerts

    %% Backend to ML & Storage
    IngestRouter -.->|Async Evaluate| MLService
    MLService --> DBFlood
    MLService --> DBWQ
    AIService --> DBStorage

    %% Client Interactions
    ClientTier --> AuthMiddleware
    AuthMiddleware --> StationSvc
    AuthMiddleware --> AIService
    AuthMiddleware --> MLService
    ClientTier -->|Supabase Realtime (RLS)| DBReadings
    ClientTier -->|Supabase Realtime (RLS)| DBAlerts
```

---

## 3. Authoritative Database Schema Design

The target schema establishes 10 core relational entities in PostgreSQL:

### 1. `profiles`
- `id` (`uuid`, Primary Key, references `auth.users(id)` ON DELETE CASCADE)
- `full_name` (`text`)
- `phone` (`varchar(20)`)
- `role` (`varchar(30)`, default `'citizen'`) — Values: `'citizen'`, `'field_officer'`, `'authority_admin'`
- `organization` (`varchar(100)`)
- `department` (`varchar(100)`)
- `created_at` (`timestamptz`, default `now()`)
- `updated_at` (`timestamptz`, default `now()`)

### 2. `monitoring_stations`
- `id` (`varchar(50)`, Primary Key, e.g. `'station_assi_ghat'`)
- `name` (`varchar(100)`, e.g. `'Assi Ghat Monitoring Station'`)
- `river` (`varchar(50)`, default `'Ganga'`)
- `location_description` (`text`)
- `latitude` (`numeric(9,6)`, NOT NULL)
- `longitude` (`numeric(9,6)`, NOT NULL)
- `status` (`varchar(20)`, default `'active'`)
- `warning_water_level_m` (`numeric(6,2)`, default `71.26`)
- `danger_water_level_m` (`numeric(6,2)`, default `73.23`)
- `created_at` (`timestamptz`, default `now()`)

### 3. `devices`
- `id` (`varchar(50)`, Primary Key, e.g. `'esp32_assi_01'`)
- `station_id` (`varchar(50)`, references `monitoring_stations(id)`)
- `device_type` (`varchar(50)`, default `'ESP32-WROOM-32'`)
- `firmware_version` (`varchar(20)`)
- `credential_hash` (`varchar(128)`, NOT NULL) — SHA-256 hash of device secret token
- `status` (`varchar(20)`, default `'provisioned'`) — `'active'`, `'inactive'`, `'revoked'`
- `last_seen_at` (`timestamptz`)
- `battery_level_pct` (`numeric(5,2)`)
- `created_at` (`timestamptz`, default `now()`)

### 4. `sensor_readings`
- `id` (`bigserial`, Primary Key)
- `station_id` (`varchar(50)`, references `monitoring_stations(id)`)
- `device_id` (`varchar(50)`, references `devices(id)`)
- `message_id` (`uuid`, Unique, for idempotency and duplicate elimination)
- `observed_at` (`timestamptz`, NOT NULL) — Device observation timestamp
- `received_at` (`timestamptz`, default `now()`) — Server receipt timestamp
- `ph` (`numeric(5,2)`)
- `turbidity_ntu` (`numeric(7,2)`)
- `temperature_c` (`numeric(5,2)`)
- `humidity_pct` (`numeric(5,2)`)
- `ec_us_cm` (`numeric(8,2)`)
- `water_level_m` (`numeric(6,2)`)
- `bod_mg_l` (`numeric(6,2)`)
- `cod_mg_l` (`numeric(6,2)`)
- `do_mg_l` (`numeric(5,2)`)
- `provenance` (`varchar(30)`, default `'real_sensor'`) — `'real_sensor'`, `'simulated'`, `'laboratory'`, `'manual'`
- `quality_status` (`varchar(30)`, default `'valid'`) — `'valid'`, `'suspect'`, `'out_of_range'`
- `raw_payload` (`jsonb`)

### 5. `pollution_reports`
- `id` (`bigserial`, Primary Key)
- `reporter_id` (`uuid`, references `profiles(id)`)
- `station_id` (`varchar(50)`, references `monitoring_stations(id)`)
- `location_name` (`varchar(100)`)
- `latitude` (`numeric(9,6)`)
- `longitude` (`numeric(9,6)`)
- `pollution_level` (`varchar(20)`)
- `pollutants` (`jsonb`)
- `assessment` (`text`)
- `description` (`text`)
- `evidence_storage_path` (`text`) — Reference in Supabase Storage
- `status` (`varchar(20)`, default `'PENDING'`) — `'PENDING'`, `'INVESTIGATING'`, `'VERIFIED'`, `'REJECTED'`, `'RESOLVED'`
- `assigned_to` (`uuid`, references `profiles(id)`)
- `created_at` (`timestamptz`, default `now()`)

### 6. `flood_predictions`
- `id` (`bigserial`, Primary Key)
- `station_id` (`varchar(50)`, references `monitoring_stations(id)`)
- `predicted_at` (`timestamptz`, default `now()`)
- `forecast_horizon_hours` (`integer`, default `24`)
- `risk_level` (`varchar(20)`, NOT NULL)
- `flood_probability` (`numeric(5,2)`, NOT NULL)
- `water_level_m` (`numeric(6,2)`)
- `discharge_cumec` (`numeric(10,2)`)
- `rain_varanasi_mm` (`numeric(6,2)`)
- `rain_upstream_mm` (`numeric(6,2)`)
- `model_version` (`varchar(30)`, default `'v2.0-rf-6feat'`)
- `reasons` (`jsonb`)
- `provenance` (`varchar(30)`, default `'operational'`)

### 7. `water_quality_predictions`
- `id` (`bigserial`, Primary Key)
- `station_id` (`varchar(50)`, references `monitoring_stations(id)`)
- `predicted_at` (`timestamptz`, default `now()`)
- `cpcb_class` (`varchar(10)`) — `'Class A'`, `'Class B'`, `'Class C'`, `'Class D'`, `'Class E'`
- `wqi_score` (`numeric(5,2)`)
- `limiting_parameters` (`jsonb`)
- `model_version` (`varchar(30)`)
- `provenance` (`varchar(30)`)

### 8. `system_alerts`
- `id` (`bigserial`, Primary Key)
- `station_id` (`varchar(50)`, references `monitoring_stations(id)`)
- `device_id` (`varchar(50)`, references `devices(id)`)
- `alert_type` (`varchar(50)`) — `'FLOOD_WARNING'`, `'WATER_POLLUTION'`, `'DEVICE_OFFLINE'`, `'SENSOR_SPIKE'`
- `severity` (`varchar(20)`) — `'INFO'`, `'WARNING'`, `'CRITICAL'`
- `title` (`varchar(150)`)
- `message` (`text`)
- `is_active` (`boolean`, default `true`)
- `acknowledged_by` (`uuid`, references `profiles(id)`)
- `acknowledged_at` (`timestamptz`)
- `resolved_at` (`timestamptz`)
- `created_at` (`timestamptz`, default `now()`)

### 9. `acoustic_events` *(Reserved for Future Hydrophone Monitoring)*
- `id` (`bigserial`, Primary Key)
- `station_id` (`varchar(50)`, references `monitoring_stations(id)`)
- `event_timestamp` (`timestamptz`, default `now()`)
- `classification` (`varchar(50)`, default `'UNCLASSIFIED_EXPERIMENTAL'`)
- `confidence` (`numeric(5,2)`)
- `audio_storage_path` (`text`)
- `notes` (`text`)

### 10. `maintenance_logs`
- `id` (`bigserial`, Primary Key)
- `station_id` (`varchar(50)`, references `monitoring_stations(id)`)
- `device_id` (`varchar(50)`, references `devices(id)`)
- `technician_id` (`uuid`, references `profiles(id)`)
- `activity_type` (`varchar(50)`) — `'CALIBRATION'`, `'SENSOR_REPLACEMENT'`, `'FIRMWARE_FLASH'`
- `details` (`text`)
- `performed_at` (`timestamptz`, default `now()`)

---

## 4. Telemetry Ingestion Contract Specification

### Endpoint: `POST /api/v1/telemetry/ingest`
- **Headers**:
  ```http
  Content-Type: application/json
  X-Device-Id: esp32_assi_01
  X-Device-Token: <pre-shared device token or HMAC signature>
  ```
- **Request Body Contract**:
  ```json
  {
    "message_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "station_id": "station_assi_ghat",
    "device_id": "esp32_assi_01",
    "observed_at": "2026-11-19T05:30:00Z",
    "firmware_version": "v2.1.0",
    "telemetry": {
      "ph": 7.42,
      "turbidity_ntu": 12.8,
      "temperature_c": 26.5,
      "humidity_pct": 68.0,
      "ec_us_cm": 460.0,
      "water_level_m": 67.85,
      "do_mg_l": 7.1
    },
    "provenance": "real_sensor",
    "status": {
      "battery_pct": 94.5,
      "sensor_errors": []
    }
  }
  ```
- **Validation & Processing Steps**:
  1. Authenticate `X-Device-Id` against `devices.credential_hash`. Confirm status is `'active'`.
  2. Verify idempotency using `message_id`. If already ingested, return HTTP 200 with cached ACK.
  3. Validate physical ranges (e.g., pH $0 \le \text{pH} \le 14$; temperature $-5 \le T \le 55$; dissolved oxygen $0 \le \text{DO} \le 20$). Mark invalid values with `quality_status = 'out_of_range'`.
  4. Write validated reading to `sensor_readings`.
  5. Update `devices.last_seen_at = now()`.
  6. Trigger alert rules if thresholds exceed statutory limits (e.g., water level $\ge$ warning level).
  7. Return response:
     ```json
     {
       "status": "success",
       "message_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
       "received_at": "2026-11-19T05:30:01.125Z"
     }
     ```
