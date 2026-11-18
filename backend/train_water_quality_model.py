"""
Water Quality / Pollution Prediction Model Training Script
============================================================
Trains a Random Forest classifier to predict water potability.
Features used: pH, turbidity, temperature, electrical conductivity (EC), dissolved oxygen (DO)
Target: potable (1 = potable/safe, 0 = not potable/unsafe)

This script generates synthetic-but-realistic water quality data based on
WHO/BIS safe water standards when no real sensor dataset is available.
If you have a real CSV dataset, replace the data generation section.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
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

RANDOM_STATE = 42
np.random.seed(RANDOM_STATE)

print("=" * 60)
print("WATER QUALITY MODEL TRAINING")
print("=" * 60)

# ---------------------------------------------------------------------------
# DATA GENERATION
# We generate synthetic sensor readings that reflect real-world ranges.
# Safe / potable class (label=1): readings within WHO / BIS limits
# Unsafe / not-potable class (label=0): readings outside safe limits
# ---------------------------------------------------------------------------

N_SAFE = 1200
N_UNSAFE = 800
N_TOTAL = N_SAFE + N_UNSAFE

print(f"\n[INFO] Generating {N_TOTAL} synthetic water quality samples "
      f"({N_SAFE} safe, {N_UNSAFE} unsafe)...")

# --- Safe / potable samples ---
ph_safe         = np.random.uniform(6.5,  8.5, N_SAFE)
turbidity_safe  = np.random.uniform(0.5,  9.9, N_SAFE)   # NTU < 10
temperature_safe= np.random.uniform(10.0, 35.0, N_SAFE)  # °C
ec_safe         = np.random.uniform(50.0, 499.9, N_SAFE)  # µS/cm < 500
do_safe         = np.random.uniform(5.1,  12.0, N_SAFE)  # mg/L > 5

# --- Unsafe / not-potable samples ---
ph_unsafe         = np.concatenate([
    np.random.uniform(0.0, 6.4, N_UNSAFE // 2),
    np.random.uniform(8.6, 14.0, N_UNSAFE // 2)
])
turbidity_unsafe  = np.random.uniform(10.0, 500.0, N_UNSAFE)
temperature_unsafe= np.random.uniform(0.0, 50.0, N_UNSAFE)
ec_unsafe         = np.random.uniform(500.0, 3000.0, N_UNSAFE)
do_unsafe         = np.random.uniform(0.0, 4.9, N_UNSAFE)

# Combine into a DataFrame
ph          = np.concatenate([ph_safe,          ph_unsafe])
turbidity   = np.concatenate([turbidity_safe,   turbidity_unsafe])
temperature = np.concatenate([temperature_safe, temperature_unsafe])
ec          = np.concatenate([ec_safe,          ec_unsafe])
do_val      = np.concatenate([do_safe,          do_unsafe])
labels      = np.array([1] * N_SAFE + [0] * N_UNSAFE)

df = pd.DataFrame({
    'ph':          ph,
    'turbidity':   turbidity,
    'temperature': temperature,
    'ec':          ec,
    'do':          do_val,
    'potable':     labels
})

# Shuffle
df = df.sample(frac=1, random_state=RANDOM_STATE).reset_index(drop=True)

print(f"[INFO] Dataset shape: {df.shape}")
print(f"[INFO] Label distribution:\n{df['potable'].value_counts()}")
print(f"\n[INFO] Feature statistics:")
print(df.drop('potable', axis=1).describe().round(2))

# ---------------------------------------------------------------------------
# TRAIN / TEST SPLIT
# ---------------------------------------------------------------------------
FEATURE_COLS = ['ph', 'turbidity', 'temperature', 'ec', 'do']
X = df[FEATURE_COLS]
y = df['potable']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
)
print(f"\n[INFO] Train: {X_train.shape[0]} samples  |  Test: {X_test.shape[0]} samples")

# ---------------------------------------------------------------------------
# FEATURE SCALING
# ---------------------------------------------------------------------------
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled  = scaler.transform(X_test)

# ---------------------------------------------------------------------------
# MODEL TRAINING
# ---------------------------------------------------------------------------
print("\n[INFO] Training Random Forest classifier...")
model = RandomForestClassifier(
    n_estimators=200,
    max_depth=12,
    min_samples_split=5,
    min_samples_leaf=2,
    class_weight='balanced',
    random_state=RANDOM_STATE,
    n_jobs=-1
)
model.fit(X_train_scaled, y_train)

# ---------------------------------------------------------------------------
# EVALUATION
# ---------------------------------------------------------------------------
y_pred      = model.predict(X_test_scaled)
y_pred_prob = model.predict_proba(X_test_scaled)[:, 1]

accuracy = accuracy_score(y_test, y_pred)
roc_auc  = roc_auc_score(y_test, y_pred_prob)

print(f"\n{'='*60}")
print("MODEL PERFORMANCE")
print(f"{'='*60}")
print(f"Accuracy :  {accuracy:.4f} ({accuracy*100:.2f}%)")
print(f"ROC-AUC  :  {roc_auc:.4f}")
print(f"\nConfusion Matrix:")
print(confusion_matrix(y_test, y_pred))
print(f"\nClassification Report:")
print(classification_report(y_test, y_pred,
      target_names=['Not Potable (0)', 'Potable (1)']))

# Feature importance
fi = pd.DataFrame({
    'feature':    FEATURE_COLS,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)
print(f"\n{'='*60}")
print("FEATURE IMPORTANCE")
print(f"{'='*60}")
for _, row in fi.iterrows():
    print(f"  {row['feature']:15s}: {row['importance']:.4f}")

# ---------------------------------------------------------------------------
# SAVE MODEL, SCALER, and METADATA
# ---------------------------------------------------------------------------
out_dir = os.path.dirname(os.path.abspath(__file__))
model_path  = os.path.join(out_dir, 'water_quality_model.pkl')
scaler_path = os.path.join(out_dir, 'water_quality_scaler.pkl')
info_path   = os.path.join(out_dir, 'water_quality_model_info.json')

joblib.dump(model,  model_path)
joblib.dump(scaler, scaler_path)

model_info = {
    'model_type':    'RandomForestClassifier',
    'features':      FEATURE_COLS,
    'n_features':    len(FEATURE_COLS),
    'target':        'potable (1=safe, 0=unsafe)',
    'n_estimators':  200,
    'accuracy':      round(accuracy, 4),
    'roc_auc':       round(roc_auc, 4),
    'train_samples': int(X_train.shape[0]),
    'test_samples':  int(X_test.shape[0]),
    'feature_importance': dict(zip(FEATURE_COLS,
                                   [round(v, 4) for v in model.feature_importances_])),
    'data_source': 'synthetic (WHO/BIS-based realistic sensor ranges)',
    'note': 'Retrained to fix sklearn version incompatibility in original model.'
}

with open(info_path, 'w') as f:
    json.dump(model_info, f, indent=2)

print(f"\n{'='*60}")
print("TRAINING COMPLETE")
print(f"{'='*60}")
print(f"[SAVED] Model  → {model_path}")
print(f"[SAVED] Scaler → {scaler_path}")
print(f"[SAVED] Info   → {info_path}")
print(f"\n⚠️  NOTE: Model is trained on synthetic data. For production use,")
print(f"   replace with real sensor measurements for improved accuracy.")
