"""
RiverSentinel Backend – Flask API
===================================
Handles ML model inference, Firebase integration, sensor data, weather,
and authority/citizen endpoints.

Models:
  - Flood prediction  : Random Forest (6 features)
  - Water quality     : Random Forest (5 features)
"""

import base64
import io
import os
import time
import json
import requests
import random
import warnings
from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
from dotenv import load_dotenv
import numpy as np
import joblib
import csv
from datetime import datetime

# Suppress sklearn version warnings – models are re-trained so this is safe
warnings.filterwarnings('ignore', category=UserWarning, module='sklearn')

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
load_dotenv()

# ---------------------------------------------------------------------------
# Firebase Initialization
# ---------------------------------------------------------------------------
import firebase_admin
from firebase_admin import credentials, db

has_service_account = False
if not firebase_admin._apps:
    try:
        sak_path = os.path.join(os.path.dirname(__file__), 'serviceAccountKey.json')
        if os.path.exists(sak_path):
            cred = credentials.Certificate(sak_path)
            firebase_admin.initialize_app(cred, {
                'databaseURL': os.getenv('FIREBASE_DATABASE_URL')
            })
            has_service_account = True
            print("[INFO] Firebase initialized with service account")
        else:
            print("[INFO] serviceAccountKey.json not found – using REST interface for Firebase")
    except Exception as e:
        print(f"[ERROR] Firebase initialization failed: {e}")

# ---------------------------------------------------------------------------
# AI Chatbot – Groq (optional module)
# ---------------------------------------------------------------------------
try:
    from groq import Groq
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        groq_client = Groq(api_key=groq_key)
        print("[INFO] Groq chatbot initialized")
    else:
        groq_client = None
        print("[WARNING] GROQ_API_KEY not found – chatbot unavailable")
except ImportError:
    groq_client = None
    print("[WARNING] groq package not installed – chatbot unavailable")
except Exception as e:
    groq_client = None
    print(f"[WARNING] Groq initialization failed: {e}")

# ---------------------------------------------------------------------------
# ML Model Loading (done once at startup – NOT per-request)
# ---------------------------------------------------------------------------
_backend_dir = os.path.dirname(os.path.abspath(__file__))

def _load_model(filename):
    path = os.path.join(_backend_dir, filename)
    if not os.path.exists(path):
        print(f"[WARNING] Model file not found: {path}")
        return None
    try:
        return joblib.load(path)
    except Exception as e:
        print(f"[ERROR] Failed to load {filename}: {e}")
        return None

flood_model  = _load_model('flood_model.pkl')
flood_scaler = _load_model('flood_scaler.pkl')
wq_model     = _load_model('water_quality_model.pkl')
wq_scaler    = _load_model('water_quality_scaler.pkl')

if flood_model:
    print(f"[INFO] Flood model loaded (features: {flood_model.n_features_in_})")
if wq_model:
    print(f"[INFO] Water quality model loaded (features: {wq_model.n_features_in_})")

# Flood feature order (must match training)
FLOOD_FEATURES = [
    'water_level_varanasi',
    'discharge_cumec',
    'rain_varanasi_mm',
    'rain_upstream_avg_mm',
    'temperature_c',
    'humidity_pct'
]

# Water quality feature order (must match training)
WQ_FEATURES = ['ph', 'turbidity', 'temperature', 'ec', 'do']

# ---------------------------------------------------------------------------
# Flask App
# ---------------------------------------------------------------------------
app = Flask(__name__)
CORS(app, resources={r'/api/*': {'origins': '*'}})

# ---------------------------------------------------------------------------
# Firebase Helper Utilities
# ---------------------------------------------------------------------------
def _firebase_rest_url(path):
    base = os.getenv('FIREBASE_DATABASE_URL', '').rstrip('/')
    secret = os.getenv('FIREBASE_SECRET', '')
    url = f"{base}/{path}.json"
    if secret:
        url += f"?auth={secret}"
    return url


def safe_db_push(node_path, data):
    """Push data to Firebase with REST fallback."""
    if has_service_account:
        try:
            return db.reference(node_path).push(data)
        except Exception as e:
            print(f"[FALLBACK] Admin push failed for {node_path}: {e}")
    url = _firebase_rest_url(node_path)
    if url and url.startswith("http"):
        try:
            r = requests.post(url, json=data, timeout=2.0)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
    return None


def safe_db_get(node_path):
    """Get data from Firebase with REST fallback."""
    if has_service_account:
        try:
            return db.reference(node_path).get()
        except Exception as e:
            print(f"[FALLBACK] Admin get failed for {node_path}: {e}")
    url = _firebase_rest_url(node_path)
    if url and url.startswith("http"):
        try:
            r = requests.get(url, timeout=2.0)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
    return None


