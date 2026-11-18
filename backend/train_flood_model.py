"""
Flood Prediction Model Training Script (Fixed)
================================================
Trains a Random Forest classifier using the existing flood dataset.
Features: water_level_varanasi, discharge_cumec, rain_varanasi_mm,
          rain_upstream_avg_mm, temperature_c, humidity_pct
Target: flood_label (1=flood, 0=no flood)

The model is saved to backend/flood_model.pkl and backend/flood_scaler.pkl.
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    classification_report, confusion_matrix,
    accuracy_score, roc_auc_score
)
import joblib
import json
import os
import warnings

warnings.filterwarnings('ignore')

print("=" * 60)
print("FLOOD PREDICTION MODEL TRAINING")
print("=" * 60)

# Resolve dataset path relative to this script
script_dir = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(script_dir, 'flood_model', 'flood_data_with_dynamic_labels.csv')

if not os.path.exists(data_path):
    raise FileNotFoundError(
        f"Flood dataset not found at: {data_path}\n"
        "Ensure flood_data_with_dynamic_labels.csv is in the flood_model/ subfolder."
    )

print(f"\n[INFO] Loading dataset from: {data_path}")
df = pd.read_csv(data_path)

print(f"[INFO] Dataset shape: {df.shape}")
print(f"[INFO] Columns: {list(df.columns)}")
print(f"[INFO] Target distribution:\n{df['flood_label'].value_counts()}")

# Feature selection – these 6 are available from real-time sensors + weather API
FEATURE_COLS = [
    'water_level_varanasi',
    'discharge_cumec',
    'rain_varanasi_mm',
    'rain_upstream_avg_mm',
    'temperature_c',
    'humidity_pct'
]

# Verify all features exist
missing = [c for c in FEATURE_COLS if c not in df.columns]
if missing:
    raise ValueError(f"Missing columns in dataset: {missing}")

X = df[FEATURE_COLS]
y = df['flood_label']

print(f"\n[INFO] Features used: {FEATURE_COLS}")
print(f"[INFO] Feature matrix shape: {X.shape}")
print(f"\n[INFO] Checking for missing values:")
print(X.isnull().sum())

# Drop any rows with NaN
X = X.dropna()
y = y[X.index]

# Train/test split with stratification
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"\n[INFO] Train: {X_train.shape[0]} samples")
print(f"[INFO] Test:  {X_test.shape[0]} samples")

# Feature scaling
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled  = scaler.transform(X_test)

# Train Random Forest
print("\n[INFO] Training Random Forest model...")
model = RandomForestClassifier(
    n_estimators=200,
    max_depth=15,
    min_samples_split=5,
    min_samples_leaf=2,
    class_weight='balanced',
    random_state=42,
    n_jobs=-1
)
model.fit(X_train_scaled, y_train)

# Evaluate
y_pred = model.predict(X_test_scaled)
y_prob = model.predict_proba(X_test_scaled)[:, 1]

accuracy = accuracy_score(y_test, y_pred)
roc_auc  = roc_auc_score(y_test, y_prob)

print(f"\n{'='*60}")
print("MODEL PERFORMANCE")
print(f"{'='*60}")
print(f"Accuracy :  {accuracy:.4f} ({accuracy*100:.2f}%)")
print(f"ROC-AUC  :  {roc_auc:.4f}")
print(f"\nConfusion Matrix:")
print(confusion_matrix(y_test, y_pred))
print(f"\nClassification Report:")
print(classification_report(y_test, y_pred, target_names=['No Flood', 'Flood']))

# Feature importance
fi = pd.DataFrame({
    'feature':    FEATURE_COLS,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)
print(f"\n{'='*60}")
print("FEATURE IMPORTANCE")
print(f"{'='*60}")
for _, row in fi.iterrows():
    print(f"  {row['feature']:30s}: {row['importance']:.4f}")

# Save model and scaler to backend root (used by app.py GET /api/flood/predict)
model_path  = os.path.join(script_dir, 'flood_model.pkl')
scaler_path = os.path.join(script_dir, 'flood_scaler.pkl')
info_path   = os.path.join(script_dir, 'model_info.json')

joblib.dump(model,  model_path)
joblib.dump(scaler, scaler_path)

model_info = {
    'model_type':   'RandomForestClassifier',
    'features':     FEATURE_COLS,
    'n_features':   len(FEATURE_COLS),
    'target':       'flood_label (1=flood, 0=no_flood)',
    'n_estimators': 200,
    'accuracy':     round(accuracy, 4),
    'roc_auc':      round(roc_auc, 4),
    'train_samples': int(X_train.shape[0]),
    'test_samples':  int(X_test.shape[0]),
    'feature_importance': dict(zip(
        FEATURE_COLS,
        [round(v, 4) for v in model.feature_importances_]
    )),
    'data_source': 'flood_data_with_dynamic_labels.csv (real Ganga/Varanasi data)',
    'sklearn_version': '1.9.1'
}

with open(info_path, 'w') as f:
    json.dump(model_info, f, indent=2)

print(f"\n{'='*60}")
print("TRAINING COMPLETE")
print(f"{'='*60}")
print(f"[SAVED] Model  -> {model_path}")
print(f"[SAVED] Scaler -> {scaler_path}")
print(f"[SAVED] Info   -> {info_path}")
