# River Sentinel 2.0 — Phase 4 Historical Trends Dashboard Specification

This document details the architecture, component implementation, and data-flow for the overhauled **Historical Trends Dashboard** (`frontend/src/components/dashboard/HistoricalTrends.tsx`).

---

## 1. Problem Statement & Audit Findings

The Phase 0 and Phase 4A audits identified the previous `HistoricalTrends.tsx` component as completely non-functional and decoupled from the backend:
- It rendered a static array of 7 points from 06:00 to 00:00 with fabricated pH and Turbidity values.
- Timeframe `<select>` had no `onChange` handler or data binding.
- Summary metric cards ("Avg pH 7.3", "Peak Pollution 12:15 PM") were hardcoded strings.
- There was no station selector; the dashboard did not reflect which Varanasi ghat was being queried.

---

## 2. Overhauled Architecture

The redesigned `HistoricalTrends.tsx` connects directly to the versioned backend REST endpoints:
1. `GET /api/v1/stations`: Discovers registered monitoring stations and populates the station selector.
2. `GET /api/v1/stations/<station_id>/readings`: Fetches parameterized historical time-series observations.
3. `GET /api/v1/export/sensor-data`: Streams filtered CSV exports directly to user downloads.

---

## 3. UI Controls & Dynamic Capabilities

### 3.1. Station Selection
- Dropdown dynamically populates with all registered stations from PostgreSQL (`monitoring_stations`).
- Displays station name, station code, and lifecycle status (`ACTIVE`, `PLANNED`, `MAINTENANCE`).
- Default selection points to the first active station (Assi Ghat).

### 3.2. Parameter Filter
Allows isolating specific sensor streams or reviewing full river health:
- `Overview (All Key Parameters)`: Multi-line chart tracking pH, Turbidity, DO, and Temperature across dual Y-axes.
- `pH Level` (pH units): Area chart with CPCB Class B reference lines at 6.5 and 8.5.
- `Turbidity` (NTU): Area chart with silt and ritual bathing runoff context.
- `Water Temperature` (°C).
- `River Stage / Level` (m MSL): Area chart with Central Water Commission (CWC) Warning Stage (70.26m) and Danger Stage (71.26m) reference lines.
- `Electrical Conductivity` (µS/cm).
- `Dissolved Oxygen (DO)` (mg/L): Area chart with CPCB minimum bathing threshold (5.0 mg/L).

### 3.3. Timeframe Windows
- `Last 24 Hours`: High-resolution granularity with `HH:mm` local timestamps.
- `Last 7 Days`: Medium-term trends with `MM/DD HH:mm` timestamps.
- `Last 30 Days`: Long-term seasonality analysis.

---

## 4. Scientific Integrity & Data Provenance

1. **Provenance Badges**:
   - The station status bar clearly reports:
     - Total Observations in query window.
     - Count of physical hardware observations (`real_sensor`).
     - Count of software simulation observations (`simulated`).
2. **Missing Data & Unmonitored Stations**:
   - If a station is in `planned` status (e.g. Manikarnika Ghat or Rajghat awaiting hardware deployment) and has no readings, the dashboard renders an informative empty state explaining that physical nodes are pending deployment.
   - It does NOT inject synthetic mock data to fill empty charts.
3. **Reference Benchmarks**:
   - Includes standard CPCB Class B limits (pH 6.5–8.5, DO ≥ 5.0 mg/L) and CWC Varanasi Gauge datums (Warning: 70.26m, Danger: 71.26m MSL).
