# scripts/seed_postgres_mock.py
import os
import sys
import numpy as np
import pandas as pd
from sqlalchemy import text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from db.postgres_client import StatIQDB

STATE_NAMES = {
    "1": "Jammu & Kashmir", "2": "Himachal Pradesh", "3": "Punjab", "4": "Chandigarh",
    "5": "Uttarakhand", "6": "Haryana", "7": "Delhi", "8": "Rajasthan",
    "9": "Uttar Pradesh", "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh",
    "13": "Nagaland", "14": "Manipur", "15": "Mizoram", "16": "Tripura",
    "17": "Meghalaya", "18": "Assam", "19": "West Bengal", "20": "Jharkhand",
    "21": "Odisha", "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
    "25": "Daman & Diu", "26": "Dadra & Nagar Haveli", "27": "Maharashtra", "28": "Andhra Pradesh",
    "29": "Karnataka", "30": "Goa", "31": "Lakshadweep", "32": "Kerala",
    "33": "Tamil Nadu", "34": "Puducherry", "35": "Andaman & Nicobar"
}

np.random.seed(42)
N = 5000  # plfs rows
N_HH = 2000 # hces hh rows
N_MEM = 5000 # hces member rows

activity_codes   = [11, 12, 21, 31, 41, 51, 61, 71, 81, 82]
activity_weights = [0.30, 0.20, 0.15, 0.05, 0.05, 0.05, 0.05, 0.07, 0.05, 0.03]

print("Generating mock data...")

# ── 1. PLFS PERSON ──
plfs_years = np.random.choice([2021, 2022, 2023], N)
plfs_states = np.random.choice(list(STATE_NAMES.keys()), N)
plfs_sectors = np.random.choice([1, 2], N, p=[0.65, 0.35])
plfs_ages = np.random.randint(5, 80, N)
plfs_genders = np.random.choice([1, 2], N, p=[0.51, 0.49])
plfs_activities = np.random.choice(activity_codes, N, p=activity_weights)
plfs_multipliers = np.random.uniform(500, 5000, N)

plfs_df = pd.DataFrame({
    "state_code": plfs_states,
    "state_name": [STATE_NAMES[s] for s in plfs_states],
    "district_code": [f"{x:02d}" for x in np.random.randint(1, 10, N)],
    "sector": plfs_sectors,
    "sector_label": ['Rural' if s == 1 else 'Urban' for s in plfs_sectors],
    "fsu_serial": [f"{x:06d}" for x in np.random.randint(100000, 999999, N)],
    "hh_serial": [f"{x:02d}" for x in np.random.randint(1, 10, N)],
    "age": plfs_ages,
    "age_group": ['0-14' if a < 15 else '15-29' if a <= 29 else '30-59' if a <= 59 else '60+' for a in plfs_ages],
    "gender": plfs_genders,
    "gender_label": ['Male' if g == 1 else 'Female' for g in plfs_genders],
    "marital_status": np.random.choice([1, 2, 3, 4], N),
    "education_code": [f"{x:02d}" for x in np.random.randint(1, 10, N)],
    "education_label": np.random.choice(['Illiterate', 'Primary', 'Middle', 'Secondary', 'Higher Secondary', 'Graduate', 'Post Graduate'], N),
    "usual_activity": [str(a) for a in plfs_activities],
    "activity_label": ['Employed' if a <= 72 else 'Unemployed' if a <= 82 else 'Outside Labour Force' for a in plfs_activities],
    "employment_status": ['Employed' if a <= 72 else 'Unemployed' if a <= 82 else 'Outside Labour Force' for a in plfs_activities],
    "in_labour_force": [1 if a <= 82 else 0 for a in plfs_activities],
    "is_employed": [1 if a <= 72 else 0 for a in plfs_activities],
    "working_age": [1 if 15 <= a <= 59 else 0 for a in plfs_ages],
    "multiplier": plfs_multipliers,
    "census_count": plfs_multipliers * 10,
    "survey_year": ['2023-24' if y == 2023 else '2022-23' if y == 2022 else '2021-22' for y in plfs_years],
    "round_no": 80,
    "survey_id": "plfs"
})

