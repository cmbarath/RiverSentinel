# River Sentinel – AI-Based Urban River Monitoring System 🌊

**Geospatially-Intelligent Urban River Protection and Early Warning Platform**

RiverSentinel is an Environmental Intelligence Platform dedicated to real-time river monitoring, pollution detection, and flood prediction for the Ganga river basin (Varanasi stretch). It combines machine learning models, real-time sensor telemetry, and situational dashboards for citizens and municipal authorities.

---

## 🌟 Key Features

- **🌊 Flood Risk Prediction:** A trained Random Forest model predicts flood probability and classifies risk (`LOW`, `MODERATE`, `HIGH`) using real-time water level, discharge, rainfall, temperature, and humidity telemetry.
- **💧 Water Quality & Potability Prediction:** A trained Random Forest classifier evaluates water potability and assigns quality ratings (`EXCELLENT`, `GOOD`, `MODERATE`, `POOR`) based on pH, turbidity, temperature, electrical conductivity, and dissolved oxygen.
- **📊 Real-Time Sensor Telemetry:** Dashboard displays live telemetry across 9 parameters (pH, Turbidity, Temperature, Humidity, EC, Water Level, BOD, COD, Dissolved Oxygen) with automatic fallback to safe default baselines.
- **🛡️ Public Safety Checker:** Ghat-by-ghat water safety evaluation for bathing, drinking, and livestock usage.
- **🏢 Authority Command Center:** Rapid response tools including legal notice generation, system-wide flood alert broadcasting, CSV sensor data export, and citizen report moderation.
- **🤖 Optional AI Assistant:** Natural language assistant powered by Groq (`llama-4-scout-17b-16e-instruct`) supporting English, Hindi, Bhojpuri, and Bengali. Fails gracefully with a clear informational message if the service is unavailable.
- **🗺️ Interactive Geospatial Maps:** GIS flood susceptibility visualization for the Varanasi riverfront.

---

## 🏗️ Architecture

```
RiverSentinel/
├── backend/
│   ├── app.py                      # Flask REST API server (all routes & ML inference)
│   ├── flood_model.pkl             # Trained Random Forest flood prediction model
│   ├── flood_scaler.pkl            # StandardScaler for flood features
│   ├── water_quality_model.pkl     # Trained Random Forest water quality model
│   ├── water_quality_scaler.pkl    # StandardScaler for water quality features
│   ├── model_info.json             # Flood model metadata and performance metrics
│   ├── water_quality_model_info.json # Water quality model metadata
│   ├── train_flood_model.py        # Reproducible flood model training pipeline
│   ├── train_water_quality_model.py # Reproducible water quality model training pipeline
│   ├── simulate_sensors.py         # Realistic sensor data generator for demo/testing
│   ├── requirements.txt            # Python dependencies
│   └── flood_model/
│       └── flood_data_with_dynamic_labels.csv # Historical Ganga river dataset (1,095 days)
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── authority-dashboard/ # Authority monitoring and alert command center
│   │   │   ├── citizen-dashboard/   # Public safety, weather, trends, and chatbot
│   │   │   ├── login/               # Authentication portal
│   │   │   └── signup/              # User registration
│   │   ├── components/dashboard/    # Modular dashboard widgets
│   │   └── hooks/useSensorData.ts   # Real-time polling hook (5-second cadence)
│   └── public/flood-map/            # QGIS Leaflet web map assets
├── start-backend.ps1                # PowerShell backend launcher
├── start-frontend.ps1               # PowerShell frontend launcher
└── README.md
```

---

## 🛠️ Tech Stack

- **Frontend:** Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS 4, Recharts, Leaflet
- **Backend:** Python 3.12, Flask, Flask-CORS, joblib, scikit-learn 1.9
- **Machine Learning:** Random Forest Classifiers (Scikit-Learn) with standard feature scaling
- **Data & Telemetry:** Firebase Realtime Database (with REST fallback), OpenWeatherMap API
- **AI / LLM:** Groq API (`llama-4-scout-17b-16e-instruct`)

---

## 🤖 Machine Learning Models

### 1. Flood Prediction Model
- **Algorithm:** Random Forest Classifier (`n_estimators=200`, `max_depth=15`, `class_weight='balanced'`)
- **Dataset:** `flood_data_with_dynamic_labels.csv` — 1,095 historical daily observations from the Varanasi Ganga stretch (2018–2020)
- **Input Features (6):**
  1. `water_level_varanasi` (meters)
  2. `discharge_cumec` (cubic meters / second)
  3. `rain_varanasi_mm` (local rainfall in mm/h)
  4. `rain_upstream_avg_mm` (upstream rainfall in mm/h)
  5. `temperature_c` (°C)
  6. `humidity_pct` (%)
- **Target:** `flood_label` (1 = Flood Event, 0 = Normal Flow)
- **Test Set Metrics:**
  - Accuracy: **99.54%**
  - ROC-AUC: **1.0000**
  - Precision / Recall (Flood): **0.99 / 1.00**
- **Top Predictive Features:** Local rainfall (39.4%), Upstream rainfall (34.0%), River discharge (18.4%), Water level (7.1%)

