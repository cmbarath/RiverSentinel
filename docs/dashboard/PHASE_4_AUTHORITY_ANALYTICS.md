# River Sentinel 2.0 — Phase 4 Authority Analytics Specification

This document outlines the architecture, security enforcement, and live aggregations powering **Authority Analytics** (`frontend/src/components/dashboard/AuthorityAnalytics.tsx`).

---

## 1. Problem Statement & Audit Findings

The pre-implementation audit discovered that `AuthorityAnalytics.tsx` previously contained:
- Hardcoded status distribution pie chart (Safe: 8, Caution: 3, Unsafe: 1).
- Hardcoded bar chart comparing 5 stations (`Dashashwamedh`, `Assi`, `Manikarnika`, `Scindia`, `Harishchandra`) with fabricated pH and Turbidity values.
- Hardcoded system performance cards ("Uptime: 99.98%", "Data Latency: 1.2s", "AI Accuracy: 87.4%").
- No authentication checks or data-fetching logic.

---

## 2. Overhauled Architecture & RBAC Security

The redesigned `AuthorityAnalytics.tsx` binds directly to `GET /api/v1/analytics/overview`.

### 2.1. Role-Based Access Control (RBAC)
- Access to the overview endpoint requires a valid Supabase Auth JWT with role `authority_admin` or `field_officer`.
- If an unauthenticated user or citizen accesses the component, the component captures the 401/403 status and displays a clean, dignified message:
  *"Authority Authentication Required: Live operational system aggregations are restricted to authorized Uttar Pradesh Pollution Control Board (UPPCB) and Central Water Commission (CWC) personnel."*
- A direct Log In link directs officers to authenticate via Supabase Auth.

---

## 3. Dynamic Visualizations & Database Metrics

### 3.1. Key Operational KPI Cards
- **Monitoring Stations**: Total registered stations in Varanasi with real Active vs Planned counts.
- **IoT Hardware Nodes**: Total provisioned ESP32 nodes with online active vs offline counts.
- **Telemetry Observations**: Total logged observations with Hardware (`real_sensor`) vs Simulation breakdown.
- **Pollution Incidents**: Total citizen-lodged reports with count of Resolved and Under Investigation incidents.

### 3.2. Station Lifecycle Distribution (Pie Chart)
- Aggregates stations by status (`active`, `planned`, `installed`, `maintenance`).
- Uses official lifecycle color-coding (Green for Active, Orange for Planned, Blue for Installed, Red for Maintenance).

### 3.3. Citizen Pollution Reports by Status (Bar Chart)
- Aggregates report records from `public.pollution_reports` by status:
  - `Submitted` (Pending initial triage)
  - `Investigating` (Assigned to field officer)
  - `Resolved` (Corrective action verified)
  - `Rejected` (Invalid or duplicate report)

### 3.4. Ghat-by-Ghat Water Quality Comparison (Bar Chart)
- Fetches real-time observations across all registered monitoring stations.
- Plots current pH and Turbidity side-by-side to allow instant identification of localized industrial or sewage influxes.

### 3.5. CWC Hydrological Alert Status & Flood Screening
- Displays live counts of flood severity predictions: `LOW`, `MODERATE`, `HIGH`, and `CRITICAL`.
- Connects directly to the Random Forest flood prediction output records stored in `public.flood_predictions`.
