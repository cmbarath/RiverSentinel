"""
CPCB Class B Water Quality Standards & Reference Assessment Engine
Implements official CPCB Designated Best Use Class B criteria for outdoor bathing.
Provides record-level deterministic evaluation with explicit partial assessments.
"""

import os
import pandas as pd
import numpy as np


# Official CPCB Class B Criteria (Outdoor Bathing)
# Source: https://cpcb.nic.in/wqm/Designated_Best_Use_Water_Quality_Criteria.pdf
CPCB_CLASS_B_THRESHOLDS = {
    'ph_min': 6.5,
    'ph_max': 8.5,
    'do_min_mg_l': 5.0,
    'bod_max_mg_l': 3.0,
    'total_coliform_max_mpn_100ml': 500.0
}

# Operational Screening Criteria (Non-Statutory)
OPERATIONAL_SCREENING_THRESHOLDS = {
    'turbidity_screening_ntu': 100.0,
    'conductivity_screening_us_cm': 1500.0
}


def evaluate_cpcb_class_b_record(record):
    """
    Evaluates a single sample record against CPCB Class B Designated Best Use criteria.
    
    Returns a dict with:
      - record_assessment: One of:
          'compliant_for_measured_parameters' (All 4 present and pass)
          'non_compliant_for_measured_parameters' (Any measured required parameter fails)
          'partial_assessment' (Measured pass, but some required are missing)
          'insufficient_data' (No required parameters measured)
      - is_fully_compliant: True only if ALL 4 required parameters are present AND pass
      - has_violation: True if any available required parameter fails
      - parameter_evaluations: Dict mapping each parameter to its pass/fail/missing status
      - failed_parameters: List of failed parameter names
      - missing_parameters: List of missing required parameter names
      - operational_screenings: Dict for non-statutory parameters (turbidity, EC)
      - reasons: Detailed human-readable explanation list
    """
    reasons = []
    failed_params = []
    missing_params = []
    param_eval = {}

    # Extract required Class B parameters
    ph = record.get('ph')
    do_val = record.get('do_mg_l')
    bod_val = record.get('bod_mg_l')
    tc_val = record.get('total_coliform_mpn_100ml')

    # 1. pH (6.5 - 8.5)
    if ph is not None and not pd.isna(ph):
        ph = float(ph)
        if CPCB_CLASS_B_THRESHOLDS['ph_min'] <= ph <= CPCB_CLASS_B_THRESHOLDS['ph_max']:
            param_eval['ph'] = {'status': 'PASS', 'value': ph, 'threshold': '6.5 - 8.5'}
        else:
            param_eval['ph'] = {'status': 'FAIL', 'value': ph, 'threshold': '6.5 - 8.5'}
            failed_params.append('ph')
            reasons.append(f"pH {ph:.2f} is outside Class B range (6.5 - 8.5)")
    else:
        param_eval['ph'] = {'status': 'MISSING', 'value': None, 'threshold': '6.5 - 8.5'}
        missing_params.append('ph')

    # 2. Dissolved Oxygen (>= 5.0 mg/L)
    if do_val is not None and not pd.isna(do_val):
        do_val = float(do_val)
        if do_val >= CPCB_CLASS_B_THRESHOLDS['do_min_mg_l']:
            param_eval['do'] = {'status': 'PASS', 'value': do_val, 'threshold': '>= 5.0 mg/L'}
        else:
            param_eval['do'] = {'status': 'FAIL', 'value': do_val, 'threshold': '>= 5.0 mg/L'}
            failed_params.append('do')
            reasons.append(f"Dissolved Oxygen {do_val:.2f} mg/L is below Class B minimum (5.0 mg/L)")
    else:
        param_eval['do'] = {'status': 'MISSING', 'value': None, 'threshold': '>= 5.0 mg/L'}
        missing_params.append('do')

    # 3. Biochemical Oxygen Demand (<= 3.0 mg/L)
    if bod_val is not None and not pd.isna(bod_val):
        bod_val = float(bod_val)
        if bod_val <= CPCB_CLASS_B_THRESHOLDS['bod_max_mg_l']:
            param_eval['bod'] = {'status': 'PASS', 'value': bod_val, 'threshold': '<= 3.0 mg/L'}
        else:
            param_eval['bod'] = {'status': 'FAIL', 'value': bod_val, 'threshold': '<= 3.0 mg/L'}
            failed_params.append('bod')
            reasons.append(f"BOD {bod_val:.2f} mg/L exceeds Class B maximum (3.0 mg/L)")
    else:
        param_eval['bod'] = {'status': 'MISSING', 'value': None, 'threshold': '<= 3.0 mg/L'}
        missing_params.append('bod')

    # 4. Total Coliform (<= 500 MPN/100 mL)
    if tc_val is not None and not pd.isna(tc_val):
        tc_val = float(tc_val)
        if tc_val <= CPCB_CLASS_B_THRESHOLDS['total_coliform_max_mpn_100ml']:
            param_eval['total_coliform'] = {'status': 'PASS', 'value': tc_val, 'threshold': '<= 500 MPN/100mL'}
        else:
            param_eval['total_coliform'] = {'status': 'FAIL', 'value': tc_val, 'threshold': '<= 500 MPN/100mL'}
            failed_params.append('total_coliform')
            reasons.append(f"Total Coliform {tc_val:.0f} MPN/100mL exceeds Class B limit (500 MPN/100mL)")
    else:
        param_eval['total_coliform'] = {'status': 'MISSING', 'value': None, 'threshold': '<= 500 MPN/100mL'}
        missing_params.append('total_coliform')

    # Independent Operational Screening (Turbidity & EC)
    turb = record.get('turbidity_ntu')
    cond = record.get('conductivity_us_cm')
    operational = {}
    if turb is not None and not pd.isna(turb):
        turb = float(turb)
        operational['turbidity'] = {
            'value': turb,
            'status': 'NORMAL' if turb <= OPERATIONAL_SCREENING_THRESHOLDS['turbidity_screening_ntu'] else 'ELEVATED_INVESTIGATION',
            'threshold': f"Screening: <= {OPERATIONAL_SCREENING_THRESHOLDS['turbidity_screening_ntu']} NTU",
            'is_statutory': False
        }
    if cond is not None and not pd.isna(cond):
        cond = float(cond)
        operational['conductivity'] = {
            'value': cond,
            'status': 'NORMAL' if cond <= OPERATIONAL_SCREENING_THRESHOLDS['conductivity_screening_us_cm'] else 'HIGH_CONDUCTIVITY',
            'threshold': f"Screening: <= {OPERATIONAL_SCREENING_THRESHOLDS['conductivity_screening_us_cm']} uS/cm",
            'is_statutory': False
        }

    # Determine Final Record Assessment
    measured_count = 4 - len(missing_params)
    has_violation = len(failed_params) > 0

    if measured_count == 0:
        record_assessment = 'insufficient_data'
        is_fully_compliant = False
        reasons.append("Insufficient data: No required CPCB Class B parameters measured")
    elif has_violation:
        record_assessment = 'non_compliant_for_measured_parameters'
        is_fully_compliant = False
    elif len(missing_params) > 0:
        record_assessment = 'partial_assessment'
        is_fully_compliant = False  # NEVER declare full compliance if parameters are missing!
        reasons.append(f"Partial assessment: Measured parameters pass, but missing: {', '.join(missing_params)}")
    else:
        record_assessment = 'compliant_for_measured_parameters'
        is_fully_compliant = True
        reasons.append("All required CPCB Class B parameters measured and compliant")

    return {
        'record_assessment': record_assessment,
        'is_fully_compliant': is_fully_compliant,
        'has_violation': has_violation,
        'measured_parameters_count': measured_count,
        'failed_parameters': failed_params,
        'missing_parameters': missing_params,
        'parameter_evaluations': param_eval,
        'operational_screenings': operational,
        'reasons': reasons
    }


