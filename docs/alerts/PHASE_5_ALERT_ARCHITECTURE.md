# River Sentinel 2.0 — Phase 5 Alert Engine Architecture

## 1. System Overview

The River Sentinel 2.0 Alert Engine is a real-time, database-backed threshold detection and lifecycle management system designed for the Varanasi Ganga River corridor. It evaluates incoming telemetry from physical IoT edge nodes (ESP32-WROOM-32), simulated telemetry, and citizen pollution reports against statutory CPCB (Central Pollution Control Board) Class B bathing criteria and CWC (Central Water Commission) hydrological reference datums.

```
+-----------------------------------------------------------------------------------+
|                              TELEMETRY INGESTION                                  |
|   - Physical ESP32 Hardware (/api/v1/telemetry/ingest)                            |
|   - Simulator Telemetry (/api/telemetry/simulate)                                 |
|   - Citizen Pollution Reports (/api/reports/submit)                               |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                                ALERT SERVICE                                      |
|   - CWC Flood Stage Screening (Warning: 70.26m, Danger: 71.26m MSL)               |
|   - CPCB Class B Water Quality Screening (pH: 6.5-8.5, DO >= 5.0mg/L, Turb <= 100)|
|   - IoT Hardware Node Stale Connectivity Detection (> 900s)                       |
|   - Pollution Incident Lodgement Triage                                           |
+------------------------------------------+----------------------------------------+
                                           |
                    +----------------------+----------------------+
                    |                                             |
                    v                                             v
+----------------------------------------+   +--------------------------------------+
|       DEDUPLICATION & LIFECYCLE        |   |         TRANSACTIONAL OUTBOX         |
| - Key: `CATEGORY:STATION_ID`           |   | - `notification_deliveries`          |
| - Increment `occurrence_count`         |   | - In-App: Immediate batch delivery   |
| - Escalate Severity (HIGH -> CRITICAL) |   | - SMS: Rate limited & backoff        |
| - Automated Hysteresis Recovery        |   | - SIMULATION STRICTLY SUPPRESSED     |
+----------------------------------------+   +--------------------------------------+
```

---

## 2. Relational Database Schema

The alert architecture persists across five dedicated PostgreSQL tables in Supabase:

### 2.1 `public.alert_rules`
Defines operational and environmental threshold rules:
- `id` (UUID, Primary Key)
- `rule_code` (VARCHAR(50), Unique Index, e.g. `RULE-CWC-FLOOD-DANGER`)
- `name` (VARCHAR(150))
- `category` (`FLOOD`, `WATER_QUALITY`, `DEVICE_HEALTH`, `POLLUTION_REPORT`)
- `station_id` (UUID, Foreign Key to `monitoring_stations.id`, nullable for network-wide rules)
- `parameter` (VARCHAR(50), e.g. `water_level`, `ph`, `do`, `turbidity`)
- `operator` (VARCHAR(10), e.g. `>`, `<`, `>=`, `<=`, `outside_range`)
- `threshold_value` (DOUBLE PRECISION)
- `threshold_unit` (VARCHAR(20), e.g. `m`, `mg/L`, `NTU`)
- `severity` (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`)
- `enabled` (BOOLEAN, default TRUE)
- `cooldown_seconds` (INTEGER, default 900)

### 2.2 `public.system_alerts`
Active, acknowledged, and resolved alert instances:
- `id` (UUID, Primary Key)
- `alert_code` (VARCHAR(50), Unique Index, format `ALT-YYYYMMDD-XXXX`)
- `station_id` (UUID, Foreign Key to `monitoring_stations.id`)
- `device_id` (UUID, Foreign Key to `devices.id`, nullable)
- `category` (VARCHAR(50))
- `severity` (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`)
- `title` (VARCHAR(255))
- `description` (TEXT)
- `source_type` (`sensor_reading`, `device_telemetry`, `pollution_report`)
- `source_record_id` (VARCHAR(100))
- `provenance` (`real_sensor`, `simulated`, `historical_backfill`, `manual_entry`)
- `quality_status` (`valid`, `provisional`, `degraded`, `out_of_range`)
- `measured_value` (DOUBLE PRECISION)
- `expected_threshold` (DOUBLE PRECISION)
- `threshold_unit` (VARCHAR(20))
- `deduplication_key` (VARCHAR(100), Unique Index on unclosed alerts)
- `status` (`active`, `acknowledged`, `resolved`)
- `occurrence_count` (INTEGER, default 1)
- `first_triggered_at` (TIMESTAMPTZ)
- `last_triggered_at` (TIMESTAMPTZ)
- `acknowledged_by` (UUID, Foreign Key to `auth.users.id`)
- `acknowledged_at` (TIMESTAMPTZ)
- `resolved_by` (UUID, Foreign Key to `auth.users.id`)
- `resolved_at` (TIMESTAMPTZ)
- `resolution_reason` (TEXT)

