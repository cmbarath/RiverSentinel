"""
Unit and Governance Test Suite for River Sentinel 2.0 — Phase 6.1
Validates Model Governance, Semi-Synthetic Provenance, Ridge Superiority,
Negative R2 Acknowledgment, IsolationForest Recall, CPCB Verification,
and Emergency Alert Suppression.
"""

import unittest
import os
import sys
import json
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import create_app
from ml.water_quality.evaluator import evaluate_cpcb_class_b_record
from ml.flood.reassess_forecaster import FEATURE_PROVENANCE


class TestPhase61Governance(unittest.TestCase):
    """Test suite for Phase 6.1 Governance and Operational Readiness."""

    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        self.models_dir = os.path.join(BASE_DIR, 'ml', 'models')
        self.data_dir = os.path.join(BASE_DIR, 'data', 'processed')

    # Test 1: Semi-synthetic forecast data provenance
    def test_01_semi_synthetic_forecast_data_provenance(self):
        """Verifies that all 17 features have documented provenance and synthetic status."""
        self.assertEqual(len(FEATURE_PROVENANCE), 17)
        for feat, meta in FEATURE_PROVENANCE.items():
            self.assertIn('provenance_status', meta)
            self.assertIn('source', meta)
            self.assertIn('available_at_prediction_time', meta)
            self.assertTrue(meta['available_at_prediction_time'], f"Feature {feat} leaks future data!")
        # Verify target is identified as semi-synthetic
        meta_path = os.path.join(self.models_dir, 'flood_stage_forecaster_v1.json')
        with open(meta_path) as f:
            meta = json.load(f)
        self.assertEqual(meta['data_provenance'], 'semi_synthetic_research_series')
        self.assertIn('semi_synthetic', meta['data_provenance'])

    # Test 2: Model registry status
    def test_02_model_registry_status(self):
        """Verifies that all models have legally and scientifically accurate registry statuses."""
        # Flood forecaster must be research_only
        with open(os.path.join(self.models_dir, 'flood_stage_forecaster_v1.json')) as f:
            f_meta = json.load(f)
        self.assertEqual(f_meta['operational_status'], 'research_only')

        # Anomaly detector must be experimental
        with open(os.path.join(self.models_dir, 'water_quality_anomaly_detector_v1.json')) as f:
            w_meta = json.load(f)
        self.assertEqual(w_meta['operational_status'], 'experimental')
        self.assertFalse(w_meta['alert_approval'])

    # Test 3: Flood forecast research-only API response
    def test_03_flood_forecast_research_only_api_response(self):
        """API must return prediction_status='research_only' and is_official_cwc_gauge=False."""
        res = self.client.get('/api/flood/predict')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['prediction_status'], 'research_only')
        self.assertEqual(data['data_provenance'], 'semi_synthetic_research_series')
        self.assertFalse(data['is_official_cwc_gauge'])
        self.assertFalse(data['alert_eligible'])

    # Test 4: Emergency alert suppression for flood forecast
    def test_04_emergency_alert_suppression_flood(self):
        """Experimental stage forecast must NEVER trigger emergency SMS or public alarms."""
        with open(os.path.join(self.models_dir, 'flood_stage_forecaster_v1.json')) as f:
            meta = json.load(f)
        rules = meta['alert_engine_rules']
        self.assertFalse(rules['allow_emergency_sms'])
        self.assertFalse(rules['allow_automated_public_alert'])
        self.assertEqual(rules['display_mode'], 'research_advisory_only')

    # Test 5: Ridge versus Random Forest ranking
    def test_05_ridge_versus_random_forest_ranking(self):
        """Verifies that Ridge Regression is ranked above Random Forest on MAE and RMSE."""
        with open(os.path.join(self.models_dir, 'flood_stage_forecaster_v1.json')) as f:
            meta = json.load(f)
        benchmarks = meta['all_model_benchmarks']
        ridge_mae = benchmarks['Ridge Regression (alpha=10.0)']['overall']['mae_m']
        rf_mae = benchmarks['Random Forest Regressor (n=100, depth=6)']['overall']['mae_m']
        ridge_rmse = benchmarks['Ridge Regression (alpha=10.0)']['overall']['rmse_m']
        rf_rmse = benchmarks['Random Forest Regressor (n=100, depth=6)']['overall']['rmse_m']

        self.assertLessEqual(ridge_mae, rf_mae, "Ridge MAE should be lower than Random Forest MAE")
        self.assertLessEqual(ridge_rmse, rf_rmse, "Ridge RMSE should be lower than Random Forest RMSE")
        self.assertEqual(meta['selected_model_type'], 'RidgeRegression (alpha=10.0)')

    # Test 6: Negative R2 reporting
    def test_06_negative_r2_reporting(self):
        """Verifies that negative R2 on the 2020 test set is honestly documented without fabrication."""
        with open(os.path.join(self.models_dir, 'flood_stage_forecaster_v1.json')) as f:
            meta = json.load(f)
        r2 = meta['metrics_test_2020']['r2']
        self.assertLess(r2, 0.0, f"R2 should be negative on test set, got {r2}")
        self.assertAlmostEqual(r2, -0.0399, places=2)
        # Check limitation documentation
        found_limitation = any('R2 score is slightly negative' in lim for lim in meta['known_limitations'])
        self.assertTrue(found_limitation, "Negative R2 must be explicitly documented in limitations")

    # Test 7: Analytical high-water subset labelling
    def test_07_analytical_high_water_subset_labelling(self):
        """Verifies that 67.5m is strictly labelled as an analytical subset boundary, not CWC warning."""
        res = self.client.get('/api/flood/predict')
        data = res.get_json()
        sf = data['stage_forecast']
        self.assertIn('analytical_high_water_subset', sf)
        self.assertIn('analytical_subset_note', sf)
        self.assertIn('NOT an official CWC statutory flood warning stage', sf['analytical_subset_note'])
        # CWC Warning must remain 70.26m
        self.assertEqual(sf['cwc_gauge_reference']['warning_stage_m'], 70.26)
        self.assertEqual(sf['cwc_gauge_reference']['danger_stage_m'], 71.26)

    # Test 8: IsolationForest recall reporting
    def test_08_isolation_forest_recall_reporting(self):
        """Verifies honest reporting of 27.1% recall on severe sewage in model metadata."""
        with open(os.path.join(self.models_dir, 'water_quality_anomaly_detector_v1.json')) as f:
            meta = json.load(f)
        rec = meta['evaluation_metrics']['recall']
        self.assertAlmostEqual(rec, 0.2708, places=3)
        self.assertEqual(meta['evaluation_metrics']['true_positives'], 13)
        self.assertEqual(meta['evaluation_metrics']['false_negatives'], 35)
        self.assertIn('parameter subspace blindness', meta['root_cause_of_low_recall'])

    # Test 9: Experimental anomaly alert suppression
    def test_09_experimental_anomaly_alert_suppression(self):
        """Verifies that anomaly detector output is labelled experimental_screening_only with alert_eligible=False."""
        res = self.client.get('/api/water-quality/predict')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        ps = data['physical_screening']
        self.assertEqual(ps['screening_status'], 'experimental_screening_only')
        self.assertFalse(ps['alert_eligible'])
        self.assertIn('Never represents a confirmed pollution event', ps['screening_note'])

    # Test 10: CPCB source-row count verification
    def test_10_cpcb_source_row_count_verification(self):
        """Verifies exact 272 rows and station breakdowns from official aligned CPCB file."""
        df = pd.read_csv(os.path.join(self.data_dir, 'varanasi_water_quality_aligned.csv'))
        self.assertEqual(len(df), 272)
        counts = df['station_name'].value_counts().to_dict()
        self.assertEqual(counts['GANGA AT VARANASI U/S (ASSIGHAT) U.P'], 64)
        self.assertEqual(counts['GANGA AT VARANASI D/S (MALVIYA BRIDGE) U.P'], 65)
        self.assertEqual(counts['RIVER VARUNA AT RAMESHWAR VARANASI'], 47)
        self.assertEqual(counts['RIVER VARUNA B/C WITH RIVER GANGA AT VARANASI'], 48)
        self.assertEqual(counts['GOMTI AT VARANASI U.P'], 48)

    # Test 11: Ganga/tributary station separation
    def test_11_ganga_tributary_station_separation(self):
        """Ganga mainstem (129 rows) must be strictly separated from tributaries (143 rows)."""
        df = pd.read_csv(os.path.join(self.data_dir, 'varanasi_water_quality_aligned.csv'))
        ganga = df[df['river'] == 'Ganga']
        tributaries = df[df['river'] != 'Ganga']
        self.assertEqual(len(ganga), 129)
        self.assertEqual(len(tributaries), 143)
        self.assertEqual(set(ganga['clean_station_name'].unique()), {
            'Ganga U/S Assi Ghat',
            'Ganga D/S Malviya Bridge (Rajghat)'
        })

    # Test 12: Class B missing-parameter handling
    def test_12_class_b_missing_parameter_handling(self):
        """Full compliance must never be declared if any statutory parameter is missing."""
        # Missing total coliform
        sample = {'ph': 8.0, 'do_mg_l': 7.5, 'bod_mg_l': 2.0}
        res = evaluate_cpcb_class_b_record(sample)
        self.assertEqual(res['record_assessment'], 'partial_assessment')
        self.assertFalse(res['is_fully_compliant'])
        self.assertIn('total_coliform', res['missing_parameters'])

        # Complete sample with all 4 passing
        sample_full = {'ph': 8.0, 'do_mg_l': 7.5, 'bod_mg_l': 2.0, 'total_coliform_mpn_100ml': 400.0}
        res_full = evaluate_cpcb_class_b_record(sample_full)
        self.assertEqual(res_full['record_assessment'], 'compliant_for_measured_parameters')
        self.assertTrue(res_full['is_fully_compliant'])


if __name__ == '__main__':
    unittest.main()
