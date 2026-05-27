"""
Flood Prediction Model Training Script
Trains a Random Forest classifier on flood data and saves the model for real-time predictions
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, roc_auc_score
import joblib
import os

# Load the dataset
print("[INFO] Loading flood dataset...")
data_path = r'c:\Users\cmbar\OneDrive\Desktop\Projects\river-sentinel_antigravity\river-sentinel\flood_backend (1)\flood_backend\flood_data_with_dynamic_labels.csv'
df = pd.read_csv(data_path)

print(f"[INFO] Dataset shape: {df.shape}")
print(f"[INFO] Target distribution:\n{df['flood_label'].value_counts()}")

# Select features for training
# Exclude: date, flood_label (target), and static basin characteristics that don't change
feature_columns = [
    'water_level_varanasi',
    'discharge_cumec',
    'rain_varanasi_mm',
    'rain_upstream_avg_mm',
    'temperature_c',
    'humidity_pct'
]

X = df[feature_columns]
y = df['flood_label']

print(f"\n[INFO] Features used: {feature_columns}")
print(f"[INFO] Feature matrix shape: {X.shape}")

# Split the data
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"\n[INFO] Training set: {X_train.shape[0]} samples")
print(f"[INFO] Test set: {X_test.shape[0]} samples")

# Scale the features
print("\n[INFO] Scaling features...")
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Train Random Forest model
print("\n[INFO] Training Random Forest model...")
rf_model = RandomForestClassifier(
    n_estimators=200,
    max_depth=15,
    min_samples_split=5,
    min_samples_leaf=2,
    random_state=42,
    n_jobs=-1,
    class_weight='balanced'  # Handle class imbalance
)

rf_model.fit(X_train_scaled, y_train)

# Evaluate the model
print("\n[INFO] Evaluating model...")
y_pred = rf_model.predict(X_test_scaled)
y_pred_proba = rf_model.predict_proba(X_test_scaled)[:, 1]

accuracy = accuracy_score(y_test, y_pred)
roc_auc = roc_auc_score(y_test, y_pred_proba)

print(f"\n{'='*60}")
print(f"MODEL PERFORMANCE")
print(f"{'='*60}")
print(f"Accuracy: {accuracy:.4f}")
print(f"ROC-AUC Score: {roc_auc:.4f}")

print(f"\nConfusion Matrix:")
print(confusion_matrix(y_test, y_pred))

print(f"\nClassification Report:")
print(classification_report(y_test, y_pred, target_names=['No Flood', 'Flood']))

# Feature importance
print(f"\n{'='*60}")
print(f"FEATURE IMPORTANCE")
print(f"{'='*60}")
feature_importance = pd.DataFrame({
    'feature': feature_columns,
    'importance': rf_model.feature_importances_
}).sort_values('importance', ascending=False)

for idx, row in feature_importance.iterrows():
    print(f"{row['feature']:30s}: {row['importance']:.4f}")

# Save the model and scaler
print(f"\n[INFO] Saving model and scaler...")
model_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(model_dir, 'flood_model.pkl')
scaler_path = os.path.join(model_dir, 'flood_scaler.pkl')

joblib.dump(rf_model, model_path)
joblib.dump(scaler, scaler_path)

print(f"[SUCCESS] ✅ Model saved to: {model_path}")
print(f"[SUCCESS] ✅ Scaler saved to: {scaler_path}")

# Save feature names for reference
feature_info = {
    'features': feature_columns,
    'feature_importance': dict(zip(feature_columns, rf_model.feature_importances_)),
    'accuracy': accuracy,
    'roc_auc': roc_auc
}

import json
info_path = os.path.join(model_dir, 'model_info.json')
with open(info_path, 'w') as f:
    json.dump(feature_info, f, indent=2)

print(f"[SUCCESS] ✅ Model info saved to: {info_path}")

print(f"\n{'='*60}")
print(f"TRAINING COMPLETE!")
print(f"{'='*60}")
