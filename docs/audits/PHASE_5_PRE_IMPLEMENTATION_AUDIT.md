# River Sentinel 2.0 — Phase 5 Pre-Implementation Audit
## Alert Engine, Notification System and Telephony Gateway Baseline

**Date**: November 19, 2026  
**Auditor**: Senior Systems Architect & Security Engineer  
**Git Checkpoint**: Commit `af1feb3` on branch `river-sentinel/phase-1-stabilization`  
**Database**: Supabase PostgreSQL (Project ID: `xqzobddgkawysprpmkpk`, Region: `ap-southeast-1`)  

---

## 1. Environment & Git State Verification

1. **Current Branch**: `river-sentinel/phase-1-stabilization`.
2. **Working Tree**: Completely clean; all Phase 4 changes committed at `af1feb3`.
3. **Repository History**: Main branch remains untouched. 5 development commits ahead of remote tracking branch.
4. **Environment Variables**: Current `.env` and `frontend/.env.local` provide Supabase URL, anon key, and service role key for database connectivity. No SMS provider credentials (`SMS_API_KEY`, `SMS_SENDER_ID`) are currently configured.

---

## 2. Remote Database Schema Inventory

A live schema inspection of the public schema via PostgreSQL catalog queries confirmed the existence of 10 database entities:
1. `cwc_reference_gauges`: CWC reference stage datums (Warning: 70.26m, Danger: 71.26m, HFL: 73.90m GTS MSL).
2. `monitoring_stations`: 4 registered monitoring stations in Varanasi (`STN-VAR-ASSI-01`, `STN-VAR-DASH-02`, `STN-VAR-MANI-03`, `STN-VAR-RAJG-04`).
3. `devices`: 4 provisioned hardware devices with SHA-256 token hashes, lifecycle status, and firmware metadata.
4. `sensor_readings`: Ingested telemetry observations tagged with provenance (`real_sensor`, `simulated`) and quality status (`valid`, `provisional`, `out_of_range`).
5. `device_telemetry_logs`: Raw device packet logs for debugging and audit.
6. `pollution_reports`: Citizen-submitted pollution reports with image evidence paths and review status.
7. `flood_predictions`: Machine learning inference outputs from the 6-feature Random Forest model.
8. `profiles`: Supabase Auth user profiles with columns `id`, `full_name`, `phone`, `role`, `account_status`, `organization`, `department`, `created_at`, `updated_at`.
9. `station_assignments`: Field officer station assignments with columns `id`, `station_id`, `user_id`, `assigned_by`, `assigned_at`, `status`.
10. `public_sensor_telemetry`: Sanitized public security view exposing only non-sensitive sensor telemetry.

### Critical Audit Finding: Zero Pre-Existing Alert / Notification Tables
There are currently **no** database tables for alert rules, system alerts, alert events, user notification preferences, or notification delivery queues. 
Previously, alert management in `backend/routes/authority.py` relied on a transient in-memory Python list (`ACTIVE_SYSTEM_ALERTS = []`), which caused state to vanish upon server restarts and prevented multi-process workers from operating safely.

---

## 3. Contact Information, Consent & RLS Audit

1. **`profiles` Table**:
   - Stores `phone` (varchar) and `full_name` (text).
   - Currently lacks explicit `phone_verified` boolean, `sms_opt_in` consent timestamp, or category preference flags.
2. **Contact Privacy**:
   - In accordance with privacy and regulatory compliance (TRAI / Telecom Commercial Communications Customer Preference Regulations), SMS notifications must remain **strictly opt-in**.
   - No notification may be dispatched to unverified or unconsenting phone numbers.
3. **Existing RLS Policies**:
   - RLS is enabled on all existing 10 public tables.
   - All new alert and notification tables (`alert_rules`, `system_alerts`, `alert_events`, `notification_preferences`, `notification_deliveries`) must enforce strict RLS:
     - Citizens can only view alerts/notifications designated for them or public environmental alerts.
     - Field officers can only access alerts for their assigned stations.
     - Authority administrators hold full management privileges.
     - Service role holds full operational execution rights for the background worker.

---

## 4. Ingestion & Prediction Flow Isolation

1. **Telemetry Ingestion Decoupling**:
   - The device telemetry route `POST /api/v1/telemetry/report` in `backend/routes/sensors.py` must **never** be blocked or delayed by alert evaluation or notification delivery failures.
   - Alert evaluation must be executed cleanly or asynchronously without raising uncaught exceptions that would fail sensor packets.
2. **Machine Learning Guardrail**:
   - Random Forest flood predictions (`public.flood_predictions`) are experimental analytical outputs.
   - Per explicit instructions, ML predictions **must not trigger public emergency warnings**. Only verified hydrological measurements evaluated against GTS MSL reference datums may trigger flood alerts.

---

## 5. Implementation Roadmap for Phase 5

1. **Phase 5B**: Author version-controlled SQL migration `20261119000003_phase5_alerts_and_notifications.sql`:
   - `alert_rules`
   - `system_alerts`
   - `alert_events`
   - `notification_preferences`
   - `notification_deliveries`
   - Indexes, unique idempotency constraints, and RLS policies.
2. **Phase 5C & 5D**: Implement Alert Generation Engine (`backend/services/alert_service.py`):
   - Deduplication keying (`deduplication_key`).
   - Cooldown, minimum duration, hysteresis, and recovery.
   - CPCB Class B bathing & BIS IS 10500 screening criteria.
   - Hardware touch & offline detection.
3. **Phase 5E & 5F**: In-app notifications API & UI:
   - Backend routes `/api/v1/notifications`, `/api/v1/notifications/unread-count`, `/api/v1/notifications/<id>/read`.
   - Update frontend navigation and notifications panel.
4. **Phase 5G**: Authority Alert Management Center:
   - Backend routes `/api/v1/alerts`, `/api/v1/alerts/<id>/acknowledge`, `/api/v1/alerts/<id>/resolve`.
   - Frontend UI with severity/category/station filtering, acknowledge & resolve actions with notes.
5. **Phase 5H & 5I**: Telephony Gateway & Notification Delivery Outbox:
   - Provider-independent SMS and email adapters (`backend/services/sms_service.py`).
   - Background delivery worker (`backend/services/notification_worker.py`) with exponential backoff and rate limits.
   - Mock provider for testing; live SMS disabled by default.
6. **Phase 5J**: User notification preferences management (`/api/v1/notifications/preferences`).
7. **Phase 5K & 5L**: Comprehensive unit & integration test suite (`backend/test_phase5_alerts.py`), regression verification, build check, and full documentation suite.
