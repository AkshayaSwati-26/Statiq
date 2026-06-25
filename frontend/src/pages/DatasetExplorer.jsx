/**
 * DatasetExplorer.jsx
 * ==================
 * Dataset Overview & Metadata Explorer page.
 * Shown after upload OR navigated to from the dataset registry.
 * Displays: summary stats, entity description, column profiles, sample values.
 */

import { useState, useEffect } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { useSession } from '../hooks/useSession'
import axios from 'axios'

const API = axios.create({ baseURL: '', withCredentials: true })

// ── helpers ───────────────────────────────────────────────────────────────────

function dtBadgeColor(dtype) {
  if (!dtype) return 'var(--text-3)'
  const d = dtype.toLowerCase()
  if (d.includes('int') || d.includes('bigint') || d.includes('smallint')) return 'var(--cyan)'
  if (d.includes('float') || d.includes('numeric') || d.includes('decimal') || d.includes('double')) return '#a78bfa'
  if (d.includes('bool')) return 'var(--green)'
  if (d.includes('timestamp') || d.includes('date')) return 'var(--amber)'
  return 'var(--text-2)'
}

function humanDtype(dtype) {
  if (!dtype) return '—'
  const d = dtype.toLowerCase()
  if (d.includes('character varying') || d.includes('varchar')) return 'TEXT'
  if (d.includes('integer') || d.includes('int4')) return 'INT'
  if (d.includes('bigint') || d.includes('int8')) return 'BIGINT'
  if (d.includes('smallint') || d.includes('int2')) return 'SMALLINT'
  if (d.includes('numeric') || d.includes('decimal')) return 'NUMERIC'
  if (d.includes('double') || d.includes('float')) return 'FLOAT'
  if (d.includes('boolean') || d.includes('bool')) return 'BOOL'
  if (d.includes('timestamp')) return 'TIMESTAMP'
  if (d.includes('text')) return 'TEXT'
  return dtype.toUpperCase().slice(0, 10)
}

function pct(val, total) {
  if (!total) return 0
  return Math.round((val / total) * 100)
}

// ── sub-components ────────────────────────────────────────────────────────────

function StatCard({ label, value, accent = 'amber', code }) {
  const colors = { amber: 'var(--amber)', cyan: 'var(--cyan)', green: 'var(--green)', red: 'var(--red)', violet: '#a78bfa' }
  const c = colors[accent] || 'var(--text-1)'
  return (
    <div style={{
      background: 'var(--ink-2)', border: `1px solid var(--rim-2)`,
      padding: '14px 16px', position: 'relative', overflow: 'hidden',
    }}>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, background: `linear-gradient(90deg, ${c}, transparent)` }} />
      {code && <div className="coord" style={{ color: 'var(--text-4)', fontSize: 9, marginBottom: 6 }}>{code}</div>}
      <div style={{ fontFamily: 'var(--font-data)', fontSize: 26, fontWeight: 500, color: c, lineHeight: 1, marginBottom: 4 }}>{value}</div>
      <div className="coord" style={{ color: 'var(--text-3)', fontSize: 9 }}>{label}</div>
    </div>
  )
}

