import base64
import io
import os
import time
import json
import requests
import random
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, db
import openai
from groq import Groq
import numpy as np
import pandas as pd
import joblib
import csv
from datetime import datetime

load_dotenv()

# --- INITIALIZATIONS ---
if not firebase_admin._apps:
    # Try to load Firebase credentials from service account key
    try:
        if os.path.exists('serviceAccountKey.json'):
            cred = credentials.Certificate('serviceAccountKey.json')
            firebase_admin.initialize_app(cred, {
                'databaseURL': os.getenv('FIREBASE_DATABASE_URL')
            })
            print("[INFO] OK: Firebase initialized successfully with service account")
        else:
            # Fallback: Initialize without credentials (limited functionality)
            print("[WARNING] serviceAccountKey.json not found")
            print("[INFO] Initializing Firebase with limited functionality...")
            firebase_admin.initialize_app(options={
                'databaseURL': os.getenv('FIREBASE_DATABASE_URL')
            })
            print("[INFO] Warning: Firebase initialized in fallback mode")
            print("[INFO] Download serviceAccountKey.json from Firebase Console for full functionality")
    except Exception as e:
        print(f"[ERROR] Firebase initialization failed: {str(e)}")
        print("[INFO] To fix:")
        print("[INFO]   1. Go to https://console.firebase.google.com/")
        print("[INFO]   2. Select project 'riversentinel-ae0b0'")
        print("[INFO]   3. Settings -> Service Accounts -> Generate New Private Key")
        print("[INFO]   4. Save as backend/serviceAccountKey.json")

openai_key = os.getenv('OPENAI_API_KEY')
if openai_key:
    openai.api_key = openai_key
    print("OK: OpenAI initialized")
else:
    print("Warning: OPENAI_API_KEY not found in .env")

# Initialize Groq Client
groq_key = os.getenv("GROQ_API_KEY")
if groq_key:
    try:
        groq_client = Groq(api_key=groq_key)
        print("OK: Groq client initialized")
    except Exception as e:
        print(f"Warning: Groq initialization failed: {e}")
        groq_client = None
else:
    print("Warning: GROQ_API_KEY not found in .env")
    groq_client = None

# Load flood prediction model
try:
    flood_model = joblib.load(os.path.join(os.path.dirname(__file__), 'flood_model', 'model.pkl'))
    flood_scaler = joblib.load(os.path.join(os.path.dirname(__file__), 'flood_model', 'scaler.pkl'))
    flood_features = joblib.load(os.path.join(os.path.dirname(__file__), 'flood_model', 'features.pkl'))
    print("OK: Flood prediction model loaded successfully")
except Exception as e:
    print(f"Warning: Could not load flood prediction model: {e}")
    flood_model = None
    flood_scaler = None
    flood_features = None

# --- FIREBASE HELPERS ---
def get_firebase_rest_url(path):
    base_url = os.getenv('FIREBASE_DATABASE_URL', '').rstrip('/')
    secret = os.getenv('FIREBASE_SECRET', '')
    url = f"{base_url}/{path}.json"
    if secret:
        url += f"?auth={secret}"
    return url

def safe_db_push(node_path, data):
    """Push data to a Firebase node with fallback to REST API"""
    try:
        # Try Admin SDK first
        return db.reference(node_path).push(data)
    except Exception as e:
        print(f"[FALLBACK] push failed for {node_path}: {e}")
        # REST API fallback
        url = get_firebase_rest_url(node_path)
        try:
            response = requests.post(url, json=data, timeout=10)
            if response.status_code == 200:
                print(f"[SUCCESS] REST push successful for {node_path}")
                return response.json()
            else:
                print(f"[ERROR] REST fallback failed for {node_path}: {response.status_code} {response.text}")
        except Exception as re:
            print(f"[ERROR] REST exception for {node_path}: {re}")
    return None

def safe_db_get(node_path):
    """Get data from a Firebase node with fallback to REST API"""
    try:
        # Try Admin SDK first
        return db.reference(node_path).get()
    except Exception as e:
        print(f"[FALLBACK] get failed for {node_path}: {e}")
        # REST API fallback
        url = get_firebase_rest_url(node_path)
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                print(f"[SUCCESS] REST get successful for {node_path}")
                return response.json()
            else:
                 print(f"[ERROR] REST fallback failed for {node_path}: {response.status_code}")
        except Exception as re:
            print(f"[ERROR] REST exception for {node_path}: {re}")
    return None

def safe_db_update(node_path, data):
    """Update data in a Firebase node with fallback to REST API"""
    try:
        # Try Admin SDK first
        return db.reference(node_path).update(data)
    except Exception as e:
        print(f"[FALLBACK] update failed for {node_path}: {e}")
        # REST API fallback (PATCH for partial update)
        url = get_firebase_rest_url(node_path)
        try:
            response = requests.patch(url, json=data, timeout=10)
            if response.status_code == 200:
                print(f"[SUCCESS] REST update successful for {node_path}")
                return response.json()
            else:
                 print(f"[ERROR] REST fallback failed for {node_path}: {response.status_code}")
        except Exception as re:
            print(f"[ERROR] REST exception for {node_path}: {re}")
    return None

app = Flask(__name__)
CORS(app, resources={r'/api/*': {'origins': '*'}})

@app.route('/')
def index():
    return jsonify({
        "message": "RiverSentinel Backend API is running",
        "endpoints": ["/api/health", "/api/ai/chat", "/api/ai/analyze-image", "/api/flood/predict"]
    })