# ── 2. HCES HOUSEHOLD ──
hces_years = np.random.choice([2022, 2023], N_HH)
hces_states = np.random.choice(list(STATE_NAMES.keys()), N_HH)
hces_sectors = np.random.choice([1, 2], N_HH, p=[0.65, 0.35])
hces_sizes = np.random.randint(1, 10, N_HH)
hces_exp = np.random.lognormal(mean=7.5, sigma=0.5, size=N_HH)
hces_mult = np.random.uniform(200, 3000, N_HH)
hces_religions = np.random.choice([1, 2, 3, 4, 5], N_HH)
hces_groups = np.random.choice([1, 2, 3, 4], N_HH)

hces_hh_df = pd.DataFrame({
    "state_code": hces_states,
    "state_name": [STATE_NAMES[s] for s in hces_states],
    "sector": hces_sectors,
    "sector_label": ['Rural' if s == 1 else 'Urban' for s in hces_sectors],
    "hh_serial": [f"{x:06d}" for x in np.random.randint(100000, 999999, N_HH)],
    "fsu_serial": [f"{x:06d}" for x in np.random.randint(100000, 999999, N_HH)],
    "sss": 1,
    "hh_size": hces_sizes,
    "religion": hces_religions,
    "religion_label": np.random.choice(['Hindu', 'Muslim', 'Christian', 'Sikh', 'Others'], N_HH),
    "social_group": hces_groups,
    "social_label": np.random.choice(['ST', 'SC', 'OBC', 'Others'], N_HH),
    "hh_type": 1,
    "hh_type_label": 'Self-employed',
    "umce": hces_exp,
    "ins_premium": np.random.uniform(0, 5000, N_HH),
    "multiplier": hces_mult,
    "nst": hces_mult * 10,
    "nstj": hces_mult * 5,
    "subdvsn": 1,
    "caph": 1,
    "smah": 1,
    "survey_year": ['2023-24' if y == 2023 else '2022-23' for y in hces_years],
    "survey_id": "hces_health"
})

# ── 3. HCES MEMBERS ──
hces_mem_states = np.random.choice(list(STATE_NAMES.keys()), N_MEM)
hces_mem_sectors = np.random.choice([1, 2], N_MEM, p=[0.65, 0.35])
hces_mem_genders = np.random.choice([1, 2], N_MEM)
hces_mem_ages = np.random.randint(5, 80, N_MEM)
hces_mem_mult = np.random.uniform(200, 3000, N_MEM)
hces_mem_years = np.random.choice([2022, 2023], N_MEM)
hces_mem_hosp = np.random.choice([0, 1], N_MEM, p=[0.95, 0.05])

hces_mem_df = pd.DataFrame({
    "state_code": hces_mem_states,
    "state_name": [STATE_NAMES[s] for s in hces_mem_states],
    "sector": hces_mem_sectors,
    "sector_label": ['Rural' if s == 1 else 'Urban' for s in hces_mem_sectors],
    "hh_serial": [f"{x:06d}" for x in np.random.randint(100000, 999999, N_MEM)],
    "fsu_serial": [f"{x:06d}" for x in np.random.randint(100000, 999999, N_MEM)],
    "sss": 1,
    "member_serial": [f"{x:03d}" for x in np.random.randint(1, 5, N_MEM)],
    "gender": hces_mem_genders,
    "gender_label": ['Male' if g == 1 else 'Female' for g in hces_mem_genders],
    "age": hces_mem_ages,
    "age_group": ['0-14' if a < 15 else '15-29' if a <= 29 else '30-59' if a <= 59 else '60+' for a in hces_mem_ages],
    "education_code": '01',
    "education_label": 'Primary',
    "hospitalised": hces_mem_hosp,
    "hosp_times": [1 if h == 1 else 0 for h in hces_mem_hosp],
    "chronic_ailment": np.random.choice([0, 1], N_MEM, p=[0.92, 0.08]),
    "ailment_15d": np.random.choice([0, 1], N_MEM, p=[0.90, 0.10]),
    "insurance_code": np.random.choice(['01', '19'], N_MEM),
    "insurance_label": np.random.choice(['AB-PMJAY', 'Not covered'], N_MEM),
    "vaccine_received": np.random.choice([0, 1, 2], N_MEM),
    "multiplier": hces_mem_mult,
    "nst": hces_mem_mult * 10,
    "nstj": hces_mem_mult * 5,
    "subdvsn": 1,
    "caph": 1,
    "smah": 1,
    "survey_year": ['2023-24' if y == 2023 else '2022-23' for y in hces_mem_years],
    "survey_id": "hces_health"
})

