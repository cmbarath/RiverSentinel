"""
Predictions & ML Routes Blueprint
Handles Ridge/RF river stage forecasting, CPCB Class B water quality evaluation,
physical sensor anomaly detection, and Open-Meteo weather fetching.
All models are strictly governed with explicit provenance, research-only/experimental
safety boundaries, and emergency alert suppression.
"""

from flask import Blueprint, jsonify, request
import os
import sys
import time
import requests
import joblib
import numpy as np
from datetime import datetime
from services.supabase_service import get_latest_sensor_reading, supabase_insert

predictions_bp = Blueprint('predictions', __name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Import Phase 6 Deterministic CPCB Evaluator
try:
    from ml.water_quality.evaluator import evaluate_cpcb_class_b_record
    HAS_CPCB_EVALUATOR = True
except Exception as e:
    print(f"[WARNING] Could not import CPCB evaluator: {e}")
    HAS_CPCB_EVALUATOR = False

# ---------------------------------------------------------------------------
# ML Artifact Initialization (Legacy Models & Phase 6 Versioned Models)
# ---------------------------------------------------------------------------
# Legacy Retired Models (Preserved for forensic reproducibility only)
legacy_flood_model = None
legacy_flood_scaler = None
legacy_wq_model = None
legacy_wq_scaler = None

try:
    f_path = os.path.join(BASE_DIR, 'flood_model.pkl')
    fs_path = os.path.join(BASE_DIR, 'flood_scaler.pkl')
    if os.path.exists(f_path) and os.path.exists(fs_path):
        legacy_flood_model = joblib.load(f_path)
        legacy_flood_scaler = joblib.load(fs_path)
        print("[INFO] Legacy flood model loaded (retired baseline)")
except Exception as e:
    print(f"[WARNING] Legacy flood model load failed: {e}")

try:
    w_path = os.path.join(BASE_DIR, 'water_quality_model.pkl')
    ws_path = os.path.join(BASE_DIR, 'water_quality_scaler.pkl')
    if os.path.exists(w_path) and os.path.exists(ws_path):
        legacy_wq_model = joblib.load(w_path)
        legacy_wq_scaler = joblib.load(ws_path)
        print("[INFO] Legacy water quality model loaded (retired baseline)")
except Exception as e:
    print(f"[WARNING] Legacy water quality model load failed: {e}")

# Phase 6 Versioned Models
models_dir = os.path.join(BASE_DIR, 'ml', 'models')
flood_stage_model = None
flood_stage_scaler = None
wq_anomaly_detector = None
wq_anomaly_scaler = None

try:
    fstage_path = os.path.join(models_dir, 'flood_stage_forecaster_v1.pkl')
    fstage_sc_path = os.path.join(models_dir, 'flood_stage_scaler_v1.pkl')
    if os.path.exists(fstage_path) and os.path.exists(fstage_sc_path):
        flood_stage_model = joblib.load(fstage_path)
        flood_stage_scaler = joblib.load(fstage_sc_path)
        print("[INFO] Phase 6.1 flood stage forecaster v1 loaded (Ridge Regressor, research_only)")
except Exception as e:
    print(f"[WARNING] Phase 6 flood stage model load failed: {e}")

try:
    wq_anom_path = os.path.join(models_dir, 'water_quality_anomaly_detector_v1.pkl')
    wq_anom_sc_path = os.path.join(models_dir, 'water_quality_scaler_v1.pkl')
    if os.path.exists(wq_anom_path) and os.path.exists(wq_anom_sc_path):
        wq_anomaly_detector = joblib.load(wq_anom_path)
        wq_anomaly_scaler = joblib.load(wq_anom_sc_path)
        print("[INFO] Phase 6.1 water quality anomaly detector v1 loaded (experimental)")
except Exception as e:
    print(f"[WARNING] Phase 6 water quality anomaly detector load failed: {e}")


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
    """
    Execute flood risk evaluation and 1-day-ahead river stage forecasting.
    Governance: Classified as research_only with explicit semi-synthetic provenance.
    Strictly quarantined from triggering emergency SMS or public alarms.
    """
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

    # Check model availability
    if flood_stage_model is None and legacy_flood_model is None:
        return jsonify({
            'error': 'Flood prediction model not available',
            'status': 'model_unavailable',
            'prediction_status': 'model_unavailable'
        }), 503

    # 1. Execute 1-Day-Ahead Stage Forecast (Phase 6.1 Ridge Forecaster)
    forecasted_stage = None
    forecast_delta = None
    if flood_stage_model is not None and flood_stage_scaler is not None:
        try:
            day_of_year = datetime.now().timetuple().tm_yday
            season_sin = np.sin(2 * np.pi * day_of_year / 365.25)
            season_cos = np.cos(2 * np.pi * day_of_year / 365.25)

            # Features (17 features strictly at time t):
            # stage_t, stage_lag1, stage_lag2, delta1d, delta2d,
            # roll_mean_3d, roll_mean_7d, roll_max_7d,
            # rain_local, rain_local_3d, rain_up, rain_up_3d,
            # discharge, temp, humidity, season_sin, season_cos
            f_vec = np.array([[
                water_level, water_level, water_level,
                0.0, 0.0,
                water_level, water_level, water_level,
                rain_varanasi, rain_varanasi * 2,
                rain_upstream, rain_upstream * 2,
                discharge, temperature, humidity,
                season_sin, season_cos
            ]])
            scaled_f = flood_stage_scaler.transform(f_vec)
            forecasted_stage = float(flood_stage_model.predict(scaled_f)[0])
            forecast_delta = round(forecasted_stage - water_level, 2)
        except Exception as e:
            print(f"[WARNING] Stage forecast inference failed: {e}")

    # 2. Execute Legacy Probability Model (preserved for backward compatibility only)
    flood_prob = 0.05
    prediction_bin = 0
    if legacy_flood_model is not None and legacy_flood_scaler is not None:
        try:
            legacy_vec = np.array([[
                water_level, discharge, rain_varanasi, rain_upstream, temperature, humidity
            ]])
            scaled_leg = legacy_flood_scaler.transform(legacy_vec)
            prediction_bin = int(legacy_flood_model.predict(scaled_leg)[0])
            flood_prob = float(legacy_flood_model.predict_proba(scaled_leg)[0][1])
        except Exception:
            pass

    # 3. Official CWC Stage Benchmarking (Authoritative Ground Truth)
    # CWC Varanasi Stages (Malviya Bridge / Rajghat):
    # Warning Stage: 70.26 m | Danger Stage: 71.26 m | HFL: 73.90 m
    cwc_warning = 70.26
    cwc_danger = 71.26
    eval_stage = max(water_level, forecasted_stage or water_level)

    if eval_stage >= cwc_danger:
        risk_level = 'HIGH'
        cwc_status = 'DANGER'
        message = f"CRITICAL: River stage ({eval_stage:.2f} m) meets or exceeds CWC Danger Stage ({cwc_danger:.2f} m)."
    elif eval_stage >= cwc_warning:
        risk_level = 'HIGH'
        cwc_status = 'WARNING'
        message = f"WARNING: River stage ({eval_stage:.2f} m) meets or exceeds CWC Warning Stage ({cwc_warning:.2f} m)."
    elif eval_stage >= 68.0:
        risk_level = 'MODERATE'
        cwc_status = 'ELEVATED'
        message = f"Elevated river flow ({eval_stage:.2f} m). Below CWC Warning Stage ({cwc_warning:.2f} m)."
    else:
        risk_level = 'LOW'
        cwc_status = 'NORMAL'
        message = f"Normal river conditions ({eval_stage:.2f} m). Well within safe hydrological bounds."

    reasons = []
    if water_level >= cwc_warning:
        reasons.append(f"Current water level ({water_level:.2f} m) exceeds CWC Warning Stage (70.26 m)")
    elif water_level > 68.0:
        reasons.append(f"Water level elevated ({water_level:.2f} m MSL)")
    if forecasted_stage and forecasted_stage >= cwc_warning:
        reasons.append(f"1-day forecast ({forecasted_stage:.2f} m) approaches/exceeds Warning Stage")
    if rain_varanasi > 50:
        reasons.append(f"Heavy local rainfall ({rain_varanasi:.1f} mm)")
    if rain_upstream > 80:
        reasons.append(f"High upstream catchment rainfall ({rain_upstream:.1f} mm)")
    if discharge > 12000:
        reasons.append(f"High river discharge ({discharge:.0f} cumec)")
    if not reasons:
        reasons.append(f"All parameters normal (Current: {water_level:.2f} m MSL)")

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
        'prediction':        'FLOOD' if (prediction_bin == 1 or risk_level == 'HIGH') else 'NO_FLOOD',
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
        'model_version': 'flood_stage_forecaster_v1' if flood_stage_model else 'legacy_flood_classifier_v0',
        'prediction_status': 'research_only',
        'data_provenance': 'semi_synthetic_research_series',
        'is_official_cwc_gauge': False,
        'alert_eligible': False,
        'stage_forecast': {
            'forecast_horizon': '1_day_ahead',
            'current_water_level_m': round(water_level, 2),
            'forecasted_water_level_m': round(forecasted_stage, 2) if forecasted_stage else None,
            'forecast_delta_m': forecast_delta,
            'analytical_high_water_subset': bool(eval_stage >= 67.5),
            'analytical_subset_note': '67.5 m is an internal analytical subset boundary, NOT an official CWC statutory flood warning stage.',
            'cwc_gauge_reference': {
                'station': 'Varanasi (Rajghat / Malviya Bridge)',
                'warning_stage_m': cwc_warning,
                'danger_stage_m': cwc_danger,
                'highest_flood_level_m': 73.90,
                'cwc_stage_status': cwc_status
            }
        },
        'disclaimer': 'Statistical 1-day-ahead stage forecast from flood_stage_forecaster_v1 (research_only, semi-synthetic provenance). Statutory flood alerts derive exclusively from official CWC gauge levels (70.26 m Warning, 71.26 m Danger).'
    })


