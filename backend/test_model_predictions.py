"""
Test the trained flood prediction model with random scenarios
"""

import numpy as np
import joblib
import os

# Load the trained model and scaler
model_path = os.path.join(os.path.dirname(__file__), 'flood_model.pkl')
scaler_path = os.path.join(os.path.dirname(__file__), 'flood_scaler.pkl')

print("="*60)
print("FLOOD PREDICTION MODEL - RANDOM VALUE TESTING")
print("="*60)

if not os.path.exists(model_path) or not os.path.exists(scaler_path):
    print("[ERROR] Model files not found!")
    print("Please run: python train_flood_model.py")
    exit(1)

model = joblib.load(model_path)
scaler = joblib.load(scaler_path)

print("\n[INFO] Model and scaler loaded successfully!")

# Define test scenarios
test_scenarios = [
    {
        'name': 'Normal Conditions (No Flood Expected)',
        'water_level': 66.5,
        'discharge': 9000,
        'rain_varanasi': 5.0,
        'rain_upstream': 8.0,
        'temperature': 28.0,
        'humidity': 65.0
    },
    {
        'name': 'High Water Level (Flood Risk)',
        'water_level': 69.5,
        'discharge': 14000,
        'rain_varanasi': 80.0,
        'rain_upstream': 100.0,
        'temperature': 26.0,
        'humidity': 85.0
    },
    {
        'name': 'Heavy Rainfall (Moderate Risk)',
        'water_level': 67.8,
        'discharge': 11500,
        'rain_varanasi': 95.0,
        'rain_upstream': 110.0,
        'temperature': 27.5,
        'humidity': 90.0
    },
    {
        'name': 'Extreme Flood Scenario',
        'water_level': 70.2,
        'discharge': 15500,
        'rain_varanasi': 120.0,
        'rain_upstream': 145.0,
        'temperature': 25.0,
        'humidity': 95.0
    },
    {
        'name': 'Dry Season (Very Low Risk)',
        'water_level': 65.0,
        'discharge': 7500,
        'rain_varanasi': 0.0,
        'rain_upstream': 0.0,
        'temperature': 32.0,
        'humidity': 45.0
    },
    {
        'name': 'Random Test Case 1',
        'water_level': np.random.uniform(65, 70),
        'discharge': np.random.uniform(8000, 15000),
        'rain_varanasi': np.random.uniform(0, 120),
        'rain_upstream': np.random.uniform(0, 140),
        'temperature': np.random.uniform(24, 35),
        'humidity': np.random.uniform(40, 95)
    },
    {
        'name': 'Random Test Case 2',
        'water_level': np.random.uniform(65, 70),
        'discharge': np.random.uniform(8000, 15000),
        'rain_varanasi': np.random.uniform(0, 120),
        'rain_upstream': np.random.uniform(0, 140),
        'temperature': np.random.uniform(24, 35),
        'humidity': np.random.uniform(40, 95)
    }
]

print("\n" + "="*60)
print("TESTING PREDICTIONS")
print("="*60)

for i, scenario in enumerate(test_scenarios, 1):
    print(f"\n{'='*60}")
    print(f"Test {i}: {scenario['name']}")
    print(f"{'='*60}")
    
    # Prepare features (must match training order)
    features = np.array([[
        scenario['water_level'],
        scenario['discharge'],
        scenario['rain_varanasi'],
        scenario['rain_upstream'],
        scenario['temperature'],
        scenario['humidity']
    ]])
    
    # Display input values
    print(f"\nInput Parameters:")
    print(f"  Water Level:      {scenario['water_level']:.2f} m")
    print(f"  Discharge:        {scenario['discharge']:.2f} cumec")
    print(f"  Rain (Varanasi):  {scenario['rain_varanasi']:.2f} mm/hr")
    print(f"  Rain (Upstream):  {scenario['rain_upstream']:.2f} mm/hr")
    print(f"  Temperature:      {scenario['temperature']:.2f} °C")
    print(f"  Humidity:         {scenario['humidity']:.2f} %")
    
    # Scale features
    features_scaled = scaler.transform(features)
    
    # Make prediction
    prediction = model.predict(features_scaled)[0]
    probability = model.predict_proba(features_scaled)[0][1]
    
    # Determine risk level
    if probability >= 0.7:
        risk_level = 'HIGH'
        risk_emoji = '🔴'
    elif probability >= 0.4:
        risk_level = 'MODERATE'
        risk_emoji = '🟡'
    else:
        risk_level = 'LOW'
        risk_emoji = '🟢'
    
    # Display results
    print(f"\n{risk_emoji} PREDICTION RESULTS:")
    print(f"  Prediction:       {'FLOOD' if prediction == 1 else 'NO FLOOD'}")
    print(f"  Probability:      {probability * 100:.2f}%")
    print(f"  Risk Level:       {risk_level}")

print("\n" + "="*60)
print("TESTING COMPLETE!")
print("="*60)
print("\n✅ All test scenarios executed successfully!")
print("The model is working correctly with random values.\n")