@app.route('/api/health')
def health(): return jsonify({'status': 'healthy'})

@app.route('/api/ai/chat', methods=['POST'])
def chat():
    data = request.json
    query = data.get('query', '')
    language = data.get('language', 'English')
    
    # Debug logging
    print(f"[DEBUG] Received chat request - Language: {language}, Query: {query[:50]}...")
    
    # Language-specific system prompts with stronger instructions
    system_prompts = {
        'English': 'You are RiverSentinel AI assistant, an expert on river water quality, pollution monitoring, and flood prediction. Provide helpful, accurate information about environmental monitoring and river safety. You MUST respond ONLY in English.',
        'हिन्दी': 'आप RiverSentinel AI सहायक हैं, जो नदी जल गुणवत्ता, प्रदूषण निगरानी और बाढ़ पूर्वानुमान के विशेषज्ञ हैं। पर्यावरण निगरानी और नदी सुरक्षा के बारे में सहायक, सटीक जानकारी प्रदान करें। आपको केवल हिन्दी में ही जवाब देना है। अंग्रेजी में बिल्कुल नहीं।',
        'भोजपुरी': 'रउआ RiverSentinel AI सहायक बानी। रउआ नदी के पानी के गुणवत्ता, प्रदूषण निगरानी आ बाढ़ के भविष्यवाणी के विशेषज्ञ बानी। पर्यावरण निगरानी आ नदी सुरक्षा के बारे में मददगार, सही जानकारी देईं। रउआ के केवल भोजपुरी में ही जवाब देवे के बा। अंग्रेजी भा हिन्दी में बिल्कुल ना। सिर्फ भोजपुरी भाषा में जवाब दीहीं।',
        'বাংলা': 'আপনি RiverSentinel AI সহায়ক, নদীর জলের গুণমান, দূষণ পর্যবেক্ষণ এবং বন্যা পূর্বাভাসের বিশেষজ্ঞ। পরিবেশ পর্যবেক্ষণ এবং নদী সুরক্ষা সম্পর্কে সহায়ক, নির্ভুল তথ্য প্রদান করুন। আপনাকে শুধুমাত্র বাংলায় উত্তর দিতে হবে। ইংরেজিতে নয়।'
    }
    
    # Get the appropriate system prompt, default to English
    system_prompt = system_prompts.get(language, system_prompts['English'])
    
    print(f"[DEBUG] Using system prompt for language: {language}")
    
    try:
        if not groq_client:
            return jsonify({'response': 'Error: Groq API key is missing. Please add GROQ_API_KEY to your .env file to use the chatbot for free.'})

        response = groq_client.chat.completions.create(
            model='llama-4-scout-17b-16e-instruct',
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': query}
            ],
            temperature=0.7,
            max_tokens=1024
        )
        response_text = response.choices[0].message.content
        print(f"[DEBUG] Response generated in {language} via Groq: {response_text[:100]}...")
        return jsonify({'response': response_text})
    except Exception as e:
        print(f"[ERROR] Chat API error: {str(e)}")
        return jsonify({'response': f'Error using Groq: {str(e)}'})

