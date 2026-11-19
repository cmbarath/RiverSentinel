# River Sentinel 2.0 — Phase 4 Pre-Implementation Audit
**Comprehensive Gap Analysis, Database Mapping & Feature Matrix**

---

### Audit Metadata
- **Audit Date:** 2026-11-19
- **Git Branch:** `river-sentinel/phase-1-stabilization`
- **Base Commit:** `b4a5bf7`
- **Working Tree:** Clean
- **Database Target:** Supabase PostgreSQL `xqzobddgkawysprpmkpk` (`river-sentinel-dev`, `ap-southeast-1`)

---

## 1. Pre-Implementation Safety & Baseline Check

### 1.1 Git Tree & Branch Verification
- Active branch is `river-sentinel/phase-1-stabilization`.
- Head commit is `b4a5bf7` (`feat(iot): complete Phase 3A.1 security hardening, retry reliability and firmware verification`).
- Working tree is clean. Unstaged changes: 0. Untracked files: 0.

### 1.2 Live Supabase Schema Inventory
Inspection of `information_schema.tables` in public schema reveals 10 entities:

| Table / View | Type | Rows | Purpose |
| :--- | :---: | :---: | :--- |
| `cwc_reference_gauges` | Table | 1 | Official CWC Varanasi Reference Gauge metadata (Warning: 70.26m, Danger: 71.26m, HFL: 73.90m) |
| `monitoring_stations` | Table | 4 | Registered monitoring stations (Assi, Dashashwamedh, Manikarnika, Rajghat; all `planned`) |
| `devices` | Table | 4 | Registered edge devices (`DEV-ESP32-ASSI-01` .. `RAJG-04`; all `provisioned`) |
| `device_telemetry_logs` | Table | 21 | Ingestion audit log for sequence, payload size, processing time, IP |
| `sensor_readings` | Table | 16 | Authoritative time-series sensor measurements |
| `public_sensor_telemetry` | View | 16 | Sanitized public view excluding device IDs and internal tokens |
| `pollution_reports` | Table | 1 | Citizen pollution reports with images and status |
| `flood_predictions` | Table | 20 | ML flood risk inference history |
| `profiles` | Table | 0 | User profile and RBAC store (roles: `citizen`, `field_officer`, `authority_admin`) |
| `station_assignments` | Table | 0 | Authority staff station assignments |

---

## 2. Frontend Component Audit & Mock Inventory

Inspection of `frontend/src/components/dashboard/` and dashboard pages identified significant reliance on hardcoded mock arrays, artificial timeouts, and unbacked metrics:

### 2.1 `HistoricalTrends.tsx`
- **Status:** **100% Mock / Placeholder**
- **Existing Implementation:**
  - Hardcoded array `const data = [{ time: "06:00", ph: 7.2 ... }]` (7 static points).
  - Unconnected `<select>` dropdown (Last 24h, 7d, 30d).
  - Hardcoded summary cards: Avg pH 7.3 (+0.2), Avg Turbidity 4.6 (-1.2 NTU), Avg Temp 23 (-2°C), Peak Pollution 12:15 PM.
  - Hardcoded textual insight block.
- **Required Action:** Replace with database-backed API querying `sensor_readings` by station, parameter, and timeframe.

### 2.2 `AuthorityAnalytics.tsx`
- **Status:** **100% Mock / Placeholder**
- **Existing Implementation:**
  - Hardcoded `statusData`: Safe: 8, Caution: 3, Unsafe: 1.
  - Hardcoded `paramData`: 5 static ghats with static pH and turbidity bars.
  - Hardcoded KPI values: Uptime: 99.98%, Data Latency: 1.2s, Report Processing: 4min, AI Accuracy: 87.4%.
- **Required Action:** Replace with actual aggregations from `monitoring_stations`, `devices`, `sensor_readings`, `pollution_reports`, and `flood_predictions`.

### 2.3 `SafetyChecker.tsx`
- **Status:** **Partially Connected / Flawed Evaluation**
- **Existing Implementation:**
  - Hardcoded list of 12 ghats in static array.
  - Regardless of selected ghat, reads the global single latest reading via `useSensorData()`.
  - Naive evaluation rules: `ph >= 6.5 && ph <= 8.5 && turbidity < 10` claimed as "safe for religious bathing", and with `ec < 500` claimed as "safe for drinking".
