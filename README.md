# RiverSentinel 2.0 🌊

**India's First Geospatially-Intelligent River Protection System**

RiverSentinel is an Environmental Intelligence Platform dedicated to real-time river monitoring, pollution detection, and flood prediction. It leverages advanced geospatial intelligence, AI-based analytics, and IoT integration to safeguard 2.3M lives with a projected 30-minute rapid response window.

---

## 🌟 Key Features

- **🤖 AI-Powered River Analysis:** Upload imagery for automated pipeline detection of pollution hotspots.
- **🌊 Flood Prediction:** ML-based flood risk assessment boasting up to 95% accuracy.
- **📊 Interactive Dashboard:** A comprehensive real-time data visualization hub for monitoring parameters such as COD, BOD, and Dissolved Oxygen (DO).
- **💬 AI Chatbot:** An intelligent on-demand assistant providing environmental guidance and data querying capabilities.
- **🗺️ Geospatial Intelligence Map:** Native Leaflet-based integration offering precise geographical tracking and risk zones mapping.

---

## 🏗️ Project Architecture

The platform follows a separated frontend and backend service-oriented architecture, synchronized with physical IoT arrays (Arduino integrations). 

```
river-sentinel/
├── frontend/             # Next.js React application driving the interactive Dashboard and User Interfaces.
├── backend/              # Python Flask API handling ML Models, Firebase connections, and business logic.
├── arduino/              # Hardware integration scripts for deploying remote IoT sensors tracking water quality.
├── start-frontend.ps1    # Automated script to serve the frontend local development environment.
└── start-backend.ps1     # Automated script to initialize the python venv and run the backend servers.
```

## 🛠️ Tech Stack

- **Frontend Environment:** Next.js 16, React 19, Tailwind CSS 4, Leaflet
- **Backend Infrastructure:** Python 3.8+, Flask framework
- **Data & AI Operations:** Scikit-learn, OpenAI APIs, Groq
- **Database / Cloud:** Firebase Realtime Database / Firestore 

---

## 🚀 Quick Start / Setup

### Prerequisites
- [Node.js](https://nodejs.org/) (v18+ recommended)
- [Python](https://www.python.org/downloads/) (v3.8+)
- Active Internet connection to fetch dependencies

### Step-by-Step Execution

Clone the repository and run the pre-configured initialization scripts:

**1. Start the Backend API:**
Open your terminal (Powershell recommended) and execute:
```powershell
.\start-backend.ps1
```
> *This script will automatically navigate to `/backend`, set up a python virtual environment, install requirements, and run `app.py` on `http://localhost:5000`.*

**2. Start the Frontend Application:**
Open a separate terminal simultaneously and execute:
```powershell
.\start-frontend.ps1
```
> *This script will navigate to `/frontend`, install NPM dependencies, and spin up the development environment on `http://localhost:3000`.*

**3. Access the Dashboard**
Launch your browser and navigate to **[http://localhost:3000](http://localhost:3000)**.

---

## 📡 Core API Endpoints Reference

The backend exposes several critical endpoints for platform modules:
- `POST /api/ai/chat` - Queries the AI chatbot for automated assistance
- `POST /api/ai/analyze-image` - Sends payload required to run AI optical pollution checks
- `POST /api/flood/predict` - Requests ML-generated flood risk assessments
- `GET /api/health` - Simple connectivity health check for the upstream systems

---

## 🤝 Contributing
Contributions are highly welcomed to help build the next generation of geospatial river protection models. 
Please ensure any feature additions or complex modifications update corresponding modules in `.gitignore`.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request
