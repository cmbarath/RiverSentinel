"""
Flood Prediction Module for RiverSentinel
Uses ML model to predict flood risk based on real-time sensor data and IMD rainfall
"""

import os
import numpy as np
import pandas as pd
import joblib
from typing import Dict, List, Tuple

# Load ML model artifacts
MODEL_DIR = os.path.join(os.path.dirname(__file__), 'ml_models', 'flood')
model = None
scaler = None
features = None

def load_model():
    """Load the trained ML model, scaler, and feature list"""
    global model, scaler, features
    try:
        model = joblib.load(os.path.join(MODEL_DIR, 'model.pkl'))
        scaler = joblib.load(os.path.join(MODEL_DIR, 'scaler.pkl'))
        features = joblib.load(os.path.join(MODEL_DIR, 'features.pkl'))
        print(f"[INFO] Flood prediction model loaded successfully")
        print(f"[INFO] Model features: {features}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to load flood prediction model: {str(e)}")
        return False

# Load model on module import
load_model()

# Static basin characteristics for Uttara Vahini, Ganga (Varanasi)
BASIN_CHARACTERISTICS = {
    'basin_area_pct': 15.2,  # % of total Ganga basin
    'mean_elevation_m': 82.0,  # Varanasi elevation above sea level
    'mean_slope': 0.0012,  # Very gentle slope in this region
    'basin_relief_m': 120.0,  # Elevation difference in basin
    'flow_accumulation': 850000.0,  # Cumulative upstream drainage area (km²)
    'twi': 12.5,  # Topographic Wetness Index for Ganga floodplain
    'network_density': 0.42  # Drainage density km/km²
}

# Flood thresholds for Varanasi (meters)
WARNING_LEVEL = 71.26
DANGER_LEVEL = 73.23

def calculate_discharge(water_level: float) -> float:
    """
    Calculate river discharge from water level using Manning's equation approximation
    
    Args:
        water_level: Water level in meters
    
    Returns:
        Discharge in cumec (cubic meters per second)
    """
    # Empirical formula based on Ganga river characteristics
    # Q = k * h^2.5 where k is a constant for this river section
    discharge = (water_level ** 2.5) * 0.85
    return max(0, discharge)  # Ensure non-negative

def prepare_features(sensor_data: Dict, rainfall_data: Dict) -> pd.DataFrame:
    """
    Prepare features for ML model prediction
    
    Args:
        sensor_data: Dict with keys: temperature, humidity, water_level, turbidity, ph
        rainfall_data: Dict with key: rainfall_24h (mm)
    
    Returns:
        DataFrame with all required features in correct order
    """
    # Extract sensor values
    water_level = sensor_data.get('water_level', 68.5)
    temperature = sensor_data.get('temperature', 28.0)
    humidity = sensor_data.get('humidity', 65.0)
    
    # Extract rainfall from IMD
    rainfall_24h = rainfall_data.get('rainfall_24h', 0.0)
    
    # Calculate discharge
    discharge = calculate_discharge(water_level)
    
    # Prepare feature dictionary
    feature_dict = {
        'water_level_varanasi': water_level,
        'discharge_cumec': discharge,
        'rain_upstream_avg_mm': rainfall_24h,
        'temperature_c': temperature,
        'humidity_pct': humidity,
        **BASIN_CHARACTERISTICS  # Add all static basin characteristics
    }
    
    # Create DataFrame in the correct feature order
    input_df = pd.DataFrame([[feature_dict[col] for col in features]], columns=features)
    
    return input_df

