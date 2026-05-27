"""
Test script for flood prediction API endpoint
"""
import requests
import json

# Base URL
BASE_URL = "http://localhost:5000"

def test_flood_prediction():
    """Test flood prediction with different scenarios"""
    
    print("=" * 60)
    print("FLOOD PREDICTION API TEST")
    print("=" * 60)
    
    # Test 1: Low Risk Scenario
    print("\n1. Testing LOW RISK scenario...")
    low_risk_data = {
        "water_level_varanasi": 60.0,
        "discharge_cumec": 1000.0,
        "rain_upstream_avg_mm": 10.0,
        "temperature_c": 25.0,
        "humidity_pct": 60.0,
        "basin_area_pct": 40.0,
        "mean_elevation_m": 150.0,
        "mean_slope": 0.05,
        "basin_relief_m": 200.0,
        "flow_accumulation": 800.0,
        "twi": 7.0,
        "network_density": 0.25
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/flood/predict", json=low_risk_data)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: Moderate Risk Scenario
    print("\n2. Testing MODERATE RISK scenario...")
    moderate_risk_data = {
        "water_level_varanasi": 68.0,
        "discharge_cumec": 2000.0,
        "rain_upstream_avg_mm": 30.0,
        "temperature_c": 28.0,
        "humidity_pct": 75.0,
        "basin_area_pct": 45.0,
        "mean_elevation_m": 150.0,
        "mean_slope": 0.05,
        "basin_relief_m": 200.0,
        "flow_accumulation": 1200.0,
        "twi": 8.5,
        "network_density": 0.3
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/flood/predict", json=moderate_risk_data)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 3: High Risk Scenario
    print("\n3. Testing HIGH RISK scenario...")
    high_risk_data = {
        "water_level_varanasi": 75.0,
        "discharge_cumec": 3000.0,
        "rain_upstream_avg_mm": 50.0,
        "temperature_c": 30.0,
        "humidity_pct": 90.0,
        "basin_area_pct": 50.0,
        "mean_elevation_m": 150.0,
        "mean_slope": 0.05,
        "basin_relief_m": 200.0,
        "flow_accumulation": 1500.0,
        "twi": 10.0,
        "network_density": 0.4
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/flood/predict", json=high_risk_data)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 4: Missing Fields Error
    print("\n4. Testing error handling (missing fields)...")
    incomplete_data = {
        "water_level_varanasi": 65.0,
        "discharge_cumec": 1500.0
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/flood/predict", json=incomplete_data)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    test_flood_prediction()
