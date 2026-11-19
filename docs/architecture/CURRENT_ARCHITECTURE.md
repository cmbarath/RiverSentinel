# CURRENT SYSTEM ARCHITECTURE (AS-IS)
**Project:** River Sentinel 2.0  
**Audit Baseline Date:** 2026-11-19  
**Status:** Phase 0 Baseline Documentation  

---

## 1. System Overview

River Sentinel 2.0 is an environmental river monitoring web application centered on the Ganga River stretch at Varanasi, Uttar Pradesh, India. The architecture combines:
1. **Frontend**: Next.js 16 (Turbopack) with React 19 and Tailwind CSS.
2. **Backend**: Python Flask 3.x REST API handling ML inference, sensor simulation, and external AI routing.
3. **Primary Database**: Supabase PostgreSQL hosting sensor readings, citizen pollution reports, and flood prediction audit logs.
4. **AI Services**: Groq API (`qwen/qwen3.8-27b`) for chatbot conversations and multimodal image pollution analysis.
5. **Legacy Cloud**: Deactivated Firebase Realtime Database.
6. **Hardware / IoT Prototypes**: Standalone Arduino ESP32 sketch and Python USB serial monitor bridge.

---

## 2. High-Level Architectural Diagram

```mermaid
flowchart TD
    subgraph Client ["Client Tier (Browser)"]
        Landing["Landing Page (/)"]
        CitizenDash["Citizen Dashboard (/citizen-dashboard)"]
        AuthDash["Authority Dashboard (/authority-dashboard)"]
        MockAuth["Mock Login (/login & /signup)"]
    end

    subgraph BackendTier ["Backend Tier (Flask on :5000)"]
        App["app.py (Monolithic 1,180 lines)"]
        FloodML["flood_model.pkl (Random Forest - 6 feat)"]
        WQML["water_quality_model.pkl (Random Forest - 5 feat)"]
        Sim["simulate_sensors.py (Simulator)"]
        SerialBridge["serial_bridge.py (USB COM Reader)"]
    end

    subgraph ExternalServices ["External Cloud Services"]
        Supabase["Supabase PostgreSQL (river-sentinel-dev)"]
        Groq["Groq Cloud API (Qwen 3.8 27B)"]
        WeatherAPI["Open-Meteo REST API"]
        FirebaseDead["Firebase RTDB (HTTP 423 Deactivated)"]
    end

    subgraph Hardware ["Hardware / Edge Tier"]
        ESP32["Arduino ESP32 (firebase_sensor_upload.ino)"]
        Sensors["Physical Sensors (pH, Turbidity, Temp, DO)"]
    end

    %% Client to Backend
    CitizenDash -->|HTTP Poll (5s)| App
    AuthDash -->|HTTP Poll (5s)| App
    CitizenDash -->|POST /api/ai/analyze-image| App
    CitizenDash -->|POST /api/ai/chat| App

    %% Backend to Internal ML
    App --> FloodML
    App --> WQML

    %% Backend to External
    App -->|PostgREST (Service Role Key)| Supabase
    App -->|REST Chat / Vision| Groq
    App -->|GET Weather| WeatherAPI
    App -.->|Failed Fallback (423)| FirebaseDead
    Sim -->|POST /sensor_readings| Supabase
    Sim -.->|Failed Fallback (423)| FirebaseDead

    %% Hardware Flows
    Sensors --> ESP32
    ESP32 -.->|Direct Failed Legacy Write| FirebaseDead
    ESP32 -->|Serial USB (Text)| SerialBridge
    SerialBridge -.->|Direct Failed REST Write| FirebaseDead
```

---

## 3. Data Flow & Communication Patterns

### 3.1 Sensor Telemetry Ingestion Flow
- **Current Flow**:
  1. `backend/simulate_sensors.py` generates fluctuating sensor dictionaries (`ph`, `turbidity`, `water_level`, `"do"`, etc.) with `provenance: "simulated"`.
  2. The script executes a direct HTTP `POST` to Supabase REST endpoint: `https://xqzobddgkawysprpmkpk.supabase.co/rest/v1/sensor_readings`.
  3. The Next.js frontend hook `useSensorData.ts` polls `GET /api/sensors/latest` on the Flask backend every 5 seconds.
  4. The backend queries Supabase with `order=created_at.desc&limit=1`, formats the reading, and returns JSON.
- **Hardware Disconnect**:
  The physical ESP32 sketch (`arduino/firebase_sensor_upload.ino`) and USB bridge (`serial_bridge.py`) do not use this path. They still attempt direct writes to the deactivated Firebase Realtime Database.

### 3.2 Flood Prediction Flow
- **Trigger**: Client requests `GET /api/flood/predict` or sends custom weather/discharge overrides.
- **Execution**:
  1. Backend queries Open-Meteo API for real-time Varanasi rainfall, temperature, and humidity.
  2. Backend estimates discharge and takes latest river water level.
  3. Scales the 6 input features using `flood_scaler.pkl`.
  4. Runs `flood_model.pkl` to compute risk probability and risk level (`LOW`, `MODERATE`, `HIGH`).
  5. Inserts an audit log into Supabase `flood_predictions`.
  6. Returns prediction, probability, contributing reasons, and disclaimer to the client.

### 3.3 Pollution Reporting & Image Analysis Flow
- **Trigger**: Citizen uploads a river pollution photo in `ReportPollution.tsx`.
- **Execution**:
  1. Frontend submits image via `multipart/form-data` to `POST /api/ai/analyze-image`.
  2. Flask encodes the image as base64 and invokes Groq Vision (`qwen/qwen3.8-27b`).
  3. AI extracts structured JSON (`pollution_level`, `confidence`, `pollutants`, `assessment`).
  4. Backend persists record to Supabase `pollution_reports`.
  5. Authority users review and update status in `ManageReports.tsx` via `POST /api/authority/reports/update`.

---

## 4. Architectural Weaknesses & Single Points of Failure

1. **Monolithic Flask Backend (`backend/app.py`)**:
   All routing, ML loading, Groq integration, weather fetching, report generation, and database queries reside inside a single 1,180-line file with global variables and no modular blueprints.
2. **Client-Side Mock Authentication**:
   Routes `/authority-dashboard` and `/citizen-dashboard` are unauthenticated. Access control is based on a trivial client-side check (`email.includes("authority")`).
3. **Overly Broad Database Grants**:
   The public `anon` role has `DELETE` and `TRUNCATE` privileges on all application tables.
4. **Dead Cloud Dependency**:
   Residual Firebase references throughout `app.py`, `simulate_sensors.py`, and `serial_bridge.py` generate unnecessary timeouts and error logs.
5. **No Device Ingestion Contract**:
   No authenticated telemetry endpoint exists (`/api/v1/telemetry/ingest`) to validate hardware credentials, message IDs, or station associations.
6. **Base64 Storage Antipattern**:
   Images are stored as data URIs in database columns or memory buffers rather than in object storage.
