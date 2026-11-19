"""
Flood Stage Forecasting Experiment & Model Pipeline
Target: river_level_at_t_plus_1_day (1-day-ahead river stage forecasting in metres MSL)
Strict chronological temporal split:
  Train: 2018-01-01 to 2019-12-31 (730 days)
  Test:  2020-01-01 to 2020-12-30 (365 days held-out)
Zero future feature leakage.
Compares:
  1. Persistence Baseline (next day = current day)
  2. Rolling Moving Average Baseline (3-day mean)
  3. Ridge Linear Regression
  4. Random Forest Regressor
  5. HistGradientBoostingRegressor
"""

import os
import json
import joblib
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def load_and_engineer_flood_features(csv_path):
    """
    Loads raw flood dataset and engineers time-series features strictly at time t.
    Target is water_level at t+1.
    """
    df = pd.read_csv(csv_path)
    df['date'] = pd.to_datetime(df['date'], dayfirst=True)
    df.sort_values('date', inplace=True)
    df.reset_index(drop=True, inplace=True)

    # Base series
    stage = df['water_level_varanasi']
    rain_local = df['rain_varanasi_mm']
    rain_up = df['rain_upstream_avg_mm']
    discharge = df['discharge_cumec']
    temp = df['temperature_c']
    humidity = df['humidity_pct']

    # Target: 1-day-ahead stage (t + 1)
    df['target_stage_t1'] = stage.shift(-1)

    # Features available at day t (strictly causal)
    df['stage_t'] = stage
    df['stage_lag1'] = stage.shift(1)
    df['stage_lag2'] = stage.shift(2)
    df['stage_delta_1d'] = stage - stage.shift(1)
    df['stage_delta_2d'] = stage - stage.shift(2)
    df['stage_rolling_mean_3d'] = stage.rolling(3).mean()
    df['stage_rolling_mean_7d'] = stage.rolling(7).mean()
    df['stage_rolling_max_7d'] = stage.rolling(7).max()

    # Rainfall features up to day t
    df['rain_local_t'] = rain_local
    df['rain_local_3d_sum'] = rain_local.rolling(3).sum()
    df['rain_upstream_t'] = rain_up
    df['rain_upstream_3d_sum'] = rain_up.rolling(3).sum()

    # Hydraulic and meteorological state at day t
    df['discharge_t'] = discharge
    df['temp_t'] = temp
    df['humidity_t'] = humidity

    # Seasonal harmonics
    day_of_year = df['date'].dt.dayofyear
    df['season_sin'] = np.sin(2 * np.pi * day_of_year / 365.25)
    df['season_cos'] = np.cos(2 * np.pi * day_of_year / 365.25)

    # Drop edge rows due to shifting (first 6 rows for 7-day rolling, last row for t+1 target)
    valid_df = df.dropna().copy()
    valid_df.reset_index(drop=True, inplace=True)
    return valid_df


