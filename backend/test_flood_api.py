"""
Test script for flood prediction API endpoint (River Sentinel 2.0)
Tests active 6-feature Random Forest model contract via test client.
"""

import json
from app import app

def test_flood_prediction():
    """Test flood prediction with canonical 6-feature scenarios"""
    client = app.test_client()

    print("=" * 60)
    print("FLOOD PREDICTION API REGRESSION TEST")
    print("=" * 60)

    # Test 1: Low Risk Scenario
    print("\n1. Testing LOW RISK scenario...")
    low_risk = {
        "water_level": 65.5,
        "discharge": 8000.0,
        "rain_varanasi": 2.0,
        "rain_upstream": 5.0,
        "temperature": 28.0,
        "humidity": 60.0
    }
    r1 = client.post("/api/flood/predict", json=low_risk)
    print(f"Status: {r1.status_code}")
    d1 = r1.get_json()
    print(f"Risk: {d1.get('risk_level')} | Prob: {d1.get('flood_probability')}% | Pred: {d1.get('prediction')}")
    assert r1.status_code == 200
    assert d1.get('risk_level') == 'LOW'

    # Test 2: High Risk Scenario
    print("\n2. Testing HIGH RISK scenario...")
    high_risk = {
        "water_level": 70.5,
        "discharge": 15000.0,
        "rain_varanasi": 85.0,
        "rain_upstream": 120.0,
        "temperature": 25.0,
        "humidity": 95.0
    }
    r2 = client.post("/api/flood/predict", json=high_risk)
    print(f"Status: {r2.status_code}")
    d2 = r2.get_json()
    print(f"Risk: {d2.get('risk_level')} | Prob: {d2.get('flood_probability')}% | Pred: {d2.get('prediction')}")
    assert r2.status_code == 200
    assert d2.get('risk_level') == 'HIGH'

    # Test 3: GET endpoint (live sensor auto-evaluation)
    print("\n3. Testing GET live prediction...")
    r3 = client.get("/api/flood/predict")
    print(f"Status: {r3.status_code}")
    d3 = r3.get_json()
    print(f"Risk: {d3.get('risk_level')} | Prob: {d3.get('flood_probability')}%")
    assert r3.status_code == 200

    print("\n" + "=" * 60)
    print("✅ All flood prediction API tests PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    test_flood_prediction()