def safe_db_update(node_path, data):
    """Update data in Firebase with REST fallback."""
    if has_service_account:
        try:
            return db.reference(node_path).update(data)
        except Exception as e:
            print(f"[FALLBACK] Admin update failed for {node_path}: {e}")
    url = _firebase_rest_url(node_path)
    if url and url.startswith("http"):
        try:
            r = requests.patch(url, json=data, timeout=2.0)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
    return None


def _get_latest_sensor_from_firebase():
    """Return latest sensor reading dict from Firebase, or None."""
    try:
        snapshot = safe_db_get('sensor_data')
        if snapshot and isinstance(snapshot, dict):
            latest_key = max(snapshot.keys())
            return snapshot[latest_key]
        if snapshot and isinstance(snapshot, list):
            return snapshot[-1]
    except Exception as e:
        print(f"[WARNING] Could not fetch sensor data: {e}")
    return None


def _validated_sensor(reading, key, default, lo=None, hi=None):
    """Get a sensor value with range validation and fallback."""
    val = reading.get(key, default) if reading else default
    try:
        val = float(val)
    except (TypeError, ValueError):
        return default
    if lo is not None and val < lo:
        return default
    if hi is not None and val > hi:
        return default
    return val

# ---------------------------------------------------------------------------
# Core Routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    return jsonify({
        "message": "RiverSentinel Backend API",
        "status": "running",
        "flood_model": "loaded" if flood_model else "not loaded",
        "water_quality_model": "loaded" if wq_model else "not loaded",
        "chatbot": "available" if groq_client else "unavailable",
        "endpoints": [
            "/api/health",
            "/api/sensors/latest",
            "/api/flood/predict",
            "/api/water-quality/predict",
            "/api/weather",
            "/api/ai/chat",
            "/api/ai/analyze-image",
            "/api/authority/reports",
            "/api/citizen/health-status"
        ]
    })


@app.route('/api/health')
def health():
    return jsonify({
        'status': 'healthy',
        'flood_model': flood_model is not None,
        'water_quality_model': wq_model is not None,
        'chatbot': groq_client is not None,
        'timestamp': int(time.time())
    })

# ---------------------------------------------------------------------------
# Sensor Data
# ---------------------------------------------------------------------------

@app.route('/api/sensors/latest', methods=['GET'])
def get_latest_sensors():
    """Return latest sensor readings from Firebase (or safe defaults)."""
    defaults = {
        'ph': 7.5, 'turbidity': 100.0, 'temperature': 28.0,
        'humidity': 65.0, 'ec': 500.0, 'water_level': 68.5,
        'bod': 30.0, 'cod': 150.0, 'do': 7.0,
        'timestamp': int(time.time()),
        'status': 'default',
        'temperature_error': False,
        'water_level_error': False
    }

    reading = _get_latest_sensor_from_firebase()
    if reading:
        raw_temp = reading.get('temperature', 28.0)
        raw_wl   = reading.get('water_level', 68.5)

        temp_error = isinstance(raw_temp, (int, float)) and (raw_temp < -100 or raw_temp > 60)
        wl_error   = isinstance(raw_wl,   (int, float)) and raw_wl <= 0

        defaults.update({
            'ph':               max(0.0, min(14.0, float(reading.get('ph', 7.5)))),
            'turbidity':        max(0.0, float(reading.get('turbidity', 100.0))),
            'temperature':      28.0 if temp_error else float(raw_temp),
            'humidity':         max(0.0, min(100.0, float(reading.get('humidity', 65.0)))),
            'ec':               max(0.0, float(reading.get('ec', 500.0))),
            'water_level':      68.5 if wl_error else float(raw_wl),
            'bod':              max(0.0, float(reading.get('bod', 30.0))),
            'cod':              max(0.0, float(reading.get('cod', 150.0))),
            'do':               max(0.0, float(reading.get('do', 7.0))),
            'timestamp':        reading.get('timestamp', int(time.time())),
            'status':           'live',
            'temperature_error': temp_error,
            'water_level_error': wl_error
        })
    else:
        print("[WARNING] No Firebase sensor data – returning defaults")

    return jsonify(defaults)

# ---------------------------------------------------------------------------
# Flood Prediction
# ---------------------------------------------------------------------------

