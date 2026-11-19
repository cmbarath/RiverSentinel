"""
Predictions & ML Routes Blueprint
Handles Random Forest flood risk forecasting, water quality evaluation, and Open-Meteo weather fetching.
"""

from flask import Blueprint, jsonify, request
import os
import time
import requests
import joblib
import numpy as np
from datetime import datetime
from services.supabase_service import get_latest_sensor_reading, supabase_insert

predictions_bp = Blueprint('predictions', __name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# ML Artifact Initialization
# ---------------------------------------------------------------------------
flood_model = None
flood_scaler = None
water_quality_model = None
water_quality_scaler = None

try:
    flood_model_path = os.path.join(BASE_DIR, 'flood_model.pkl')
    flood_scaler_path = os.path.join(BASE_DIR, 'flood_scaler.pkl')
    if os.path.exists(flood_model_path) and os.path.exists(flood_scaler_path):
        flood_model = joblib.load(flood_model_path)
        flood_scaler = joblib.load(flood_scaler_path)
        print("[INFO] Flood model loaded (features: 6)")
except Exception as e:
    print(f"[ERROR] Failed to load flood model: {e}")

try:
    wq_model_path = os.path.join(BASE_DIR, 'water_quality_model.pkl')
    wq_scaler_path = os.path.join(BASE_DIR, 'water_quality_scaler.pkl')
    if os.path.exists(wq_model_path) and os.path.exists(wq_scaler_path):
        water_quality_model = joblib.load(wq_model_path)
        water_quality_scaler = joblib.load(wq_scaler_path)
        print("[INFO] Water quality model loaded (features: 5)")
except Exception as e:
    print(f"[ERROR] Failed to load water quality model: {e}")


def _validated_sensor(reading, key, default, lo=None, hi=None):
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


@predictions_bp.route('/api/weather', methods=['GET'])
def get_weather():
    """Fetch live weather data from Open-Meteo for Varanasi."""
    try:
        lat, lon = 25.3176, 82.9739
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m"
            f"&timezone=Asia%2FKolkata"
        )
        r = requests.get(url, timeout=3.0)
        if r.status_code == 200:
            c = r.json().get('current', {})
            return jsonify({
                'temperature': c.get('temperature_2m', 28.0),
                'humidity':    c.get('relative_humidity_2m', 65),
                'rain_mm':     c.get('precipitation', 0.0),
                'wind_speed':  c.get('wind_speed_10m', 8.0),
                'condition':   'Clear' if c.get('weather_code', 0) < 3 else 'Cloudy / Rain',
                'source':      'Open-Meteo'
            })
    except Exception as e:
        print(f"[WARNING] Open-Meteo fetch failed: {e}")

    return jsonify({
        'temperature': 28.5,
        'humidity':    65,
        'rain_mm':     0.0,
        'wind_speed':  7.5,
        'condition':   'Partly Cloudy (Default)',
        'source':      'default'
    })


@predictions_bp.route('/api/flood/predict', methods=['GET', 'POST'])
def predict_flood_risk():
    """Execute flood risk prediction using 6-feature Random Forest model."""
    reading = get_latest_sensor_reading()

    # Base values
    water_level   = _validated_sensor(reading, 'water_level', 67.5, 50, 90)
    bod           = _validated_sensor(reading, 'bod', 20.0)
    cod           = _validated_sensor(reading, 'cod', 80.0)
    do_level      = _validated_sensor(reading, 'do', 6.5)
    temperature   = _validated_sensor(reading, 'temperature', 28.0, 0, 50)
    humidity      = _validated_sensor(reading, 'humidity', 65.0, 0, 100)
    rain_varanasi = 0.0
    rain_upstream = 0.0

    # Overrides from JSON payload
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        water_level   = float(data.get('water_level', water_level))
        discharge_in  = data.get('discharge')
        rain_varanasi = float(data.get('rain_varanasi', rain_varanasi))
        rain_upstream = float(data.get('rain_upstream', rain_upstream))
        temperature   = float(data.get('temperature', temperature))
        humidity      = float(data.get('humidity', humidity))
    else:
        discharge_in = None

    # Estimate discharge if not supplied
    if discharge_in is not None:
        discharge = float(discharge_in)
    else:
        h = max(0.0, water_level - 58.0)
        discharge = round(float(25.0 * 50.0 * (h ** 1.3)), 2)

    if flood_model is None or flood_scaler is None:
        return jsonify({
            'error': 'Flood prediction model not available',
            'status': 'unavailable'
        }), 503

    features = np.array([[
        water_level,
        discharge,
        rain_varanasi,
        rain_upstream,
        temperature,
        humidity
    ]])

    try:
        scaled_features = flood_scaler.transform(features)
        prediction_bin  = int(flood_model.predict(scaled_features)[0])
        probabilities   = flood_model.predict_proba(scaled_features)[0]
        flood_prob      = float(probabilities[1])
    except Exception as e:
        return jsonify({'error': f'Inference failed: {str(e)}'}), 500

    # Risk classification
    if flood_prob >= 0.70:
        risk_level = 'HIGH'
        message = 'High flood risk detected. Immediate monitoring recommended.'
    elif flood_prob >= 0.40:
        risk_level = 'MODERATE'
        message = 'Moderate flood risk. Monitor conditions closely.'
    else:
        risk_level = 'LOW'
        message = 'Low flood risk. River conditions within normal range.'

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

    # Persist prediction audit record in Supabase
    try:
        supabase_insert('flood_predictions', {
            'risk_level': risk_level,
            'flood_probability': round(flood_prob * 100, 2),
            'water_level': round(water_level, 2),
            'discharge': round(discharge, 2),
            'rain_varanasi': round(rain_varanasi, 2),
            'rain_upstream': round(rain_upstream, 2),
            'message': message,
            'reasons': reasons
        })
    except Exception:
        pass

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
        'prediction_time': datetime.now().strftime('%Y-%m-%dT%H:%M:%S+05:30'),
        'disclaimer': 'Statistical early-warning estimate from 6-feature Random Forest; consult official CWC bulletins for statutory warnings.'
    })


