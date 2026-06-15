"""
src/ingestion/metadata_generator.py
====================================
Extracts and compiles survey data dictionaries, schemas, profiles, 
sample values, relationships, and suggested queries for ingestion.
"""

import json
import logging
import pandas as pd
import numpy as np

log = logging.getLogger("statiq.ingestion.metadata")

DERIVED_COLUMN_DESCRIPTIONS = {
    'state_code': 'Official MoSPI two-digit state identifier code',
    'state_name': 'State name mapped from official state code',
    'sector': 'Sector code (1=Rural, 2=Urban)',
    'sector_label': 'Sector of residence (Rural / Urban)',
    'gender': 'Gender code (1=Male, 2=Female, 3=Transgender)',
    'gender_label': 'Gender of respondent (Male / Female / Transgender)',
    'education_code': 'General education attainment code',
    'education_label': 'Education attainment level mapped from official codes',
    'insurance_code': 'Health insurance coverage code',
    'insurance_label': 'Health insurance coverage category mapped from official codes',
    'usual_activity': 'Usual activity status code',
    'activity_label': 'Usual activity status category mapped from official codes',
    'employment_status': 'Employment status derived from usual activity (Employed / Unemployed / NLF)',
    'in_labour_force': 'Indicator flag: 1 if in labor force (employed or unemployed), 0 otherwise',
    'is_employed': 'Indicator flag: 1 if employed, 0 otherwise',
    'working_age': 'Indicator flag: 1 if age is between 15 and 59, 0 otherwise',
    'age_group': 'Binned age group of respondent (e.g. 0-4, 5-14, 15-24, 25-34, 35-44, 45-59, 60+)',
    'out_of_pocket': 'Calculated out-of-pocket medical expenditure (total expense - reimbursed)',
    'religion': 'Religion code identifier',
    'religion_label': 'Religion label mapped from official codes',
    'social_group': 'Social group category code',
    'social_label': 'Social group label mapped from official codes',
    'hh_type': 'Household type classification code',
    'hh_type_label': 'Household type description based on sector and primary occupation',
    'ailment_code': 'Nature of ailment code',
    'ailment_label': 'Nature of ailment category mapped from official codes',
    'institution_type': 'Type of medical institution code',
    'institution_label': 'Type of healthcare institution (Govt/Public, Private, Charitable)',
    'finance_source': 'Primary source of finance code for medical expenses',
    'finance_label': 'Primary source of finance for medical expenses (Savings, Borrowings, etc.)',
    'multiplier': 'Survey multiplier weight (for weighted estimates)',
    'census_count': 'Census population estimate weight',
    'survey_year': 'Reference year of the survey data',
    'round_no': 'MoSPI NSS survey round identifier',
    'survey_id': 'Unique identifier for the survey type',
    'ingested_at': 'Timestamp of ingestion into the database',
    'fsu_serial': 'First Stage Unit Serial Number (sampling identifier)',
    'hh_serial': 'Household Serial Number (sampling identifier)',
    'member_serial': 'Member Serial Number within the household',
    'case_serial': 'Hospitalisation case serial number'
}

RELATIONSHIPS = {
    'hces_health': [
        {
            'parent_table': 'hces_health_hh',
            'child_table': 'hces_health_members',
            'join_keys': ['fsu_serial', 'hh_serial'],
            'relationship_type': 'one-to-many',
            'description': 'Links a household to all its resident members.'
        },
        {
            'parent_table': 'hces_health_members',
            'child_table': 'hces_health_hosp',
            'join_keys': ['fsu_serial', 'hh_serial', 'member_serial'],
            'relationship_type': 'one-to-many',
            'description': 'Links a household member to their hospitalization records.'
        }
    ],
    'plfs': []
}