- **Required Action:**
  - User selects actual registered stations from database.
  - Fetch latest reading specifically for selected station.
  - Report unavailable/stale status if no recent telemetry.
  - Separate drinking water screening, bathing water screening, ecological limits, and anomaly detection.
  - Document reference standards (CPCB / BIS IS 10500:2012) and disclaim single-sensor limitations.

### 2.4 `ProfileAndNotif.tsx`
- **Status:** **100% Mock / Placeholder**
- **Existing Implementation:**
  - Hardcoded user identity: "Aviral Sharma", "Member since Dec 2025", "RIVER GUARDIAN".
  - Hardcoded statistics: 25 Reports Submitted, 1.2k Lives Impacted, 12 Sensors Verified, 3 Rewards Claimed.
  - Hardcoded alerts: Fake flood alert, fake points notification.
- **Required Action:** Bind to authenticated user profile via Supabase Auth + `/api/auth/me` and fetch user's real pollution reports via `/api/citizen/my-reports`.

### 2.5 `SendSMSAlerts.tsx`
- **Status:** **Fake Simulation (`setTimeout`)**
- **Existing Implementation:**
  - `setTimeout(..., 2500)` simulating SMS broadcast.
  - Pop-up alert: `"SMS Alert sent to 45,230 residents in the Varanasi Ghat area."`
  - Hardcoded stats: 45.2k Active Subscribers, ₹6,750 Estimated Cost.
- **Required Action:** Remove fake confirmation and recipient stats. Present clear status indicating SMS gateway is not configured (Phase 5 milestone).

### 2.6 `DatasetUpload.tsx`
- **Status:** **Fake Simulation (`setTimeout`)**
- **Existing Implementation:**
  - `setTimeout(..., 2000)` simulating upload of 2,450 rows.
  - Hardcoded recent uploads table.
- **Required Action:** Remove fake processing alert. Clarify that model datasets require staging/validation (Phase 6) and cannot be injected into live sensor telemetry.

### 2.7 `RewardsDashboard.tsx`
- **Status:** **Mock Gamification**
- **Existing Implementation:**
  - Hardcoded 1,250 points, Amazon vouchers, certificates, local leaderboard.
- **Required Action:** Remove from primary operational navigation. Document as deferred citizen-engagement feature.

### 2.8 `CommandCenter.tsx`
- **Status:** **Partially Real, Partially Mock**
- **Existing Implementation:**
  - Hardcoded KPI values: Active Stations 11/12, Critical Alerts 03, Pending Reports 14, System Health 98.5%.
  - Actions call real `/api/authority/export-data` and template notices, but SMS endpoint simulates fake recipients.
- **Required Action:** Bind KPIs to live database counts and tie actions to real operations.

---

## 3. Database Source Mapping for Dashboard Metrics

| Dashboard UI Component | Metric / Value | Authoritative Database Source | Current Source | Status |
| :--- | :--- | :--- | :--- | :---: |
| **Header / Nav** | User Name & Role | `public.profiles` (`full_name`, `role`) via JWT | Hardcoded "Aviral" | **To Fix** |
| **Historical Trends** | Parameter Time Series | `public.sensor_readings` (`observed_at`, `ph`, `turbidity`, etc.) | Static `data` array | **To Fix** |
| **Historical Trends** | Period Min/Max/Avg | SQL aggregation over `sensor_readings` | Static numbers | **To Fix** |
| **Safety Checker** | Station List | `public.monitoring_stations` (`id`, `station_name`, `status`) | Static `ghats` array | **To Fix** |
| **Safety Checker** | Latest Ghat Readings | `public.sensor_readings` filtered by `station_id` | Global single reading | **To Fix** |
| **Safety Checker** | Safety Verdict | Transparent multi-criteria standard (CPCB/BIS) | In-component expression | **To Fix** |
| **Authority Analytics** | Station Status Breakdown | `SELECT status, count(*) FROM monitoring_stations GROUP BY status` | Hardcoded 8/3/1 | **To Fix** |
| **Authority Analytics** | Device Status Breakdown | `SELECT status, count(*) FROM devices GROUP BY status` | Hardcoded uptime | **To Fix** |
| **Authority Analytics** | Pollution Report Stats | `SELECT status, count(*) FROM pollution_reports GROUP BY status` | None | **To Fix** |
| **Authority Analytics** | Flood Prediction Risk | `SELECT risk_level, count(*) FROM flood_predictions` | None | **To Fix** |
| **Profile** | User Information | `public.profiles` where `id = auth.uid()` | Hardcoded "Aviral" | **To Fix** |
| **Profile** | User Submitted Reports | `public.pollution_reports` where `created_by = auth.uid()` | Hardcoded "25" | **To Fix** |
| **Command Center** | Station Counts | `monitoring_stations` live counts | Hardcoded "11/12" | **To Fix** |
| **Command Center** | Pending Reports | `pollution_reports WHERE status = 'submitted'` | Hardcoded "14" | **To Fix** |