@app.route('/api/flood/predict', methods=['GET', 'POST'])
def predict_flood_risk():
    """Predict flood risk using the trained 6-feature Random Forest model.
    Accepts GET (telemetry defaults) or POST with custom feature overrides.
    """
    if not flood_model or not flood_scaler:
        return jsonify({
            'error': 'Flood prediction model not loaded. Run train_flood_model.py first.',
            'risk_level': 'UNKNOWN',
            'flood_probability': 0,
            'reasons': ['Model unavailable']
        }), 503

    # --- Defaults ---
    water_level = 68.5
    temperature = 28.0
    humidity    = 65.0

    # --- Live sensor data ---
    reading = _get_latest_sensor_from_firebase()
    if reading:
        raw_temp = reading.get('temperature', 28.0)
        raw_wl   = reading.get('water_level', 68.5)

        if isinstance(raw_temp, (int, float)) and -10 <= raw_temp <= 60:
            temperature = float(raw_temp)

        if isinstance(raw_wl, (int, float)) and raw_wl > 0:
            water_level = float(raw_wl)

        humidity = max(0.0, min(100.0, float(reading.get('humidity', 65.0))))

        bod      = max(0.0, float(reading.get('bod',      30.0)))
        cod      = max(0.0, float(reading.get('cod',     150.0)))
        do_level = max(0.0, float(reading.get('do',        7.0)))
    else:
        bod, cod, do_level = 30.0, 150.0, 7.0

    # --- Rainfall from OpenWeatherMap ---
    rain_varanasi  = 0.0
    rain_upstream  = 0.0
    api_key = os.getenv('OPENWEATHER_API_KEY', '')
    if api_key:
        try:
            lat, lon = 25.3176, 82.9739
            url = (f"https://api.openweathermap.org/data/2.5/weather"
                   f"?lat={lat}&lon={lon}&appid={api_key}&units=metric")
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                wd = resp.json()
                r1h = wd.get('rain', {}).get('1h', 0) or 0
                r3h = wd.get('rain', {}).get('3h', 0) or 0
                rain_varanasi = float(r1h if r1h > 0 else r3h / 3.0)
                rain_upstream = rain_varanasi * 1.2
        except Exception as e:
            print(f"[WARNING] Weather API failed: {e}")

    # Check for POST or query-param overrides
    req_data = request.get_json(silent=True) or {}
    if request.args:
        req_data = {**request.args.to_dict(), **req_data}

    if req_data:
        try:
            if 'water_level_varanasi' in req_data or 'water_level' in req_data:
                water_level = float(req_data.get('water_level_varanasi', req_data.get('water_level', water_level)))
            if 'discharge_cumec' in req_data or 'discharge' in req_data:
                discharge_val = float(req_data.get('discharge_cumec', req_data.get('discharge', 0)))
            else:
                discharge_val = None
            if 'rain_varanasi_mm' in req_data or 'rain_varanasi' in req_data:
                rain_varanasi = float(req_data.get('rain_varanasi_mm', req_data.get('rain_varanasi', rain_varanasi)))
            if 'rain_upstream_avg_mm' in req_data or 'rain_upstream' in req_data:
                rain_upstream = float(req_data.get('rain_upstream_avg_mm', req_data.get('rain_upstream', rain_upstream)))
            if 'temperature_c' in req_data or 'temperature' in req_data:
                temperature = float(req_data.get('temperature_c', req_data.get('temperature', temperature)))
            if 'humidity_pct' in req_data or 'humidity' in req_data:
                humidity = float(req_data.get('humidity_pct', req_data.get('humidity', humidity)))
        except (ValueError, TypeError):
            pass
    else:
        discharge_val = None

    # --- Discharge estimate if not explicitly provided ---
    discharge = discharge_val if discharge_val is not None else (8000.0 + (water_level - 65.0) * 2000.0)

    # --- Model inference ---
    features = np.array([[
        water_level,    # water_level_varanasi
        discharge,      # discharge_cumec
        rain_varanasi,  # rain_varanasi_mm
        rain_upstream,  # rain_upstream_avg_mm
        temperature,    # temperature_c
        humidity        # humidity_pct
    ]])

    try:
        f_scaled = flood_scaler.transform(features)
        prediction_bin = int(flood_model.predict(f_scaled)[0])
        flood_prob     = float(flood_model.predict_proba(f_scaled)[0][1])
    except Exception as e:
        print(f"[ERROR] Flood inference failed: {e}")
        return jsonify({'error': str(e), 'risk_level': 'UNKNOWN',
                        'flood_probability': 0, 'reasons': [str(e)]}), 500

    # --- Risk classification ---
    if flood_prob >= 0.70:
        risk_level = 'HIGH'
        message = 'High flood risk detected. Immediate action recommended.'
    elif flood_prob >= 0.40:
        risk_level = 'MODERATE'
        message = 'Moderate flood risk. Monitor conditions closely.'
    else:
        risk_level = 'LOW'
        message = 'Low flood risk. Conditions are normal.'

    # --- Key reasons ---
    reasons = []
    if water_level > 68.0:
        reasons.append(f"Water level elevated ({water_level:.2f} m)")
    if rain_varanasi > 50:
        reasons.append(f"Heavy local rainfall ({rain_varanasi:.1f} mm/h)")
    if rain_upstream > 80:
        reasons.append(f"High upstream rainfall ({rain_upstream:.1f} mm/h)")
    if discharge > 12000:
        reasons.append(f"High discharge ({discharge:.0f} cumec)")
    if not reasons:
        reasons.append("All parameters within normal range")

    return jsonify({
        'prediction':        'FLOOD' if prediction_bin == 1 else 'NO_FLOOD',
        'flood_probability': round(flood_prob * 100, 2),
        'risk_level':        risk_level,
        'message':           message,
        'reasons':           reasons,
        'sensor_data': {
            'water_level':   round(water_level, 2),
            'discharge':     round(discharge, 2),
            'rain_varanasi': round(rain_varanasi, 2),
            'rain_upstream': round(rain_upstream, 2),
            'temperature':   round(temperature, 2),
            'humidity':      round(humidity, 2),
            'bod':           round(bod, 1),
            'cod':           round(cod, 1),
            'do':            round(do_level, 1)
        },
        'prediction_time': datetime.now().strftime('%Y-%m-%dT%H:%M:%S+05:30')
    })