SUGGESTED_QUERIES = {
    'plfs': [
        {
            'title': 'Weighted Labour Force Participation Rate (LFPR) by State',
            'description': 'Calculates population-representative LFPR for working-age persons (15-59) across all states.',
            'sql_query': "SELECT state_name, ROUND(SUM(CASE WHEN in_labour_force = 1 THEN multiplier ELSE 0 END) / NULLIF(SUM(multiplier), 0) * 100, 2) AS lfpr_pct FROM plfs_person WHERE working_age = 1 GROUP BY state_name ORDER BY lfpr_pct DESC;"
        },
        {
            'title': 'Female Workforce Participation Rate (WPR) by Sector',
            'description': 'Calculates the rural vs urban employment rates for females.',
            'sql_query': "SELECT sector_label, ROUND(SUM(CASE WHEN is_employed = 1 THEN multiplier ELSE 0 END) / NULLIF(SUM(multiplier), 0) * 100, 2) AS wpr_pct FROM plfs_person WHERE gender_label = 'Female' AND working_age = 1 GROUP BY sector_label;"
        },
        {
            'title': 'Unemployment Rate by Education Level',
            'description': 'Calculates unemployment rate across different educational qualifications.',
            'sql_query': "SELECT education_label, ROUND(SUM(CASE WHEN employment_status = 'Unemployed' THEN multiplier ELSE 0 END) / NULLIF(SUM(CASE WHEN in_labour_force = 1 THEN multiplier ELSE 0 END), 0) * 100, 2) AS unemployment_rate FROM plfs_person WHERE working_age = 1 AND education_label IS NOT NULL GROUP BY education_label ORDER BY unemployment_rate DESC;"
        }
    ],
    'hces_health': [
        {
            'title': 'Average Out-of-Pocket Hospitalisation Expense by State',
            'description': 'Calculates the average out-of-pocket expense (total expense minus reimbursement) for hospitalized cases grouped by state.',
            'sql_query': "SELECT state_name, ROUND(AVG(out_of_pocket), 2) AS avg_out_of_pocket_rs, COUNT(*) AS sample_n FROM hces_health_hosp GROUP BY state_name ORDER BY avg_out_of_pocket_rs DESC;"
        },
        {
            'title': 'Hospitalisation Rate by Gender and Sector',
            'description': 'Calculates the percentage of members hospitalized in the last 365 days, binned by gender and rural/urban sector.',
            'sql_query': "SELECT sector_label, gender_label, ROUND(SUM(CASE WHEN hospitalised = 1 THEN multiplier ELSE 0 END) / NULLIF(SUM(multiplier), 0) * 100, 2) AS hosp_rate_pct FROM hces_health_members GROUP BY sector_label, gender_label;"
        },
        {
            'title': 'Distribution of Hospitalisations by Institution Type',
            'description': 'Shows the percentage of hospitalisations that occurred in public vs private hospitals.',
            'sql_query': "SELECT institution_label, COUNT(*) AS case_count, ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER () * 100, 2) AS share_pct FROM hces_health_hosp WHERE institution_label IS NOT NULL GROUP BY institution_label;"
        }
    ]
}


