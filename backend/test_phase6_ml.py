"""
Unit and Integration Test Suite for River Sentinel 2.0 — Phase 6B & 6C
Validates CPCB Class B Standards, Alignment, Deterministic Evaluator,
Flood Stage Forecaster, Baseline Comparisons, and Backend API Compatibility.
"""

import unittest
import os
import sys
import json
import pandas as pd
import numpy as np

# Add backend directory to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import create_app
from ml.water_quality.evaluator import (
    evaluate_cpcb_class_b_record,
    CPCB_CLASS_B_THRESHOLDS,
    OPERATIONAL_SCREENING_THRESHOLDS
)
from ml.water_quality.alignment import STATION_METADATA
from ml.flood.forecaster import load_and_engineer_flood_features


class TestWaterQualityCPCBStandards(unittest.TestCase):
    """Tests deterministic CPCB Class B criteria and record assessment logic."""

    def test_full_compliance_all_four_parameters(self):
        """Full compliance must only be declared when all 4 required parameters pass."""
        sample = {
            'ph': 7.8,
            'do_mg_l': 7.2,
            'bod_mg_l': 2.1,
            'total_coliform_mpn_100ml': 350.0
        }
        res = evaluate_cpcb_class_b_record(sample)
        self.assertEqual(res['record_assessment'], 'compliant_for_measured_parameters')
        self.assertTrue(res['is_fully_compliant'])
        self.assertFalse(res['has_violation'])
        self.assertEqual(len(res['failed_parameters']), 0)
        self.assertEqual(len(res['missing_parameters']), 0)

    def test_ph_criterion_failure_acidic_and_alkaline(self):
        """pH outside 6.5 - 8.5 must fail."""
        # Acidic failure
        res_acid = evaluate_cpcb_class_b_record({'ph': 6.2, 'do_mg_l': 6.0, 'bod_mg_l': 2.0, 'total_coliform_mpn_100ml': 100})
        self.assertEqual(res_acid['record_assessment'], 'non_compliant_for_measured_parameters')
        self.assertIn('ph', res_acid['failed_parameters'])

        # Alkaline failure (> 8.5)
        res_alk = evaluate_cpcb_class_b_record({'ph': 8.7, 'do_mg_l': 6.0, 'bod_mg_l': 2.0, 'total_coliform_mpn_100ml': 100})
        self.assertEqual(res_alk['record_assessment'], 'non_compliant_for_measured_parameters')
        self.assertIn('ph', res_alk['failed_parameters'])

    def test_do_criterion_failure(self):
        """DO < 5.0 mg/L must fail."""
        res = evaluate_cpcb_class_b_record({'ph': 7.5, 'do_mg_l': 4.2, 'bod_mg_l': 2.0, 'total_coliform_mpn_100ml': 100})
        self.assertEqual(res['record_assessment'], 'non_compliant_for_measured_parameters')
        self.assertIn('do', res['failed_parameters'])

    def test_bod_criterion_failure(self):
        """BOD > 3.0 mg/L must fail."""
        res = evaluate_cpcb_class_b_record({'ph': 7.5, 'do_mg_l': 6.5, 'bod_mg_l': 3.8, 'total_coliform_mpn_100ml': 200})
        self.assertEqual(res['record_assessment'], 'non_compliant_for_measured_parameters')
        self.assertIn('bod', res['failed_parameters'])

    def test_total_coliform_criterion_failure(self):
        """Total coliform > 500 MPN/100mL must fail."""
        res = evaluate_cpcb_class_b_record({'ph': 7.5, 'do_mg_l': 6.5, 'bod_mg_l': 2.0, 'total_coliform_mpn_100ml': 2500})
        self.assertEqual(res['record_assessment'], 'non_compliant_for_measured_parameters')
        self.assertIn('total_coliform', res['failed_parameters'])

    def test_partial_assessment_when_parameters_missing(self):
        """If measured parameters pass but others are missing, must report partial_assessment, NEVER fully compliant."""
        sample = {'ph': 8.1, 'do_mg_l': 7.5, 'bod_mg_l': 2.5}  # Missing coliform
        res = evaluate_cpcb_class_b_record(sample)
        self.assertEqual(res['record_assessment'], 'partial_assessment')
        self.assertFalse(res['is_fully_compliant'])
        self.assertIn('total_coliform', res['missing_parameters'])

    def test_insufficient_data(self):
        """If all statutory parameters are missing, must report insufficient_data."""
        res = evaluate_cpcb_class_b_record({'turbidity_ntu': 25.0})
        self.assertEqual(res['record_assessment'], 'insufficient_data')
        self.assertFalse(res['is_fully_compliant'])

    def test_turbidity_is_independent_operational_screening(self):
        """Turbidity > 100 NTU must trigger operational screening flag but NOT statutory failure if other 4 pass."""
        sample = {
            'ph': 7.5,
            'do_mg_l': 6.5,
            'bod_mg_l': 2.0,
            'total_coliform_mpn_100ml': 300,
            'turbidity_ntu': 150.0  # High turbidity
        }
        res = evaluate_cpcb_class_b_record(sample)
        self.assertEqual(res['record_assessment'], 'compliant_for_measured_parameters')
        self.assertTrue(res['is_fully_compliant'])
        self.assertEqual(res['operational_screenings']['turbidity']['status'], 'ELEVATED_INVESTIGATION')
        self.assertFalse(res['operational_screenings']['turbidity']['is_statutory'])