@app.route('/api/weather', methods=['GET'])
def get_weather():
    """Fetch real-time weather data for Uttara Vahini area (Ganga, Varanasi)"""
    try:
        # OpenWeatherMap API - Using user's API key
        api_key = os.getenv('OPENWEATHER_API_KEY')
        
        # Uttara Vahini area coordinates (Ganga river, Varanasi)
        # This is the northern stretch of Ganga in Varanasi
        lat = 25.3176  # Varanasi - Uttara Vahini area
        lon = 83.0099  # Ganga river coordinates
        
        # Fetch current weather
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
        print(f"[DEBUG] Fetching weather for Uttara Vahini, Ganga (Varanasi)")
        response = requests.get(url, timeout=10)
        
        print(f"[DEBUG] Weather API status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"[DEBUG] Weather data received: {data.get('main', {})}")
            
            # Get rainfall data
            rain_1h = data.get('rain', {}).get('1h', 0)  # mm in last hour
            rain_3h = data.get('rain', {}).get('3h', 0)  # mm in last 3 hours
            
            # Calculate rainfall rate (mm/h) and estimate 24h
            rainfall_rate = rain_1h if rain_1h > 0 else (rain_3h / 3 if rain_3h > 0 else 0)
            rainfall_24h = rainfall_rate * 24  # Rough estimate for 24-hour rainfall
            
            weather_data = {
                'temperature': round(data['main']['temp'], 1),
                'feels_like': round(data['main']['feels_like'], 1),
                'humidity': data['main']['humidity'],
                'pressure': data['main']['pressure'],
                'description': data['weather'][0]['description'],
                'icon': data['weather'][0]['icon'],
                'wind_speed': round(data['wind']['speed'] * 3.6, 1),  # Convert m/s to km/h
                'clouds': data['clouds']['all'],
                'visibility': data.get('visibility', 10000) / 1000,  # Convert to km
                'rain': rainfall_rate,  # Current rainfall rate in mm/h
                'rainfall_24h': rainfall_24h,  # Estimated 24-hour rainfall
                'city': 'Uttara Vahini, Ganga (Varanasi)',
                'timestamp': data['dt']
            }
            print(f"[DEBUG] Returning weather: {weather_data['temperature']}°C, Rainfall: {rainfall_rate}mm/h")
            return jsonify(weather_data)
        else:
            print(f"[ERROR] Weather API error: {response.status_code} - {response.text}")
            # Fallback to realistic default values
            return jsonify({
                'temperature': 28.5,
                'feels_like': 30.2,
                'humidity': 65,
                'pressure': 1012,
                'description': 'partly cloudy',
                'icon': '02d',
                'wind_speed': 12.5,
                'clouds': 40,
                'visibility': 10,
                'rain': 0,
                'city': 'Varanasi',
                'timestamp': int(time.time()),
                'fallback': True
            })
    except Exception as e:
        print(f"[ERROR] Weather API exception: {str(e)}")
        # Return realistic fallback data
        return jsonify({
            'temperature': 28.5,
            'feels_like': 30.2,
            'humidity': 65,
            'pressure': 1012,
            'description': 'partly cloudy',
            'icon': '02d',
            'wind_speed': 12.5,
            'clouds': 40,
            'visibility': 10,
            'rain': 0,
            'city': 'Varanasi',
            'timestamp': int(time.time()),
            'fallback': True
        })

@app.route('/api/sensors/latest', methods=['GET'])
def get_latest_sensors():
    """Get latest sensor readings from Firebase - all 9 Arduino sensors"""
    # Default sensor values (always valid response)
    sensor_data = {
        'ph': 7.5,
        'turbidity': 100.0,
        'temperature': 28.0,
        'humidity': 65.0,
        'ec': 500.0,
        'water_level': 68.5,
        'bod': 30.0,
        'cod': 150.0,
        'do': 7.0,
        'timestamp': int(time.time()),
        'status': 'default',
        'temperature_error': False,
        'water_level_error': False
    }
    
    try:
        sensor_snapshot = safe_db_get('sensor_data')
        
        if sensor_snapshot and isinstance(sensor_snapshot, dict):
            # Get the latest reading
            latest_key = max(sensor_snapshot.keys())
            latest_reading = sensor_snapshot[latest_key]
            
            # Fetch all parameters with validation
            raw_temp = latest_reading.get('temperature', 28.0)
            raw_water_level = latest_reading.get('water_level', 68.5)
            
            # Handle sensor errors
            if raw_temp < -100 or raw_temp > 60:
                sensor_data['temperature'] = 28.0
                sensor_data['temperature_error'] = True
            else:
                sensor_data['temperature'] = raw_temp
                sensor_data['temperature_error'] = False
            
            if raw_water_level <= 0:
                sensor_data['water_level'] = 68.5
                sensor_data['water_level_error'] = True
            else:
                sensor_data['water_level'] = raw_water_level
                sensor_data['water_level_error'] = False
            
            # Fetch other parameters
            sensor_data['ph'] = max(0, min(14, latest_reading.get('ph', 7.5)))
            sensor_data['turbidity'] = max(0, latest_reading.get('turbidity', 100.0))
            sensor_data['humidity'] = max(0, min(100, latest_reading.get('humidity', 65.0)))
            sensor_data['ec'] = max(0, latest_reading.get('ec', 500.0))
            sensor_data['bod'] = max(0, latest_reading.get('bod', 30.0))
            sensor_data['cod'] = max(0, latest_reading.get('cod', 150.0))
            sensor_data['do'] = max(0, latest_reading.get('do', 7.0))
            sensor_data['timestamp'] = latest_reading.get('timestamp', int(time.time()))
            sensor_data['status'] = 'live'
            
            print(f"[DEBUG] Latest sensor data: pH={sensor_data['ph']}, Temp={sensor_data['temperature']}°C, Water={sensor_data['water_level']}m")
        else:
            print("[WARNING] No sensor data found in Firebase, using defaults")
            
    except Exception as e:
        print(f"[ERROR] Failed to fetch sensor data from Firebase: {str(e)}")
        print("[INFO] Returning default sensor values")
    
    # Always return valid JSON, never error
    return jsonify(sensor_data)

@app.route('/api/flood/predict', methods=['GET'])
def predict_flood_risk():
    """Predict flood risk using trained Random Forest model with real-time sensor data"""
    try:
        # Load the trained model and scaler
        model_path = os.path.join(os.path.dirname(__file__), 'flood_model.pkl')
        scaler_path = os.path.join(os.path.dirname(__file__), 'flood_scaler.pkl')
        
        if not os.path.exists(model_path) or not os.path.exists(scaler_path):
            return jsonify({
                'error': 'Model not found. Please run train_flood_model.py first',
                'risk_level': 'UNKNOWN',
                'flood_probability': 0,
                'reasons': ['Flood prediction model not trained yet']
            }), 500
        
        model = joblib.load(model_path)
        scaler = joblib.load(scaler_path)
        
        # Default sensor values (used if Firebase fails or no data available)
        water_level = 68.5
        temperature = 28.0
        humidity = 65.0
        
        # Try to fetch real-time sensor data from Firebase
        try:
            sensor_snapshot = safe_db_get('sensor_data')
            
            if sensor_snapshot and isinstance(sensor_snapshot, dict):
                latest_key = max(sensor_snapshot.keys())
                latest_reading = sensor_snapshot[latest_key]
                
                raw_temp = latest_reading.get('temperature', 28.0)
                raw_water_level = latest_reading.get('water_level', 68.5)
                
                # Handle sensor errors
                if raw_temp < -100 or raw_temp > 60:
                    print(f"[WARNING] Invalid temperature: {raw_temp}°C, using default")
                    temperature = 28.0
                else:
                    temperature = raw_temp
                    
                if raw_water_level <= 0:
                    print(f"[WARNING] Invalid water level: {raw_water_level}m, using default")
                    water_level = 68.5
                else:
                    water_level = raw_water_level
                
                humidity = max(0, min(100, latest_reading.get('humidity', 65.0)))
                print(f"[INFO] Using live sensor data from Firebase")
        except Exception as e:
            print(f"[WARNING] Could not fetch sensor data from Firebase: {str(e)}")
            print(f"[INFO] Using default sensor values for prediction")
        
        # Fetch weather data for rainfall
        api_key = os.getenv('OPENWEATHER_API_KEY')
        lat, lon = 25.3176, 82.9739  # Varanasi coordinates
        
        rain_varanasi = 0
        rain_upstream = 0
        
        if api_key:
            try:
                weather_url = f'https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric'
                weather_response = requests.get(weather_url, timeout=5)
                
                if weather_response.status_code == 200:
                    weather_data = weather_response.json()
                    rain_1h = weather_data.get('rain', {}).get('1h', 0)
                    rain_3h = weather_data.get('rain', {}).get('3h', 0)
                    
                    # Calculate rainfall rate
                    rain_varanasi = rain_1h if rain_1h > 0 else (rain_3h / 3 if rain_3h > 0 else 0)
                    rain_upstream = rain_varanasi * 1.2  # Estimate upstream as 20% higher
                    
                    print(f"[DEBUG] Rainfall: {rain_varanasi}mm/h, Upstream: {rain_upstream}mm/h")
            except Exception as e:
                print(f"[WARNING] Weather API failed: {str(e)}")
        
        # Calculate discharge (simplified formula based on water level)
        discharge = 8000 + (water_level - 65) * 2000  # Approximate discharge in cumec
        
        # Prepare features for model (must match training order)
        features = np.array([[
            water_level,        # water_level_varanasi
            discharge,          # discharge_cumec
            rain_varanasi,      # rain_varanasi_mm
            rain_upstream,      # rain_upstream_avg_mm
            temperature,        # temperature_c
            humidity            # humidity_pct
        ]])
        
        # Scale features
        features_scaled = scaler.transform(features)
        
        # Predict
        flood_prediction = model.predict(features_scaled)[0]
        flood_probability = model.predict_proba(features_scaled)[0][1]  # Probability of flood
        
        # Determine risk level
        if flood_probability >= 0.7:
            risk_level = 'HIGH'
            risk_message = 'High flood risk detected. Immediate action recommended.'
        elif flood_probability >= 0.4:
            risk_level = 'MODERATE'
            risk_message = 'Moderate flood risk. Monitor conditions closely.'
        else:
            risk_level = 'LOW'
            risk_message = 'Low flood risk. Conditions are normal.'
        
        # Key factors contributing to prediction
        reasons = []
        if water_level > 68:
            reasons.append(f'Water level elevated ({water_level:.2f}m)')
        if rain_varanasi > 50:
            reasons.append(f'Heavy rainfall ({rain_varanasi:.1f}mm/hr)')
        if rain_upstream > 80:
            reasons.append(f'Upstream rainfall high ({rain_upstream:.1f}mm/hr)')
        if discharge > 12000:
            reasons.append(f'High discharge ({discharge:.0f} cumec)')
        
        if not reasons:
            reasons.append('All parameters within normal range')
        
        response = {
            'prediction': 'FLOOD' if flood_prediction == 1 else 'NO_FLOOD',
            'flood_probability': round(flood_probability * 100, 2),
            'risk_level': risk_level,
            'message': risk_message,
            'reasons': reasons,
            'sensor_data': {
                'water_level': round(water_level, 2),
                'discharge': round(discharge, 2),
                'rain_varanasi': round(rain_varanasi, 2),
                'rain_upstream': round(rain_upstream, 2),
                'temperature': round(temperature, 2),
                'humidity': round(humidity, 2),
                'bod': round(latest_reading.get('bod', 30.0), 1) if 'latest_reading' in locals() else 30.0,
                'cod': round(latest_reading.get('cod', 150.0), 1) if 'latest_reading' in locals() else 150.0,
                'do': round(latest_reading.get('do', 7.0), 1) if 'latest_reading' in locals() else 7.0
            },
            'prediction_time': time.strftime('%Y-%m-%dT%H:%M:%S+05:30')
        }
        
        print(f"[DEBUG] Flood prediction: {response['prediction']} ({response['flood_probability']}%)")
        return jsonify(response)
        
    except Exception as e:
        print(f"[ERROR] Flood prediction failed: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'error': str(e),
            'risk_level': 'UNKNOWN',
            'flood_probability': 0,
            'reasons': [f'Server error: {str(e)}']
        }), 500