def extract_column_metadata(survey_id: str, table_name: str, df: pd.DataFrame, layout_spec: dict = None) -> list:
    """Extract column definitions, data types, descriptions, and privacy sensitivity flags."""
    records = []
    
    # Map layout fields by name for easy lookup
    layout_map = {}
    if layout_spec and 'fields' in layout_spec:
        for f in layout_spec['fields']:
            layout_map[f['name'].lower()] = f

    # Handle standard COLUMN_MAPPING renames from postgres_client.py
    COLUMN_MAPPING_INV = {
        'state_code': 'st',
        'sector': 'sec',
        'fsu_serial': 'fsu',
        'hh_serial': 'hhd',
        'multiplier': 'mult',
        'hh_size': 'hhsz',
        'religion': 'b5i2',
        'social_group': 'b5i3',
        'hh_type': 'b5i4',
        'ins_premium': 'b5i6',
        'member_serial': 'b3c1',
        'gender': 'b3c4',
        'age': 'b3c5',
        'education_code': 'b3c7',
        'hospitalised': 'b3c14',
        'chronic_ailment': 'b3c10',
        'ailment_15d': 'b3c11',
        'insurance_code': 'b3c17',
        'vaccine_received': 'b3c16',
        'ailment_code': 'b6i5',
        'institution_type': 'b6i7',
        'stay_days': 'b6i12',
        'total_medical': 'b7i12',
        'total_expense': 'b7i15',
        'reimbursed': 'b7i16',
        'finance_source': 'b7i17',
        'district_code': 'district',
        'round_no': 'round',
    }

    for col in df.columns:
        col_lower = col.lower()
        
        # Determine Data Type
        dtype_str = str(df[col].dtype)
        if 'int' in dtype_str:
            data_type = 'integer'
        elif 'float' in dtype_str or 'num' in dtype_str:
            data_type = 'numeric'
        else:
            data_type = 'varchar'

        # Fetch Description
        description = DERIVED_COLUMN_DESCRIPTIONS.get(col_lower)
        if not description:
            # Check layout using mapped original names or renamed names
            orig_name = COLUMN_MAPPING_INV.get(col_lower, col_lower)
            f_spec = layout_map.get(orig_name) or layout_map.get(col_lower)
            if f_spec:
                description = f_spec.get('remarks') or f_spec.get('full_name')
                
        if not description:
            description = f"Column {col} from raw layout specs"

        # Determine if sensitive (PII)
        is_sensitive = col_lower in ('fsu_serial', 'hh_serial', 'fsu', 'hhd', 'user_ip_hash', 'api_key_hash')

        records.append({
            'survey_id': survey_id,
            'table_name': table_name,
            'column_name': col,
            'data_type': data_type,
            'description': description.strip() if description else '',
            'is_sensitive': is_sensitive
        })
        
    return records


def extract_dictionary_metadata(survey_id: str, codebook: dict) -> list:
    """Compile dictionary codes and mapping definitions."""
    records = []
    
    # 1. Add Excel codebook translations
    for var_name, codes in codebook.items():
        for code, desc in codes.items():
            records.append({
                'survey_id': survey_id,
                'variable_name': var_name.lower(),
                'code': str(code).strip(),
                'code_description': str(desc).strip()
            })

    # 2. Add static mappings from transforms.py
    from ingestion.transforms import (STATE_CODES, SECTOR_MAP, GENDER_MAP, MARITAL_MAP, 
                                    RELIGION_MAP, SOCIAL_MAP, EDUCATION_MAP, INSURANCE_MAP, 
                                    AILMENT_MAP, PLFS_ACTIVITY_MAP, PLFS_EMPLOYMENT_MAP)
    
    static_maps = {
        'state_code': STATE_CODES,
        'st': STATE_CODES,
        'sector': SECTOR_MAP,
        'sec': SECTOR_MAP,
        'gender': GENDER_MAP,
        'b3c4': GENDER_MAP,
        'marst': MARITAL_MAP,
        'marital_status': MARITAL_MAP,
        'religion': RELIGION_MAP,
        'b5i2': RELIGION_MAP,
        'social_group': SOCIAL_MAP,
        'b5i3': SOCIAL_MAP,
        'education_code': EDUCATION_MAP,
        'b3c7': EDUCATION_MAP,
        'insurance_code': INSURANCE_MAP,
        'b3c17': INSURANCE_MAP,
        'ailment_code': AILMENT_MAP,
        'b6i5': AILMENT_MAP,
        'b8i5': AILMENT_MAP,
        'usual_activity': PLFS_ACTIVITY_MAP,
        'employment_status': PLFS_EMPLOYMENT_MAP
    }

    for var, mapping in static_maps.items():
        # Only include if variable matches survey context
        # PLFS uses activity / employment; HCES uses religion / social / ailment / insurance
        is_plfs_var = var in ('usual_activity', 'employment_status')
        is_hces_var = var in ('religion', 'b5i2', 'social_group', 'b5i3', 'insurance_code', 'b3c17', 'ailment_code', 'b6i5', 'b8i5')
        
        if (survey_id == 'plfs' and is_hces_var) or (survey_id == 'hces_health' and is_plfs_var):
            continue

        for code, desc in mapping.items():
            # Check duplicates
            if not any(r['variable_name'] == var and r['code'] == str(code) for r in records):
                records.append({
                    'survey_id': survey_id,
                    'variable_name': var,
                    'code': str(code).strip(),
                    'code_description': str(desc).strip()
                })

    return records