def generate_explanation(feature_dict: Dict, probability: float) -> List[str]:
    """
    Generate human-readable explanation for the flood prediction
    
    Args:
        feature_dict: Dictionary of all features used in prediction
        probability: Predicted flood probability (0-1)
    
    Returns:
        List of explanation strings
    """
    reasons = []
    
    water_level = feature_dict['water_level_varanasi']
    rainfall = feature_dict['rain_upstream_avg_mm']
    discharge = feature_dict['discharge_cumec']
    humidity = feature_dict['humidity_pct']
    temperature = feature_dict['temperature_c']
    
    # Water level analysis
    if water_level >= DANGER_LEVEL:
        reasons.append(f"🔴 CRITICAL: Water level ({water_level:.2f}m) has reached danger level ({DANGER_LEVEL}m)")
    elif water_level >= WARNING_LEVEL:
        reasons.append(f"🟠 WARNING: Water level ({water_level:.2f}m) has crossed warning level ({WARNING_LEVEL}m)")
    elif water_level >= WARNING_LEVEL - 1.0:
        reasons.append(f"🟡 ALERT: Water level ({water_level:.2f}m) is approaching warning level ({WARNING_LEVEL}m)")
    else:
        distance = WARNING_LEVEL - water_level
        reasons.append(f"🟢 Water level ({water_level:.2f}m) is {distance:.2f}m below warning level")
    
    # Rainfall analysis
    if rainfall > 100:
        reasons.append(f"🌧️ Extremely heavy rainfall detected: {rainfall:.1f}mm in 24 hours")
    elif rainfall > 50:
        reasons.append(f"🌧️ Heavy rainfall upstream: {rainfall:.1f}mm in 24 hours")
    elif rainfall > 20:
        reasons.append(f"🌦️ Moderate rainfall: {rainfall:.1f}mm in 24 hours")
    elif rainfall > 0:
        reasons.append(f"🌦️ Light rainfall: {rainfall:.1f}mm in 24 hours")
    else:
        reasons.append(f"☀️ No significant rainfall in the past 24 hours")
    
    # Discharge analysis
    if discharge > 60000:
        reasons.append(f"💧 Very high river discharge: {discharge:.0f} cumec")
    elif discharge > 40000:
        reasons.append(f"💧 High river discharge: {discharge:.0f} cumec")
    elif discharge > 20000:
        reasons.append(f"💧 Moderate river discharge: {discharge:.0f} cumec")
    
    # Humidity analysis (monsoon indicator)
    if humidity > 85:
        reasons.append(f"💨 Very high humidity ({humidity:.0f}%) indicates active monsoon conditions")
    elif humidity > 75:
        reasons.append(f"💨 High humidity ({humidity:.0f}%) suggests monsoon activity")
    
    # Temperature context
    if temperature > 35:
        reasons.append(f"🌡️ High temperature ({temperature:.1f}°C) may increase evaporation")
    
    # Add overall assessment
    if probability >= 0.75:
        reasons.append("⚠️ IMMEDIATE ACTION REQUIRED: High flood risk detected")
    elif probability >= 0.40:
        reasons.append("⚠️ MONITOR CLOSELY: Moderate flood risk present")
    else:
        reasons.append("✅ Situation under control: Low flood risk")
    
    return reasons

def predict_flood(sensor_data: Dict, rainfall_data: Dict) -> Dict:
    """
    Predict flood risk using ML model
    
    Args:
        sensor_data: Real-time sensor data from Firebase
        rainfall_data: Rainfall data from IMD
    
    Returns:
        Dictionary with prediction results and explanation
    """
    if model is None or scaler is None or features is None:
        return {
            'error': 'ML model not loaded',
            'risk_level': 'UNKNOWN',
            'flood_probability': 0,
            'reasons': ['Model initialization failed']
        }
    
    try:
        # Prepare features
        input_df = prepare_features(sensor_data, rainfall_data)
        
        # Create feature dictionary for explanation
        feature_dict = {
            'water_level_varanasi': sensor_data.get('water_level', 68.5),
            'discharge_cumec': calculate_discharge(sensor_data.get('water_level', 68.5)),
            'rain_upstream_avg_mm': rainfall_data.get('rainfall_24h', 0.0),
            'temperature_c': sensor_data.get('temperature', 28.0),
            'humidity_pct': sensor_data.get('humidity', 65.0),
            **BASIN_CHARACTERISTICS
        }
        
        # Scale features
        input_scaled = scaler.transform(input_df)
        
        # Predict probability
        prob = model.predict_proba(input_scaled)[0][1]
        prob = float(np.clip(prob, 0.01, 0.99))  # Clip to reasonable range
        
        # Classify risk level
        if prob >= 0.75:
            risk_level = "HIGH"
            risk_color = "#ef4444"
        elif prob >= 0.40:
            risk_level = "MODERATE"
            risk_color = "#f59e0b"
        else:
            risk_level = "LOW"
            risk_color = "#10b981"
        
        # Generate explanation
        reasons = generate_explanation(feature_dict, prob)
        
        # Determine confidence based on data quality
        confidence = "HIGH"  # Since we're using real sensors now
        if sensor_data.get('water_level') is None:
            confidence = "MEDIUM"
        
        return {
            'risk_level': risk_level,
            'risk_color': risk_color,
            'flood_probability': round(prob * 100, 2),
            'confidence': confidence,
            'reasons': reasons,
            'sensor_data_used': {
                'water_level': feature_dict['water_level_varanasi'],
                'temperature': feature_dict['temperature_c'],
                'humidity': feature_dict['humidity_pct'],
                'discharge_estimated': round(feature_dict['discharge_cumec'], 0),
                'rainfall_24h': feature_dict['rain_upstream_avg_mm']
            },
            'thresholds': {
                'warning_level': WARNING_LEVEL,
                'danger_level': DANGER_LEVEL
            }
        }
    
    except Exception as e:
        print(f"[ERROR] Flood prediction failed: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'error': str(e),
            'risk_level': 'UNKNOWN',
            'flood_probability': 0,
            'reasons': [f'Prediction error: {str(e)}']
        }