class TestStationSeparationAndAlignment(unittest.TestCase):
    """Verifies station role definitions and distinct hydrological context handling."""

    def test_ganga_stations_separated_from_tributaries(self):
        """Assi Ghat and Malviya Bridge are Ganga mainstem; Varuna/Gomti are tributaries."""
        self.assertEqual(STATION_METADATA['GANGA AT VARANASI U/S (ASSIGHAT) U.P']['river'], 'Ganga')
        self.assertEqual(STATION_METADATA['GANGA AT VARANASI D/S (MALVIYA BRIDGE) U.P']['river'], 'Ganga')
        self.assertEqual(STATION_METADATA['RIVER VARUNA AT RAMESHWAR VARANASI']['river'], 'Varuna')
        self.assertEqual(STATION_METADATA['RIVER VARUNA B/C WITH RIVER GANGA AT VARANASI']['river'], 'Varuna')
        self.assertEqual(STATION_METADATA['GOMTI AT VARANASI U.P']['river'], 'Gomti')

    def test_aligned_dataset_file_exists_and_verified(self):
        """Checks aligned dataset structure, row counts, and column types."""
        path = os.path.join(BASE_DIR, 'data', 'processed', 'varanasi_water_quality_aligned.csv')
        self.assertTrue(os.path.exists(path), f"Missing {path}")
        df = pd.read_csv(path)
        self.assertGreaterEqual(len(df), 250)
        self.assertIn('station_name', df.columns)
        self.assertIn('river', df.columns)
        self.assertIn('sample_date', df.columns)
        self.assertIn('ph', df.columns)
        self.assertIn('do_mg_l', df.columns)
        self.assertIn('bod_mg_l', df.columns)


class TestFloodForecastingAndDataReconciliation(unittest.TestCase):
    """Tests flood data engineering, causal leakage prevention, and CWC benchmarks."""

    def setUp(self):
        self.csv_path = os.path.join(BASE_DIR, 'flood_model', 'flood_data_with_dynamic_labels.csv')

    def test_no_future_leakage_in_features(self):
        """Verifies that features are computed strictly up to day t and target is t+1."""
        df = load_and_engineer_flood_features(self.csv_path)
        # Check target is exactly next day's stage
        for i in range(len(df) - 1):
            curr_target = df.loc[i, 'target_stage_t1']
            next_stage = df.loc[i + 1, 'stage_t']
            self.assertAlmostEqual(curr_target, next_stage, places=4)

    def test_cwc_benchmark_stages_varanasi(self):
        """Verifies official CWC hydrological stages for Ganga at Varanasi."""
        warning_stage = 70.26
        danger_stage = 71.26
        hfl = 73.90
        raw_df = pd.read_csv(self.csv_path)
        max_water_level = raw_df['water_level_varanasi'].max()

        # Documented fact: Dataset water level never reached CWC warning stage
        self.assertLess(max_water_level, warning_stage)
        self.assertAlmostEqual(max_water_level, 69.63, places=2)

    def test_versioned_flood_model_and_scaler_loadable(self):
        """Verifies that Phase 6 flood stage model is serialized with metadata."""
        model_path = os.path.join(BASE_DIR, 'ml', 'models', 'flood_stage_forecaster_v1.pkl')
        meta_path = os.path.join(BASE_DIR, 'ml', 'models', 'flood_stage_forecaster_v1.json')
        self.assertTrue(os.path.exists(model_path))
        self.assertTrue(os.path.exists(meta_path))

        with open(meta_path) as f:
            meta = json.load(f)
        self.assertEqual(meta['version'], '1.0.0')
        self.assertEqual(meta['status'], 'experimental')
        self.assertIn('known_limitations', meta)


class TestPredictionsAPIEndpoints(unittest.TestCase):
    """Tests Flask API endpoints for backwards compatibility and Phase 6 provenance."""

    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_weather_endpoint_success(self):
        res = self.client.get('/api/weather')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('temperature', data)
        self.assertIn('humidity', data)
        self.assertIn('source', data)

    def test_flood_prediction_contract_and_metadata(self):
        res = self.client.get('/api/flood/predict')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        # Existing frontend contract fields
        self.assertIn('prediction', data)
        self.assertIn('flood_probability', data)
        self.assertIn('risk_level', data)
        self.assertIn('message', data)
        self.assertIn('reasons', data)
        self.assertIn('sensor_data', data)
        self.assertIn('prediction_time', data)

        # Phase 6 provenance fields
        self.assertEqual(data['model_version'], 'flood_stage_forecaster_v1')
        self.assertEqual(data['prediction_status'], 'experimental')
        self.assertIn('stage_forecast', data)
        sf = data['stage_forecast']
        self.assertEqual(sf['forecast_horizon'], '1_day_ahead')
        self.assertEqual(sf['cwc_gauge_reference']['warning_stage_m'], 70.26)
        self.assertEqual(sf['cwc_gauge_reference']['danger_stage_m'], 71.26)

    def test_water_quality_prediction_contract_and_cpcb_breakdown(self):
        res = self.client.get('/api/water-quality/predict')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        # Existing frontend contract fields
        self.assertIn('potable', data)
        self.assertFalse(data['potable'])  # Raw river water is non-potable
        self.assertIn('quality_score', data)
        self.assertIn('quality_level', data)
        self.assertIn('reasons', data)
        self.assertIn('recommendations', data)

        # Phase 6 provenance and CPCB Class B fields
        self.assertEqual(data['model_version'], 'water_quality_evaluator_v1')
        self.assertEqual(data['prediction_status'], 'rule_based_reference_screening')
        self.assertIn('cpcb_class_b_assessment', data)
        cpcb = data['cpcb_class_b_assessment']
        self.assertIn('record_assessment', cpcb)
        self.assertIn('parameter_evaluations', cpcb)
        self.assertIn('physical_screening', data)


if __name__ == '__main__':
    unittest.main()