### 2.3 `public.alert_events`
Immutable append-only audit trail:
- `id` (UUID, Primary Key)
- `alert_id` (UUID, Foreign Key to `system_alerts.id` ON DELETE CASCADE)
- `event_type` (`triggered`, `repeated`, `escalated`, `acknowledged`, `resolved`, `reopened`)
- `actor_id` (UUID, nullable, Foreign Key to `auth.users.id`)
- `metadata` (JSONB)
- `created_at` (TIMESTAMPTZ)

### 2.4 `public.notification_preferences`
User-level notification routing and consent guardrails:
- `user_id` (UUID, Primary Key, Foreign Key to `auth.users.id`)
- `in_app_enabled` (BOOLEAN, default TRUE)
- `email_enabled` (BOOLEAN, default FALSE)
- `sms_enabled` (BOOLEAN, default FALSE)
- `preferred_severities` (TEXT[], default `['CRITICAL', 'HIGH']`)
- `preferred_categories` (TEXT[], default `['FLOOD', 'WATER_QUALITY', 'POLLUTION_REPORT']`)
- `phone_number_verified` (BOOLEAN, default FALSE)
- `email_verified` (BOOLEAN, default FALSE)
- `consent_timestamp` (TIMESTAMPTZ, nullable)

### 2.5 `public.notification_deliveries`
Transactional Outbox table:
- `id` (UUID, Primary Key)
- `alert_id` (UUID, Foreign Key to `system_alerts.id` ON DELETE CASCADE)
- `recipient_user_id` (UUID, Foreign Key to `auth.users.id`)
- `recipient_phone` (VARCHAR(20), nullable)
- `channel` (`in_app`, `sms`, `email`)
- `provider` (`internal`, `mock`, `cdac_sms`, `twilio`)
- `status` (`queued`, `processing`, `accepted`, `delivered`, `failed`, `cancelled`, `suppressed`)
- `attempt_count` (INTEGER, default 0)
- `max_attempts` (INTEGER, default 3)
- `next_attempt_at` (TIMESTAMPTZ)
- `error_code` (VARCHAR(50))
- `error_message` (TEXT)
- `idempotency_key` (VARCHAR(150), Unique)
- `message_payload` (JSONB)
- `read_at` (TIMESTAMPTZ, for in_app notifications)
- `created_at` (TIMESTAMPTZ)
- `updated_at` (TIMESTAMPTZ)

---

## 3. Regulatory Baselines & Engineering Principles

1. **Central Water Commission (CWC) GTS MSL Benchmark**:
   Water levels are measured against Great Trigonometrical Survey Mean Sea Level datums.
   - Assi Ghat Warning Level: **70.26 m MSL**
   - Assi Ghat Danger Level: **71.26 m MSL**
   - Historical High Flood Level (HFL, 1978): **73.90 m MSL**
   Flood alerts are strictly constrained to stations with verified `cwc_reference_gauge_id` bindings.

2. **Central Pollution Control Board (CPCB) Designated Best Use Criteria (Class B Bathing)**:
   - pH: **6.5 to 8.5**
   - Dissolved Oxygen (DO): **>= 5.0 mg/L**
   - Turbidity: **<= 100 NTU** (statutory riparian standard)

3. **Simulation Protection**:
   Telephonic SMS broadcasts are strictly suppressed for simulated readings (`provenance == 'simulated'`), preventing false alarms and protecting telephony budgets.