@app.route('/api/water-quality/predict', methods=['GET'])
def predict_water_quality():
    """Predict water quality and potability using trained ML model"""
    try:
        # Load the trained water quality model and scaler
        model_path = os.path.join(os.path.dirname(__file__), 'water_quality_model.pkl')
        scaler_path = os.path.join(os.path.dirname(__file__), 'water_quality_scaler.pkl')
        
        if not os.path.exists(model_path) or not os.path.exists(scaler_path):
            return jsonify({
                'error': 'Water quality model not found',
                'potable': None,
                'quality_level': 'UNKNOWN',
                'quality_score': 0,
                'reasons': ['Water quality prediction model not available. Please copy model files to backend directory.']
            }), 500
        
        model = joblib.load(model_path)
        scaler = joblib.load(scaler_path)
        
        # Default sensor values (used if Firebase fails or no data available)
        ph = 7.0
        turbidity = 100.0
        temperature = 28.0
        humidity = 65.0
        ec = 500.0
        water_level = 68.5
        bod = 30.0
        cod = 150.0
        do_level = 7.0
        
        # Try to fetch real-time sensor data from Firebase
        try:
            sensor_snapshot = safe_db_get('sensor_data')
            
            if sensor_snapshot and isinstance(sensor_snapshot, dict):
                latest_key = max(sensor_snapshot.keys())
                latest_reading = sensor_snapshot[latest_key]
                
                # Get sensor values with validation
                ph = max(0, min(14, latest_reading.get('ph', 7.0)))
                turbidity = max(0, latest_reading.get('turbidity', 100.0))
                temperature = latest_reading.get('temperature', 28.0)
                humidity = max(0, min(100, latest_reading.get('humidity', 65.0)))
                ec = max(0, latest_reading.get('ec', 500.0))
                water_level = max(0, latest_reading.get('water_level', 68.5))
                bod = max(0, latest_reading.get('bod', 30.0))
                cod = max(0, latest_reading.get('cod', 150.0))
                do_level = max(0, latest_reading.get('do', 7.0))
                
                print(f"[INFO] Using live sensor data for water quality prediction")
        except Exception as e:
            print(f"[WARNING] Could not fetch sensor data from Firebase: {str(e)}")
            print(f"[INFO] Using default sensor values for water quality prediction")
        
        # Prepare features for prediction - Model expects 5 features
        # Based on scaler.n_features_in_ = 5
        features = np.array([[
            ph,
            turbidity,
            temperature,
            ec,
            do_level
        ]])
        
        # Scale features
        features_scaled = scaler.transform(features)
        
        # Make prediction
        prediction = model.predict(features_scaled)[0]
        probability = model.predict_proba(features_scaled)[0]
        
        # Determine potability (1 = potable, 0 = not potable)
        is_potable = bool(prediction == 1)
        potability_score = round(probability[1] * 100, 2) if len(probability) > 1 else round(probability[0] * 100, 2)
        
        # Determine quality level based on score
        if potability_score >= 80:
            quality_level = "EXCELLENT"
        elif potability_score >= 60:
            quality_level = "GOOD"
        elif potability_score >= 40:
            quality_level = "MODERATE"
        else:
            quality_level = "POOR"
        
        # Generate reasons based on sensor values
        reasons = []
        recommendations = []
        
        if ph < 6.5 or ph > 8.5:
            reasons.append(f"pH level {'too low' if ph < 6.5 else 'too high'} ({round(ph, 2)})")
            recommendations.append("pH adjustment required for safe consumption")
        else:
            reasons.append(f"pH level optimal ({round(ph, 2)})")
        
        if turbidity > 200:
            reasons.append(f"High turbidity ({round(turbidity, 1)} NTU)")
            recommendations.append("Filtration recommended to reduce turbidity")
        elif turbidity > 100:
            reasons.append(f"Moderate turbidity ({round(turbidity, 1)} NTU)")
        
        if bod > 50:
            reasons.append(f"High BOD level ({round(bod, 1)} mg/L)")
            recommendations.append("Water treatment needed to reduce organic matter")
        elif bod > 30:
            reasons.append(f"Elevated BOD ({round(bod, 1)} mg/L)")
        
        if cod > 200:
            reasons.append(f"High COD level ({round(cod, 1)} mg/L)")
            recommendations.append("Advanced treatment required")
        elif cod > 150:
            reasons.append(f"Moderate COD ({round(cod, 1)} mg/L)")
        
        if do_level < 5:
            reasons.append(f"Low dissolved oxygen ({round(do_level, 1)} mg/L)")
            recommendations.append("Aeration recommended")
        elif do_level >= 7:
            reasons.append(f"Good dissolved oxygen ({round(do_level, 1)} mg/L)")
        
        if ec > 1000:
            reasons.append(f"High conductivity ({round(ec, 0)} µS/cm)")
            recommendations.append("Desalination may be required")
        
        # Generate message
        if is_potable:
            if quality_level == "EXCELLENT":
                message = "Water quality is excellent. Safe for consumption."
            else:
                message = "Water is potable but may benefit from treatment."
        else:
            message = "Water is not safe for direct consumption. Treatment required."
        
        if not recommendations:
            recommendations.append("Continue regular monitoring")
        
        # Prepare response
        response = {
            'potable': is_potable,
            'quality_score': potability_score,
            'quality_level': quality_level,
            'message': message,
            'reasons': reasons[:5],  # Limit to top 5 reasons
            'recommendations': recommendations[:3],  # Limit to top 3 recommendations
            'sensor_data': {
                'ph': round(ph, 2),
                'turbidity': round(turbidity, 1),
                'temperature': round(temperature, 1),
                'humidity': round(humidity, 1),
                'ec': round(ec, 0),
                'water_level': round(water_level, 2),
                'bod': round(bod, 1),
                'cod': round(cod, 1),
                'do': round(do_level, 1)
            },
            'prediction_time': time.strftime('%Y-%m-%dT%H:%M:%S%z')
        }
        
        print(f"[DEBUG] Water quality prediction: {'POTABLE' if is_potable else 'NOT POTABLE'} ({potability_score}%)")
        return jsonify(response)
        
    except Exception as e:
        print(f"[ERROR] Water quality prediction failed: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'error': str(e),
            'potable': None,
            'quality_level': 'UNKNOWN',
            'quality_score': 0,
            'reasons': [f'Server error: {str(e)}']
        }), 500