def evaluate_dataset(df):
    """
    Evaluates an entire dataframe of aligned CPCB records.
    Adds evaluation columns directly to the dataframe.
    """
    eval_records = []
    for _, row in df.iterrows():
        res = evaluate_cpcb_class_b_record(row)
        eval_records.append({
            'record_assessment': res['record_assessment'],
            'is_fully_compliant': res['is_fully_compliant'],
            'has_violation': res['has_violation'],
            'failed_parameters_str': ', '.join(res['failed_parameters']),
            'missing_parameters_str': ', '.join(res['missing_parameters']),
            'reasons_str': '; '.join(res['reasons'])
        })
    eval_df = pd.DataFrame(eval_records, index=df.index)
    return pd.concat([df, eval_df], axis=1)


def generate_evaluation_report(df):
    """Generates rigorous statistical report from evaluated dataset."""
    evaluated = evaluate_dataset(df)
    
    print("=" * 60)
    print("DETERMINISTIC CPCB CLASS B EVALUATION AUDIT")
    print("=" * 60)
    
    for station in evaluated['station_name'].unique():
        st_df = evaluated[evaluated['station_name'] == station]
        clean_name = st_df['clean_station_name'].iloc[0]
        river = st_df['river'].iloc[0]
        n_total = len(st_df)
        
        counts = st_df['record_assessment'].value_counts().to_dict()
        fully_comp = st_df['is_fully_compliant'].sum()
        has_viol = st_df['has_violation'].sum()
        
        # pH evaluations
        ph_series = st_df['ph'].dropna()
        ph_viol = st_df[st_df['ph'] > 8.5]
        
        # DO evaluations
        do_series = st_df['do_mg_l'].dropna()
        do_viol = st_df[st_df['do_mg_l'] < 5.0]
        
        # BOD evaluations
        bod_series = st_df['bod_mg_l'].dropna()
        bod_viol = st_df[st_df['bod_mg_l'] > 3.0]
        
        # Coliform evaluations
        tc_series = st_df['total_coliform_mpn_100ml'].dropna()
        tc_viol = st_df[st_df['total_coliform_mpn_100ml'] > 500.0]

        print(f"\nStation: {clean_name} [{river}] (n = {n_total})")
        print(f"  Record Assessments: {counts}")
        print(f"  Fully Compliant Records (All 4 met): {fully_comp} ({fully_comp/n_total*100:.1f}%)")
        print(f"  Non-Compliant Records (Any violation): {has_viol} ({has_viol/n_total*100:.1f}%)")
        print(f"  Individual Parameter Statistics & Failures:")
        print(f"    - pH: count={len(ph_series)}, mean={ph_series.mean():.2f}, min={ph_series.min():.2f}, max={ph_series.max():.2f}")
        print(f"      Violations (pH > 8.5): {len(ph_viol)} samples. Dates: {ph_viol['sample_date'].str[:10].tolist()}")
        print(f"    - DO: count={len(do_series)}, mean={do_series.mean():.2f} mg/L, min={do_series.min():.2f}, max={do_series.max():.2f}")
        print(f"      Violations (DO < 5.0): {len(do_viol)} samples.")
        print(f"    - BOD: count={len(bod_series)}, mean={bod_series.mean():.2f} mg/L, min={bod_series.min():.2f}, max={bod_series.max():.2f}")
        print(f"      Violations (BOD > 3.0): {len(bod_viol)} samples ({len(bod_viol)/len(bod_series)*100:.1f}% of measured BOD!)")
        print(f"    - Total Coliform: count={len(tc_series)}, mean={tc_series.mean():.0f} MPN, min={tc_series.min():.0f}, max={tc_series.max():.0f}")
        print(f"      Violations (TC > 500): {len(tc_viol)} samples ({len(tc_viol)/len(tc_series)*100:.1f}% of measured Coliform!)")
        print("-" * 50)
        
    return evaluated


if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_path = os.path.join(base_dir, 'backend', 'data', 'processed', 'varanasi_water_quality_aligned.csv')
    if not os.path.exists(data_path):
        data_path = os.path.join(base_dir, 'data', 'processed', 'varanasi_water_quality_aligned.csv')
    df = pd.read_csv(data_path)
    generate_evaluation_report(df)
