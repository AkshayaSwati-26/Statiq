"""
src/ingestion/transforms.py
============================
Step 2 of ingestion: derive human-readable fields, age groups,
employment status, and survey weights from raw parsed DataFrames.

One transform function per survey level.
Each function takes a raw DataFrame → returns an enriched DataFrame.
"""

import pandas as pd
import numpy as np
import logging

log = logging.getLogger("statiq.ingestion.transforms")

# ── Reference tables ──────────────────────────────────────────
STATE_CODES = {
    '01':'Jammu & Kashmir',    '02':'Himachal Pradesh',
    '03':'Punjab',             '04':'Chandigarh',
    '05':'Uttarakhand',        '06':'Haryana',
    '07':'Delhi',              '08':'Rajasthan',
    '09':'Uttar Pradesh',      '10':'Bihar',
    '11':'Sikkim',             '12':'Arunachal Pradesh',
    '13':'Nagaland',           '14':'Manipur',
    '15':'Mizoram',            '16':'Tripura',
    '17':'Meghalaya',          '18':'Assam',
    '19':'West Bengal',        '20':'Jharkhand',
    '21':'Odisha',             '22':'Chhattisgarh',
    '23':'Madhya Pradesh',     '24':'Gujarat',
    '25':'D&NH & Daman & Diu', '27':'Maharashtra',
    '28':'Andhra Pradesh',     '29':'Karnataka',
    '30':'Goa',                '31':'Lakshadweep',
    '32':'Kerala',             '33':'Tamil Nadu',
    '34':'Puducherry',         '35':'Andaman & Nicobar',
    '36':'Telangana',          '37':'Ladakh',
}

SECTOR_MAP    = {'1': 'Rural', '2': 'Urban'}
GENDER_MAP    = {'1': 'Male',  '2': 'Female', '3': 'Transgender'}
MARITAL_MAP   = {'1': 'Never married', '2': 'Currently married',
                 '3': 'Widowed',       '4': 'Divorced/Separated'}
RELIGION_MAP  = {'1': 'Hindu', '2': 'Islam',  '3': 'Christian',
                 '4': 'Sikh',  '5': 'Jain',   '6': 'Buddhist',
                 '7': 'Zoroastrian', '9': 'Other'}
SOCIAL_MAP    = {'1': 'Scheduled Tribe', '2': 'Scheduled Caste',
                 '3': 'Other Backward Class', '9': 'Other'}

EDUCATION_MAP = {
    '01': 'Not literate',                 '02': 'Literate (non-formal)',
    '03': 'Below primary',                '04': 'Primary',
    '05': 'Upper primary',                '06': 'Secondary',
    '07': 'Higher secondary',             '08': 'Diploma (≤secondary)',
    '10': 'Diploma (higher secondary)',   '11': 'Diploma (graduation+)',
    '12': 'Graduate',                     '13': 'Postgraduate and above',
}

INSURANCE_MAP = {
    '01': 'AB-PMJAY',                    '02': 'State Health Insurance',
    '03': 'ESIS/ESIC',                   '04': 'CGHS/ECHS/Central Govt',
    '05': 'State Govt (employees)',      '06': 'PSU employer',
    '07': 'Other employer',              '10': 'Private commercial',
    '19': 'Not covered',
}