@app.route('/api/ai/analyze-image', methods=['POST'])
def analyze_image():
    if not groq_client:
        return jsonify({'error': 'AI vision module (Groq) is not initialized. Check your GROQ_API_KEY in .env'}), 503
        
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400

    image_file = request.files['image']
    if image_file.filename == '':
        return jsonify({'error': 'No image selected'}), 400

    try:
        # Read and encode image to base64
        image_bytes = image_file.read()
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        # Determine mime type
        mime_type = image_file.mimetype or "image/jpeg"

        prompt = """
        Analyze this river image for pollution.
        Return ONLY a raw JSON strictly following this format (no markdown, no backticks):
        {
            "pollution_level": "Low" | "Moderate" | "High" | "Critical",
            "confidence": <number 0-100>,
            "pollutants": ["list", "of", "visible", "pollutants"],
            "assessment": "Brief assessment of the water quality and visual evidence."
        }
        """

        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}",
                            },
                        },
                    ],
                }
            ],
            model="llama-4-scout-17b-16e-instruct",
            temperature=0.1,
            max_tokens=1024,
            top_p=1,
            stream=False,
            stop=None,
        )

        response_text = chat_completion.choices[0].message.content.strip()
        
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        analysis_result = json.loads(response_text)
        
        try:
            timestamp = int(time.time() * 1000)
            data_to_save = {
                "pollution_level": analysis_result.get("pollution_level"),
                "confidence": analysis_result.get("confidence"),
                "pollutants": analysis_result.get("pollutants"),
                "assessment": analysis_result.get("assessment"),
                "timestamp": timestamp,
                "imageUrl": f"data:{mime_type};base64,{base64_image}",
                "status": "PENDING",
                "location": "Ganga River",
                "reporter": "Citizen AI"
            }
            safe_db_push('analysis_history', data_to_save)
        except Exception as e:
            print(f"Firebase Save Error: {e}")

        return jsonify(analysis_result)

    except Exception as e:
        print(f"Error analyzing image: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/flood/predict', methods=['POST'])
def predict_flood():
    """Predict flood risk based on sensor data and environmental factors"""
    if flood_model is None:
        return jsonify({'error': 'Flood prediction model not loaded'}), 503
    
    try:
        data = request.get_json(silent=True) or {}
        
        # Validate required fields
        required_fields = [
            'water_level_varanasi', 'discharge_cumec', 'rain_upstream_avg_mm',
            'temperature_c', 'humidity_pct', 'basin_area_pct', 'mean_elevation_m',
            'mean_slope', 'basin_relief_m', 'flow_accumulation', 'twi', 'network_density'
        ]
        
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({
                'error': 'Missing required fields',
                'missing_fields': missing_fields,
                'required_fields': required_fields
            }), 400
        
        # Arrange input in training feature order
        input_df = pd.DataFrame([[data[col] for col in flood_features]], columns=flood_features)
        
        # Scale features
        input_scaled = flood_scaler.transform(input_df)
        
        # Predict flood probability
        prob = flood_model.predict_proba(input_scaled)[0][1]
        prob = float(np.clip(prob, 0.01, 0.99))
        
        # Classify risk level
        if prob >= 0.75:
            risk_level = "HIGH FLOOD RISK"
        elif prob >= 0.40:
            risk_level = "MODERATE FLOOD RISK"
        else:
            risk_level = "LOW FLOOD RISK"
        
        # Save to Firebase (optional)
        try:
            timestamp = int(time.time() * 1000)
            prediction_data = {
                "risk_level": risk_level,
                "flood_probability": round(prob * 100, 2),
                "timestamp": timestamp,
                "input_data": data
            }
            safe_db_push('flood_predictions', prediction_data)
        except Exception as e:
            print(f"Firebase Save Error: {e}")
        
        return jsonify({
            'risk_level': risk_level,
            'flood_probability': round(prob * 100, 2)
        })
    
    except Exception as e:
        print(f"Error predicting flood: {e}")
        return jsonify({'error': str(e)}), 500

# --- AUTHORITY ACTIONS ---

@app.route('/api/authority/send-sms', methods=['POST'])
def send_emergency_sms():
    """Simulate sending emergency SMS to residents"""
    try:
        data = request.get_json(silent=True) or {}
        message = data.get('message', "EMERGENCY: River water levels rising. Please stay away from ghatt areas. - RiverSentinel")
        
        # Simulated target numbers
        mock_targets = ["+91 987XXXXX21", "+91 882XXXXX45", "+91 701XXXXX89"]
        
        print(f"[AUTHORITY] Sending SMS: {message}")
        print(f"[AUTHORITY] Targeted devices: {len(mock_targets)}")
        
        # Simulate delay
        time.sleep(1)
        
        return jsonify({
            "status": "success",
            "message": "Emergency SMS broadcast initiated successfully",
            "recipients": len(mock_targets),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/authority/trigger-alert', methods=['POST'])
def trigger_alert():
    """Trigger a high-priority system-wide alert"""
    try:
        data = request.get_json(silent=True) or {}
        alert_type = data.get('type', 'FLOOD')
        severity = data.get('severity', 'CRITICAL')
        
        print(f"[AUTHORITY] TRIGGERED {severity} {alert_type} ALERT")
        
        # In a real app, this would push to Firebase 'alerts' node
        try:
            timestamp = int(time.time() * 1000)
            alert_data = {
                "type": alert_type,
                "severity": severity,
                "title": f"{severity} {alert_type} WARNING",
                "message": f"System-wide {alert_type.lower()} alert activated by Authority. Take immediate precautions.",
                "timestamp": timestamp,
                "active": True
            }
            safe_db_push('alerts', alert_data)
        except Exception as fe:
            print(f"Firebase Alert Error: {fe}")

        return jsonify({
            "status": "success",
            "message": f"{severity} {alert_type} alert triggered successfully",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/authority/generate-notice', methods=['POST'])
def generate_legal_notice():
    """Generate a legal notice based on environmental violations"""
    try:
        data = request.get_json(silent=True) or {}
        # Mock data for notice
        notice_id = f"RS-NOT-2026-{random.randint(1000, 9999)}"
        content = f"""
RIVER SENTINEL - AUTHORITY LEGAL NOTICE
Code: {notice_id}
Date: {datetime.now().strftime("%B %d, %Y")}

TO: INDUSTRIAL COMPLIANCE DIVISION / LOCAL BODIES
SUBJECT: ENVIRONMENTAL VIOLATION NOTICE

Notice is hereby given based on automated monitoring data from RiverSentinel Station: Assi Ghat.
Recent measurements recorded:
- COD: 210 mg/L (Exceeds limit of 150 mg/L)
- BOD: 65 mg/L (Exceeds limit of 30 mg/L)
- Dissolved Oxygen: 3.2 mg/L (Below minimum limit of 4.0 mg/L)

ACTION REQUIRED: Immediate inspection of upstream discharge points and containment 
of non-compliant effluents within 24 hours.

Issued by:
Central Pollution Control Board (UPPCB)
RiverSentinel Intelligent Dashboard
        """
        
        return jsonify({
            "status": "success",
            "notice_id": notice_id,
            "content": content,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/authority/export-data', methods=['GET'])
def export_system_data():
    """Export latest environmental data as CSV"""
    try:
        # Generate some mock history for the CSV or fetch from Firebase if available
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Timestamp', 'Station', 'pH', 'Turbidity', 'Temp (C)', 'Water Level (m)', 'BOD', 'COD', 'DO'])
        
        # Mock data for export
        base_time = time.time()
        for i in range(10):
            row_time = datetime.fromtimestamp(base_time - i * 3600).strftime("%Y-%m-%d %H:%M:%S")
            writer.writerow([
                row_time,
                'Assi Ghat',
                round(random.uniform(6.5, 8.5), 2),
                round(random.uniform(50, 200), 1),
                round(random.uniform(25, 30), 1),
                round(random.uniform(67, 69), 2),
                round(random.uniform(20, 40), 1),
                round(random.uniform(100, 180), 1),
                round(random.uniform(4, 9), 1)
            ])
        
        # Flask response with CSV
        from flask import make_response
        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = "attachment; filename=RiverSentinel_Export.csv"
        response.headers["Content-type"] = "text/csv"
        return response
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- REPORT MANAGEMENT ---

@app.route('/api/authority/reports', methods=['GET'])
def get_reports():
    """Fetch all citizen reports for moderation"""
    reports = [
        {"id": "mock_1", "location": "Dashashwamedh Steps", "reporter": "Aviral S.", "pollution_level": "High", "status": "PENDING", "timestamp": int(time.time()*1000), "assessment": "Visible oil slicks near boat landing."},
        {"id": "mock_2", "location": "Assi Ghat", "reporter": "Priya V.", "pollution_level": "Moderate", "status": "VERIFIED", "timestamp": int(time.time()*1000)-3600000, "assessment": "Plastic waste accumulating at riverbank."}
    ]
    try:
        reports_dict = safe_db_get('analysis_history')
        
        if not reports_dict:
            return jsonify(reports) # Return mocks if empty
            
        real_reports = []
        # Firebase returns a list if keys are sequential integers, else a dict
        if isinstance(reports_dict, dict):
            for key, val in reports_dict.items():
                if not isinstance(val, dict): continue
                val['id'] = key
                if 'status' not in val: val['status'] = 'PENDING'
                if 'location' not in val: val['location'] = 'Dashashwamedh Steps'
                if 'reporter' not in val: val['reporter'] = 'Anonymous'
                real_reports.append(val)
        elif isinstance(reports_dict, list):
            for idx, val in enumerate(reports_dict):
                if not val or not isinstance(val, dict): continue
                val['id'] = str(idx)
                if 'status' not in val: val['status'] = 'PENDING'
                if 'location' not in val: val['location'] = 'Dashashwamedh Steps'
                if 'reporter' not in val: val['reporter'] = 'Anonymous'
                real_reports.append(val)
            
        if real_reports:
            # Sort by timestamp descending
            real_reports.sort(key=lambda x: x.get('timestamp', 0) or 0, reverse=True)
            return jsonify(real_reports)
            
    except Exception as e:
        print(f"[ERROR] get_reports failed: {e}")
        print("[INFO] Returning mock reports for dashboard preview")
        
    return jsonify(reports)

@app.route('/api/authority/reports/update', methods=['POST'])
def update_report_status():
    """Update status of a report (VERIFIED, REJECTED, RESOLVED)"""
    try:
        data = request.get_json(silent=True) or {}
        report_id = data.get('reportId')
        new_status = data.get('status')
        
        if not report_id or not new_status:
            return jsonify({"status": "error", "message": "Missing reportId or status"}), 400
            
        safe_db_update(f'analysis_history/{report_id}', {"status": new_status})
        
        print(f"[AUTHORITY] Updated report {report_id} status to {new_status}")
        
        return jsonify({
            "status": "success",
            "message": f"Report marked as {new_status.lower()}",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/reports/submit', methods=['POST'])
def submit_full_report():
    """Internal endpoint to save a final report with user-provided details"""
    try:
        data = request.get_json(silent=True) or {}
        
        # In a real app, we'd find the existing analysis and merge
        # but for now we'll just push a full record
        report_data = {
            **data,
            "timestamp": int(time.time() * 1000),
            "status": "PENDING"
        }
        
        safe_db_push('analysis_history', report_data)
        return jsonify({"status": "success", "message": "Report submitted successfully"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/authority/report-summary', methods=['GET'])
def get_report_summary():
    """Aggregate statistics for the formal authority report"""
    # Initial defaults
    sensor_stats = {
        "avg_ph": 7.2,
        "avg_do": 6.8,
        "avg_turbidity": 15.5,
        "avg_water_level": 65.0,
        "trend": "STABLE"
    }
    report_stats = {
        "total": 12, # Mock totals for better UI preview
        "verified": 8,
        "rejected": 2,
        "pending": 2,
        "resolution_rate": 83.3
    }
    active_alerts_count = 1

    try:
        # 1. Sensor Averages (Last 50 readings)
        recent_sensors = safe_db_get('sensor_data') # Fetch all for summary calculation
        
        if recent_sensors:
            if isinstance(recent_sensors, dict):
                vals = [v for v in recent_sensors.values() if isinstance(v, dict)]
            elif isinstance(recent_sensors, list):
                vals = [v for v in recent_sensors if isinstance(v, dict)]
            else:
                vals = []

            if vals:
                def safe_avg(key, default):
                    nums = [v.get(key) for v in vals if v.get(key) is not None]
                    return float(round(float(np.mean(nums)), 2)) if nums else default

                sensor_stats["avg_ph"] = safe_avg('ph', 7.2)
                sensor_stats["avg_do"] = safe_avg('do', 6.8)
                sensor_stats["avg_turbidity"] = safe_avg('turbidity', 15.5)
                sensor_stats["avg_water_level"] = safe_avg('water_level', 65.0)

        # 2. Report Statistics
        all_reports = safe_db_get('analysis_history')
        
        if all_reports:
            if isinstance(all_reports, dict):
                reports_list = [r for r in all_reports.values() if isinstance(r, dict)]
            elif isinstance(all_reports, list):
                reports_list = [r for r in all_reports if isinstance(r, dict)]
            else:
                reports_list = []

            if reports_list:
                report_stats["total"] = len(reports_list)
                report_stats["verified"] = 0
                report_stats["rejected"] = 0
                report_stats["pending"] = 0
                for r in reports_list:
                    status = str(r.get('status', 'PENDING')).upper()
                    if status == 'VERIFIED': report_stats["verified"] += 1
                    elif status == 'REJECTED': report_stats["rejected"] += 1
                    else: report_stats["pending"] += 1
                
                if report_stats["total"] > 0:
                    report_stats["resolution_rate"] = round(((report_stats["verified"] + report_stats["rejected"]) / report_stats["total"]) * 100, 1)

        # 3. Active Alerts
        alerts = safe_db_get('alerts')
        if alerts:
            if isinstance(alerts, dict):
                alert_list = [a for a in alerts.values() if isinstance(a, dict)]
            elif isinstance(alerts, list):
                alert_list = [a for a in alerts if isinstance(a, dict)]
            else:
                alert_list = []
            active_alerts_count = len([a for a in alert_list if a.get('active', True)])
        else:
            active_alerts_count = 0

    except Exception as e:
        print(f"[ERROR] get_report_summary failed: {e}")
        print("[INFO] Returning default metrics for report preview")

    return jsonify({
        "status": "success",
        "sensor_summary": sensor_stats,
        "report_summary": report_stats,
        "active_alerts": active_alerts_count,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "agency": "UP Pollution Control Board (VARANASI)"
    })

@app.route('/api/citizen/health-status', methods=['GET'])
def get_citizen_health_status():
    """Aggregate simplified health metrics for public report"""
    try:
        # Defaults
        health_score = 78
        grade = "B+"
        status = "SAFE"
        metrics = {
            "ph": 7.4,
            "do": 6.5,
            "purity": 88
        }

        try:
            ref = db.reference('sensor_data')
            latest = ref.order_by_key().limit_to_last(1).get()
            
            if latest and isinstance(latest, dict):
                v = list(latest.values())[0]
                metrics["ph"] = v.get('ph', 7.4)
                metrics["do"] = v.get('do', 6.5)
                # Calculate internal purity score
                metrics["purity"] = 100 - (v.get('turbidity', 15.0) / 5)
                metrics["purity"] = max(0, min(100, metrics["purity"]))

                # Health Score Calculation
                # Perfect PH is 7, weights: ph (30), do (40), purity (30)
                ph_score = 100 - abs(metrics["ph"] - 7) * 20
                score = (ph_score * 0.3) + (metrics["do"] * 10 * 0.4) + (metrics["purity"] * 0.3)
                health_score = int(max(0, min(100, score)))

                if health_score > 90: grade, status = "A+", "EXCELLENT"
                elif health_score > 80: grade, status = "A", "SAFE"
                elif health_score > 70: grade, status = "B+", "NOTICE"
                elif health_score > 60: grade, status = "B", "CAUTION"
                else: grade, status = "C", "WARNING"
                
        except Exception as fe:
            print(f"[ERROR] health-status firebase failed: {fe}")

        return jsonify({
            "status": "success",
            "health_score": health_score,
            "grade": grade,
            "safety_status": status,
            "metrics": metrics,
            "location": "Varanasi (Dashashwamedh)",
            "authority": "Varanasi Nagar Nigam & Namami Gange",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