function ColumnRow({ col, idx, rowCount }) {
  const [open, setOpen] = useState(false)
  const nullPct = rowCount ? pct(col.null_count ?? 0, rowCount) : (col.null_pct ?? 0)
  const hasSamples = col.sample_values && col.sample_values.length > 0
  const isSensitive = col.is_sensitive

  return (
    <div style={{
      borderBottom: '1px solid var(--rim)',
      background: idx % 2 === 0 ? 'var(--surface)' : 'var(--ink-2)',
    }}>
      {/* Main row */}
      <div
        onClick={() => setOpen(o => !o)}
        style={{
          display: 'grid',
          gridTemplateColumns: '2fr 1fr 1fr 1fr 80px',
          gap: 12, padding: '11px 16px',
          cursor: 'pointer', alignItems: 'center',
          transition: 'background 0.15s',
        }}
        onMouseEnter={e => e.currentTarget.style.background = 'rgba(34,211,238,0.04)'}
        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
      >
        {/* Col name */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
          <span style={{
            fontFamily: "'DM Mono', monospace", fontSize: 12,
            color: isSensitive ? 'var(--red)' : 'var(--text-0)',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>{col.column_name}</span>
          {isSensitive && (
            <span style={{ fontSize: 8, padding: '1px 5px', border: '1px solid var(--red)', color: 'var(--red)', flexShrink: 0 }}>PII</span>
          )}
        </div>

        {/* Dtype badge */}
        <span style={{
          fontFamily: "'Space Mono', monospace", fontSize: 9, fontWeight: 700,
          color: dtBadgeColor(col.data_type),
          border: `1px solid ${dtBadgeColor(col.data_type)}30`,
          padding: '2px 6px', display: 'inline-block',
        }}>{humanDtype(col.data_type)}</span>

        {/* Null % bar */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
            <span className="coord" style={{ fontSize: 9, color: 'var(--text-4)' }}>NULL</span>
            <span className="coord" style={{ fontSize: 9, color: nullPct > 20 ? 'var(--red)' : 'var(--text-3)' }}>{nullPct}%</span>
          </div>
          <div style={{ height: 3, background: 'var(--ink-3)', borderRadius: 2 }}>
            <div style={{
              height: '100%', borderRadius: 2,
              width: `${nullPct}%`,
              background: nullPct > 20 ? 'var(--red)' : nullPct > 5 ? 'var(--amber)' : 'var(--green)',
              transition: 'width 0.3s',
            }} />
          </div>
        </div>

        {/* Description preview */}
        <div className="coord" style={{
          fontSize: 9, color: 'var(--text-3)',
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>
          {col.description || '—'}
        </div>

        {/* Expand chevron */}
        <div style={{ textAlign: 'right', color: 'var(--text-4)', fontSize: 10 }}>
          {hasSamples ? (open ? '▲' : '▼') : ''}
        </div>
      </div>

      {/* Expanded sample values */}
      {open && hasSamples && (
        <div style={{ padding: '10px 16px 14px 16px', background: 'rgba(34,211,238,0.02)', borderTop: '1px solid var(--rim)' }}>
          <div className="coord" style={{ fontSize: 9, color: 'var(--text-4)', marginBottom: 8 }}>SAMPLE VALUES</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {col.sample_values.slice(0, 20).map((v, i) => (
              <span key={i} style={{
                fontFamily: "'DM Mono', monospace", fontSize: 11,
                background: 'var(--ink-3)', border: '1px solid var(--rim-2)',
                padding: '2px 8px', color: 'var(--text-1)',
              }}>{String(v)}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── main component ────────────────────────────────────────────────────────────

export default function DatasetExplorer() {
  const { id } = useParams()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const user = useSession(s => s.user)
  // Also allow reading from session if navigated right after upload
  const sessionDatasetId = useSession(s => s.datasetId)

  const datasetId = id || sessionDatasetId || searchParams.get('id')

  const [meta, setMeta] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')

  useEffect(() => {
    if (!datasetId) {
      setError('No dataset ID provided.')
      setLoading(false)
      return
    }
    setLoading(true)
    setError('')
    API.get(`/v1/datasets/${encodeURIComponent(datasetId)}/meta`)
      .then(r => setMeta(r.data))
      .catch(e => setError(e?.response?.data?.detail || 'Failed to load dataset metadata.'))
      .finally(() => setLoading(false))
  }, [datasetId])

  const filteredCols = (meta?.columns || []).filter(c =>
    !search || c.column_name.toLowerCase().includes(search.toLowerCase()) ||
    (c.description || '').toLowerCase().includes(search.toLowerCase())
  )

  const profile = meta?.profile || {}
  const rowCount = profile.row_count || 0
  const colCount = meta?.columns?.length || 0
  const missingPct = rowCount && colCount
    ? pct(profile.missing_values || 0, rowCount * colCount)
    : 0

  const completeness = 100 - missingPct

  return (
    <div style={{ maxWidth: 1100, display: 'flex', flexDirection: 'column', gap: 20 }}>

      {/* Header */}
      <div className="a-iris">
        <div className="coord" style={{ color: 'var(--cyan)', marginBottom: 6 }}>
          // DATASET EXPLORER / {datasetId}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
          <h1 style={{ fontFamily: "'Syne', sans-serif", fontWeight: 800, fontSize: 24, color: 'var(--text-0)', margin: 0 }}>
            {meta?.original_name || datasetId}
          </h1>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={() => navigate(-1)} className="iris-btn iris-btn-ghost" style={{ fontSize: 11 }}>
              ← BACK
            </button>
            <button
              onClick={() => {
                useSession.getState().setDataset({
                  session_id: `ses_${Date.now()}`,
                  dataset_id: datasetId,
                  file_name: meta?.table_name || datasetId,
                  file_format: meta?.file_format || '',
                  row_count: rowCount,
                  column_count: colCount,
                  columns: [],
                  preview_rows: [],
                })
                navigate('/query')
              }}
              className="iris-btn iris-btn-primary"
              style={{ fontSize: 11 }}
            >
              OPEN IN QUERY WORKSPACE →
            </button>
          </div>
        </div>
        <div className="label-xs" style={{ marginTop: 4, color: 'var(--text-3)' }}>
          Table: <code style={{ color: 'var(--cyan)', fontFamily: "'DM Mono', monospace" }}>{meta?.table_name || '—'}</code>
          {meta?.uploaded_at && (
            <span style={{ marginLeft: 16 }}>
              Uploaded: {new Date(meta.uploaded_at).toLocaleString('en-IN')}
            </span>
          )}
        </div>
      </div>

      {loading && (
        <div style={{ padding: 60, textAlign: 'center', fontFamily: "'Space Mono', monospace", fontSize: 12, color: 'var(--text-3)' }}>
          LOADING METADATA...
        </div>
      )}

      {error && (
        <div style={{
          padding: '14px 18px', background: 'rgba(220,38,38,0.06)',
          border: '1px solid rgba(220,38,38,0.25)', borderLeft: '3px solid var(--red)',
          fontFamily: "'Space Mono', monospace", fontSize: 12, color: 'var(--red)',
        }}>
          // ERROR: {error}
        </div>
      )}

      {!loading && meta && (
        <>
          {/* Summary stat cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 10 }}>
            <StatCard code="STAT-01" label="TOTAL ROWS" value={rowCount.toLocaleString()} accent="amber" />
            <StatCard code="STAT-02" label="COLUMNS" value={colCount} accent="cyan" />
            <StatCard code="STAT-03" label="MISSING VALS" value={`${missingPct}%`} accent={missingPct > 10 ? 'red' : 'green'} />
            <StatCard code="STAT-04" label="COMPLETENESS" value={`${completeness}%`} accent="green" />
            <StatCard code="STAT-05" label="FORMAT" value={meta.file_format || 'VIEW'} accent="violet" />
          </div>

          {/* Entity & Description */}
          {meta.description && (
            <div className="panel a-iris d1" style={{ padding: 0, overflow: 'hidden' }}>
              <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--rim)', display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={{ width: 2, height: 14, background: 'var(--cyan)' }} />
                <span className="label-sm">ENTITY & SCHEMA DESCRIPTION</span>
                <span className="tag tag-cyan" style={{ marginLeft: 'auto', fontSize: 9 }}>AI GENERATED</span>
              </div>
              <div style={{ padding: '16px 20px' }}>
                <pre style={{
                  fontFamily: "'Space Mono', monospace", fontSize: 11,
                  color: 'var(--text-1)', lineHeight: 1.8, whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word', margin: 0,
                }}>
                  {meta.description}
                </pre>
              </div>
            </div>
          )}

          {/* Column Explorer */}
          <div className="panel a-iris d2" style={{ padding: 0, overflow: 'hidden' }}>
            <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--rim)', display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
              <div style={{ width: 2, height: 14, background: 'var(--amber)' }} />
              <span className="label-sm">COLUMN / ATTRIBUTE EXPLORER</span>
              <span className="tag tag-dim" style={{ fontSize: 9 }}>{colCount} COLUMNS</span>
              <div style={{ marginLeft: 'auto', position: 'relative' }}>
                <input
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  placeholder="Search columns..."
                  style={{
                    padding: '6px 12px', width: 200, boxSizing: 'border-box',
                    background: 'var(--ink-2)', border: '1px solid var(--rim-2)',
                    color: 'var(--text-0)', fontFamily: "'Space Mono', monospace", fontSize: 11, outline: 'none',
                  }}
                  onFocus={e => e.target.style.borderColor = 'var(--amber)'}
                  onBlur={e => e.target.style.borderColor = 'var(--rim-2)'}
                />
              </div>
            </div>

            {/* Table header */}
            <div style={{
              display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr 80px',
              gap: 12, padding: '8px 16px', background: 'var(--ink-3)',
              borderBottom: '1px solid var(--rim)',
            }}>
              {['COLUMN NAME', 'TYPE', 'NULL %', 'DESCRIPTION', ''].map(h => (
                <div key={h} className="coord" style={{ fontSize: 9, color: 'var(--text-4)', fontWeight: 700 }}>{h}</div>
              ))}
            </div>

            <div>
              {filteredCols.length === 0 ? (
                <div style={{ padding: 30, textAlign: 'center', fontFamily: "'Space Mono', monospace", fontSize: 12, color: 'var(--text-4)' }}>
                  No columns match your search.
                </div>
              ) : (
                filteredCols.map((col, i) => (
                  <ColumnRow key={col.column_name} col={col} idx={i} rowCount={rowCount} />
                ))
              )}
            </div>
          </div>

          {/* Data preview */}
          {meta.preview_rows && meta.preview_rows.length > 0 && (
            <div className="panel a-iris d3" style={{ padding: 0, overflow: 'hidden' }}>
              <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--rim)', display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={{ width: 2, height: 14, background: 'var(--green)' }} />
                <span className="label-sm">DATA PREVIEW</span>
                <span className="tag tag-dim" style={{ fontSize: 9, marginLeft: 'auto' }}>
                  TOP {meta.preview_rows.length} ROWS
                </span>
              </div>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                  <thead>
                    <tr style={{ background: 'var(--ink-3)' }}>
                      {Object.keys(meta.preview_rows[0] || {}).map(col => (
                        <th key={col} style={{
                          padding: '8px 12px', textAlign: 'left',
                          fontFamily: "'Space Mono', monospace", fontSize: 9,
                          color: 'var(--text-3)', fontWeight: 700, letterSpacing: '0.08em',
                          borderBottom: '1px solid var(--rim)', whiteSpace: 'nowrap',
                        }}>
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {meta.preview_rows.map((row, i) => (
                      <tr key={i} style={{ background: i % 2 === 0 ? 'var(--surface)' : 'var(--ink-2)' }}>
                        {Object.values(row).map((val, j) => (
                          <td key={j} style={{
                            padding: '8px 12px',
                            fontFamily: "'DM Mono', monospace", fontSize: 12,
                            color: 'var(--text-1)', borderBottom: '1px solid var(--rim)',
                            whiteSpace: 'nowrap',
                          }}>
                            {val === null ? <span style={{ color: 'var(--text-4)' }}>NULL</span> : String(val)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