AILMENT_MAP = {
    '01':'Fever (consciousness loss)', '02':'Malaria',
    '03':'Diphtheria/Whooping cough',  '04':'Other fevers',
    '05':'Tuberculosis',               '06':'Filariasis',
    '07':'Tetanus',                    '08':'HIV/AIDS',
    '09':'Other STDs',                 '10':'Jaundice',
    '11':'Diarrhoea/Dysentery',        '12':'Worm infestation',
    '13':'Cancer',                     '14':'Anaemia',
    '15':'Bleeding disorders',         '16':'Sickle cell/Thalassemia',
    '17':'Diabetes',                   '18':'Under-nutrition',
    '19':'Thyroid disease',            '20':'Obesity/Endocrine',
    '21':'Mental retardation',         '22':'Mental disorders',
    '23':'Headache',                   '24':'Epilepsy',
    '25':'Muscle weakness',            '26':'Stroke/Hemiplegia',
    '27':'Memory loss',                '28':'Eye pain/Redness',
    '29':'Cataract',                   '30':'Glaucoma',
    '31':'Decreased vision',           '32':'Other eye disorders',
    '33':'Ear infection',              '34':'Hearing loss',
    '35':'Hypertension',               '36':'Heart disease',
    '37':'Acute respiratory infection','38':'Cough with sputum',
    '39':'Bronchial asthma',           '40':'Dental/Mouth disease',
    '41':'Gastric/Peptic ulcer',       '42':'Abdominal lump',
    '43':'GI bleeding',                '44':'Skin infection',
    '45':'Joint/Bone disease',         '46':'Back/Body ache',
    '47':'Urinary difficulty',         '48':'Pelvic pain',
    '49':'Menstrual disorder',         '50':'Pregnancy complications',
    '51':'Post-birth complications',   '52':'Newborn illness',
    '53':'Accidental injury',          '54':'Drowning',
    '55':'Burns',                      '56':'Poisoning',
    '57':'Self-harm',                  '58':'Assault',
    '59':'Animal contact',             '60':'Kidney failure',
    '61':'Other symptoms',             '62':'Cannot state symptoms',
    '87':'Normal delivery',            '88':'Caesarean delivery',
    '89':'Other delivery',
}

INSTITUTION_MAP  = {'1': 'Govt/Public hospital',
                    '2': 'Charitable/NGO/Trust hospital',
                    '3': 'Private hospital'}
FINANCE_MAP      = {'1': 'Household savings',  '2': 'Borrowings',
                    '3': 'Sale of assets',     '4': 'Friends/Relatives',
                    '9': 'Other sources'}

PLFS_ACTIVITY_MAP = {
    '11': 'Self-employed (own farm)',       '12': 'Self-employed (non-farm)',
    '21': 'Regular wage/salaried',          '22': 'Casual labour - public works',
    '31': 'Casual labour - other',          '41': 'Unemployed (prev worked)',
    '51': 'Unemployed (never worked)',      '61': 'Domestic duties only',
    '71': 'Domestic + free collection',    '81': 'Rentier/Pensioner',
    '91': 'Household duties',              '92': 'Student',
    '93': 'Retired',                       '94': 'Begging',
    '95': 'Others (NLF)',                  '97': 'Too young (<5yr)',
    '98': 'Disabled',                      '99': 'Others',
}
PLFS_EMPLOYMENT_MAP = {
    '11': 'Employed', '12': 'Employed', '21': 'Employed',
    '22': 'Employed', '31': 'Employed',
    '41': 'Unemployed', '51': 'Unemployed',
    '61': 'NLF', '71': 'NLF', '81': 'NLF', '91': 'NLF',
    '92': 'NLF', '93': 'NLF', '94': 'NLF', '95': 'NLF',
    '97': 'NLF', '98': 'NLF', '99': 'NLF',
}


# ─────────────────────────────────────────────────────────────
# SHARED UTILITY
# ─────────────────────────────────────────────────────────────

def compute_age_group(age_series: pd.Series) -> pd.Series:
    """Bin a numeric age Series into standard NSS age groups."""
    age = pd.to_numeric(age_series, errors='coerce')
    conditions = [
        age < 5,
        (age >= 5)  & (age < 15),
        (age >= 15) & (age < 25),
        (age >= 25) & (age < 35),
        (age >= 35) & (age < 45),
        (age >= 45) & (age < 60),
        age >= 60,
    ]
    choices = ['0-4', '5-14', '15-24', '25-34', '35-44', '45-59', '60+']
    return pd.Series(
        np.select(conditions, choices, default=pd.NA),
        index=age_series.index,
    )