@predictions_bp.route('/api/water-quality/predict', methods=['GET', 'POST'])
def predict_water_quality():
    """Predict water potability screening and quality score."""
    reading = get_latest_sensor_reading()

    ph          = _validated_sensor(reading, 'ph', 7.5, 0, 14)
    turbidity   = _validated_sensor(reading, 'turbidity', 15.0, 0, 5000)
    temperature = _validated_sensor(reading, 'temperature', 26.0, -10, 60)
    ec          = _validated_sensor(reading, 'ec', 480.0, 0, 10000)
    do_level    = _validated_sensor(reading, 'do', 6.8, 0, 30)
    bod         = _validated_sensor(reading, 'bod', 18.0, 0, 500)
    cod         = _validated_sensor(reading, 'cod', 85.0, 0, 1000)
    water_level = _validated_sensor(reading, 'water_level', 67.5, 0, 100)
    humidity    = _validated_sensor(reading, 'humidity', 65.0, 0, 100)

    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        ph          = float(data.get('ph', ph))
        turbidity   = float(data.get('turbidity', turbidity))
        temperature = float(data.get('temperature', temperature))
        ec          = float(data.get('ec', ec))
        do_level    = float(data.get('do', do_level))

    if water_quality_model is None or water_quality_scaler is None:
        return jsonify({'error': 'Water quality model not loaded'}), 503

    try:
        features = np.array([[ph, turbidity, temperature, ec, do_level]])
        scaled_features = water_quality_scaler.transform(features)
        is_potable = bool(water_quality_model.predict(scaled_features)[0] == 1)
    except Exception as e:
        return jsonify({'error': f'Inference failed: {str(e)}'}), 500

    # Calculate heuristic score
    score = 100.0
    reasons = []
    if ph < 6.5 or ph > 8.5:
        score -= 20
        reasons.append(f"pH level non-optimal ({ph:.2f})")
    else:
        reasons.append(f"pH level optimal ({ph:.2f})")

    if turbidity > 50:
        score -= 30
        reasons.append(f"High turbidity ({turbidity:.1f} NTU)")
    elif turbidity > 10:
        score -= 15
        reasons.append(f"Moderate turbidity ({turbidity:.1f} NTU)")

    if do_level < 4.0:
        score -= 25
        reasons.append(f"Critical dissolved oxygen ({do_level:.1f} mg/L)")
    elif do_level >= 5.0:
        reasons.append(f"Good dissolved oxygen ({do_level:.1f} mg/L)")

    if bod > 30.0:
        score -= 15
        reasons.append(f"Elevated BOD ({bod:.1f} mg/L)")

    score = max(0.0, min(100.0, score))
    quality_level = 'GOOD' if score >= 70 else 'MODERATE' if score >= 40 else 'POOR'

    return jsonify({
        'potable': is_potable,
        'quality_score': score,
        'quality_level': quality_level,
        'message': 'Water is suitable for direct consumption with basic filtration.' if is_potable else 'Water is not safe for direct consumption. Treatment required.',
        'reasons': reasons,
        'recommendations': ['Continue regular monitoring'] if is_potable else ['Boil or purify before drinking', 'Avoid direct consumption'],
        'sensor_data': {
            'ph': ph,
            'turbidity': turbidity,
            'temperature': temperature,
            'ec': ec,
            'do': do_level,
            'bod': bod,
            'cod': cod,
            'water_level': water_level,
            'humidity': humidity
        },
        'prediction_time': datetime.now().strftime('%Y-%m-%dT%H:%M:%S+05:30'),
        'disclaimer': 'Preliminary screening model trained on WHO/BIS drinking water guidelines; does not replace certified microbiological/chemical laboratory analysis.'
    })
