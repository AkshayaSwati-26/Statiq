import axios from 'axios'
import { USE_MOCK, MOCK_UPLOAD, MOCK_QUERY_RESULT } from '../utils/mockData'

const BASE = 'http://localhost:8000'
const wait = (ms) => new Promise(r => setTimeout(r, ms))

export const uploadDataset = async (file) => {
  if (USE_MOCK) { await wait(1200); return MOCK_UPLOAD }
  const form = new FormData()
  form.append('file', file)
  const res = await axios.post(`${BASE}/upload`, form)
  return res.data
}

export const runNLQuery = async (sessionId, query) => {
  if (USE_MOCK) { await wait(1400); return MOCK_QUERY_RESULT }
  const res = await axios.post(`${BASE}/query`, {
    session_id: sessionId,
    query
  })
  return res.data
}

export const runBuilderQuery = async (sessionId, filters) => {
  if (USE_MOCK) { await wait(1000); return MOCK_QUERY_RESULT }
  const res = await axios.post(`${BASE}/query/builder`, {
    session_id: sessionId,
    filters
  })
  return res.data
}