# ---------------------------------------------------------------------------
# Water Quality / Pollution Prediction
# ---------------------------------------------------------------------------

@app.route('/api/water-quality/predict', methods=['GET', 'POST'])
def predict_water_quality():
    """Predict water potability using 5-feature Random Forest model.
    Accepts GET (telemetry defaults) or POST with custom feature overrides.
    """
    if not wq_model or not wq_scaler:
        return jsonify({
            'error': 'Water quality model not loaded. Run train_water_quality_model.py first.',
            'potable': None, 'quality_level': 'UNKNOWN', 'quality_score': 0,
            'reasons': ['Model unavailable']
        }), 503

    # --- Defaults ---
    ph        = 7.0
    turbidity = 100.0
    temp      = 28.0
    ec        = 500.0
    do_level  = 7.0

    # Extra display-only params
    humidity    = 65.0
    water_level = 68.5
    bod         = 30.0
    cod         = 150.0

    # --- Live sensor data ---
    reading = _get_latest_sensor_from_firebase()
    if reading:
        ph        = max(0.0,   min(14.0,  float(reading.get('ph',          ph))))
        turbidity = max(0.0,             float(reading.get('turbidity',  turbidity)))
        temp      = float(reading.get('temperature', temp))
        ec        = max(0.0,             float(reading.get('ec',          ec)))
        do_level  = max(0.0,             float(reading.get('do',       do_level)))
        humidity    = max(0.0, min(100.0, float(reading.get('humidity',  humidity))))
        water_level = max(0.0,            float(reading.get('water_level', water_level)))
        bod         = max(0.0,            float(reading.get('bod',          bod)))
        cod         = max(0.0,            float(reading.get('cod',          cod)))

    # Check for POST or query-param overrides
    req_data = request.get_json(silent=True) or {}
    if request.args:
        req_data = {**request.args.to_dict(), **req_data}

    if req_data:
        try:
            if 'ph' in req_data:
                ph = max(0.0, min(14.0, float(req_data['ph'])))
            if 'turbidity' in req_data:
                turbidity = max(0.0, float(req_data['turbidity']))
            if 'temperature' in req_data or 'temperature_c' in req_data:
                temp = float(req_data.get('temperature', req_data.get('temperature_c', temp)))
            if 'ec' in req_data:
                ec = max(0.0, float(req_data['ec']))
            if 'do' in req_data or 'do_level' in req_data:
                do_level = max(0.0, float(req_data.get('do', req_data.get('do_level', do_level))))
            if 'humidity' in req_data or 'humidity_pct' in req_data:
                humidity = max(0.0, min(100.0, float(req_data.get('humidity', req_data.get('humidity_pct', humidity)))))
            if 'water_level' in req_data:
                water_level = max(0.0, float(req_data['water_level']))
            if 'bod' in req_data:
                bod = max(0.0, float(req_data['bod']))
            if 'cod' in req_data:
                cod = max(0.0, float(req_data['cod']))
        except (ValueError, TypeError):
            pass

    # --- Inference ---
    features = np.array([[ph, turbidity, temp, ec, do_level]])
    try:
        f_scaled   = wq_scaler.transform(features)
        prediction = int(wq_model.predict(f_scaled)[0])
        proba      = wq_model.predict_proba(f_scaled)[0]
        potable_score = float(proba[1]) * 100 if len(proba) > 1 else float(proba[0]) * 100
    except Exception as e:
        print(f"[ERROR] Water quality inference failed: {e}")
        return jsonify({'error': str(e), 'potable': None,
                        'quality_level': 'UNKNOWN', 'quality_score': 0,
                        'reasons': [str(e)]}), 500

    is_potable = (prediction == 1)

    # --- Quality level ---
    if potable_score >= 80:
        quality_level = "EXCELLENT"
    elif potable_score >= 60:
        quality_level = "GOOD"
    elif potable_score >= 40:
        quality_level = "MODERATE"
    else:
        quality_level = "POOR"

    # --- Reasons & recommendations ---
    reasons = []
    recommendations = []

    if ph < 6.5 or ph > 8.5:
        reasons.append(f"pH {'too low' if ph < 6.5 else 'too high'} ({ph:.2f})")
        recommendations.append("pH adjustment required for safe consumption")
    else:
        reasons.append(f"pH level optimal ({ph:.2f})")

    if turbidity > 200:
        reasons.append(f"High turbidity ({turbidity:.1f} NTU)")
        recommendations.append("Filtration recommended to reduce turbidity")
    elif turbidity > 100:
        reasons.append(f"Moderate turbidity ({turbidity:.1f} NTU)")

    if bod > 50:
        reasons.append(f"High BOD ({bod:.1f} mg/L)")
        recommendations.append("Water treatment needed to reduce organic matter")
    elif bod > 30:
        reasons.append(f"Elevated BOD ({bod:.1f} mg/L)")

    if cod > 200:
        reasons.append(f"High COD ({cod:.1f} mg/L)")
        recommendations.append("Advanced treatment required")

    if do_level < 5:
        reasons.append(f"Low dissolved oxygen ({do_level:.1f} mg/L)")
        recommendations.append("Aeration recommended")
    else:
        reasons.append(f"Good dissolved oxygen ({do_level:.1f} mg/L)")

    if ec > 1000:
        reasons.append(f"High conductivity ({ec:.0f} µS/cm)")
        recommendations.append("Desalination may be required")

    if is_potable:
        message = ("Water quality is excellent. Safe for consumption."
                   if quality_level == "EXCELLENT"
                   else "Water is potable but may benefit from treatment.")
    else:
        message = "Water is not safe for direct consumption. Treatment required."

    if not recommendations:
        recommendations.append("Continue regular monitoring")

    return jsonify({
        'potable':         is_potable,
        'quality_score':   round(potable_score, 2),
        'quality_level':   quality_level,
        'message':         message,
        'reasons':         reasons[:5],
        'recommendations': recommendations[:3],
        'sensor_data': {
            'ph':          round(ph, 2),
            'turbidity':   round(turbidity, 1),
            'temperature': round(temp, 1),
            'humidity':    round(humidity, 1),
            'ec':          round(ec, 0),
            'water_level': round(water_level, 2),
            'bod':         round(bod, 1),
            'cod':         round(cod, 1),
            'do':          round(do_level, 1)
        },
        'prediction_time': datetime.now().strftime('%Y-%m-%dT%H:%M:%S+05:30')
    })

