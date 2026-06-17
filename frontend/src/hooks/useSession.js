import { create } from 'zustand'

const SESSION_TIMEOUT_MS = 30 * 60 * 1000 // 30 minutes

const getStoredUser = () => {
  try {
    const item = localStorage.getItem('mospi_user')
    return item ? JSON.parse(item) : null
  } catch {
    return null
  }
}

export const useSession = create((set, get) => ({
  user:         getStoredUser(),
  sessionId:    null,
  filename:     null,
  datasetReady: false,
  columns:      [],
  rowCount:     0,
  uploadTime:   null,
  datasetId:    null,
  fileType:     null,
  previewRows:  [],
  lastQuery:    '',
  lastResult:   null,
  isQuerying:   false,
  queryError:   null,
  queryHistory: [],
  _timeoutHandle: null,

  loginUser: (userData) => {
    localStorage.setItem('mospi_user', JSON.stringify(userData))
    set({ user: userData })
  },

  logoutUser: () => {
    localStorage.removeItem('mospi_user')
    get().clearDataset()
    set({ user: null })
  },

  upgradeToPremium: () => {
    const current = get().user
    if (current && current.scope === 'public') {
      const updated = {
        ...current,
        scope: 'research',
        isSimulatedPremium: true
      }
      localStorage.setItem('mospi_user', JSON.stringify(updated))
      set({ user: updated })
    }
  },

  setDataset: (data) => {
    const prev = get()._timeoutHandle
    if (prev) clearTimeout(prev)
    const handle = setTimeout(() => {
      get().clearDataset()
      alert('Session expired after 30 minutes of inactivity. Please re-upload your dataset.')
    }, SESSION_TIMEOUT_MS)
    set({
      sessionId:    data.session_id,
      filename:     data.filename,
      datasetReady: true,
      columns:      data.column_names || [],
      rowCount:     data.rows,
      uploadTime:   data.upload_time,
      datasetId:    data.dataset_id,
      fileType:     data.file_type,
      previewRows:  data.preview_rows || [],
      lastResult:   null,
      lastQuery:    '',
      _timeoutHandle: handle,
    })
  },

  clearDataset: () => {
    const h = get()._timeoutHandle
    if (h) clearTimeout(h)
    set({
      sessionId: null, filename: null, datasetReady: false,
      columns: [], rowCount: 0, lastResult: null,
      previewRows: [], _timeoutHandle: null,
    })
  },

  resetTimeout: () => {
    const prev = get()._timeoutHandle
    if (prev) clearTimeout(prev)
    if (!get().datasetReady) return
    const handle = setTimeout(() => {
      get().clearDataset()
      alert('Session expired. Please re-upload your dataset.')
    }, SESSION_TIMEOUT_MS)
    set({ _timeoutHandle: handle })
  },

  setQuerying: (val) => {
    get().resetTimeout()
    set({ isQuerying: val, queryError: null })
  },

  setResult: (result, query) => set((state) => ({
    lastResult:   result,
    lastQuery:    query,
    isQuerying:   false,
    queryHistory: [
      { id: Date.now(), query, result, time: new Date().toLocaleString() },
      ...state.queryHistory.slice(0, 19),
    ],
  })),

  setQueryError: (msg) => set({ queryError: msg, isQuerying: false }),
}))