def _safe_numeric(df, col):
    """Convert a column to numeric safely; return 0-filled if missing."""
    if col in df.columns:
        return pd.to_numeric(df[col], errors='coerce').fillna(0)
    return pd.Series(0.0, index=df.index)


# ─────────────────────────────────────────────────────────────
# HCES HEALTH TRANSFORMS
# ─────────────────────────────────────────────────────────────

def transform_hces_hh(
    df: pd.DataFrame, survey_year: str, survey_id: str
) -> pd.DataFrame:
    """
    Household-level transforms (Level 01).
    Derives: state_name, sector_label, religion_label, social_label,
             hh_type_label, and converts expenditure columns to numeric.
    """
    df = df.copy()
    df['state_name']     = df['st'].astype(str).str.strip().map(STATE_CODES)
    df['sector_label']   = df['sec'].astype(str).str.strip().map(SECTOR_MAP)
    df['religion_label'] = df['b5i2'].astype(str).str.strip().map(RELIGION_MAP)
    df['social_label']   = df['b5i3'].astype(str).str.strip().map(SOCIAL_MAP)

    # Household type depends on sector (rural vs urban codes differ)
    HH_TYPE_RURAL = {
        '1': 'Self-employed (agri)',    '2': 'Self-employed (non-agri)',
        '3': 'Regular wage (agri)',     '4': 'Regular wage (non-agri)',
        '5': 'Casual labour (agri)',    '6': 'Casual labour (non-agri)',
        '9': 'Other',
    }
    HH_TYPE_URBAN = {
        '1': 'Self-employed', '2': 'Regular wage/salaried',
        '3': 'Casual labour', '9': 'Other',
    }
    df['hh_type_label'] = df.apply(
        lambda r: HH_TYPE_RURAL.get(str(r.get('b5i4', '')).strip())
                  if str(r.get('sec', '')).strip() == '1'
                  else HH_TYPE_URBAN.get(str(r.get('b5i4', '')).strip()),
        axis=1,
    )

    for col in ['umce', 'mult', 'b5i6', 'b5i7', 'b5i8', 'b5i9', 'b5i10', 'b5i11',
                'nst', 'nstj', 'subdvsn', 'caph', 'smah', 'hhsz']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    df['survey_year'] = survey_year
    df['survey_id']   = survey_id
    return df


def transform_hces_members(
    df: pd.DataFrame, survey_year: str, survey_id: str
) -> pd.DataFrame:
    """
    Member-level transforms (Level 02).
    Derives: state_name, sector_label, gender_label, education_label,
             insurance_label, age_group.
    """
    df = df.copy()
    df['state_name']      = df['st'].astype(str).str.strip().map(STATE_CODES)
    df['sector_label']    = df['sec'].astype(str).str.strip().map(SECTOR_MAP)
    df['gender_label']    = df['b3c4'].astype(str).str.strip().map(GENDER_MAP)
    df['education_label'] = df['b3c7'].astype(str).str.strip().map(EDUCATION_MAP)
    df['insurance_label'] = df['b3c17'].astype(str).str.strip().map(INSURANCE_MAP)

    if 'b3c5' in df.columns:
        df['age_group'] = compute_age_group(df['b3c5'])

    for col in ['mult', 'nst', 'nstj', 'subdvsn', 'caph', 'smah', 'b3c10']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    df['survey_year'] = survey_year
    df['survey_id']   = survey_id
    return df