# ── 4. HCES HOSPITALISATIONS ──
hosp_mask = hces_mem_df["hospitalised"] == 1
hces_hosp_df = hces_mem_df[hosp_mask].copy()
hces_hosp_df = hces_hosp_df.drop(columns=["hospitalised", "hosp_times", "chronic_ailment", "ailment_15d", "insurance_code", "insurance_label", "vaccine_received"])
hces_hosp_df["ailment_code"] = "01"
hces_hosp_df["ailment_label"] = "General"
hces_hosp_df["institution_type"] = np.random.choice([1, 2], len(hces_hosp_df))
hces_hosp_df["institution_label"] = ['Public' if t == 1 else 'Private' for t in hces_hosp_df["institution_type"]]
hces_hosp_df["stay_days"] = np.random.randint(1, 15, len(hces_hosp_df))
hces_hosp_df["total_expense"] = np.random.uniform(1000, 50000, len(hces_hosp_df))
hces_hosp_df["reimbursed"] = np.random.uniform(0, hces_hosp_df["total_expense"])
hces_hosp_df["out_of_pocket"] = hces_hosp_df["total_expense"] - hces_hosp_df["reimbursed"]
hces_hosp_df["finance_source"] = 1
hces_hosp_df["finance_label"] = "Self"

print("Loading DataFrames into PostgreSQL...")
db = StatIQDB()
db.bulk_load(plfs_df, "plfs_person", if_exists="replace")
db.bulk_load(hces_hh_df, "hces_health_hh", if_exists="replace")
db.bulk_load(hces_mem_df, "hces_health_members", if_exists="replace")
db.bulk_load(hces_hosp_df, "hces_health_hosp", if_exists="replace")

print("Refreshing database views...")
db.refresh_views()

