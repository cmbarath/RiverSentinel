# River Sentinel 2.0 — Alert Lifecycle, Deduplication & Recovery

## 1. Lifecycle State Machine

Each alert progresses through a strict state machine governed by database constraints and audit logs:

```
                  +-------------------------+
                  |    Condition Detected   |
                  +------------+------------+
                               |
                               v
                     +-------------------+
                     |      ACTIVE       | <----+ (Repeated observation /
                     +---------+---------+      |  Escalation from HIGH to CRITICAL)
                               |                |
             +-----------------+----------------+
             |                                  |
             v                                  v
+------------------------+          +------------------------+
|      ACKNOWLEDGED      |          |     AUTO-RESOLVED      |
|  (Officer logs notes)  |          | (Telemetry returns to  |
+-----------+------------+          |   hysteresis threshold)|
            |                       +------------------------+
            v                                   ^
+------------------------+                      |
|    MANUALLY RESOLVED   |----------------------+
| (Officer logs reason)  |
+------------------------+
```

---

## 2. Deduplication Strategy

Continuous telemetry from real sensors or simulators transmits observations every few seconds or minutes. Without deduplication, this would flood the database with duplicate alerts.

### 2.1 Deduplication Key
Each open alert has a unique deduplication key:
- **Flood**: `FLOOD:<station_id>`
- **Water Quality**: `WQ:<parameter>:<station_id>`
- **Device Health**: `DEVICE_OFFLINE:<device_id>`
- **Citizen Report**: `POLLUTION_REPORT:<report_id>`

### 2.2 Occurrence Counting & Severity Escalation
When a deviating reading arrives with an existing active or acknowledged alert for the same deduplication key:
1. No new row is inserted into `system_alerts`.
2. `occurrence_count` increments by 1.
3. `last_triggered_at` and `measured_value` are updated to reflect the latest reading.
4. If severity increases (e.g. river stage rises from Warning to Danger), severity updates from `HIGH` to `CRITICAL`.
5. An audit event of type `repeated` or `escalated` is appended to `alert_events`.

---

## 3. Automated Recovery via Hysteresis

To prevent "alert flapping" (rapid oscillating between active and resolved states when a measurement hovers around a threshold), the engine enforces hysteresis bands:

| Parameter | Trigger Threshold | Recovery Threshold | Hysteresis Buffer |
| :--- | :--- | :--- | :--- |
| Water Level | `>= 70.26 m` | `<= 70.11 m` | 0.15 m |
| pH (Acidic) | `< 6.50` | `>= 6.60` | 0.10 pH |
| pH (Alkaline) | `> 8.50` | `<= 8.40` | 0.10 pH |
| Dissolved Oxygen | `< 5.00 mg/L` | `>= 5.20 mg/L` | 0.20 mg/L |
| Turbidity | `> 100.0 NTU` | `<= 90.0 NTU` | 10.0 NTU |
| Device Heartbeat | `> 900 s` | `<= 900 s` | Reconnect |

When telemetry satisfies the recovery condition:
1. `system_alerts.status` transitions to `resolved`.
2. `resolved_at` is set to the current UTC timestamp.
3. `resolution_reason` records the telemetry recovery measurement.
4. An event of type `resolved` is appended to `alert_events`.

---

## 4. Role-Based Human Operations

Field Officers and Authority Administrators can intervene manually:

### 4.1 Acknowledge Alert
- Endpoint: `POST /api/v1/alerts/<alert_id>/acknowledge`
- Permissions: `authority_admin`, `field_officer`
- Requires: Optional operational notes.
- Action: Sets `status = 'acknowledged'`, records `acknowledged_by` and `acknowledged_at`, and appends an `acknowledged` event to `alert_events`.

### 4.2 Resolve Alert
- Endpoint: `POST /api/v1/alerts/<alert_id>/resolve`
- Permissions: `authority_admin`, `field_officer`
- Requires: Mandatory resolution reason (minimum 5 characters).
- Action: Sets `status = 'resolved'`, records `resolved_by`, `resolved_at`, and `resolution_reason`, and appends a `resolved` event to `alert_events`.
