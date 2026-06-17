// USE_MOCK controls:
//   USE_MOCK_UPLOAD  = false → real file upload hits the backend
//   USE_MOCK_QUERY   = true  → NL/builder queries still return mock data
//                             (set to false once Ollama/Claude is configured)
export const USE_MOCK        = false   // legacy alias — not used directly anymore
export const USE_MOCK_UPLOAD = false   // real upload endpoint
export const USE_MOCK_QUERY  = true    // mock NL/SQL queries

export const MOCK_UPLOAD = {
  session_id: 'sess_001',
  filename: 'PLFS_2024_Annual.csv',
  dataset_id: 'DS-2024-001',
  file_type: 'CSV',
  rows: 12450000,
  columns: 157,
  upload_time: '2024-01-15 10:32 AM',
  status: 'Ready',
  column_names: ['state','sector','gender','age_group',
    'employment_rate','unemployment_rate','lfpr','survey_year','multiplier'],
  preview_rows: [
    { state:'Tamil Nadu',  sector:'Rural', gender:'Female', employment_rate:42.8, unemployment_rate:12.4, survey_year:2024 },
    { state:'Karnataka',   sector:'Urban', gender:'Male',   employment_rate:67.3, unemployment_rate:8.1,  survey_year:2024 },
    { state:'Kerala',      sector:'Rural', gender:'Female', employment_rate:38.5, unemployment_rate:15.2, survey_year:2024 },
    { state:'Maharashtra', sector:'Urban', gender:'Female', employment_rate:35.2, unemployment_rate:18.6, survey_year:2024 },
    { state:'Bihar',       sector:'Rural', gender:'Male',   employment_rate:55.1, unemployment_rate:22.3, survey_year:2024 },
  ]
}

export const MOCK_HCES_UPLOAD = {
  session_id: 'sess_hces',
  filename: 'HCES_2023_Health_Members.csv',
  dataset_id: 'api_hces_members',
  file_type: 'CSV',
  rows: 489000,
  columns: 31,
  upload_time: '2024-02-10 11:15 AM',
  status: 'Ready',
  column_names: ['state_name', 'sector_label', 'gender_label', 'age', 'education_label', 'hospitalised', 'chronic_ailment', 'insurance_label', 'multiplier'],
  preview_rows: [
    { state_name: 'Tamil Nadu', sector_label: 'Rural', gender_label: 'Female', age: 34, hospitalised: 0, chronic_ailment: 0 },
    { state_name: 'Kerala', sector_label: 'Urban', gender_label: 'Male', age: 45, hospitalised: 1, chronic_ailment: 1 },
    { state_name: 'Delhi', sector_label: 'Urban', gender_label: 'Female', age: 28, hospitalised: 0, chronic_ailment: 0 }
  ]
}

export const MOCK_QUERY_RESULT = {
  indicator_name: 'Female Unemployment Rate — Rural Sector',
  result_value: '12.4%',
  dataset_used: 'PLFS_2024_Annual.csv',
  records_analyzed: 3420150,
  query_time_ms: 847,
  confidence_score: 96,
  sql: `SELECT state,\n  ROUND(\n    SUM(unemployed * multiplier) /\n    SUM(labour_force * multiplier) * 100\n  , 2) AS unemployment_rate\nFROM plfs_2024\nWHERE gender = 'Female'\n  AND sector = 'Rural'\nGROUP BY state\nORDER BY unemployment_rate`,
  data: [
    { name:'Tamil Nadu',    value: 12.4 },
    { name:'Kerala',        value: 15.2 },
    { name:'Karnataka',     value: 13.8 },
    { name:'Maharashtra',   value: 18.6 },
    { name:'Uttar Pradesh', value: 24.1 },
    { name:'Bihar',         value: 28.3 },
  ],
  explanation: 'The unemployment rate among rural women in Tamil Nadu is 12.4%. This is below the national average of 18.2% and represents a 2.1 percentage point improvement compared to the 2023 survey round. Tamil Nadu ranks 2nd best among major states.',
  formula: 'Unemployment Rate = (Unemployed Persons ÷ Total Labour Force) × 100',
  formula_note: 'All values weighted using survey multipliers to represent population estimates.',
  traceability: {
    dataset: 'PLFS 2024 Annual',
    state: 'Tamil Nadu',
    gender: 'Female',
    sector: 'Rural',
    year: '2024',
    aggregation: 'Weighted Average',
  },
  privacy_safe: true,
  privacy_message: 'All results based on aggregated data. No individual records exposed.',
}

export const MOCK_DASHBOARD_STATS = {
  total_datasets: 3,
  total_queries: 47,
  records_processed: '37.2M',
  recent_activity: [
    { action:'Dataset uploaded', detail:'PLFS_2024.csv',         time:'10 min ago'  },
    { action:'Query executed',   detail:'Female unemployment TN', time:'12 min ago'  },
    { action:'Result exported',  detail:'results.csv',            time:'25 min ago'  },
    { action:'Dataset uploaded', detail:'HCES_2023.csv',          time:'2 hours ago' },
  ]
}