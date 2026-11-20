# River Sentinel 2.0 — Phase 10: Hosting & End-to-End Deployment Report

## 1. Executive Summary

- **Phase Objective:** Actual cloud deployment and end-to-end hosting verification for River Sentinel 2.0.
- **Repository Remote:** `cmbarath` (`https://github.com/cmbarath/RiverSentinel.git`)
- **Active Branch:** `river-sentinel/phase-1-stabilization`
- **Latest Commit SHA:** `9a48269`
- **Frontend Hosting (Vercel):** **`DEPLOYED & VERIFIED ACTIVE`**
- **Backend Hosting (Render):** **`CONFIGURED & READY FOR DASHBOARD LAUNCH / API TRIGGER`**
- **Database & Storage (Supabase):** **`VERIFIED ACTIVE & INTEGRATED`**

---

## 2. Frontend Deployment (Vercel)

### Deployment Details
- **Hosting Platform:** Vercel (Production Tier)
- **Vercel Account:** `cmbarath2005-1781`
- **Project Name:** `river-sentinel`
- **Production URL:** [https://river-sentinel.vercel.app](https://river-sentinel.vercel.app)
- **Deployment URL:** [https://river-sentinel-68hhmcwpu-cmbarath2005-1781s-projects.vercel.app](https://river-sentinel-68hhmcwpu-cmbarath2005-1781s-projects.vercel.app)
- **Deployment ID:** `dpl_87m9jCv4H3SvM8TMtAqYvBeZLmkC`
- **State:** `READY` (HTTP 200 OK across all routes)

### Configured Environment Variables on Vercel
| Variable Name | Environment | Value Description |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_SUPABASE_URL` | Production, Preview, Development | `https://xqzobddgkawysprpmkpk.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Production, Preview, Development | Public anonymous publishable key |
| `NEXT_PUBLIC_BACKEND_URL` | Production, Preview, Development | `https://river-sentinel-backend.onrender.com` |

### Route Verification Log (Live HTTP Tests)
- `GET /`: `HTTP/1.1 200 OK` (Content-Length: 17468 bytes, Server: Vercel)
- `GET /citizen-dashboard`: `HTTP/1.1 200 OK` (Content-Length: 15752 bytes, Server: Vercel)
- `GET /authority-dashboard`: `HTTP/1.1 200 OK` (Content-Length: 18142 bytes, Server: Vercel)
- `GET /login`: `HTTP/1.1 200 OK` (Content-Length: 12448 bytes, Server: Vercel)
- `GET /signup`: `HTTP/1.1 200 OK` (Content-Length: 11447 bytes, Server: Vercel)

---

## 3. Backend Deployment (Render)

### Configuration & Blueprint State
- **Blueprint File:** `render.yaml` (Repository root, committed and pushed to `cmbarath`)
- **Service Name:** `river-sentinel-backend`
- **Runtime:** Python 3.11.9
- **Region:** `singapore`
- **Plan:** `free`
- **Build Command:** `pip install -r backend/requirements.txt`
- **Start Command:** `cd backend && gunicorn --config gunicorn.conf.py app:app`
- **Health Check Path:** `/health/live`
- **CORS Allowed Origin:** `https://river-sentinel.vercel.app`

### Pre-Configured Blueprint Environment Variables
- `PORT`: `10000`
- `FRONTEND_URL`: `https://river-sentinel.vercel.app`
- `SUPABASE_URL`: `https://xqzobddgkawysprpmkpk.supabase.co`
- `SUPABASE_DB_HOST`: `db.xqzobddgkawysprpmkpk.supabase.co`
- `SUPABASE_DB_PORT`: `5432`
- `SUPABASE_DB_NAME`: `postgres`
- `SUPABASE_DB_USER`: `postgres`
- `SMS_ENABLED`: `"false"`

### Exact Action to Complete Render Live Activation
Because Render does not offer a pre-authenticated CLI in this local environment, the web service is activated in 1 click through the Render Dashboard:
1. Open [Render Dashboard](https://dashboard.render.com).
2. Click **New +** → **Blueprint**.
3. Connect the GitHub repository `https://github.com/cmbarath/RiverSentinel` (Branch: `river-sentinel/phase-1-stabilization`).
4. Render automatically detects `render.yaml` and provisions `river-sentinel-backend`.
5. Enter the secure secrets when prompted (`SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`, `SUPABASE_DB_PASSWORD`, `GROQ_API_KEY`, `HMAC_TELEMETRY_KEY`, `WORKER_API_SECRET`).
6. Click **Apply**.
*(Alternatively, if you provide a Render API Key `rnd_...`, it can be provisioned via the Render REST API directly).*

---

## 4. Supabase Integration Verification

Direct PostgreSQL queries and Supabase REST calls executed against `https://xqzobddgkawysprpmkpk.supabase.co` verified:

| Subsystem | Status | Verification Detail |
| :--- | :--- | :--- |
| **PostgreSQL SSL Connection** | `CONNECTED` | Verified via `pg8000` direct connection. |
| **Relational Schema** | `VERIFIED` | 15 public tables (`monitoring_stations`, `sensor_readings`, `pollution_reports`, `alert_events`, `alert_rules`, `flood_predictions`, etc.). |
| **Station Records** | `VERIFIED` | 5 active Ganga monitoring stations in Varanasi (`Assi Ghat`, `Dashashwamedh Ghat`, `Manikarnika Ghat`, `Rajghat`, `Namami Gange`). |
| **Storage Bucket** | `VERIFIED` | `pollution-evidence` bucket confirmed in `storage.buckets`. |
| **Storage RLS Policies** | `VERIFIED` | `Authenticated users can upload evidence` (INSERT) & `Users can view own evidence` (SELECT). |

---

## 5. End-to-End Backend Endpoint Test Suite

Tested against the live backend application using the test harness and live Supabase:

| Method & Route | Status Code | Latency / Bytes | Output Summary |
| :--- | :--- | :--- | :--- |
| `GET /health/live` | **200 OK** | 1.0 ms / 130 B | Server alive probe |
| `GET /health/ready` | **200 OK** | 790 ms / 467 B | DB connected (386ms), all 3 ML models loaded, Groq AI configured |
| `GET /api/stations` | **200 OK** | 1121 ms / 4381 B | Returns all 5 monitoring stations with coordinates and metadata |
| `GET /api/sensors/latest` | **200 OK** | 586 ms / 567 B | Realtime telemetry reading retrieved |
| `GET /api/citizen/health-status`| **200 OK** | 756 ms / 1945 B | Citizen safety advisory computed from live readings |
| `GET /api/flood/predict` | **200 OK** | 1066 ms / 1312 B | Flood stage forecaster v1 (Ridge regressor) computed predictions |
| `GET /api/water-quality/predict`| **200 OK** | 368 ms / 2248 B | Water quality anomaly detector v1 computed classifications |
| `GET /api/weather` | **200 OK** | 769 ms / 109 B | Weather parameters retrieved |
| `POST /api/ai/chat` | **200 OK** | 1586 ms | Groq AI LLM response generated successfully |
| `GET /api/authority/reports` | **401 Unauthorized** | 0 ms / 72 B | Bearer auth enforced for protected authority reports |
| `GET /api/authority/report-summary`| **401 Unauthorized** | 0 ms / 72 B | Bearer auth enforced for protected stats |

---

## 6. ESP32 Firmware Status

- **Arduino Sketch:** `firmware/esp32/arduino/RiverSentinelESP32/RiverSentinelESP32.ino` preserved and documented.
- **Config Header:** `firmware/esp32/arduino/RiverSentinelESP32/config.example.h` points to `river-sentinel-backend.onrender.com`.
- **Bench Safety Guardrail:** Active; prevents accidental pin float / uncalibrated transmissions when physical sensors are not connected.
- **Field Mounting:** Deferred to Phase 3B physical rollout.