def transform_hces_hosp(
    df: pd.DataFrame, survey_year: str, survey_id: str
) -> pd.DataFrame:
    """
    Hospitalisation case transforms (Level 04).
    Derives: ailment_label, institution_label, finance_label, out_of_pocket.
    out_of_pocket = total_expense (b7i15) - reimbursed (b7i16)
    """
    df = df.copy()
    df['state_name']        = df['st'].astype(str).str.strip().map(STATE_CODES)
    df['sector_label']      = df['sec'].astype(str).str.strip().map(SECTOR_MAP)
    df['ailment_label']     = df['b6i5'].astype(str).str.strip().map(AILMENT_MAP)
    df['institution_label'] = df['b6i7'].astype(str).str.strip().map(INSTITUTION_MAP)
    df['finance_label']     = df['b7i17'].astype(str).str.strip().map(FINANCE_MAP)

    for col in ['b7i12', 'b7i15', 'b7i16', 'mult', 'nst', 'nstj',
                'subdvsn', 'caph', 'smah', 'b6i12']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    total = _safe_numeric(df, 'b7i15')
    reimb = _safe_numeric(df, 'b7i16')
    df['out_of_pocket'] = (total - reimb).round(2)

    df['survey_year'] = survey_year
    df['survey_id']   = survey_id
    return df


def transform_hces_outpatient(
    df: pd.DataFrame, survey_year: str, survey_id: str
) -> pd.DataFrame:
    """
    Outpatient ailment transforms (Level 05).
    Derives: ailment_label, out_of_pocket (b9i19 - b9i20).
    """
    df = df.copy()
    df['state_name']    = df['st'].astype(str).str.strip().map(STATE_CODES)
    df['sector_label']  = df['sec'].astype(str).str.strip().map(SECTOR_MAP)
    df['ailment_label'] = df['b8i5'].astype(str).str.strip().map(AILMENT_MAP)

    for col in ['b9i16', 'b9i19', 'b9i20', 'mult', 'nst', 'nstj']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    total = _safe_numeric(df, 'b9i19')
    reimb = _safe_numeric(df, 'b9i20')
    df['out_of_pocket'] = (total - reimb).round(2)

    df['survey_year'] = survey_year
    df['survey_id']   = survey_id
    return df


# ─────────────────────────────────────────────────────────────
# PLFS TRANSFORMS
# ─────────────────────────────────────────────────────────────

def transform_plfs_person(
    df: pd.DataFrame, survey_year: str
) -> pd.DataFrame:
    """
    PLFS person-level transforms.
    Derives: state_name, sector_label, gender_label, education_label,
             activity_label, employment_status, in_labour_force,
             is_employed, working_age, age_group.
    """
    df = df.copy()

    # State — try multiple possible column names
    st_col = next((c for c in ['st', 'State', 'state_code', 'State/Ut Code'] if c in df.columns), None)
    if st_col:
        df['state_code'] = df[st_col]
        df['state_name'] = df[st_col].astype(str).str.strip().map(STATE_CODES)

    # Sector
    sec_col = next((c for c in ['sec', 'Sector', 'sector'] if c in df.columns), None)
    if sec_col:
        df['sector'] = pd.to_numeric(df[sec_col], errors='coerce')
        df['sector_label'] = df[sec_col].astype(str).str.strip().map(SECTOR_MAP)

    # Gender
    g_col = next((c for c in ['b3c4', 'gender', 'Gender', 'sex', 'Sex'] if c in df.columns), None)
    if g_col:
        df['gender'] = pd.to_numeric(df[g_col], errors='coerce')
        df['gender_label'] = df[g_col].astype(str).str.strip().map(GENDER_MAP)

    # Education
    e_col = next((c for c in ['b3c7', 'education_code', 'Gen_Education', 'gedu_lvl'] if c in df.columns), None)
    if e_col:
        df['education_code'] = df[e_col]
        df['education_label'] = df[e_col].astype(str).str.strip().map(EDUCATION_MAP)

    # Usual activity / employment status
    act_col = next((c for c in ['usual_activity', 'Usual_Activity', 'b7c22', 'pas'] if c in df.columns), None)
    if act_col:
        df['usual_activity'] = df[act_col]
        df['activity_label']    = df[act_col].astype(str).str.strip().map(PLFS_ACTIVITY_MAP)
        df['employment_status'] = df[act_col].astype(str).str.strip().map(PLFS_EMPLOYMENT_MAP)
        df['in_labour_force']   = df['employment_status'].isin(['Employed', 'Unemployed']).astype(int)
        df['is_employed']       = (df['employment_status'] == 'Employed').astype(int)

    # Age
    age_col = next((c for c in ['age', 'Age', 'b3c5'] if c in df.columns), None)
    if age_col:
        age_num           = pd.to_numeric(df[age_col], errors='coerce')
        df['age']         = age_num
        df['age_group']   = compute_age_group(df[age_col])
        df['working_age'] = ((age_num >= 15) & (age_num <= 59)).astype(int)

    # Survey weight
    for col in ['multiplier', 'mult', 'census_count']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    if 'mult' in df.columns and 'multiplier' not in df.columns:
        df['multiplier'] = df['mult']

    # Other demographics
    if 'marst' in df.columns:
        df['marital_status'] = pd.to_numeric(df['marst'], errors='coerce')
    if 'dc' in df.columns:
        df['district_code'] = df['dc']
    if 'mfsu' in df.columns:
        df['fsu_serial'] = df['mfsu']
    if 'ssu' in df.columns:
        df['hh_serial'] = df['ssu']

    df['survey_year'] = survey_year
    df['survey_id']   = 'plfs'
    return df


