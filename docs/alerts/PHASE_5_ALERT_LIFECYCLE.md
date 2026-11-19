# River Sentinel 2.0 — Alert Lifecycle, Granular Deduplication & Hysteresis Recovery (Phase 5.1 Hardened)

## 1. Lifecycle State Machine

Each alert progresses through a strict state machine governed by PostgreSQL constraints and immutable audit logs:

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

## 2. Granular Deduplication Strategy

Continuous telemetry transmits observations at high frequencies. Without granular deduplication, distinct parameters could collide or overwrite each other.

### 2.1 Granular Deduplication Key Architecture
To guarantee that simultaneous anomalies (e.g., low dissolved oxygen and high turbidity at the same station) generate independent alerts, deduplication keys incorporate the rule prefix, station ID, and target parameter:

| Alert Scenario | Granular Deduplication Key Format | Example |
| :--- | :--- | :--- |
| **CWC Flood Stage** | `RULE-CWC-FLOOD:{station_id}:water_level` | `RULE-CWC-FLOOD:e66507dc...:water_level` |
| **CPCB pH Range** | `RULE-CPCB-PH-RANGE:{station_id}:ph` | `RULE-CPCB-PH-RANGE:e66507dc...:ph` |
| **CPCB Minimum DO** | `RULE-CPCB-DO-MIN:{station_id}:do` | `RULE-CPCB-DO-MIN:e66507dc...:do` |
| **Turbidity Investigation** | `RULE-TURB-HIGH:{station_id}:turbidity` | `RULE-TURB-HIGH:e66507dc...:turbidity` |
| **IoT Node Connectivity** | `RULE-DEV-OFFLINE:{device_id}` | `RULE-DEV-OFFLINE:65d0490a...` |
| **Citizen Pollution Report** | `RULE-POLLUTION-NEW:{report_id}` | `RULE-POLLUTION-NEW:89a124ce...` |

### 2.2 Occurrence Counting & Severity Escalation
When a repeated deviating observation arrives matching an active alert's deduplication key:
1. No redundant row is created in `system_alerts`.
2. `occurrence_count` increments atomically.
3. `last_triggered_at` and `measured_value` update to reflect the latest reading.
4. If severity increases (e.g., river stage escalates from Warning to Danger), `severity` is elevated from `HIGH` to `CRITICAL` while preserving original rule identity, `rule_id`, and `rule_version`.
5. An audit entry of type `repeated` or `escalated` is written to `alert_events` with complete transition metadata.

---

## 3. Automated Recovery via Hysteresis Bands

To prevent "alert flapping" (rapid oscillating between active and resolved states when telemetry hovers around threshold boundaries), the engine enforces strict hysteresis recovery bands:

| Parameter | Trigger Threshold | Recovery Threshold | Hysteresis Buffer | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Water Level** | $\ge 70.26\text{ m}$ | $\le 70.11\text{ m}$ | $0.15\text{ m}$ | CWC Varanasi Datum |
| **pH (Acidic)** | $< 6.50$ | $\ge 6.60$ | $0.10\text{ pH}$ | CPCB Class B |
| **pH (Alkaline)** | $> 8.50$ | $\le 8.40$ | $0.10\text{ pH}$ | CPCB Class B |
| **Dissolved Oxygen** | $< 5.00\text{ mg/L}$ | $\ge 5.20\text{ mg/L}$ | $0.20\text{ mg/L}$ | CPCB Class B |
| **Turbidity** | $> 100.0\text{ NTU}$ | $\le 85.0\text{ NTU}$ | $15.0\text{ NTU}$ | Project Investigation Guideline v2.0 |
| **Device Heartbeat** | $> 900\text{ s}$ | $\le 900\text{ s}$ | Valid Reconnect | Recovers on fresh valid telemetry |

When telemetry satisfies the recovery condition:
1. `system_alerts.status` transitions automatically to `resolved`.
2. `resolved_at` is set to the current UTC timestamp.
3. `alert_events` logs a `resolved` audit event with recovery measurement details.
