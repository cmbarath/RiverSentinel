# Phase 8.1F: Release Candidate Operational Status Matrix
## Authoritative Technical Truthfulness, Verification Boundaries & Capability Matrix

**Milestone:** Phase 8.1F — Final Product Status Accuracy  
**Target Geography:** Ganga River, Varanasi, Uttar Pradesh, India  
**Date:** November 19, 2026  
**Auditor:** Antigravity System Architecture & Release Governance  

---

## 1. Executive Summary

This status matrix defines the exact operational readiness, scientific status, and deployment verification level of every major capability within **River Sentinel 2.0 (Development Release Candidate 1)**.

To prevent overclaiming or misrepresenting software readiness, every subsystem is categorized into one of five rigorous operational states:
1. **Fully Verified (Production-Grade):** Functionally active, tested, and meeting all design criteria.
2. **Deterministic Standards-Based:** Formally evaluated against statutory criteria (e.g., CPCB Class B).
3. **Research-Only / Experimental:** Functionally operational but constrained by advisory governance banners.
4. **Compiled / Deferred Hardware:** Code/firmware fully verified; physical site deployment intentionally scheduled for later phase.
5. **Partially Verified / Environment-Dependent:** Backed by working code, but dependent on external infrastructure (e.g., Docker, cron runner, remote runners).

---

## 2. Platform Capability Status Matrix

| Subsystem / Capability | Operational Classification | Verification Status | Implementation & Boundary Evidence |
|---|---|---|---|
| **CPCB Water Quality Evaluator** | Deterministic Standards-Based | **Fully Verified** | Evaluates telemetry against CPCB Designated Best Use Class B (pH 6.5–8.5, DO ≥ 5 mg/L, BOD ≤ 3 mg/L). Decoupled from turbidity. |
| **BIS IS 10500 Screening** | Deterministic Standards-Based | **Fully Verified** | Confirms river water requires conventional treatment before potability; reports acceptable and permissible limits. |
| **Flood Stage Forecaster v1** | `research_only` | **Verified Advisory** | Ridge Regressor ($\alpha=10.0$, MAE: 0.7882 m, RMSE: 0.9719 m, $R^2$: -0.0399). Advisory only; emergency alerts suppressed. |
| **Water Quality Anomaly Detector** | `experimental` | **Verified Advisory** | Isolation Forest (`contamination=0.03`). Screens multi-parameter anomalies without triggering automated public alarms. |
| **Legacy ML Models** | `retired_baseline` | **Retired / Archived** | Preserved in `backend/*.pkl` strictly as historical comparison benchmarks; isolated from live inference paths. |
| **ESP32 IoT Firmware Framework** | Compiled Framework | **Verified Software** | PlatformIO firmware compiles cleanly; HMAC-SHA256 and flash ring buffer active. **Physical on-ghat installation deferred to Phase 3B**. |
| **Telemetry Ingestion Gateways** | Production-Grade | **Fully Verified** | `/api/telemetry/ingest` verifies HMAC signatures; `/api/telemetry/simulate` provides authenticated simulation testing. |
| **CWC Gauge Threshold Integration** | Reference-Gauge Specific | **Fully Verified** | Mapped to official CWC Varanasi stages: Warning (70.26 m) and Danger (71.26 m); 67.5 m recognized strictly as internal analytical subset. |
| **Alert & Notification Engine** | Production-Grade | **Fully Verified** | Database-backed state machine (`ACTIVE` -> `ACKNOWLEDGED` -> `RESOLVED`), rate limiting, and hysteresis deduplication. |
| **Telephony Gateway (SMS)** | Provider-Dependent / Mock | **Verified Safe Default** | Operates safely with `SMS_ENABLED=false` via `MockSMSProvider`. Live carrier dispatch unconfigured until Twilio credentials provisioned. |
| **PostgreSQL Disaster Recovery** | Production-Grade | **Fully Verified** | Verified independent restoration of 15 tables, 634 rows, 48 constraints, 27 indexes, and 31 RLS policies with **41.99s RTO**. |
| **Full Supabase Platform Recovery** | Partially Verified | **Partial / Conditional** | Relational database fully verified; standalone local GoTrue auth daemon and S3-compatible storage binaries require Docker orchestration. |
| **Automated Hourly Backups** | Script Functional | **Manual / CLI Only** | Multi-pass backup engine `postgres_backup.py` is fully functional; automated recurring execution requires external OS cron or cloud scheduler. |
| **Static GIS Flood Map** | Informational GIS | **Verified Static** | Visualizes historical flood susceptibility zones and ghat geometries. Does not compute dynamic live hydraulic flood inundation polygons. |
| **Statutory Notice Generation** | Governed Advisory | **Fully Verified** | Formally labeled `DRAFT — FOR AUTHORIZED REGULATORY REVIEW ONLY`. Disclaims official enforcement authority. |
| **GitHub Actions CI Pipeline** | Validated Locally | **Unverified Remote** | Local emulation confirmed 100% pass across backend compilation, unit tests, frontend lint, and build. Remote GitHub run unverified. |
| **Frontend Web Application** | Production-Grade | **Fully Verified** | Next.js 16.1.6 Turbopack with React 19; 8 static routes prerendered in 648 ms; WCAG 2.1 AA accessibility compliant. |

---

## 3. Transparency & Truthfulness Commitment

River Sentinel 2.0 adheres strictly to engineering integrity:
1. **No Simulated Sensors Reported as Physical:** Telemetry payloads explicitly display provenance chips (`🟢 Live Hardware`, `🟡 Software Simulation`, `⚪ Baseline`).
2. **No Model Overclaiming:** Negative test $R^2$ and semi-synthetic training data are transparently disclosed.
3. **No Authority Spoofing:** Software is explicitly identified as an advisory intelligence tool, never impersonating statutory regulatory agencies.
