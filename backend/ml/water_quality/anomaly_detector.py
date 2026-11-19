"""
Water Quality Anomaly Detector & Physical Screening Model
Trained on empirical baseline distributions from CPCB Ganga monitoring at Varanasi (Assi Ghat & Malviya Bridge).
Identifies physical sensor anomalies, sudden contaminant surges, and out-of-distribution water quality events.
Evaluated on:
  - In-distribution Ganga baseline samples
  - Out-of-distribution severely polluted tributary samples (Varuna before confluence)
"""

import os
import json
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


def train_water_quality_anomaly_detector(data_csv_path, output_dir=None):
    df = pd.read_csv(data_csv_path)

    # Filter for Ganga Mainstem River stations
    ganga_df = df[df['river'] == 'Ganga'].copy()
    
    # Feature columns for real-time physical-chemical IoT screening
    feature_cols = ['ph', 'do_mg_l', 'turbidity_ntu', 'conductivity_us_cm']

    # Impute missing physical features using station-specific medians for baseline fitting
    # Note: pH and DO are 100% complete; turbidity and EC have median values available
    X_raw = ganga_df[feature_cols].copy()
    for col in feature_cols:
        med = X_raw[col].median()
        X_raw[col] = X_raw[col].fillna(med)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_raw)

    # Train IsolationForest on Ganga baseline
    # contamination=0.08 expects ~8% anomalous events in historical baseline
    detector = IsolationForest(
        n_estimators=100,
        contamination=0.08,
        random_state=42
    )
    detector.fit(X_scaled)

    # Evaluate on Ganga Baseline (In-Distribution)
    ganga_preds = detector.predict(X_scaled)  # 1 = normal, -1 = anomaly
    ganga_scores = detector.score_samples(X_scaled)
    ganga_anomaly_pct = (ganga_preds == -1).mean() * 100

    # Evaluate on Varuna Confluence (Severe Out-of-Distribution Urban Sewage / Industrial)
    varuna_df = df[df['clean_station_name'] == 'Varuna Before Confluence with Ganga'].copy()
    X_varuna = varuna_df[feature_cols].copy()
    for col in feature_cols:
        med = X_raw[col].median()
        X_varuna[col] = X_varuna[col].fillna(med)
    X_varuna_scaled = scaler.transform(X_varuna)

    varuna_preds = detector.predict(X_varuna_scaled)
    varuna_anomaly_pct = (varuna_preds == -1).mean() * 100

    print("=" * 65)
    print("WATER QUALITY ANOMALY DETECTOR BENCHMARK")
    print("=" * 65)
    print(f"Ganga Baseline Samples: {len(X_scaled)}")
    print(f"  Anomaly Rate Detected on Baseline: {ganga_anomaly_pct:.1f}%")
    print(f"Varuna Confluence Extreme Samples: {len(X_varuna_scaled)}")
    print(f"  Anomaly Detection Recall on Varuna: {varuna_anomaly_pct:.1f}%")
    print("=" * 65)

    if output_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if os.path.basename(base_dir) == 'backend':
            base_dir = os.path.dirname(base_dir)
        output_dir = os.path.join(base_dir, 'backend', 'ml', 'models')
        os.makedirs(output_dir, exist_ok=True)

    model_path = os.path.join(output_dir, 'water_quality_anomaly_detector_v1.pkl')
    scaler_path = os.path.join(output_dir, 'water_quality_scaler_v1.pkl')
    meta_path = os.path.join(output_dir, 'water_quality_anomaly_detector_v1.json')

    joblib.dump(detector, model_path)
    joblib.dump(scaler, scaler_path)

    metadata = {
        'model_name': 'water_quality_anomaly_detector_v1',
        'task': 'physical_chemical_sensor_anomaly_detection',
        'model_type': 'IsolationForest',
        'version': '1.0.0',
        'features': feature_cols,
        'units': {
            'ph': 'dimensionless',
            'do_mg_l': 'mg/L',
            'turbidity_ntu': 'NTU',
            'conductivity_us_cm': 'uS/cm'
        },
        'training_data': 'CPCB Uttar Pradesh Ganga Stations (Assi Ghat & Malviya Bridge 2018-2021)',
        'baseline_sample_count': int(len(X_scaled)),
        'contamination_prior': 0.08,
        'benchmark_results': {
            'baseline_anomaly_rate_pct': round(float(ganga_anomaly_pct), 2),
            'varuna_sewage_anomaly_recall_pct': round(float(varuna_anomaly_pct), 2)
        },
        'status': 'experimental',
        'known_limitations': [
            'Does not measure or predict 5-day Biochemical Oxygen Demand (BOD) or Total Coliform bacteria.',
            'Cannot declare CPCB Class B compliance without certified laboratory biological analysis.',
            'Intended solely for in-situ IoT sensor screening, sensor malfunction detection, or industrial spill screening.'
        ]
    }

    with open(meta_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"[OK] Model saved to:  {model_path}")
    print(f"[OK] Scaler saved to: {scaler_path}")
    print(f"[OK] Meta saved to:   {meta_path}")

    return metadata


if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if os.path.basename(base_dir) == 'backend':
        base_dir = os.path.dirname(base_dir)
    data_csv = os.path.join(base_dir, 'backend', 'data', 'processed', 'varanasi_water_quality_aligned.csv')
    train_water_quality_anomaly_detector(data_csv)