### 2. Water Quality & Potability Model
- **Algorithm:** Random Forest Classifier (`n_estimators=200`, `max_depth=12`, `class_weight='balanced'`)
- **Dataset:** 2,000 synthetic samples based on WHO and Bureau of Indian Standards (BIS IS 10500:2012) drinking water limits
- **Input Features (5):**
  1. `ph` (standard pH units, safe: 6.5–8.5)
  2. `turbidity` (NTU, safe: < 10 NTU)
  3. `temperature` (°C, safe: 10–35 °C)
  4. `ec` (Electrical Conductivity in µS/cm, safe: < 500 µS/cm)
  5. `do` (Dissolved Oxygen in mg/L, safe: > 5.0 mg/L)
- **Target:** `potable` (1 = Safe/Potable, 0 = Unsafe/Treatment Required)
- **Test Set Metrics:**
  - Accuracy: **100.0%** (on synthetic benchmark)
  - ROC-AUC: **1.0000**
- **Important Note:** *This model was trained on synthetic data representing WHO standards. While mathematically sound and fully functional for demonstration, production deployment should incorporate laboratory-verified sensor measurements.*

---

## 🚀 Quick Start Guide

### Prerequisites
- [Node.js](https://nodejs.org/) (v18 or higher)
- [Python](https://www.python.org/) (v3.10 or higher)

### 1. Start the Backend API

Open PowerShell:
```powershell
cd c:\Project\RiverSentinel-main\backend
.\venv\Scripts\Activate.ps1
python app.py
```
*Backend will start on `http://localhost:5000`.*

### 2. Start the Frontend Application

Open a second PowerShell terminal:
```powershell
cd c:\Project\RiverSentinel-main\frontend
npm run dev
```
*Frontend will start on `http://localhost:3000`.*

### 3. Open the Dashboards

- **Citizen Dashboard:** [http://localhost:3000/citizen-dashboard](http://localhost:3000/citizen-dashboard)
- **Authority Dashboard:** [http://localhost:3000/authority-dashboard](http://localhost:3000/authority-dashboard)
- **Landing Page:** [http://localhost:3000](http://localhost:3000)

---

## 📡 Core API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | System health check (reports model and chatbot status) |
| `GET` | `/api/sensors/latest` | Real-time readings across all 9 sensors |
| `GET` | `/api/flood/predict` | ML flood risk evaluation with contributing factors |
| `GET` | `/api/water-quality/predict` | ML water potability evaluation with treatment advice |
| `GET` | `/api/weather` | Live weather data (falls back to defaults if key missing) |
| `POST` | `/api/ai/chat` | Multilingual chatbot (fails gracefully if key missing) |
| `POST` | `/api/ai/analyze-image` | Optical pollution analysis from uploaded image |
| `POST` | `/api/authority/send-sms` | Simulate emergency SMS broadcast |
| `POST` | `/api/authority/trigger-alert` | Broadcast system-wide flood alert |
| `POST` | `/api/authority/generate-notice` | Generate and download legal violation notice |
| `GET` | `/api/authority/export-data` | Download environmental telemetry as CSV |
| `GET` | `/api/authority/reports` | Retrieve citizen pollution reports for review |
| `GET` | `/api/authority/report-summary` | Aggregated authority dashboard statistics |
| `GET` | `/api/citizen/health-status` | Simplified river health score (0–100) and grade |

---

## 🧪 Simulation / Demo Mode

To feed simulated live sensor fluctuations into the system for demonstration:

```powershell
cd c:\Project\RiverSentinel-main\backend
.\venv\Scripts\Activate.ps1
python simulate_sensors.py
```

This generates realistic periodic sensor fluctuations (rising/falling water levels, changing turbidity, etc.) that immediately reflect on the frontend dashboards.

---

## ⚙️ Environment Configuration (`backend/.env`)

```ini
# Database
FIREBASE_DATABASE_URL=https://riversentinel-ae0b0-default-rtdb.firebaseio.com/
FIREBASE_SECRET=

# Optional AI API Keys (leave blank if unavailable)
GROQ_API_KEY=your_groq_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Optional Weather API Key (leave blank for realistic fallback weather)
OPENWEATHER_API_KEY=your_openweathermap_api_key_here

# Server
PORT=5000
```

> **Note regarding OpenAI:** The OpenAI API key in this project has reached its quota limit. The application is designed to function completely and independently without it. The chatbot optionally uses Groq if a key is provided, or displays a graceful fallback message without causing errors.

---

## 🔒 Security & Best Practices

- Secret keys are kept in `.env` files and excluded from Git tracking via `.gitignore`.
- Database credentials use environment variables; no credentials are hardcoded into frontend components.
- CORS is restricted to appropriate endpoints.
- Sensor input ranges are strictly validated before being fed into ML models to prevent NaN/Inf crashes.

---

## 📋 Known Limitations

1. **Water Quality Training Data:** The water quality model is trained on a synthetic dataset generated from WHO drinking water parameters. It provides reliable demonstration behavior, but should be trained on empirical multi-sensor lab data for scientific use.
2. **AI Chatbot Availability:** The AI chatbot depends on external LLM services (Groq). If an API key is not supplied, the chatbot displays an informational message while all other platform features remain fully operational.
3. **OpenWeatherMap Integration:** Without a valid `OPENWEATHER_API_KEY`, the platform serves realistic fallback weather telemetry for Varanasi.
