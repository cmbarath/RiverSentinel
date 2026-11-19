"""
CPCB Water Quality Dataset Alignment Pipeline
Processes official raw CPCB physical, chemical, and biological datasets for Varanasi.
Aligns laboratory observations strictly by (Station, Sample Timestamp).
Preserves explicit river identity and distinguishes Ganga stations from tributaries.
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime


# Station Metadata Definitions
STATION_METADATA = {
    'GANGA AT VARANASI U/S (ASSIGHAT) U.P': {
        'clean_name': 'Ganga U/S Assi Ghat',
        'river': 'Ganga',
        'waterbody_type': 'Mainstem River',
        'station_role': 'upstream_baseline',
        'latitude': 25.2917,
        'longitude': 83.0039
    },
    'GANGA AT VARANASI D/S (MALVIYA BRIDGE) U.P': {
        'clean_name': 'Ganga D/S Malviya Bridge (Rajghat)',
        'river': 'Ganga',
        'waterbody_type': 'Mainstem River',
        'station_role': 'downstream_impact',
        'latitude': 25.3211,
        'longitude': 83.0317
    },
    'RIVER VARUNA AT RAMESHWAR VARANASI': {
        'clean_name': 'Varuna at Rameshwar',
        'river': 'Varuna',
        'waterbody_type': 'Tributary',
        'station_role': 'rural_tributary',
        'latitude': 25.3850,
        'longitude': 82.8800
    },
    'RIVER VARUNA B/C WITH RIVER GANGA AT VARANASI': {
        'clean_name': 'Varuna Before Confluence with Ganga',
        'river': 'Varuna',
        'waterbody_type': 'Tributary',
        'station_role': 'urban_tributary_confluence',
        'latitude': 25.3350,
        'longitude': 83.0450
    },
    'GOMTI AT VARANASI U.P': {
        'clean_name': 'Gomti at Varanasi',
        'river': 'Gomti',
        'waterbody_type': 'Tributary',
        'station_role': 'regional_tributary',
        'latitude': 25.5000,
        'longitude': 83.1500
    }
}


def _clean_numeric(series):
    """Clean a series containing numeric values, strings like '-', or corrupted text like 'Clear'."""
    s = series.astype(str).str.strip()
    s = s.replace({'-': np.nan, 'nan': np.nan, 'None': np.nan, '': np.nan})
    return pd.to_numeric(s, errors='coerce')


def align_cpcb_water_quality(raw_dir=None, output_path=None):
    """
    Loads raw CPCB physical, chemical, and biological files,
    filters for Varanasi stations, aligns strictly by sampling timestamp,
    cleans parameters, and outputs aligned dataset.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if raw_dir is None:
        raw_dir = os.path.join(base_dir, 'backend', 'data', 'raw', 'cpcb')
        if not os.path.exists(raw_dir):
            raw_dir = os.path.join(base_dir, 'data', 'raw', 'cpcb')
    if output_path is None:
        output_dir = os.path.join(base_dir, 'data', 'processed')
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, 'varanasi_water_quality_aligned.csv')

    print(f"[INFO] Reading raw CPCB packages from {raw_dir}...")
    
    # 1. Load Chemical Datasets
    chem_files = [
        os.path.join(raw_dir, 'chemical_up_1961_2020.csv'),
        os.path.join(raw_dir, 'chemical_up_2021_2025.csv')
    ]
    chem_dfs = [pd.read_csv(f, low_memory=False) for f in chem_files if os.path.exists(f)]
    chem = pd.concat(chem_dfs, ignore_index=True) if chem_dfs else pd.DataFrame()
    
    # 2. Load Biological Datasets
    bio_files = [
        os.path.join(raw_dir, 'biological_up_1961_2020.csv'),
        os.path.join(raw_dir, 'biological_up_2021_2025.csv')
    ]
    bio_dfs = [pd.read_csv(f, low_memory=False) for f in bio_files if os.path.exists(f)]
    bio = pd.concat(bio_dfs, ignore_index=True) if bio_dfs else pd.DataFrame()
    
    # 3. Load Physical Datasets
    phy_files = [
        os.path.join(raw_dir, 'physical_up_1961_2020.csv'),
        os.path.join(raw_dir, 'physical_up_2021_2025.csv')
    ]
    phy_dfs = [pd.read_csv(f, low_memory=False) for f in phy_files if os.path.exists(f)]
    phy = pd.concat(phy_dfs, ignore_index=True) if phy_dfs else pd.DataFrame()

    print(f"[INFO] Raw counts loaded: Chem={len(chem)}, Bio={len(bio)}, Phy={len(phy)}")

    # 4. Filter for Target Varanasi River Stations
    target_stations = list(STATION_METADATA.keys())
    
    c_var = chem[chem['Station'].isin(target_stations)].copy()
    b_var = bio[bio['Station'].isin(target_stations)].copy()
    p_var = phy[phy['Station'].isin(target_stations)].copy()

    # Track rejected non-river Varanasi rows (e.g. industrial areas, STP groundwater)
    all_var_chem = chem[chem['Station'].astype(str).str.contains('VARANASI', case=False, na=False)]
    rejected_stations = sorted(list(set(all_var_chem['Station']) - set(target_stations)))
    print(f"[INFO] Rejected non-river / industrial monitoring stations in Varanasi: {rejected_stations}")

    # Standardize Timestamp Format (DD-MM-YYYY HH:MM)
    for df in [c_var, b_var, p_var]:
        df['datetime'] = pd.to_datetime(df['Data Acquisition Time'], format='%d-%m-%Y %H:%M', errors='coerce')
        df['sample_date'] = df['datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')

    # Drop duplicates on (Station, sample_date) if any
    c_var = c_var.drop_duplicates(subset=['Station', 'sample_date'])
    b_var = b_var.drop_duplicates(subset=['Station', 'sample_date'])
    p_var = p_var.drop_duplicates(subset=['Station', 'sample_date'])

    # 5. Extract and Clean Columns
    # Chemical parameters
    c_cols = {
        'Potential of Hydrogen (pH)': 'ph',
        'Dissolved oxygen (mg/L)': 'do_mg_l',
        'Total Dissolved Solids (mg/L)': 'tds_mg_l',
        'Nitrate (mg/L)': 'nitrate_mg_l'
    }
    c_sub = c_var[['Station', 'sample_date'] + [col for col in c_cols.keys() if col in c_var.columns]].copy()
    for raw_col, clean_col in c_cols.items():
        if raw_col in c_sub.columns:
            c_sub[clean_col] = _clean_numeric(c_sub[raw_col])
            c_sub.drop(columns=[raw_col], inplace=True)

    # Biological parameters
    b_cols = {
        'Biochemical Oxygen Demand (mg/L)': 'bod_mg_l',
        'Chemical Oxygen Demand (mg/L)': 'cod_mg_l',
        'Total Coliform (MPN/100mL)': 'total_coliform_mpn_100ml',
        'Fecal Coliform (MPN/100mL)': 'fecal_coliform_mpn_100ml'
    }
    b_sub = b_var[['Station', 'sample_date'] + [col for col in b_cols.keys() if col in b_var.columns]].copy()
    for raw_col, clean_col in b_cols.items():
        if raw_col in b_sub.columns:
            b_sub[clean_col] = _clean_numeric(b_sub[raw_col])
            b_sub.drop(columns=[raw_col], inplace=True)

    # Physical parameters
    p_cols = {
        'Electric Conductivity (μS/cm)': 'conductivity_us_cm',
        'Turbidity (NTU)': 'turbidity_ntu',
        'Temperature (ºC)': 'temperature_c'
    }
    p_sub = p_var[['Station', 'sample_date'] + [col for col in p_cols.keys() if col in p_var.columns]].copy()
    for raw_col, clean_col in p_cols.items():
        if raw_col in p_sub.columns:
            p_sub[clean_col] = _clean_numeric(p_sub[raw_col])
            p_sub.drop(columns=[raw_col], inplace=True)

    # 6. Align on (Station, sample_date)
    # Outer join Chem & Bio (known to have 100% timestamp alignment)
    aligned = pd.merge(c_sub, b_sub, on=['Station', 'sample_date'], how='outer')
    # Left join Physical (covers ~75% of sampling events)
    aligned = pd.merge(aligned, p_sub, on=['Station', 'sample_date'], how='left')

    # Sort chronologically by Station and Date
    aligned.sort_values(by=['Station', 'sample_date'], inplace=True)
    aligned.reset_index(drop=True, inplace=True)

    # 7. Add Station and River Metadata
    aligned['station_name'] = aligned['Station']
    aligned['clean_station_name'] = aligned['Station'].map(lambda s: STATION_METADATA.get(s, {}).get('clean_name', s))
    aligned['river'] = aligned['Station'].map(lambda s: STATION_METADATA.get(s, {}).get('river', 'Unknown'))
    aligned['waterbody_type'] = aligned['Station'].map(lambda s: STATION_METADATA.get(s, {}).get('waterbody_type', 'River'))
    aligned['station_role'] = aligned['Station'].map(lambda s: STATION_METADATA.get(s, {}).get('station_role', 'monitoring'))
    aligned['latitude'] = aligned['Station'].map(lambda s: STATION_METADATA.get(s, {}).get('latitude', np.nan))
    aligned['longitude'] = aligned['Station'].map(lambda s: STATION_METADATA.get(s, {}).get('longitude', np.nan))

    # 8. Add Completeness Indicators
    aligned['has_ph'] = ~aligned['ph'].isna()
    aligned['has_do'] = ~aligned['do_mg_l'].isna()
    aligned['has_bod'] = ~aligned['bod_mg_l'].isna()
    aligned['has_coliform'] = ~aligned['total_coliform_mpn_100ml'].isna()
    aligned['has_turbidity'] = ~aligned['turbidity_ntu'].isna()
    aligned['has_conductivity'] = ~aligned['conductivity_us_cm'].isna()

    # Full CPCB Class B completeness indicator
    aligned['is_cpcb_class_b_complete'] = (
        aligned['has_ph'] & aligned['has_do'] & aligned['has_bod'] & aligned['has_coliform']
    )

    # Save to CSV
    cols_order = [
        'station_name', 'clean_station_name', 'river', 'waterbody_type', 'station_role',
        'latitude', 'longitude', 'sample_date',
        'ph', 'do_mg_l', 'bod_mg_l', 'total_coliform_mpn_100ml', 'fecal_coliform_mpn_100ml',
        'turbidity_ntu', 'conductivity_us_cm', 'temperature_c', 'tds_mg_l', 'cod_mg_l', 'nitrate_mg_l',
        'is_cpcb_class_b_complete'
    ]
    aligned = aligned[[c for c in cols_order if c in aligned.columns]]
    aligned.to_csv(output_path, index=False)
    print(f"[OK] Aligned dataset successfully written to {output_path} ({len(aligned)} rows)")

    # Print Summary Report
    print("\n" + "=" * 60)
    print("CPCB ALIGNMENT SUMMARY REPORT")
    print("=" * 60)
    for st_name, meta in STATION_METADATA.items():
        st_df = aligned[aligned['station_name'] == st_name]
        total = len(st_df)
        comp = st_df['is_cpcb_class_b_complete'].sum()
        ph_cnt = st_df['ph'].count()
        do_cnt = st_df['do_mg_l'].count()
        bod_cnt = st_df['bod_mg_l'].count()
        tc_cnt = st_df['total_coliform_mpn_100ml'].count()
        turb_cnt = st_df['turbidity_ntu'].count()
        cond_cnt = st_df['conductivity_us_cm'].count()
        print(f"Station: {meta['clean_name']} ({meta['river']})")
        print(f"  Total Sampling Events: {total}")
        print(f"  Complete CPCB Class B Samples: {comp} ({comp/total*100:.1f}%)")
        print(f"  Parameter Counts: pH={ph_cnt}, DO={do_cnt}, BOD={bod_cnt}, TotalColiform={tc_cnt}, Turbidity={turb_cnt}, EC={cond_cnt}")
        if total > 0:
            print(f"  Observation Span: {st_df['sample_date'].min()[:10]} to {st_df['sample_date'].max()[:10]}")
        print("-" * 50)

    return aligned


if __name__ == '__main__':
    align_cpcb_water_quality()
