# River Sentinel 2.0 — Phase 7: Database Performance & Data Retention
**Document Date:** November 19, 2026  
**Module:** Query Optimization, Indexing & Data Retention Architecture  
**Target Environment:** Varanasi, Ganga River Monitoring  

---

## 1. Query Patterns & Targeted Performance Indexing

To ensure low latency during high-frequency sensor ingestion and high-concurrency public dashboard queries, database query patterns were audited and reinforced via migration [supabase/migrations/20261119000005_phase7_performance_indexes.sql](file:///c:/Project/RiverSentinel-main/supabase/migrations/20261119000005_phase7_performance_indexes.sql).

### 1.1 Targeted Indexes Added in Phase 7

| Index Name | Target Table | Columns & Conditions | Justification |
| :--- | :--- | :--- | :--- |
| `idx_notification_deliveries_processing_recovery` | `notification_deliveries` | `(status, updated_at) WHERE status = 'processing'` | Fast sweep of abandoned jobs during crash recovery without full table scan. |
| `idx_sensor_readings_station_quality_created` | `sensor_readings` | `(station_id, created_at DESC, quality_status)` | Eliminates sequential scans during station telemetry history and stale data filtering. |
| `idx_alert_events_created_desc` | `alert_events` | `(alert_id, created_at DESC)` | High-speed incident timeline generation for authority audits. |
| `idx_pollution_reports_status_created` | `pollution_reports` | `(status, created_at DESC)` | Instant filtering of pending citizen pollution reports for authority review dashboards. |

### 1.2 Anti-Pattern Avoidance
- **No Blind Indexing**: Indexes were not added to low-cardinality flags (e.g. `is_simulated`) or small reference tables (`cwc_reference_gauges`).
- **Partial Indexing**: The worker recovery index is partial (`WHERE status = 'processing'`), keeping index size minimal (< 16 KB).
- **Preserved RLS**: All indexes operate seamlessly alongside active Row Level Security policies.

---

## 2. Query Bounds & Pagination Guardrails

All database access functions enforce strict upper bounds to prevent memory exhaustion:
1. `get_sensor_summary()`: Clamped to `LIMIT 50`.
2. `get_reports_summary()`: Clamped to `LIMIT 200`.
3. `list_system_alerts_v1()`: Default `limit = 100`, strictly clamped between 1 and 500.
4. `notification_worker`: Batch claiming clamped between 1 and 50.

---

## 3. Data Retention & Archival Policies

Scientific measurements and environmental legal evidence must be preserved with complete chronological integrity. River Sentinel enforces strict retention rules:

| Data Category | Table Name | Active Hot Retention | Archival Tier | Deletion Policy |
| :--- | :--- | :---: | :---: | :--- |
| **Sensor Telemetry** | `sensor_readings` | 365 Days (1 Year) | Cold Storage / S3 Parquet | **Never Deleted Automatically**. Retained permanently for Ganga hydrological modeling. |
| **Telemetry Audit Logs**| `device_telemetry_logs` | 90 Days | Compressed JSON | Pruned after 90 days following security audit sign-off. |
| **Alert Incidents** | `system_alerts` | 3 Years | Analytical Archive | Permanent statutory record for CWC/CPCB disaster compliance. |
| **Alert Lifecycle Events**| `alert_events` | 3 Years | Analytical Archive | Permanent statutory audit log. |
| **Notification Deliveries**| `notification_deliveries`| 180 Days | Compressed Archive | Retained 180 days for TRAI/DLT telephony audit compliance. |
| **Pollution Evidence** | `pollution_reports` / Bucket | Permanent | Glacier Deep Archive | Legal evidence. Requires explicit authority officer review before archival. |
| **Model Predictions** | `flood_predictions` | 180 Days | Research Logs | Retained for research validation against physical gauges. |

### Strict Non-Destruction Constraint:
No automated `CRON` or background task may run `TRUNCATE` or unverified `DELETE` against `sensor_readings` or `pollution_reports`. Any data movement must follow the verified backup and restoration procedure before table compaction.
