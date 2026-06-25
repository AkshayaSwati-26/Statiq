import { useState, useEffect, useCallback } from 'react'
import { useSession } from '../hooks/useSession'
import axios from 'axios'

const API = axios.create({ baseURL: '', withCredentials: true })

const STATUS_COLOR = {
  200: 'var(--green)', 201: 'var(--green)',
  400: 'var(--amber)', 401: 'var(--amber)', 403: 'var(--amber)',
  404: 'var(--amber)', 422: 'var(--amber)',
  500: 'var(--red)',   502: 'var(--red)',   503: 'var(--red)',
}

function StatusBadge({ code }) {
  const c = STATUS_COLOR[code] || 'var(--text-3)'
  return (
    <span style={{
      padding: '2px 7px', fontSize: 10, fontWeight: 700,
      fontFamily: "'Space Mono',monospace", letterSpacing: '0.06em',
      border: `1px solid ${c}`, color: c, background: 'transparent',
    }}>
      {code || '—'}
    </span>
  )
}

function LabelInput({ label, value, onChange, type = 'text', placeholder }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div className="coord" style={{ fontSize: 9, color: 'var(--text-4)' }}>{label}</div>
      <input
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        style={{
          padding: '8px 10px', background: 'var(--ink-2)', border: '1px solid var(--rim-2)',
          color: 'var(--text-0)', fontFamily: "'Space Mono',monospace", fontSize: 12,
          outline: 'none', width: '100%', boxSizing: 'border-box',
        }}
        onFocus={e => e.target.style.borderColor = 'var(--cyan)'}
        onBlur={e => e.target.style.borderColor = 'var(--rim-2)'}
      />
    </div>
  )
}