# ---------------------------------------------------------------------------
# Weather
# ---------------------------------------------------------------------------

@app.route('/api/weather', methods=['GET'])
def get_weather():
    """Fetch weather for Varanasi (Ganga). Falls back to plausible defaults."""
    api_key = os.getenv('OPENWEATHER_API_KEY', '')
    lat, lon = 25.3176, 83.0099

    if api_key:
        try:
            url = (f"https://api.openweathermap.org/data/2.5/weather"
                   f"?lat={lat}&lon={lon}&appid={api_key}&units=metric")
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                d = resp.json()
                r1h = d.get('rain', {}).get('1h', 0) or 0
                r3h = d.get('rain', {}).get('3h', 0) or 0
                rain_rate = float(r1h if r1h > 0 else r3h / 3.0)
                return jsonify({
                    'temperature': round(d['main']['temp'], 1),
                    'feels_like':  round(d['main']['feels_like'], 1),
                    'humidity':    d['main']['humidity'],
                    'pressure':    d['main']['pressure'],
                    'description': d['weather'][0]['description'],
                    'icon':        d['weather'][0]['icon'],
                    'wind_speed':  round(d['wind']['speed'] * 3.6, 1),
                    'clouds':      d['clouds']['all'],
                    'visibility':  d.get('visibility', 10000) / 1000,
                    'rain':        rain_rate,
                    'rainfall_24h': rain_rate * 24,
                    'city':        'Varanasi (Ganga)',
                    'timestamp':   d['dt'],
                    'fallback':    False
                })
        except Exception as e:
            print(f"[WARNING] Weather API failed: {e}")

    # Fallback
    return jsonify({
        'temperature': 28.5, 'feels_like': 30.2, 'humidity': 65,
        'pressure': 1012, 'description': 'partly cloudy',
        'icon': '02d', 'wind_speed': 12.5, 'clouds': 40,
        'visibility': 10, 'rain': 0, 'rainfall_24h': 0,
        'city': 'Varanasi', 'timestamp': int(time.time()), 'fallback': True
    })

# ---------------------------------------------------------------------------
# AI Chatbot (Groq – optional)
# ---------------------------------------------------------------------------

