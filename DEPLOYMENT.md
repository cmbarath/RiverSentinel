# River Sentinel 2.0 — Production Deployment Runbook

This guide documents the end-to-end production deployment process for the River Sentinel 2.0 urban river monitoring platform targeting the Ganga River in Varanasi, Uttar Pradesh.

---

## 1. Architecture Overview

```
                      +-----------------------------+
                      |   Citizen & Official Users  |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |       Vercel Hosting        |
                      |  Next.js 16 (App Router)    |
                      |  React 19 / Turbopack       |
                      +--------------+--------------+
                                     |
              REST & Auth API Calls  |  Supabase Auth / Storage
                                     v
      +------------------------------+-------------------------------+
      |                                                              |
      v                                                              v
+-------------------------------+                     +-------------------------------+
|         Render Hosting        |                     |      Supabase Cloud (PaaS)    |
|   Flask 3.0 + Gunicorn API    |  Database / TLS     |   PostgreSQL 15 Database      |
|   Port 10000 / Singapore      |-------------------->|   Row-Level Security (RLS)    |
|   Scikit-Learn ML Models      |                     |   Supabase Storage (Evidence) |
+---------------+---------------+                     +-------------------------------+
                ^
                | HTTPS REST Ingest (X-Device-Code / X-Device-Token)
                |
+---------------+---------------+
|       ESP32-WROOM-32 IoT      |
|    Ganga Monitoring Station   |
|   (Assi / Dashashwamedh etc.) |
+-------------------------------+
```

- **Frontend:** Next.js 16 (App Router, Turbopack, React 19) hosted on **Vercel**.
- **Backend API:** Python 3.11 / Flask 3.0 managed with Gunicorn WSGI on **Render** (Singapore region).
- **Database, Auth & Storage:** Managed **Supabase** PostgreSQL 15 with strict Row-Level Security, JWT auth, and private storage buckets.
- **Hardware Telemetry:** ESP32-WROOM-32 nodes transmitting Schema 2.0 JSON telemetry over HTTPS to `/api/v1/telemetry/ingest`.

---

## 2. Supabase Production Database Setup