def run_flood_experiments(csv_path, output_dir=None):
    df = load_and_engineer_flood_features(csv_path)

    feature_cols = [
        'stage_t', 'stage_lag1', 'stage_lag2',
        'stage_delta_1d', 'stage_delta_2d',
        'stage_rolling_mean_3d', 'stage_rolling_mean_7d', 'stage_rolling_max_7d',
        'rain_local_t', 'rain_local_3d_sum',
        'rain_upstream_t', 'rain_upstream_3d_sum',
        'discharge_t', 'temp_t', 'humidity_t',
        'season_sin', 'season_cos'
    ]
    target_col = 'target_stage_t1'

    # Strict Temporal Split:
    # Train: 2018-01-01 to 2019-12-31
    # Test:  2020-01-01 to 2020-12-30
    train_df = df[df['date'] < '2020-01-01'].copy()
    test_df = df[df['date'] >= '2020-01-01'].copy()

    X_train = train_df[feature_cols].values
    y_train = train_df[target_col].values
    X_test = test_df[feature_cols].values
    y_test = test_df[target_col].values

    print(f"[INFO] Train samples: {len(X_train)} (dates: {train_df['date'].min().strftime('%Y-%m-%d')} to {train_df['date'].max().strftime('%Y-%m-%d')})")
    print(f"[INFO] Test samples:  {len(X_test)}  (dates: {test_df['date'].min().strftime('%Y-%m-%d')} to {test_df['date'].max().strftime('%Y-%m-%d')})")

    # Fit scaler strictly on training partition
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Current stage for persistence baseline
    current_stage_test = test_df['stage_t'].values
    rolling_3d_test = test_df['stage_rolling_mean_3d'].values

    # High water mask on test set (water_level >= 67.5m)
    high_water_mask = (y_test >= 67.5)
    normal_water_mask = ~high_water_mask
    print(f"[INFO] Test set distribution: High water (>= 67.5m): {high_water_mask.sum()} days ({high_water_mask.mean()*100:.1f}%), Normal: {normal_water_mask.sum()} days")

    # Define Models to benchmark
    models = {
        'Persistence Baseline (y_t+1 = y_t)': None,
        'Rolling 3-Day Mean Baseline': None,
        'Ridge Regression': Ridge(alpha=10.0),
        'Random Forest Regressor': RandomForestRegressor(n_estimators=100, max_depth=6, min_samples_split=5, random_state=42),
        'HistGradientBoosting Regressor': HistGradientBoostingRegressor(max_iter=100, max_depth=4, l2_regularization=1.0, random_state=42)
    }

    results = {}

    for name, model in models.items():
        if name.startswith('Persistence'):
            y_pred = current_stage_test
        elif name.startswith('Rolling'):
            y_pred = rolling_3d_test
        else:
            model.fit(X_train_scaled, y_train)
            y_pred = model.predict(X_test_scaled)

        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        bias = np.mean(y_pred - y_test)
        r2 = r2_score(y_test, y_pred)

        # Segmented evaluation
        mae_high = mean_absolute_error(y_test[high_water_mask], y_pred[high_water_mask])
        rmse_high = np.sqrt(mean_squared_error(y_test[high_water_mask], y_pred[high_water_mask]))
        bias_high = np.mean(y_pred[high_water_mask] - y_test[high_water_mask])

        mae_norm = mean_absolute_error(y_test[normal_water_mask], y_pred[normal_water_mask])
        rmse_norm = np.sqrt(mean_squared_error(y_test[normal_water_mask], y_pred[normal_water_mask]))

        results[name] = {
            'overall': {'mae_m': round(float(mae), 4), 'rmse_m': round(float(rmse), 4), 'bias_m': round(float(bias), 4), 'r2': round(float(r2), 4)},
            'high_water': {'mae_m': round(float(mae_high), 4), 'rmse_m': round(float(rmse_high), 4), 'bias_m': round(float(bias_high), 4)},
            'normal_water': {'mae_m': round(float(mae_norm), 4), 'rmse_m': round(float(rmse_norm), 4)},
            'model_obj': model
        }

    print("\n" + "=" * 75)
    print("FLOOD STAGE FORECASTING BENCHMARK (Held-out Test Year 2020)")
    print("=" * 75)
    print(f"{'Model':<35} | {'MAE (m)':<8} | {'RMSE (m)':<8} | {'Bias (m)':<8} | {'R2':<6} | {'High-Water MAE':<14}")
    print("-" * 75)
    for name, res in results.items():
        o = res['overall']
        hw = res['high_water']
        print(f"{name:<35} | {o['mae_m']:<8.4f} | {o['rmse_m']:<8.4f} | {o['bias_m']:<8.4f} | {o['r2']:<6.4f} | {hw['mae_m']:<14.4f}")
    print("=" * 75)

    # Save Best Model as versioned artifact
    # Selected: Ridge Regression or Random Forest Regressor
    best_model_name = 'Random Forest Regressor'
    best_model = results[best_model_name]['model_obj']

    if output_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if os.path.basename(base_dir) == 'backend':
            base_dir = os.path.dirname(base_dir)
        output_dir = os.path.join(base_dir, 'backend', 'ml', 'models')
        os.makedirs(output_dir, exist_ok=True)

    model_save_path = os.path.join(output_dir, 'flood_stage_forecaster_v1.pkl')
    scaler_save_path = os.path.join(output_dir, 'flood_stage_scaler_v1.pkl')
    meta_save_path = os.path.join(output_dir, 'flood_stage_forecaster_v1.json')

    joblib.dump(best_model, model_save_path)
    joblib.dump(scaler, scaler_save_path)

    metadata = {
        'model_name': 'flood_stage_forecaster_v1',
        'task': 'river_stage_regression_1day_ahead',
        'model_type': 'RandomForestRegressor',
        'version': '1.0.0',
        'target': 'river_level_at_t_plus_1_day_metres_msl',
        'features': feature_cols,
        'units': {
            'stage': 'metres MSL',
            'rainfall': 'mm',
            'discharge': 'cumec',
            'temperature': 'deg C',
            'humidity': 'percent'
        },
        'training_period': '2018-01-08 to 2019-12-30',
        'test_period': '2020-01-01 to 2020-12-29',
        'test_samples': int(len(X_test)),
        'metrics_test_2020': {
            'mae_metres': results[best_model_name]['overall']['mae_m'],
            'rmse_metres': results[best_model_name]['overall']['rmse_m'],
            'bias_metres': results[best_model_name]['overall']['bias_m'],
            'r2_score': results[best_model_name]['overall']['r2'],
            'high_water_mae_metres': results[best_model_name]['high_water']['mae_m']
        },
        'baseline_comparison': {
            'persistence_mae_metres': results['Persistence Baseline (y_t+1 = y_t)']['overall']['mae_m'],
            'persistence_rmse_metres': results['Persistence Baseline (y_t+1 = y_t)']['overall']['rmse_m']
        },
        'statutory_cwc_thresholds_varanasi': {
            'warning_stage_m': 70.26,
            'danger_stage_m': 71.26,
            'highest_flood_level_m': 73.90
        },
        'status': 'experimental',
        'known_limitations': [
            'Dataset contains no records crossing CWC Warning Stage (70.26 m) or Danger Stage (71.26 m).',
            'Historical dataset reflects semi-synthetic simulation perturbations with non-seasonal rainfall artifacts.',
            'Cannot trigger statutory emergency alerts; statutory alerts must strictly follow CWC gauge readings.',
            'Requires upstream hydro-meteorological inputs from Prayagraj / Yamuna confluence for catastrophic flood forecasting.'
        ]
    }

    with open(meta_save_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"[OK] Model saved to:  {model_save_path}")
    print(f"[OK] Scaler saved to: {scaler_save_path}")
    print(f"[OK] Meta saved to:   {meta_save_path}")

    return results, metadata


if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # Check if base_dir ends with backend or project root
    if os.path.basename(base_dir) == 'backend':
        base_dir = os.path.dirname(base_dir)
    data_csv = os.path.join(base_dir, 'backend', 'flood_model', 'flood_data_with_dynamic_labels.csv')
    run_flood_experiments(data_csv)
