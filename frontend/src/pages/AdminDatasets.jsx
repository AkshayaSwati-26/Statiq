import { useState, useEffect, useCallback } from 'react'
import { useSession } from '../hooks/useSession'
import { useNavigate, Link } from 'react-router-dom'
import axios from 'axios'

const API = axios.create({ baseURL: '', withCredentials: true })

function AccessBadge({ tier }) {
  const isPremium = tier === 'premium'
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      padding: '3px 10px', fontSize: 10, fontWeight: 700,
      fontFamily: "'Space Mono', monospace", letterSpacing: '0.08em',
      border: `1px solid ${isPremium ? 'rgba(34,211,238,0.4)' : 'rgba(16,185,129,0.4)'}`,
      color: isPremium ? 'var(--cyan)' : 'var(--green)',
      background: isPremium ? 'rgba(34,211,238,0.06)' : 'rgba(16,185,129,0.06)',
    }}>
      {isPremium ? '⬡ PREMIUM' : '◎ FREE'}
    </span>
  )
}

function FormatBadge({ fmt }) {
  const colors = { CSV: 'var(--amber)', XLSX: 'var(--green)', SAV: 'var(--cyan)', DTA: '#a78bfa', VIEW: 'var(--text-3)', ZIP: '#f472b6' }
  const c = colors[fmt?.toUpperCase()] || 'var(--text-3)'
  return (
    <span style={{
      padding: '2px 7px', fontSize: 9, fontWeight: 700,
      fontFamily: "'Space Mono', monospace", letterSpacing: '0.06em',
      border: `1px solid ${c}`, color: c, background: 'transparent',
    }}>
      {fmt?.toUpperCase() || '—'}
    </span>
  )
}