def generate_relationship_metadata(survey_id: str) -> list:
    """Generate explicit table relationships and joint paths."""
    records = []
    rel_list = RELATIONSHIPS.get(survey_id, [])
    for r in rel_list:
        records.append({
            'survey_id': survey_id,
            'parent_table': r['parent_table'],
            'child_table': r['child_table'],
            'join_keys': r['join_keys'],
            'relationship_type': r['relationship_type'],
            'description': r['description']
        })
    return records


def generate_suggested_queries(survey_id: str) -> list:
    """Load pre-computed suggested template SQL queries."""
    records = []
    queries = SUGGESTED_QUERIES.get(survey_id, [])
    for q in queries:
        records.append({
            'survey_id': survey_id,
            'title': q['title'],
            'description': q['description'],
            'sql_query': q['sql_query']
        })
    return records


def generate_sample_values(survey_id: str, table_name: str, df: pd.DataFrame) -> list:
    """Extract sample categorical values from columns with low cardinality."""
    records = []
    
    for col in df.columns:
        col_lower = col.lower()
        # Skip numeric/PII columns
        if col_lower in ('fsu_serial', 'hh_serial', 'member_serial', 'multiplier', 'census_count', 'mult'):
            continue
            
        # Get unique count
        try:
            unique_vals = df[col].dropna().unique()
            cardinality = len(unique_vals)
        except Exception:
            continue

        # If it acts like a label, code, or categorical variable (1 to 60 unique options)
        if 1 <= cardinality <= 60:
            samples = [str(x).strip() for x in unique_vals[:20]]
            records.append({
                'survey_id': survey_id,
                'table_name': table_name,
                'column_name': col,
                'sample_values': samples
            })
            
    return records


def generate_dataset_profile(survey_id: str, table_name: str, df: pd.DataFrame) -> list:
    """Profile data dimensions, completeness, and basic statistics."""
    row_count = len(df)
    column_count = len(df.columns)
    missing_values = int(df.isna().sum().sum())
    
    # Compile statistics per column
    col_profiles = {}
    for col in df.columns:
        col_lower = col.lower()
        null_count = int(df[col].isna().sum())
        completeness = round((1 - (null_count / max(row_count, 1))) * 100, 2)
        
        dtype_str = str(df[col].dtype)
        col_meta = {
            'completeness_pct': completeness,
            'null_count': null_count,
            'type': dtype_str
        }
        
        if 'int' in dtype_str or 'float' in dtype_str or 'num' in dtype_str:
            numeric_series = pd.to_numeric(df[col], errors='coerce').dropna()
            if not numeric_series.empty:
                col_meta.update({
                    'min': float(numeric_series.min()),
                    'max': float(numeric_series.max()),
                    'mean': float(numeric_series.mean())
                })
        else:
            try:
                col_meta['unique_count'] = int(df[col].nunique())
            except Exception:
                pass
                
        col_profiles[col] = col_meta

    profile_data = {
        'columns': col_profiles,
        'summary': {
            'row_count': row_count,
            'column_count': column_count,
            'missing_values': missing_values,
            'completeness_overall_pct': round((1 - (missing_values / max(row_count * column_count, 1))) * 100, 2)
        }
    }
    
    return [{
        'survey_id': survey_id,
        'table_name': table_name,
        'row_count': row_count,
        'column_count': column_count,
        'missing_values': missing_values,
        'profile_data': profile_data
    }]
