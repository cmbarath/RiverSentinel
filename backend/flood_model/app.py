from fastapi import FastAPI
from pydantic import BaseModel
import numpy as np
import pandas as pd
import joblib


# Load trained objects
model = joblib.load("model.pkl")
scaler = joblib.load("scaler.pkl")
features = joblib.load("features.pkl")

app = FastAPI(title="Flood Prediction API")

# ---------- Input Schema ----------
class FloodInput(BaseModel):
    water_level_varanasi: float
    discharge_cumec: float
    rain_upstream_avg_mm: float
    temperature_c: float
    humidity_pct: float
    basin_area_pct: float
    mean_elevation_m: float
    mean_slope: float
    basin_relief_m: float
    flow_accumulation: float
    twi: float
    network_density: float

# ---------- Prediction Endpoint ----------
@app.post("/predict-flood")
def predict_flood(data: FloodInput):
    input_dict = data.dict()

    # Arrange input in training feature order
    input_df = pd.DataFrame([[input_dict[col] for col in features]], columns=features)

    # Scale
    input_scaled = scaler.transform(input_df)

    # Predict
    prob = model.predict_proba(input_scaled)[0][1]
    prob = float(np.clip(prob, 0.01, 0.99))

    # Risk classification
    if prob >= 0.75:
        risk = "HIGH FLOOD RISK"
    elif prob >= 0.40:
        risk = "MODERATE FLOOD RISK"
    else:
        risk = "LOW FLOOD RISK"

    return {
        "risk_level": risk,
        "flood_probability": round(prob * 100, 2)
    }