export default function AdminDatasets() {
  const navigate = useNavigate()
  const user = useSession(s => s.user)
  const [datasets, setDatasets] = useState([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState('')
  const [search, setSearch]     = useState('')
  const [tierFilter, setTierFilter] = useState('')
  const [toggling, setToggling] = useState({})
  const [deleting, setDeleting] = useState({})
  const [toast, setToast]       = useState(null)

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3000)
  }

  const fetchDatasets = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const params = {}
      if (tierFilter) params.tier = tierFilter
      if (search)     params.search = search
      const r = await API.get('/v1/admin/datasets', { params })
      setDatasets(r.data)
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to load datasets')
    } finally {
      setLoading(false)
    }
  }, [tierFilter, search])

  useEffect(() => { fetchDatasets() }, [fetchDatasets])

  if (!user || user.scope !== 'admin') {
    return (
      <div style={{ padding: 40, color: 'var(--red)', fontFamily: "'Space Mono',monospace" }}>
        ACCESS RESTRICTED — ADMIN ONLY
      </div>
    )
  }

  const handleToggleTier = async (dataset) => {
    const newTier = dataset.access_tier === 'free' ? 'premium' : 'free'
    setToggling(t => ({ ...t, [dataset.dataset_id]: true }))
    try {
      await API.patch(`/v1/admin/datasets/${dataset.dataset_id}/tier`, { access_tier: newTier })
      setDatasets(ds => ds.map(d =>
        d.dataset_id === dataset.dataset_id ? { ...d, access_tier: newTier } : d
      ))
      showToast(`"${dataset.original_name}" set to ${newTier.toUpperCase()}`)
    } catch (e) {
      showToast(e?.response?.data?.detail || 'Update failed', 'error')
    } finally {
      setToggling(t => ({ ...t, [dataset.dataset_id]: false }))
    }
  }

  const handleDelete = async (dataset) => {
    if (!window.confirm(`Soft-delete "${dataset.original_name}"? It will be hidden but data is preserved.`)) return
    setDeleting(d => ({ ...d, [dataset.dataset_id]: true }))
    try {
      await API.delete(`/v1/admin/datasets/${dataset.dataset_id}`)
      setDatasets(ds => ds.filter(d => d.dataset_id !== dataset.dataset_id))
      showToast(`"${dataset.original_name}" removed from registry`)
    } catch (e) {
      showToast(e?.response?.data?.detail || 'Delete failed', 'error')
    } finally {
      setDeleting(d => ({ ...d, [dataset.dataset_id]: false }))
    }
  }

  const formatRows = (n) => {
    if (!n && n !== 0) return '—'
    return String(n)
  }

  const fmtDate = (iso) => {
    if (!iso) return '—'
    return new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
  }

  return (
    <div style={{ maxWidth: 1200, display: 'flex', flexDirection: 'column', gap: 20 }}>

      {/* Toast */}
      {toast && (
        <div style={{
          position: 'fixed', bottom: 24, right: 24, zIndex: 9999,
          padding: '12px 20px', maxWidth: 380,
          background: toast.type === 'error' ? 'rgba(220,38,38,0.12)' : 'rgba(16,185,129,0.12)',
          border: `1px solid ${toast.type === 'error' ? 'var(--red)' : 'var(--green)'}`,
          fontFamily: "'Space Mono',monospace", fontSize: 12,
          color: toast.type === 'error' ? 'var(--red)' : 'var(--green)',
          animation: 'fadeIn 0.2s ease',
        }}>
          {toast.msg}
        </div>
      )}

      {/* Header */}
      <div className="a-iris">
        <div className="coord" style={{ color: 'var(--amber)', marginBottom: 6 }}>
          // ADM-01 / DATASET MANAGEMENT
        </div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h1 style={{ fontFamily: "'Syne',sans-serif", fontWeight: 800, fontSize: 26, color: 'var(--text-0)', margin: 0 }}>
            DATASET REGISTRY
          </h1>
          <button
            onClick={() => navigate('/ingest')}
            className="iris-btn iris-btn-amber"
            style={{ fontSize: 12 }}
          >
            + UPLOAD NEW DATASET
          </button>
        </div>
        <div className="label-xs" style={{ marginTop: 4, color: 'var(--text-3)' }}>
          Manage all uploaded datasets · Control access tiers · Enforce data governance
        </div>
      </div>

      {/* Filters */}
      <div className="panel a-iris d1" style={{ padding: '14px 20px' }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: 200, position: 'relative' }}>
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search datasets..."
              style={{
                width: '100%', padding: '9px 36px 9px 12px', boxSizing: 'border-box',
                background: 'var(--ink-2)', border: '1px solid var(--rim-2)',
                color: 'var(--text-0)', fontFamily: "'Space Mono',monospace", fontSize: 12,
                outline: 'none',
              }}
              onFocus={e => e.target.style.borderColor = 'var(--amber)'}
              onBlur={e => e.target.style.borderColor = 'var(--rim-2)'}
            />
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            {['', 'free', 'premium'].map(t => (
              <button
                key={t}
                onClick={() => setTierFilter(t)}
                className={`iris-btn ${tierFilter === t ? 'iris-btn-amber' : 'iris-btn-ghost'}`}
                style={{ fontSize: 11, padding: '7px 14px' }}
              >
                {t === '' ? 'ALL' : t.toUpperCase()}
              </button>
            ))}
          </div>
          <button onClick={fetchDatasets} className="iris-btn iris-btn-ghost" style={{ fontSize: 11 }}>
            ↻ REFRESH
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="panel a-iris d2" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '12px 20px', borderBottom: '1px solid var(--rim)', display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 2, height: 14, background: 'var(--amber)' }}></div>
          <span className="label-sm">REGISTERED DATASETS</span>
          <span className="tag tag-dim" style={{ marginLeft: 'auto', fontSize: 9 }}>
            {datasets.length} TOTAL
          </span>
        </div>

        {loading ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-3)', fontFamily: "'Space Mono',monospace", fontSize: 12 }}>
            LOADING REGISTRY...
          </div>
        ) : error ? (
          <div style={{ padding: 24, color: 'var(--red)', fontFamily: "'Space Mono',monospace", fontSize: 12 }}>
            // ERROR: {error}
          </div>
        ) : datasets.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-3)', fontFamily: "'Space Mono',monospace", fontSize: 12 }}>
            NO DATASETS FOUND
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: 'var(--ink-3)' }}>
                  {['DATASET NAME', 'TABLE ID', 'FORMAT', 'ROWS', 'UPLOADED BY', 'DATE', 'ACCESS TIER', 'ACTIONS'].map(h => (
                    <th key={h} style={{
                      padding: '10px 14px', textAlign: 'left',
                      fontFamily: "'Space Mono',monospace", fontSize: 9,
                      color: 'var(--text-3)', fontWeight: 700, letterSpacing: '0.08em',
                      borderBottom: '1px solid var(--rim)', whiteSpace: 'nowrap',
                    }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {datasets.map((ds, i) => (
                  <tr
                    key={ds.dataset_id}
                    style={{ background: i % 2 === 0 ? 'var(--surface)' : 'var(--ink-2)', transition: 'background 0.15s' }}
                    onMouseEnter={e => e.currentTarget.style.background = 'rgba(245,158,11,0.03)'}
                    onMouseLeave={e => e.currentTarget.style.background = i % 2 === 0 ? 'var(--surface)' : 'var(--ink-2)'}
                  >
                    <td style={{ padding: '12px 14px', borderBottom: '1px solid var(--rim)' }}>
                      <div style={{ fontFamily: "'Syne',sans-serif", fontWeight: 700, fontSize: 13, color: 'var(--text-0)', marginBottom: 2 }}>
                        {ds.original_name}
                      </div>
                      {ds.description && (
                        <div className="coord" style={{ fontSize: 9, color: 'var(--text-4)', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {ds.description}
                        </div>
                      )}
                    </td>
                    <td style={{ padding: '12px 14px', borderBottom: '1px solid var(--rim)' }}>
                      <code style={{ fontFamily: "'DM Mono',monospace", fontSize: 11, color: 'var(--cyan)', background: 'rgba(34,211,238,0.06)', padding: '2px 6px' }}>
                        {ds.table_name}
                      </code>
                    </td>
                    <td style={{ padding: '12px 14px', borderBottom: '1px solid var(--rim)' }}>
                      <FormatBadge fmt={ds.file_format} />
                    </td>
                    <td style={{ padding: '12px 14px', borderBottom: '1px solid var(--rim)' }}>
                      <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 13, color: 'var(--text-0)' }}>
                        {formatRows(ds.row_count)}
                      </span>
                    </td>
                    <td style={{ padding: '12px 14px', borderBottom: '1px solid var(--rim)' }}>
                      <span className="coord" style={{ fontSize: 10 }}>{ds.uploaded_by || '—'}</span>
                    </td>
                    <td style={{ padding: '12px 14px', borderBottom: '1px solid var(--rim)' }}>
                      <span className="coord" style={{ fontSize: 10 }}>{fmtDate(ds.uploaded_at)}</span>
                    </td>
                    <td style={{ padding: '12px 14px', borderBottom: '1px solid var(--rim)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <AccessBadge tier={ds.access_tier} />
                        <button
                          onClick={() => handleToggleTier(ds)}
                          disabled={toggling[ds.dataset_id]}
                          title={`Switch to ${ds.access_tier === 'free' ? 'PREMIUM' : 'FREE'}`}
                          style={{
                            width: 32, height: 17, borderRadius: 2, cursor: 'pointer',
                            background: ds.access_tier === 'premium' ? 'var(--cyan)' : 'var(--ink-3)',
                            border: `1px solid ${ds.access_tier === 'premium' ? 'var(--cyan)' : 'var(--rim-2)'}`,
                            position: 'relative', transition: 'all 0.2s', padding: 0, flexShrink: 0,
                            opacity: toggling[ds.dataset_id] ? 0.5 : 1,
                          }}
                        >
                          <div style={{
                            width: 11, height: 11, background: 'white', borderRadius: 1,
                            position: 'absolute', top: 2,
                            left: ds.access_tier === 'premium' ? 17 : 2, transition: 'left 0.2s',
                          }} />
                        </button>
                      </div>
                        <div style={{ display: 'flex', gap: 6, marginTop: 10 }}>
                          <button
                            onClick={() => navigate(`/datasets/${encodeURIComponent(ds.dataset_id)}/explore`)}
                            className="iris-btn iris-btn-ghost"
                            style={{ fontSize: 10, padding: '4px 8px', borderColor: 'rgba(34,211,238,0.3)', color: 'var(--cyan)' }}
                          >
                            🔍 EXPLORE
                          </button>
                          <button
                            onClick={() => {
                              // Load the actual dataset into the global session so QueryWorkspace can use it!
                              useSession.getState().setDataset({
                                session_id: `ses_${Date.now()}`,
                                dataset_id: ds.dataset_id,
                                file_name: ds.table_name,
                                file_format: ds.file_format,
                                row_count: ds.row_count,
                                column_count: ds.column_count,
                                columns: [],
                                preview_rows: [],
                                upload_time: ds.upload_time
                              })
                              navigate('/query')
                            }}
                            className="iris-btn iris-btn-ghost"
                            style={{ fontSize: 10, padding: '4px 8px' }}
                          >
                            OPEN IN WORKSPACE
                          </button>
                        </div>
                    </td>
                    <td style={{ padding: '12px 14px', borderBottom: '1px solid var(--rim)' }}>
                      <button
                        onClick={() => handleDelete(ds)}
                        disabled={deleting[ds.dataset_id]}
                        style={{
                          padding: '4px 10px', fontSize: 10, cursor: 'pointer',
                          background: 'transparent', border: '1px solid rgba(220,38,38,0.3)',
                          color: 'var(--red)', fontFamily: "'Space Mono',monospace",
                          letterSpacing: '0.06em', opacity: deleting[ds.dataset_id] ? 0.5 : 1,
                          transition: 'all 0.15s',
                        }}
                        onMouseEnter={e => { e.currentTarget.style.background = 'rgba(220,38,38,0.08)' }}
                        onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}
                      >
                        {deleting[ds.dataset_id] ? '...' : 'REMOVE'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Legend */}
      <div style={{ display: 'flex', gap: 20, padding: '12px 0', borderTop: '1px solid var(--rim)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <AccessBadge tier="free" />
          <span className="coord" style={{ fontSize: 9 }}>Accessible by all users (public + research + admin)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <AccessBadge tier="premium" />
          <span className="coord" style={{ fontSize: 9 }}>Accessible by research + admin scope only</span>
        </div>
      </div>
    </div>
  )
}