### Prerequisites
1. Create a production Supabase project at [supabase.com](https://supabase.com).
2. Note your project URL (`https://<project-ref>.supabase.co`), `anon` key, `service_role` key, and PostgreSQL connection credentials.

### Step 1: Execute Schema Migrations
Execute the migrations in sequential order using the Supabase SQL Editor:

1. `backend/migrations/001_initial_schema.sql`: Core schema (`stations`, `devices`, `sensor_readings`, `water_quality_assessments`, `flood_predictions`, `pollution_reports`, `profiles`).
2. `backend/migrations/002_rls_policies.sql`: Row-Level Security policies enforcing role isolation (citizen, field_officer, authority_admin).
3. `backend/migrations/003_storage_buckets.sql`: Storage bucket configuration (`pollution-evidence`, private, authenticated upload).
4. `backend/migrations/004_phase5_alert_tables.sql`: Alert engine schema (`alert_rules`, `alerts`, `alert_events`, `notification_deliveries`, `user_notification_preferences`, `worker_heartbeats`).
5. `backend/migrations/005_phase5_1_cpcb_correction.sql`: Regulatory correction decoupling turbidity from CPCB Class B statutory rules and adding notification outbox deduplication indices.

### Step 2: Seed Static Data
Execute seed scripts to populate initial Varanasi stations, alert rules, and device credentials:
```bash
python backend/scripts/seed_stations.py
python backend/scripts/seed_alert_rules.py
python backend/scripts/seed_devices.py
```

### Step 3: Verify Supabase Storage
1. Navigate to **Storage** in the Supabase Dashboard.
2. Ensure the bucket `pollution-evidence` exists and is marked **Private**.
3. Confirm RLS policy: Authenticated users can insert; only authorities and report owners can select.

---

## 3. Render Backend Deployment (Flask API)

### Option A: Using `render.yaml` (Recommended Blueprint)
1. In the Render Dashboard, click **New + → Blueprint**.
2. Connect your Git repository: `https://github.com/cmbarath/RiverSentinel.git`.
3. Select branch: `river-sentinel/phase-1-stabilization`.
4. Render will parse `render.yaml` automatically.
5. In the Environment settings, populate secret variables:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `SUPABASE_JWT_SECRET`
   - `SUPABASE_DB_HOST`
   - `SUPABASE_DB_PASSWORD`
   - `HMAC_TELEMETRY_KEY`
   - `GROQ_API_KEY`
   - `FRONTEND_URL` (Set to your Vercel URL once generated)
6. Click **Apply**.

### Option B: Manual Web Service Setup
1. In Render Dashboard, click **New + → Web Service**.
2. Connect repository and select branch `river-sentinel/phase-1-stabilization`.
3. Settings:
   - **Name:** `river-sentinel-backend`
   - **Region:** `Singapore (Southeast Asia)`
   - **Runtime:** `Python`
   - **Build Command:** `pip install -r backend/requirements.txt`
   - **Start Command:** `cd backend && gunicorn --config gunicorn.conf.py app:app`
   - **Health Check Path:** `/health/live`
4. Add all environment variables listed in [ENVIRONMENT_VARIABLES.md](file:///c:/Project/RiverSentinel-main/ENVIRONMENT_VARIABLES.md).
5. Click **Create Web Service**.

---

## 4. Vercel Frontend Deployment (Next.js)

### Step 1: Import Project to Vercel
1. Log in to [vercel.com](https://vercel.com) and click **Add New... → Project**.
2. Import repository `https://github.com/cmbarath/RiverSentinel.git`.
3. In **Project Settings**:
   - **Framework Preset:** `Next.js`
   - **Root Directory:** Edit and set to `frontend` (Click Save).
   - **Build Command:** `npm run build`
   - **Output Directory:** `.next`
   - **Install Command:** `npm install`

### Step 2: Configure Environment Variables
Add the following in Vercel **Settings → Environment Variables**:

| Variable Name | Environment | Value Description |
|---|---|---|
| `NEXT_PUBLIC_BACKEND_URL` | Production, Preview, Dev | Render backend URL (e.g. `https://river-sentinel-backend.onrender.com`) |
| `NEXT_PUBLIC_SUPABASE_URL` | Production, Preview, Dev | Supabase project URL (`https://<project-ref>.supabase.co`) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Production, Preview, Dev | Supabase public anonymous API key |

### Step 3: Deploy
1. Click **Deploy**.
2. Once deployed, note your production domain (e.g., `https://river-sentinel.vercel.app`).
3. Return to Render and update the `FRONTEND_URL` environment variable to match your Vercel domain to restrict CORS properly.

---

## 5. Post-Deployment Verification

### 1. Backend Liveness & Readiness Probes
```bash
# Liveness check (instant process validation)
curl -i https://river-sentinel-backend.onrender.com/health/live

# Readiness check (validates database connection and model loading)
curl -i https://river-sentinel-backend.onrender.com/health/ready
```
Expected response:
```json
{
  "status": "healthy",
  "database": { "status": "connected", "latency_ms": 42.1 },
  "models": {
    "flood_forecaster_ready": true,
    "anomaly_detector_ready": true,
    "cpcb_evaluator_ready": true
  }
}
```

### 2. Frontend User Journeys
1. **Public/Citizen:** Open Vercel URL → View landing page → Access live station monitoring → Submit test pollution report.
2. **Citizen Authentication:** Sign up new citizen account → Log in → View user dashboard and notification center.
3. **Authority / Field Officer:** Log in with designated authority credentials → Access `/authority-dashboard` → Verify Command Center, Alert Outbox dispatch, and Report Review.

### 3. ESP32 Ingestion Verification
Test the production ingest endpoint using curl with a mock ESP32 payload:
```bash
curl -X POST https://river-sentinel-backend.onrender.com/api/v1/telemetry/ingest \
  -H "Content-Type: application/json" \
  -H "X-Device-Code: DEV-ESP32-ASSI-01" \
  -H "X-Device-Token: YOUR_TOKEN" \
  -d '{
    "schema_version": "2.0",
    "device_code": "DEV-ESP32-ASSI-01",
    "message_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "sequence_number": 1,
    "observed_at": "2026-11-19T22:00:00Z",
    "firmware_version": "2.1.0-arduino",
    "sensor_readings": {
      "ph": 7.4,
      "turbidity": 12.0,
      "temperature": 24.0,
      "water_level": 66.5,
      "ec": 350.0,
      "do": 7.1,
      "battery_pct": 99.0
    },
    "sensor_status": {
      "ph": "bench_simulation",
      "turbidity": "bench_simulation",
      "temperature": "bench_simulation",
      "water_level": "bench_simulation",
      "ec": "bench_simulation",
      "do": "bench_simulation"
    }
  }'
```
Expected response: `HTTP 200/201` with `status: "success"`.