export default function AdminAuditLogs() {
  const user = useSession(s => s.user)

  const [rows, setRows]           = useState([])
  const [total, setTotal]         = useState(0)
  const [pages, setPages]         = useState(1)
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState('')
  const [autoRefresh, setAutoRefresh] = useState(false)

  // Filters
  const [page, setPage]           = useState(1)
  const [pageSize]                = useState(50)
  const [endpoint, setEndpoint]   = useState('')
  const [statusCode, setStatusCode] = useState('')
  const [dateFrom, setDateFrom]   = useState('')
  const [dateTo, setDateTo]       = useState('')
  const [sortBy, setSortBy]       = useState('ts')
  const [sortDir, setSortDir]     = useState('desc')

  const fetchLogs = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const params = { page, page_size: pageSize, sort_by: sortBy, sort_dir: sortDir }
      if (endpoint)   params.endpoint   = endpoint
      if (statusCode) params.status_code = statusCode
      if (dateFrom)   params.date_from  = dateFrom
      if (dateTo)     params.date_to    = dateTo

      const r = await API.get('/v1/admin/audit-logs', { params })
      setRows(r.data.rows)
      setTotal(r.data.total)
      setPages(r.data.pages)
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to load audit logs')
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, endpoint, statusCode, dateFrom, dateTo, sortBy, sortDir])

  useEffect(() => { fetchLogs() }, [fetchLogs])

  // Auto-refresh every 30s
  useEffect(() => {
    if (!autoRefresh) return
    const iv = setInterval(fetchLogs, 30000)
    return () => clearInterval(iv)
  }, [autoRefresh, fetchLogs])

  if (!user || user.scope !== 'admin') {
    return (
      <div style={{ padding: 40, color: 'var(--red)', fontFamily: "'Space Mono',monospace" }}>
        ACCESS RESTRICTED — ADMIN ONLY
      </div>
    )
  }

  const handleExport = () => {
    if (!rows.length) return
    const cols = Object.keys(rows[0])
    const csv  = [cols.join(','), ...rows.map(r => cols.map(c => JSON.stringify(r[c] ?? '')).join(','))].join('\n')
    const blob  = new Blob([csv], { type: 'text/csv' })
    const url   = URL.createObjectURL(blob)
    const a     = document.createElement('a')
    a.href      = url
    a.download  = `audit_log_${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  const fmtTime = (iso) => {
    if (!iso) return '—'
    const d = new Date(iso)
    return d.toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', second: '2-digit' })
  }

  const toggleSort = (col) => {
    if (sortBy === col) setSortDir(d => d === 'desc' ? 'asc' : 'desc')
    else { setSortBy(col); setSortDir('desc') }
    setPage(1)
  }

  const SortIndicator = ({ col }) => (
    sortBy === col
      ? <span style={{ color: 'var(--cyan)', marginLeft: 4 }}>{sortDir === 'desc' ? '↓' : '↑'}</span>
      : <span style={{ color: 'var(--text-4)', marginLeft: 4 }}>↕</span>
  )

  return (
    <div style={{ maxWidth: 1400, display: 'flex', flexDirection: 'column', gap: 20 }}>

      {/* Header */}
      <div className="a-iris">
        <div className="coord" style={{ color: 'var(--amber)', marginBottom: 6 }}>
          ADM-02 / AUDIT LOG VIEWER
        </div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h1 style={{ fontFamily: "'Syne',sans-serif", fontWeight: 800, fontSize: 26, color: 'var(--text-0)', margin: 0 }}>
            AUDIT LOGS
          </h1>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span className="status-dot" style={{ background: autoRefresh ? 'var(--green)' : 'var(--text-4)', width: 8, height: 8, borderRadius: '50%' }}></span>
              <button
                onClick={() => setAutoRefresh(v => !v)}
                className="iris-btn iris-btn-ghost"
                style={{ fontSize: 11 }}
              >
                {autoRefresh ? 'AUTO-REFRESH ON' : 'AUTO-REFRESH OFF'}
              </button>
            </div>
            <button onClick={handleExport} className="iris-btn iris-btn-cyan" style={{ fontSize: 11 }} disabled={!rows.length}>
              ↓ EXPORT CSV
            </button>
          </div>
        </div>
        <div className="label-xs" style={{ marginTop: 4, color: 'var(--text-3)' }}>
          Tamper-evident audit log · TimescaleDB hypertable · Filtered + sorted · 7-year retention
        </div>
      </div>

      {/* Filters Panel */}
      <div className="panel a-iris d1" style={{ padding: 20 }}>
        <div className="label-sm" style={{ marginBottom: 14, color: 'var(--text-3)' }}>FILTERS</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(170px, 1fr))', gap: 12 }}>
          <LabelInput label="ENDPOINT" value={endpoint} onChange={e => { setEndpoint(e.target.value); setPage(1) }} placeholder="/v1/query/nl" />
          <LabelInput label="STATUS CODE" value={statusCode} onChange={e => { setStatusCode(e.target.value); setPage(1) }} placeholder="200, 403, 500..." type="number" />
          <LabelInput label="DATE FROM" value={dateFrom} onChange={e => { setDateFrom(e.target.value); setPage(1) }} type="date" />
          <LabelInput label="DATE TO" value={dateTo} onChange={e => { setDateTo(e.target.value); setPage(1) }} type="date" />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <div className="coord" style={{ fontSize: 9, color: 'var(--text-4)' }}>QUICK STATUS FILTER</div>
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
              {[['ALL', ''], ['2XX', '2XX'], ['4XX', '4XX'], ['5XX', '5XX']].map(([label, code]) => (
                <button
                  key={label}
                  onClick={() => { setStatusCode(code); setPage(1) }}
                  style={{
                    padding: '5px 8px', fontSize: 9, cursor: 'pointer',
                    fontFamily: "'Space Mono',monospace", letterSpacing: '0.06em',
                    background: statusCode === code ? 'var(--amber-glow)' : 'transparent',
                    border: `1px solid ${statusCode === code ? 'var(--amber)' : 'var(--rim-2)'}`,
                    color: statusCode === code ? 'var(--amber)' : 'var(--text-3)',
                  }}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        </div>
        <div style={{ marginTop: 12, display: 'flex', gap: 10 }}>
          <button onClick={() => { setEndpoint(''); setStatusCode(''); setDateFrom(''); setDateTo(''); setPage(1) }}
            className="iris-btn iris-btn-ghost" style={{ fontSize: 11 }}>
            CLEAR FILTERS
          </button>
          <button onClick={fetchLogs} className="iris-btn iris-btn-amber" style={{ fontSize: 11 }}>
            ↻ APPLY
          </button>
        </div>
      </div>

      {/* Stats bar */}
      <div style={{ display: 'flex', gap: 16 }}>
        {[
          { label: 'TOTAL RECORDS', value: total.toLocaleString(), color: 'var(--amber)' },
          { label: 'SHOWING', value: `${rows.length} / ${pageSize}`, color: 'var(--cyan)' },
          { label: 'PAGE', value: `${page} / ${pages}`, color: 'var(--green)' },
        ].map(s => (
          <div key={s.label} className="panel" style={{ padding: '10px 16px', flex: 1 }}>
            <div className="coord" style={{ fontSize: 9, color: 'var(--text-4)', marginBottom: 4 }}>{s.label}</div>
            <div style={{ fontFamily: "'DM Mono',monospace", fontSize: 18, fontWeight: 700, color: s.color }}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Log Table */}
      <div className="panel a-iris d2" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '12px 20px', borderBottom: '1px solid var(--rim)', display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 2, height: 14, background: 'var(--cyan)' }}></div>
          <span className="label-sm">API USAGE LOG</span>
          {loading && <span className="coord" style={{ color: 'var(--amber)', marginLeft: 'auto', fontSize: 10 }}>LOADING...</span>}
        </div>

        {error ? (
          <div style={{ padding: 24, color: 'var(--red)', fontFamily: "'Space Mono',monospace", fontSize: 12 }}>
            ERROR: {error}
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: 'var(--ink-3)' }}>
                  {[
                    { label: 'TIMESTAMP', col: 'ts' },
                    { label: 'ENDPOINT', col: 'endpoint' },
                    { label: 'USER/KEY', col: 'user' },
                    { label: 'STATUS', col: 'status_code' },
                    { label: 'ROWS', col: null },
                    { label: 'RESP MS', col: 'response_ms' },
                    { label: 'CACHE', col: null },
                    { label: 'SUPPRESSED', col: null },
                  ].map(h => (
                    <th
                      key={h.label}
                      onClick={() => h.col && toggleSort(h.col)}
                      style={{
                        padding: '10px 12px', textAlign: 'left',
                        fontFamily: "'Space Mono',monospace", fontSize: 9,
                        color: 'var(--text-3)', fontWeight: 700, letterSpacing: '0.08em',
                        borderBottom: '1px solid var(--rim)', whiteSpace: 'nowrap',
                        cursor: h.col ? 'pointer' : 'default',
                        userSelect: 'none',
                      }}
                    >
                      {h.label}{h.col && <SortIndicator col={h.col} />}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.length === 0 && !loading ? (
                  <tr>
                    <td colSpan={8} style={{ padding: 32, textAlign: 'center', color: 'var(--text-3)', fontFamily: "'Space Mono',monospace", fontSize: 11 }}>
                      NO AUDIT RECORDS FOUND
                    </td>
                  </tr>
                ) : rows.map((r, i) => (
                  <tr
                    key={i}
                    style={{ background: i % 2 === 0 ? 'var(--surface)' : 'var(--ink-2)', transition: 'background 0.15s' }}
                    onMouseEnter={e => e.currentTarget.style.background = 'rgba(34,211,238,0.03)'}
                    onMouseLeave={e => e.currentTarget.style.background = i % 2 === 0 ? 'var(--surface)' : 'var(--ink-2)'}
                  >
                    <td style={{ padding: '9px 12px', borderBottom: '1px solid var(--rim)', whiteSpace: 'nowrap' }}>
                      <span className="coord" style={{ fontSize: 10 }}>{fmtTime(r.ts)}</span>
                    </td>
                    <td style={{ padding: '9px 12px', borderBottom: '1px solid var(--rim)' }}>
                      <code style={{ fontFamily: "'DM Mono',monospace", fontSize: 11, color: 'var(--cyan)' }}>
                        {r.endpoint || '—'}
                      </code>
                    </td>
                    <td style={{ padding: '9px 12px', borderBottom: '1px solid var(--rim)' }}>
                      <span className="coord" style={{ fontSize: 10, color: 'var(--text-2)' }}>
                        {r.api_key_hash ? r.api_key_hash.slice(0, 12) + '…' : (r.user_ip_hash ? r.user_ip_hash.slice(0, 12) + '…' : '—')}
                      </span>
                    </td>
                    <td style={{ padding: '9px 12px', borderBottom: '1px solid var(--rim)' }}>
                      <StatusBadge code={r.status_code} />
                    </td>
                    <td style={{ padding: '9px 12px', borderBottom: '1px solid var(--rim)' }}>
                      <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 12, color: 'var(--text-1)' }}>
                        {r.rows_returned ?? '—'}
                      </span>
                    </td>
                    <td style={{ padding: '9px 12px', borderBottom: '1px solid var(--rim)' }}>
                      <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 12, color: r.response_ms > 1000 ? 'var(--amber)' : 'var(--text-1)' }}>
                        {r.response_ms != null ? `${r.response_ms}ms` : '—'}
                      </span>
                    </td>
                    <td style={{ padding: '9px 12px', borderBottom: '1px solid var(--rim)' }}>
                      <span style={{ fontSize: 11, color: r.cache_hit ? 'var(--green)' : 'var(--text-3)' }}>
                        {r.cache_hit ? '⬡ HIT' : '— MISS'}
                      </span>
                    </td>
                    <td style={{ padding: '9px 12px', borderBottom: '1px solid var(--rim)' }}>
                      {r.suppressed_cells > 0 ? (
                        <span style={{ color: 'var(--amber)', fontFamily: "'DM Mono',monospace", fontSize: 11 }}>
                          ⚠ {r.suppressed_cells}
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-4)', fontSize: 10 }}>—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination */}
      {pages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'center', gap: 6 }}>
          <button onClick={() => setPage(1)} disabled={page === 1} className="iris-btn iris-btn-ghost" style={{ fontSize: 11, padding: '6px 12px' }}>
            «
          </button>
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="iris-btn iris-btn-ghost" style={{ fontSize: 11, padding: '6px 12px' }}>
            ‹
          </button>
          {[...Array(Math.min(7, pages))].map((_, i) => {
            const pg = Math.max(1, Math.min(page - 3, pages - 6)) + i
            return (
              <button key={pg} onClick={() => setPage(pg)}
                className={`iris-btn ${pg === page ? 'iris-btn-amber' : 'iris-btn-ghost'}`}
                style={{ fontSize: 11, padding: '6px 12px', minWidth: 36 }}>
                {pg}
              </button>
            )
          })}
          <button onClick={() => setPage(p => Math.min(pages, p + 1))} disabled={page === pages} className="iris-btn iris-btn-ghost" style={{ fontSize: 11, padding: '6px 12px' }}>
            ›
          </button>
          <button onClick={() => setPage(pages)} disabled={page === pages} className="iris-btn iris-btn-ghost" style={{ fontSize: 11, padding: '6px 12px' }}>
            »
          </button>
        </div>
      )}
    </div>
  )
}