SYSTEM_PROMPTS = {
    'English': ('You are RiverSentinel AI assistant, an expert on river water quality, '
                'pollution monitoring, and flood prediction. Provide helpful, accurate '
                'information about environmental monitoring and river safety. '
                'You MUST respond ONLY in English.'),
    'हिन्दी': ('आप RiverSentinel AI सहायक हैं, जो नदी जल गुणवत्ता, प्रदूषण निगरानी और '
                'बाढ़ पूर्वानुमान के विशेषज्ञ हैं। आपको केवल हिन्दी में ही जवाब देना है।'),
    'भोजपुरी': ('रउआ RiverSentinel AI सहायक बानी। रउआ के केवल भोजपुरी में ही जवाब देवे के बा।'),
    'বাংলা': ('আপনি RiverSentinel AI সহায়ক। আপনাকে শুধুমাত্র বাংলায় উত্তর দিতে হবে।')
}


@app.route('/api/ai/chat', methods=['POST'])
def chat():
    """Chatbot via Groq. Returns a graceful message when unavailable."""
    if not groq_client:
        return jsonify({
            'response': (
                'AI chatbot is currently unavailable because the configured AI service '
                'is unavailable. Please add a valid GROQ_API_KEY to backend/.env and '
                'restart the server.'
            )
        })

    data = request.json or {}
    query = str(data.get('query', '')).strip()
    language = str(data.get('language', 'English'))

    if not query:
        return jsonify({'response': 'Please ask a question.'}), 400

    system_prompt = SYSTEM_PROMPTS.get(language, SYSTEM_PROMPTS['English'])

    try:
        completion = groq_client.chat.completions.create(
            model='qwen/qwen3.8-27b',
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user',   'content': query}
            ],
            temperature=0.7,
            max_tokens=800
        )
        response_text = completion.choices[0].message.content
        return jsonify({'response': response_text})
    except Exception as e:
        print(f"[ERROR] Groq chat error: {e}")
        return jsonify({
            'response': (
                'AI chatbot is currently unavailable because the configured AI service '
                'is unavailable. Please try again later.'
            )
        })


@app.route('/api/ai/analyze-image', methods=['POST'])
def analyze_image():
    """Analyze river image for pollution using Groq vision model."""
    if not groq_client:
        return jsonify({
            'error': 'AI vision module unavailable. Check GROQ_API_KEY in .env'
        }), 503

    if 'image' not in request.files or request.files['image'].filename == '':
        return jsonify({'error': 'No image provided'}), 400

    image_file = request.files['image']
    try:
        image_bytes   = image_file.read()
        b64_image     = base64.b64encode(image_bytes).decode('utf-8')
        mime_type     = image_file.mimetype or 'image/jpeg'

        prompt = (
            'Analyze this river image for pollution. Return ONLY raw JSON:\n'
            '{"pollution_level":"Low"|"Moderate"|"High"|"Critical",'
            '"confidence":<0-100>,'
            '"pollutants":["list"],'
            '"assessment":"brief description"}'
        )

        completion = groq_client.chat.completions.create(
            messages=[{
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': prompt},
                    {'type': 'image_url', 'image_url': {
                        'url': f"data:{mime_type};base64,{b64_image}"
                    }}
                ]
            }],
            model='qwen/qwen3.8-27b',
            temperature=0.1, max_tokens=512
        )

        raw = completion.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if '```json' in raw:
            raw = raw.split('```json')[1].split('```')[0].strip()
        elif '```' in raw:
            raw = raw.split('```')[1].split('```')[0].strip()

        result = json.loads(raw)

        # Persist to Firebase
        try:
            ts = int(time.time() * 1000)
            safe_db_push('analysis_history', {
                **result,
                'timestamp': ts,
                'imageUrl':  f"data:{mime_type};base64,{b64_image}",
                'status':    'PENDING',
                'location':  'Ganga River',
                'reporter':  'Citizen AI'
            })
        except Exception as fe:
            print(f"[WARNING] Firebase save failed: {fe}")

        return jsonify(result)

    except Exception as e:
        print(f"[ERROR] Image analysis error: {e}")
        return jsonify({'error': str(e)}), 500

# ---------------------------------------------------------------------------
# Authority Actions
# ---------------------------------------------------------------------------

@app.route('/api/authority/send-sms', methods=['POST'])
def send_emergency_sms():
    data = request.get_json(silent=True) or {}
    message = data.get(
        'message',
        "EMERGENCY: River water levels rising. Stay away from ghat areas. – RiverSentinel"
    )
    mock_targets = ["+91 987XXXXX21", "+91 882XXXXX45", "+91 701XXXXX89"]
    print(f"[AUTHORITY] SMS: {message} | Targets: {len(mock_targets)}")
    time.sleep(1)
    return jsonify({
        'status':     'success',
        'message':    'Emergency SMS broadcast initiated',
        'recipients': len(mock_targets),
        'timestamp':  datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })


@app.route('/api/authority/trigger-alert', methods=['POST'])
def trigger_alert():
    data      = request.get_json(silent=True) or {}
    a_type    = data.get('type', 'FLOOD')
    severity  = data.get('severity', 'CRITICAL')
    print(f"[AUTHORITY] {severity} {a_type} ALERT TRIGGERED")
    try:
        safe_db_push('alerts', {
            'type':      a_type,
            'severity':  severity,
            'title':     f"{severity} {a_type} WARNING",
            'message':   f"System-wide {a_type.lower()} alert activated. Take immediate precautions.",
            'timestamp': int(time.time() * 1000),
            'active':    True
        })
    except Exception as e:
        print(f"[WARNING] Firebase alert push failed: {e}")
    return jsonify({
        'status':    'success',
        'message':   f"{severity} {a_type} alert triggered",
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })


@app.route('/api/authority/generate-notice', methods=['POST'])
def generate_legal_notice():
    notice_id = f"RS-NOT-2026-{random.randint(1000, 9999)}"
    content = f"""RIVER SENTINEL – AUTHORITY LEGAL NOTICE
Code: {notice_id}
Date: {datetime.now().strftime("%B %d, %Y")}

TO: INDUSTRIAL COMPLIANCE DIVISION / LOCAL BODIES
SUBJECT: ENVIRONMENTAL VIOLATION NOTICE

Notice is hereby given based on automated monitoring from RiverSentinel Station: Assi Ghat.
Recent measurements recorded:
  COD: 210 mg/L  (Limit: 150 mg/L)
  BOD:  65 mg/L  (Limit:  30 mg/L)
  DO:   3.2 mg/L (Minimum: 4.0 mg/L)

ACTION: Immediate inspection and containment within 24 hours.

Issued by:
Central Pollution Control Board (UPPCB)
RiverSentinel Intelligent Dashboard
"""
    return jsonify({
        'status':    'success',
        'notice_id': notice_id,
        'content':   content,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })


@app.route('/api/authority/export-data', methods=['GET'])
def export_system_data():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Timestamp', 'Station', 'pH', 'Turbidity', 'Temp (C)',
                     'Water Level (m)', 'BOD', 'COD', 'DO'])
    base_time = time.time()
    for i in range(10):
        row_time = datetime.fromtimestamp(base_time - i * 3600).strftime('%Y-%m-%d %H:%M:%S')
        writer.writerow([
            row_time, 'Assi Ghat',
            round(random.uniform(6.5, 8.5), 2),
            round(random.uniform(50, 200), 1),
            round(random.uniform(25, 30), 1),
            round(random.uniform(67, 69), 2),
            round(random.uniform(20, 40), 1),
            round(random.uniform(100, 180), 1),
            round(random.uniform(4, 9), 1)
        ])
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=RiverSentinel_Export.csv'
    response.headers['Content-type'] = 'text/csv'
    return response


@app.route('/api/authority/reports', methods=['GET'])
def get_reports():
    mock_reports = [
        {'id': 'mock_1', 'location': 'Dashashwamedh Steps', 'reporter': 'Aviral S.',
         'pollution_level': 'High', 'status': 'PENDING',
         'timestamp': int(time.time() * 1000),
         'assessment': 'Visible oil slicks near boat landing.'},
        {'id': 'mock_2', 'location': 'Assi Ghat', 'reporter': 'Priya V.',
         'pollution_level': 'Moderate', 'status': 'VERIFIED',
         'timestamp': int(time.time() * 1000) - 3600000,
         'assessment': 'Plastic waste at riverbank.'}
    ]
    try:
        reports_dict = safe_db_get('analysis_history')
        if not reports_dict:
            return jsonify(mock_reports)

        real_reports = []
        items = reports_dict.items() if isinstance(reports_dict, dict) else enumerate(reports_dict)
        for key, val in items:
            if not isinstance(val, dict):
                continue
            val['id'] = str(key)
            val.setdefault('status', 'PENDING')
            val.setdefault('location', 'Dashashwamedh Steps')
            val.setdefault('reporter', 'Anonymous')
            real_reports.append(val)

        if real_reports:
            real_reports.sort(key=lambda x: x.get('timestamp', 0) or 0, reverse=True)
            return jsonify(real_reports)
    except Exception as e:
        print(f"[ERROR] get_reports: {e}")

    return jsonify(mock_reports)


@app.route('/api/authority/reports/update', methods=['POST'])
def update_report_status():
    data      = request.get_json(silent=True) or {}
    report_id = data.get('reportId')
    new_status = data.get('status')
    if not report_id or not new_status:
        return jsonify({'status': 'error', 'message': 'Missing reportId or status'}), 400
    safe_db_update(f'analysis_history/{report_id}', {'status': new_status})
    return jsonify({
        'status':    'success',
        'message':   f"Report marked as {new_status.lower()}",
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })


@app.route('/api/reports/submit', methods=['POST'])
def submit_full_report():
    data = request.get_json(silent=True) or {}
    safe_db_push('analysis_history', {
        **data,
        'timestamp': int(time.time() * 1000),
        'status':    'PENDING'
    })
    return jsonify({'status': 'success', 'message': 'Report submitted successfully'})


@app.route('/api/authority/report-summary', methods=['GET'])
def get_report_summary():
    sensor_stats = {'avg_ph': 7.2, 'avg_do': 6.8, 'avg_turbidity': 15.5,
                    'avg_water_level': 65.0, 'trend': 'STABLE'}
    report_stats = {'total': 12, 'verified': 8, 'rejected': 2,
                    'pending': 2, 'resolution_rate': 83.3}
    active_alerts = 1

    try:
        sensors = safe_db_get('sensor_data')
        if sensors:
            vals = [v for v in (sensors.values() if isinstance(sensors, dict)
                                else sensors) if isinstance(v, dict)]
            if vals:
                def safe_avg(key, default):
                    nums = [float(v[key]) for v in vals
                            if v.get(key) is not None]
                    return round(float(np.mean(nums)), 2) if nums else default
                sensor_stats.update({
                    'avg_ph':          safe_avg('ph', 7.2),
                    'avg_do':          safe_avg('do', 6.8),
                    'avg_turbidity':   safe_avg('turbidity', 15.5),
                    'avg_water_level': safe_avg('water_level', 65.0)
                })

        all_reports = safe_db_get('analysis_history')
        if all_reports:
            rlist = [r for r in (all_reports.values() if isinstance(all_reports, dict)
                                 else all_reports) if isinstance(r, dict)]
            if rlist:
                stats = {'total': len(rlist), 'verified': 0, 'rejected': 0, 'pending': 0}
                for r in rlist:
                    s = str(r.get('status', 'PENDING')).upper()
                    if s == 'VERIFIED':   stats['verified'] += 1
                    elif s == 'REJECTED': stats['rejected'] += 1
                    else:                 stats['pending'] += 1
                total = stats['total']
                stats['resolution_rate'] = round(
                    (stats['verified'] + stats['rejected']) / total * 100, 1
                ) if total else 0.0
                report_stats.update(stats)

        alerts = safe_db_get('alerts')
        if alerts:
            alist = [a for a in (alerts.values() if isinstance(alerts, dict)
                                 else alerts) if isinstance(a, dict)]
            active_alerts = len([a for a in alist if a.get('active', True)])
        else:
            active_alerts = 0

    except Exception as e:
        print(f"[ERROR] report-summary: {e}")

    return jsonify({
        'status':         'success',
        'sensor_summary': sensor_stats,
        'report_summary': report_stats,
        'active_alerts':  active_alerts,
        'generated_at':   datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'agency':         'UP Pollution Control Board (VARANASI)'
    })


@app.route('/api/citizen/health-status', methods=['GET'])
def get_citizen_health_status():
    health_score = 78
    grade  = 'B+'
    status = 'SAFE'
    metrics = {'ph': 7.4, 'do': 6.5, 'purity': 88}

    reading = _get_latest_sensor_from_firebase()
    if reading:
        try:
            metrics['ph'] = float(reading.get('ph', 7.4))
            metrics['do'] = float(reading.get('do', 6.5))
            turb = float(reading.get('turbidity', 15.0))
            metrics['purity'] = max(0.0, min(100.0, 100.0 - turb / 5.0))

            ph_score = 100 - abs(metrics['ph'] - 7) * 20
            score = (ph_score * 0.3) + (metrics['do'] * 10 * 0.4) + (metrics['purity'] * 0.3)
            health_score = int(max(0, min(100, score)))

            if   health_score > 90: grade, status = 'A+', 'EXCELLENT'
            elif health_score > 80: grade, status = 'A',  'SAFE'
            elif health_score > 70: grade, status = 'B+', 'NOTICE'
            elif health_score > 60: grade, status = 'B',  'CAUTION'
            else:                   grade, status = 'C',  'WARNING'
        except Exception as e:
            print(f"[WARNING] health-status calculation error: {e}")

    return jsonify({
        'status':        'success',
        'health_score':  health_score,
        'grade':         grade,
        'safety_status': status,
        'metrics':       metrics,
        'location':      'Varanasi (Dashashwamedh)',
        'authority':     'Varanasi Nagar Nigam & Namami Gange',
        'timestamp':     datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print(f"[INFO] Starting RiverSentinel backend on port {port}")
    app.run(debug=True, host='0.0.0.0', port=port)
