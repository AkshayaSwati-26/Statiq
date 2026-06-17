import axios from 'axios'
import {
  USE_MOCK_UPLOAD, USE_MOCK_QUERY,
  MOCK_UPLOAD, MOCK_HCES_UPLOAD, MOCK_QUERY_RESULT
} from '../utils/mockData'
import { getErrorMessage } from '../utils/errors'

const BASE = 'http://localhost:8000'
const wait = (ms) => new Promise(r => setTimeout(r, ms))

// Axios instance with cookie credentials (backend uses HttpOnly cookies for auth)
const api = axios.create({
  baseURL: BASE,
  withCredentials: true,   // send HttpOnly cookies automatically
})

// ── Dataset Upload ────────────────────────────────────────────────────────────

export const uploadDataset = async (file) => {
  if (USE_MOCK_UPLOAD) {
    await wait(1200)
    if (file.name.toLowerCase().includes('hces')) return MOCK_HCES_UPLOAD
    return MOCK_UPLOAD
  }

  const form = new FormData()
  form.append('file', file)

  try {
    const res = await api.post('/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return res.data
  } catch (err) {
    throw new Error(getErrorMessage(err, 'Upload failed'))
  }
}

// ── NL Query ─────────────────────────────────────────────────────────────────

export const runNLQuery = async (sessionId, query) => {
  if (USE_MOCK_QUERY) { await wait(1400); return MOCK_QUERY_RESULT }
  const res = await api.post('/v1/query/nl', {
    session_id: sessionId,
    question: query,
    language: 'en',
  })
  return res.data
}

// ── Builder Query ─────────────────────────────────────────────────────────────

export const runBuilderQuery = async (sessionId, filters) => {
  if (USE_MOCK_QUERY) { await wait(1000); return MOCK_QUERY_RESULT }
  const res = await api.post('/v1/query/builder', {
    session_id: sessionId,
    filters,
  })
  return res.data
}