print("Loading suggested queries metadata...")
suggested_queries = [
    # English examples
    {
        "title": "Show unemployment rate among rural women in Tamil Nadu",
        "description": "Calculates unemployment rate for rural females in Tamil Nadu.",
        "sql_query": "SELECT state_name, sector_label, gender_label, ROUND(SUM(CASE WHEN employment_status = 'Unemployed' THEN multiplier ELSE 0 END) / NULLIF(SUM(CASE WHEN in_labour_force = 1 THEN multiplier ELSE 0 END), 0) * 100, 2) AS unemployment_rate FROM api_plfs_person WHERE state_name = 'Tamil Nadu' AND sector_label = 'Rural' AND gender_label = 'Female' GROUP BY state_name, sector_label, gender_label;"
    },
    {
        "title": "Compare employment trends across all states in 2024",
        "description": "Workforce Participation Rate (WPR) by state.",
        "sql_query": "SELECT state_name, survey_year, ROUND(SUM(CASE WHEN is_employed = 1 THEN multiplier ELSE 0 END) / NULLIF(SUM(multiplier), 0) * 100, 2) AS wpr_pct FROM api_plfs_person GROUP BY state_name, survey_year ORDER BY wpr_pct DESC;"
    },
    {
        "title": "Labour force participation by sector and gender",
        "description": "LFPR by sector and gender.",
        "sql_query": "SELECT sector_label, gender_label, ROUND(SUM(CASE WHEN in_labour_force = 1 THEN multiplier ELSE 0 END) / NULLIF(SUM(multiplier), 0) * 100, 2) AS lfpr_pct FROM api_plfs_person GROUP BY sector_label, gender_label;"
    },
    {
        "title": "What is the LFPR for urban males aged 15–29?",
        "description": "Urban male 15-29 LFPR.",
        "sql_query": "SELECT state_name, ROUND(SUM(CASE WHEN in_labour_force = 1 THEN multiplier ELSE 0 END) / NULLIF(SUM(multiplier), 0) * 100, 2) AS lfpr_pct FROM api_plfs_person WHERE sector_label = 'Urban' AND gender_label = 'Male' AND age BETWEEN 15 AND 29 GROUP BY state_name;"
    },
    {
        "title": "Show consumption expenditure trends 2020 to 2024",
        "description": "Average consumption expenditure by year.",
        "sql_query": "SELECT state_name, survey_year, ROUND(SUM(consumption_expenditure * multiplier) / NULLIF(SUM(multiplier), 0), 2) AS mpce_mean FROM hces_household GROUP BY state_name, survey_year ORDER BY survey_year;"
    },
    # Hindi examples
    {
        "title": "तमिलनाडु में ग्रामीण महिलाओं की बेरोजगारी दर दिखाएं",
        "description": "तमिलनाडु में ग्रामीण महिलाओं की बेरोजगारी दर।",
        "sql_query": "SELECT state_name, sector_label, gender_label, ROUND(SUM(CASE WHEN employment_status = 'Unemployed' THEN multiplier ELSE 0 END) / NULLIF(SUM(CASE WHEN in_labour_force = 1 THEN multiplier ELSE 0 END), 0) * 100, 2) AS unemployment_rate FROM api_plfs_person WHERE state_name = 'Tamil Nadu' AND sector_label = 'Rural' AND gender_label = 'Female' GROUP BY state_name, sector_label, gender_label;"
    },
    {
        "title": "2024 में सभी राज्यों में रोजगार के रुझान की तुलना करें",
        "description": "सभी राज्यों में कार्यबल भागीदारी दर।",
        "sql_query": "SELECT state_name, survey_year, ROUND(SUM(CASE WHEN is_employed = 1 THEN multiplier ELSE 0 END) / NULLIF(SUM(multiplier), 0) * 100, 2) AS wpr_pct FROM api_plfs_person GROUP BY state_name, survey_year ORDER BY wpr_pct DESC;"
    },
    {
        "title": "क्षेत्र और लिंग के अनुसार श्रम बल भागीदारी दिखाएं",
        "description": "लिंग और क्षेत्र के आधार पर श्रम बल भागीदारी दर।",
        "sql_query": "SELECT sector_label, gender_label, ROUND(SUM(CASE WHEN in_labour_force = 1 THEN multiplier ELSE 0 END) / NULLIF(SUM(multiplier), 0) * 100, 2) AS lfpr_pct FROM api_plfs_person GROUP BY sector_label, gender_label;"
    },
    {
        "title": "15-29 वर्ष के शहरी पुरुषों के लिए LFPR क्या है?",
        "description": "युवा शहरी पुरुषों के लिए LFPR।",
        "sql_query": "SELECT state_name, ROUND(SUM(CASE WHEN in_labour_force = 1 THEN multiplier ELSE 0 END) / NULLIF(SUM(multiplier), 0) * 100, 2) AS lfpr_pct FROM api_plfs_person WHERE sector_label = 'Urban' AND gender_label = 'Male' AND age BETWEEN 15 AND 29 GROUP BY state_name;"
    },
    {
        "title": "राज्यों में बेरोजगारी दर की तुलना करें",
        "description": "राज्यों के बीच बेरोजगारी दर की तुलना।",
        "sql_query": "SELECT state_name, ROUND(SUM(CASE WHEN employment_status = 'Unemployed' THEN multiplier ELSE 0 END) / NULLIF(SUM(CASE WHEN in_labour_force = 1 THEN multiplier ELSE 0 END), 0) * 100, 2) AS unemployment_rate FROM api_plfs_person GROUP BY state_name ORDER BY unemployment_rate DESC;"
    }
]

# Write directly to survey_metadata_suggested_queries table
with db.engine.connect() as conn:
    conn.execute(text("DELETE FROM survey_metadata_suggested_queries"))
    for q in suggested_queries:
        conn.execute(text("""
            INSERT INTO survey_metadata_suggested_queries (survey_id, title, description, sql_query)
            VALUES ('plfs', :title, :description, :sql_query)
        """), q)
        conn.execute(text("""
            INSERT INTO survey_metadata_suggested_queries (survey_id, title, description, sql_query)
            VALUES ('hces_health', :title, :description, :sql_query)
        """), q)
    conn.commit()

print("Mock seeding successful!")