# ─────────────────────────────────────────────────────────────
# WEIGHTED INDICATOR COMPUTATION
# ─────────────────────────────────────────────────────────────

def compute_weighted_lfpr(
    df: pd.DataFrame,
    group_cols: list = None,
) -> pd.DataFrame:
    """
    Compute Labour Force Participation Rate using survey multiplier.

    Formula (MoSPI methodology):
      LFPR = Σ(in_labour_force × multiplier) / Σ(multiplier) × 100
      where sum is over working-age persons (15–59) in each group.

    This is NOT a simple row count — it uses the survey weight
    to produce population-representative estimates.
    """
    if group_cols is None:
        group_cols = ['state_name', 'sector_label', 'survey_year']

    wa = df[df['working_age'] == 1].copy()
    wa['mult_num'] = pd.to_numeric(wa['multiplier'], errors='coerce').fillna(0)

    agg = wa.groupby(group_cols).apply(
        lambda g: pd.Series({
            'weighted_lf':    (g['in_labour_force'] * g['mult_num']).sum(),
            'weighted_emp':   (g['is_employed']     * g['mult_num']).sum(),
            'weighted_total': g['mult_num'].sum(),
            'sample_n':       len(g),
        })
    ).reset_index()

    agg['lfpr_pct'] = (
        agg['weighted_lf'] / agg['weighted_total'].replace(0, np.nan) * 100
    ).round(2)
    agg['wpr_pct'] = (
        agg['weighted_emp'] / agg['weighted_total'].replace(0, np.nan) * 100
    ).round(2)
    agg['unemp_rate_pct'] = (
        (agg['weighted_lf'] - agg['weighted_emp'])
        / agg['weighted_lf'].replace(0, np.nan) * 100
    ).round(2)
    return agg


def compute_weighted_mean(
    df: pd.DataFrame,
    value_col: str,
    weight_col: str = 'multiplier',
    group_cols: list = None,
) -> pd.DataFrame:
    """
    Compute weighted mean of any numeric column.
    Used for MPCE, out-of-pocket expenditure, stay duration, etc.

    weighted_mean = Σ(value × weight) / Σ(weight)
    """
    if group_cols is None:
        group_cols = ['state_name', 'sector_label', 'survey_year']

    df = df.copy()
    df['_val'] = pd.to_numeric(df[value_col], errors='coerce')
    df['_wt']  = pd.to_numeric(df[weight_col], errors='coerce').fillna(0)
    df['_wv']  = df['_val'] * df['_wt']

    agg = df.groupby(group_cols).agg(
        weighted_sum=('_wv', 'sum'),
        total_weight=('_wt', 'sum'),
        sample_n=('_val', 'count'),
    ).reset_index()

    agg[f'weighted_mean_{value_col}'] = (
        agg['weighted_sum'] / agg['total_weight'].replace(0, np.nan)
    ).round(2)
    return agg