@predictions_bp.route('/api/water-quality/predict', methods=['GET', 'POST'])
def predict_water_quality():
    """
    Predict water quality screening, CPCB Class B compliance assessment,
    and physical sensor anomaly detection.
    Governance: Anomaly detector is experimental and cannot trigger public alerts.
    """
    reading = get_latest_sensor_reading()

    ph          = _validated_sensor(reading, 'ph', 7.5, 0, 14)
    turbidity   = _validated_sensor(reading, 'turbidity', 15.0, 0, 5000)
    temperature = _validated_sensor(reading, 'temperature', 26.0, -10, 60)
    ec          = _validated_sensor(reading, 'ec', 480.0, 0, 10000)
    do_level    = _validated_sensor(reading, 'do', 6.8, 0, 30)
    bod         = _validated_sensor(reading, 'bod', 2.8, 0, 500)
    cod         = _validated_sensor(reading, 'cod', 18.0, 0, 1000)
    total_coliform = reading.get('total_coliform') if reading else None
    water_level = _validated_sensor(reading, 'water_level', 67.5, 0, 100)
    humidity    = _validated_sensor(reading, 'humidity', 65.0, 0, 100)

    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        ph          = float(data.get('ph', ph))
        turbidity   = float(data.get('turbidity', turbidity))
        temperature = float(data.get('temperature', temperature))
        ec          = float(data.get('ec', ec))
        do_level    = float(data.get('do', do_level))
        if 'bod' in data:
            bod = float(data['bod'])
        if 'total_coliform' in data:
            total_coliform = float(data['total_coliform'])

    # 1. Deterministic CPCB Class B Assessment
    cpcb_eval = {}
    if HAS_CPCB_EVALUATOR:
        eval_record = {
            'ph': ph,
            'do_mg_l': do_level,
            'bod_mg_l': bod,
            'total_coliform_mpn_100ml': total_coliform,
            'turbidity_ntu': turbidity,
            'conductivity_us_cm': ec
        }
        cpcb_eval = evaluate_cpcb_class_b_record(eval_record)

    # 2. Physical Sensor Anomaly Detection (Phase 6.1 Experimental Model)
    anomaly_status = 'NORMAL'
    anomaly_score = None
    if wq_anomaly_detector is not None and wq_anomaly_scaler is not None:
        try:
            anom_vec = np.array([[ph, do_level, turbidity, ec]])
            scaled_anom = wq_anomaly_scaler.transform(anom_vec)
            pred = wq_anomaly_detector.predict(scaled_anom)[0]
            anomaly_status = 'PHYSICAL_ANOMALY' if pred == -1 else 'NORMAL'
            anomaly_score = float(wq_anomaly_detector.score_samples(scaled_anom)[0])
        except Exception as e:
            print(f"[WARNING] Anomaly detector failed: {e}")

    # 3. Calculate Operational Quality Score (0 to 100)
    score = 100.0
    reasons = []

    # pH Assessment
    if ph < 6.5 or ph > 8.5:
        score -= 25
        reasons.append(f"pH non-compliant with CPCB Class B ({ph:.2f})")
    else:
        reasons.append(f"pH optimal for outdoor bathing ({ph:.2f})")

    # Dissolved Oxygen Assessment
    if do_level < 5.0:
        score -= 30
        reasons.append(f"Dissolved oxygen below CPCB Class B standard ({do_level:.1f} mg/L < 5.0 mg/L)")
    elif do_level >= 6.5:
        reasons.append(f"Good dissolved oxygen ({do_level:.1f} mg/L)")
    else:
        reasons.append(f"Adequate dissolved oxygen ({do_level:.1f} mg/L)")

    # Turbidity Operational Screening (Non-statutory)
    if turbidity > 100:
        score -= 20
        reasons.append(f"High turbidity screening alert ({turbidity:.1f} NTU > 100 NTU)")
    elif turbidity > 50:
        score -= 10
        reasons.append(f"Elevated turbidity ({turbidity:.1f} NTU)")

    # Conductivity Screening
    if ec > 1500:
        score -= 15
        reasons.append(f"Elevated conductivity ({ec:.0f} uS/cm)")

    # BOD Assessment (if available)
    if bod is not None:
        if bod > 3.0:
            score -= 20
            reasons.append(f"BOD exceeds CPCB Class B limit ({bod:.1f} mg/L > 3.0 mg/L)")
        else:
            reasons.append(f"BOD compliant with Class B ({bod:.1f} mg/L)")

    # Anomaly indicator
    if anomaly_status == 'PHYSICAL_ANOMALY':
        score -= 10
        reasons.append("Physical-chemical parameters deviate from historical Ganga baseline")

    score = max(0.0, min(100.0, score))
    quality_level = 'GOOD' if score >= 70 else 'MODERATE' if score >= 40 else 'POOR'

    # Raw river water is never potable without conventional municipal treatment!
    is_potable = False

    recommendations = []
    if quality_level == 'POOR':
        recommendations.extend(['Avoid direct immersion or bathing', 'Boil and thoroughly treat all water', 'Report potential pollution source'])
    elif quality_level == 'MODERATE':
        recommendations.extend(['Safe for outdoor bathing if BOD/Coliform pass', 'Do not consume directly without treatment', 'Monitor turbidity'])
    else:
        recommendations.extend(['Water quality compliant for designated outdoor bathing', 'Conventional water treatment required before drinking', 'Continue routine monitoring'])

    return jsonify({
        'potable': is_potable,
        'quality_score': score,
        'quality_level': quality_level,
        'message': 'Surface water meets physical screening criteria for outdoor bathing. Raw river water requires conventional treatment before drinking.' if score >= 70 else 'Surface water shows parameter elevation or contamination. Treatment and caution advised.',
        'reasons': reasons,
        'recommendations': recommendations,
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
        'model_version': 'water_quality_evaluator_v1',
        'prediction_status': 'rule_based_reference_screening',
        'cpcb_class_b_assessment': cpcb_eval,
        'physical_screening': {
            'anomaly_status': anomaly_status,
            'anomaly_score': anomaly_score,
            'screening_status': 'experimental_screening_only',
            'alert_eligible': False,
            'screening_note': 'Experimental physical anomaly score. Never represents a confirmed pollution event or biological contamination.',
            'turbidity_status': 'NORMAL' if turbidity <= 100 else 'ELEVATED_INVESTIGATION',
            'conductivity_status': 'NORMAL' if ec <= 1500 else 'HIGH_CONDUCTIVITY'
        },
        'disclaimer': 'Evaluated against official CPCB Designated Best Use Class B outdoor bathing criteria. Raw river surface water is never potable for direct drinking without certified conventional water treatment.'
    })