---

## 4. Comprehensive Feature Matrix

| Feature | Category | Implementation State | Required Action in Phase 4 |
| :--- | :--- | :---: | :--- |
| **JWT & Role Authentication** | Security | **Completed** | Preserve existing Flask `@require_role` and JWT verification |
| **Schema 2.0 Telemetry Ingestion** | IoT | **Completed** | Preserve existing `/api/v1/telemetry/ingest` and duplicate retry |
| **CWC Varanasi Reference Gauge** | Scientific | **Completed** | Retain official thresholds (70.26m Warning, 71.26m Danger) |
| **Station Registry API (`/api/v1/stations`)** | Backend API | **Partially Completed** | Formalize versioned endpoints with latest readings & runtime lifecycle |
| **Historical Sensor API (`/api/v1/stations/{id}/readings`)** | Backend API | **Not Implemented** | Implement time filters (24h, 7d, 30d, custom), pagination, UTC |
| **Station Analytics API (`/api/v1/stations/{id}/analytics`)** | Backend API | **Not Implemented** | Implement min/max/avg, reading counts, and quality distributions |
| **System-wide Analytics API (`/api/v1/analytics/overview`)** | Backend API | **Not Implemented** | Implement database aggregations for authority dashboard |
| **Filtered CSV Export API** | Backend API | **Partially Completed** | Add station, parameter, date range, and provenance query parameters |
| **Historical Trends Chart** | Frontend | **Mock / Placeholder** | Connect to `/api/v1/stations/{id}/readings` with actual Recharts data |
| **Authority Analytics Charts** | Frontend | **Mock / Placeholder** | Connect to `/api/v1/analytics/overview` with real database aggregations |
| **Dynamic Station Safety Checker** | Frontend | **Partially Completed** | Refactor to per-station evaluation, transparent limits, no single-point claims |
| **Citizen Profile & Report Tracking** | Frontend | **Mock / Placeholder** | Connect to real Supabase session, profile, and user reports |
| **SMS Broadcast Gateway** | Alerts | **Requires External Provider** | Remove fake setTimeout, indicate gateway unconfigured, defer to Phase 5 |
| **ML Dataset Staging & Ingestion** | ML Ops | **Deferred** | Remove fake upload confirmation, prepare schema-validated staging, defer to Phase 6 |
| **Gamification Rewards & Points** | Community | **Mock / Placeholder** | Remove from active navigation, document as optional future feature |
| **Interactive Map Station Display** | Frontend | **Partially Completed** | Ensure station status matches database (`planned`, `active`, etc.) |
| **Groq AI Chatbot & Image Analysis** | AI | **Completed** | Preserve existing Qwen 2.5 72B / 3.8 27B integrations and disclaimers |

---

## 5. Implementation Strategy for Phase 4

1. **Phase 4B:** Implement versioned station routes (`/api/v1/stations/*`), historical parameter queries, system analytics overview, and filtered CSV export in Flask.
2. **Phase 4C:** Overhaul `HistoricalTrends.tsx` with dynamic station and parameter selectors, database-backed data series, loading/error/empty states, and statistical summaries.
3. **Phase 4D:** Overhaul `AuthorityAnalytics.tsx` with live database counts for stations, devices, readings, reports, and predictions.
4. **Phase 4E:** Overhaul `SafetyChecker.tsx` to evaluate station-specific readings against documented scientific screening benchmarks (CPCB / BIS IS 10500:2012) without claiming drinking water safety from raw probes.
5. **Phase 4F:** Overhaul `ProfileAndNotif.tsx` to read the real user's profile and user's submitted reports.
6. **Phase 4G:** Clean up `SendSMSAlerts.tsx`, `DatasetUpload.tsx`, and navigation in `citizen-dashboard/page.tsx` and `authority-dashboard/page.tsx`.
7. **Phase 4H & 4I:** Verify Interactive Map and ensure AI features remain preserved.
8. **Testing & Documentation:** Execute comprehensive regression and new integration tests; deliver documentation.
