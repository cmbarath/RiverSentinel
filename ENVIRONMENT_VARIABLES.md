# River Sentinel 2.0 — Environment Variables Specification

This document details every environment variable used across the River Sentinel 2.0 platform for frontend (Next.js), backend (Flask API), and database/worker services.

---

## 1. Frontend Environment Variables (Next.js / Vercel)

All client-facing variables in Next.js require the `NEXT_PUBLIC_` prefix and are bundled into client-side JavaScript.

| Variable Name | Required | Default / Fallback | Sensitivity | Description |
|---|---|---|---|---|
| `NEXT_PUBLIC_BACKEND_URL` | **Yes** | `http://localhost:5000` | Public | URL of the backend Flask API server (e.g. `https://river-sentinel-backend.onrender.com`). |
| `NEXT_PUBLIC_SUPABASE_URL` | **Yes** | — | Public | Supabase project API gateway endpoint (`https://<project-ref>.supabase.co`). |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | **Yes** | — | Public | Supabase public anonymous API key for client-side Auth and RLS-protected queries. |

---

## 2. Backend Environment Variables (Flask / Render)

These variables must be configured on the host (e.g., Render Web Service settings or `.env` for local development). They must **never** be exposed to the browser or committed to Git.

### Server & Platform Configuration

| Variable Name | Required | Default / Fallback | Sensitivity | Description |
|---|---|---|---|---|
| `PORT` | Optional | `5000` (Render defaults to `10000`) | Internal | HTTP listening port for Flask / Gunicorn. |
| `PYTHON_VERSION` | Optional | `3.11.9` | Internal | Python runtime version specified in `render.yaml`. |
| `FRONTEND_URL` | **Yes** | `*` | Configuration | Permitted CORS origin(s) for the frontend (e.g., `https://river-sentinel.vercel.app`). Comma-separated for multiple origins. |
| `MAX_CONTENT_LENGTH` | Optional | `16777216` (16 MB) | Configuration | Maximum allowed HTTP request body size (allows high-res citizen evidence uploads). |

### Supabase Database & Security

| Variable Name | Required | Default / Fallback | Sensitivity | Description |
|---|---|---|---|---|
| `SUPABASE_URL` | **Yes** | — | Secret | Supabase project REST URL (`https://<project-ref>.supabase.co`). |
| `SUPABASE_SERVICE_ROLE_KEY` | **Yes** | — | **Critical Secret** | Supabase service_role key granting administrative DB bypass for trusted backend routes. |
| `SUPABASE_JWT_SECRET` | **Yes** | — | **Critical Secret** | Secret key used to sign and verify Supabase user session tokens (`HS256`). |
| `SUPABASE_DB_HOST` | **Yes** | — | Secret | PostgreSQL database direct host (e.g. `db.<project-ref>.supabase.co`). |
| `SUPABASE_DB_PORT` | Optional | `5432` | Configuration | PostgreSQL connection port. |
| `SUPABASE_DB_NAME` | Optional | `postgres` | Configuration | Database name. |
| `SUPABASE_DB_USER` | Optional | `postgres` | Configuration | Database username. |
| `SUPABASE_DB_PASSWORD` | **Yes** | — | **Critical Secret** | PostgreSQL database password for direct pg8000 pooled connection. |

### AI, IoT & Worker Services

| Variable Name | Required | Default / Fallback | Sensitivity | Description |
|---|---|---|---|---|
| `GROQ_API_KEY` | Optional | — | Secret | API key for Groq Cloud AI service (powering vision pollution analysis and multilingual chatbot). |
| `HMAC_TELEMETRY_KEY` | **Yes** | — | **Critical Secret** | Cryptographic secret for verifying IoT telemetry HMAC signatures and token generation. |
| `WORKER_API_SECRET` | Optional | `test_worker_secret_key_varanasi` | Secret | Secret token for invoking background worker jobs (e.g. `/api/v1/notifications/process-outbox`). |
| `SMS_ENABLED` | Optional | `false` | Configuration | Flag to enable SMS dispatch gateway (`true` or `false`). |
| `SMS_GATEWAY_URL` | Optional | — | Secret | Third-party SMS gateway webhook/endpoint. |
| `SMS_GATEWAY_API_KEY` | Optional | — | Secret | API key for SMS gateway provider. |

---

## 3. Firmware Configuration (ESP32 / `config.h`)

Values configured directly on the ESP32 node in `firmware/esp32/arduino/RiverSentinelESP32/config.h`:

| Constant | Description | Example / Recommendation |
|---|---|---|
| `WIFI_SSID` | Station local Wi-Fi SSID | `"RiverSentinel_Field_Net"` |
| `WIFI_PASSWORD` | Station local Wi-Fi Password | (Secret WPA2 key) |
| `BACKEND_HOST` | Hostname of backend API | `"river-sentinel-backend.onrender.com"` |
| `BACKEND_PORT` | Backend port | `443` (for HTTPS) / `5000` (for local dev) |
| `USE_TLS` | Enable TLS / SSL | `true` |
| `DEVICE_CODE` | Registered hardware station code | `"DEV-ESP32-ASSI-01"` |
| `DEVICE_TOKEN` | Pre-shared high-entropy token | `"rs_dev_assi01_..."` |
| `SENSORS_PHYSICALLY_ATTACHED` | Hardware mounting state | `false` (bench mode) / `true` (field wired) |
