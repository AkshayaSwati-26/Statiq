import { useState, useEffect, useCallback } from 'react'
import { useSession } from '../hooks/useSession'
import axios from 'axios'

const API = axios.create({ baseURL: '', withCredentials: true })

export default function AdminSensitivity() {
  const user = useSession(s => s.user)

  const [columns, setColumns]     = useState([])
  const [settings, setSettings]   = useState([])
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState('')
  const [toast, setToast]         = useState(null)
  const [toggling, setToggling]   = useState({})
  const [tableFilter, setTableFilter] = useState('')
  const [showSensitive, setShowSensitive] = useState(null)

  // Cell size editor
  const [cellSize, setCellSize]   = useState('30')
  const [savingCell, setSavingCell] = useState(false)

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3500)
  }

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [colRes, setRes] = await Promise.all([
        API.get('/v1/admin/sensitive-columns'),
        API.get('/v1/admin/settings'),
      ])
      setColumns(colRes.data)
      setSettings(setRes.data)
      const cs = setRes.data.find(s => s.key === 'min_cell_size')
      if (cs) setCellSize(cs.value)
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  if (!user || user.scope !== 'admin') {
    return (
      <div style={{ padding: 40, color: 'var(--red)', fontFamily: "'Space Mono',monospace" }}>
        ACCESS RESTRICTED — ADMIN ONLY
      </div>
    )
  }

  const handleSaveCellSize = async () => {
    const val = parseInt(cellSize)
    if (isNaN(val) || val < 1 || val > 1000) {
      showToast('Cell size must be between 1 and 1000', 'error')
      return
    }
    setSavingCell(true)
    try {
      await API.patch('/v1/admin/settings', { key: 'min_cell_size', value: String(val) })
      showToast(`MIN_CELL_SIZE updated to ${val}`)
    } catch (e) {
      showToast(e?.response?.data?.detail || 'Failed to save', 'error')
    } finally {
      setSavingCell(false)
    }
  }

  const handleToggle = async (col, field) => {
    const newVal = !col[field]
    const label = field === 'is_sensitive' ? 'SENSITIVE' : 'MASKED'

    if (field === 'is_masked' && newVal) {
      if (!window.confirm(
        `⚠ MASKING "${col.column_name}" will strip it from ALL API responses for ALL users immediately.\n\nThis affects live queries. Continue?`
      )) return
    }

    setToggling(t => ({ ...t, [`${field}_${col.id}`]: true }))
    try {
      await API.patch(`/v1/admin/sensitive-columns/${col.id}`, { [field]: newVal })
      setColumns(cs => cs.map(c => c.id === col.id ? { ...c, [field]: newVal } : c))
      showToast(`"${col.column_name}" ${label} → ${newVal ? 'ON' : 'OFF'}`)
    } catch (e) {
      showToast(e?.response?.data?.detail || 'Update failed', 'error')
    } finally {
      setToggling(t => ({ ...t, [`${field}_${col.id}`]: false }))
    }
  }

  const tables = [...new Set(columns.map(c => c.table_name))].sort()
  const filteredCols = columns.filter(c => {
    if (tableFilter && c.table_name !== tableFilter) return false
    if (showSensitive === true  && !c.is_sensitive && !c.is_masked) return false
    if (showSensitive === false && (c.is_sensitive || c.is_masked)) return false
    return true
  })

  const Toggle = ({ val, onChange, disabled, color = 'var(--green)' }) => (
    <button
      onClick={onChange}
      disabled={disabled}
      style={{
        width: 36, height: 18, borderRadius: 2, cursor: disabled ? 'not-allowed' : 'pointer',
        background: val ? color : 'var(--ink-3)',
        border: `1px solid ${val ? color : 'var(--rim-2)'}`,
        position: 'relative', transition: 'all 0.2s', padding: 0,
        opacity: disabled ? 0.5 : 1,
      }}
    >
      <div style={{
        width: 12, height: 12, background: 'white', borderRadius: 1,
        position: 'absolute', top: 2,
        left: val ? 20 : 2, transition: 'left 0.2s',
      }} />
    </button>
  )

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
        }}>
          {toast.msg}
        </div>
      )}

      {/* Header */}
      <div className="a-iris">
        <div className="coord" style={{ color: 'var(--amber)', marginBottom: 6 }}>
          // ADM-04 / PRIVACY & SENSITIVITY CONTROLS
        </div>
        <h1 style={{ fontFamily: "'Syne',sans-serif", fontWeight: 800, fontSize: 26, color: 'var(--text-0)', margin: 0 }}>
          CELL SUPPRESSION & COLUMN SENSITIVITY
        </h1>
        <div className="label-xs" style={{ marginTop: 4, color: 'var(--text-3)' }}>
          Configure global suppression threshold · Mark columns as sensitive or masked · DPDP Act 2023 compliance
        </div>
      </div>

      {/* Cell Size Controls */}
      <div className="panel a-iris d1" style={{ overflow: 'hidden' }}>
        <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--rim)', display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 3, height: 16, background: 'var(--amber)' }}></div>
          <span className="label-sm">GLOBAL SUPPRESSION THRESHOLD</span>
        </div>
        <div style={{ padding: 24 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
            {/* Setting */}
            <div>
              <div className="coord" style={{ fontSize: 9, color: 'var(--text-4)', marginBottom: 8 }}>MIN_CELL_SIZE</div>
              <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                <input
                  type="number"
                  min={1} max={1000}
                  value={cellSize}
                  onChange={e => setCellSize(e.target.value)}
                  style={{
                    width: 100, padding: '12px 14px',
                    background: 'var(--ink-2)', border: '1px solid var(--rim-2)',
                    color: 'var(--amber)', fontFamily: "'DM Mono',monospace",
                    fontSize: 22, fontWeight: 700, textAlign: 'center', outline: 'none',
                  }}
                  onFocus={e => e.target.style.borderColor = 'var(--amber)'}
                  onBlur={e => e.target.style.borderColor = 'var(--rim-2)'}
                />
                <button
                  onClick={handleSaveCellSize}
                  disabled={savingCell}
                  className="iris-btn iris-btn-amber"
                  style={{ fontSize: 12, padding: '12px 24px' }}
                >
                  {savingCell ? 'SAVING...' : 'SAVE'}
                </button>
              </div>
              <div className="coord" style={{ marginTop: 10, color: 'var(--text-3)', fontSize: 10, lineHeight: 1.6 }}>
                Aggregation cells with fewer than this many respondents will be suppressed
                (all numeric values replaced with null) to prevent re-identification.
              </div>
            </div>

            {/* Preview */}
            <div style={{ background: 'var(--ink-2)', border: '1px solid var(--rim-2)', padding: 16 }}>
              <div className="coord" style={{ fontSize: 9, marginBottom: 12, color: 'var(--text-4)' }}>SUPPRESSION PREVIEW</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 10px', background: 'rgba(16,185,129,0.04)', border: '1px solid rgba(16,185,129,0.15)' }}>
                  <span style={{ fontFamily: "'Space Mono',monospace", fontSize: 11, color: 'var(--text-1)' }}>
                    Tamil Nadu · Female · Rural
                  </span>
                  <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 11, color: 'var(--green)' }}>
                    n=4,823 → ✓ VISIBLE
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 10px', background: 'rgba(245,158,11,0.04)', border: '1px solid rgba(245,158,11,0.15)' }}>
                  <span style={{ fontFamily: "'Space Mono',monospace", fontSize: 11, color: 'var(--text-1)' }}>
                    Lakshadweep · Male · Urban
                  </span>
                  <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 11, color: 'var(--amber)' }}>
                    n={parseInt(cellSize) - 1 || 29} → ⚠ SUPPRESSED
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Column Sensitivity Table */}
      <div className="panel a-iris d2" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--rim)', display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          <div style={{ width: 3, height: 16, background: 'var(--red)' }}></div>
          <span className="label-sm">COLUMN SENSITIVITY REGISTRY</span>

          <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, alignItems: 'center' }}>
            <button
              onClick={() => {
                const pii = ['name', 'email', 'phone', 'ip', 'address', 'aadhar', 'pan', 'id'];
                columns.forEach(c => {
                  const n = c.column_name.toLowerCase();
                  if (pii.some(p => n.includes(p) || n === p) && !c.is_sensitive) {
                    handleToggle(c, 'is_sensitive');
                  }
                });
                showToast('Auto-detection triggered for PII fields');
              }}
              className="iris-btn iris-btn-amber"
              style={{ padding: '5px 10px', fontSize: 10 }}
            >
              AUTO-DETECT PII
            </button>
            {/* Table filter */}
            <select
              value={tableFilter}
              onChange={e => setTableFilter(e.target.value)}
              style={{
                padding: '5px 8px', fontSize: 10,
                background: 'var(--ink-2)', border: '1px solid var(--rim-2)',
                color: 'var(--text-0)', fontFamily: "'Space Mono',monospace", outline: 'none', cursor: 'pointer',
              }}
            >
              <option value="">ALL TABLES</option>
              {tables.map(t => <option key={t} value={t}>{t}</option>)}
            </select>

            {/* Sensitivity filter */}
            {[
              { label: 'ALL', val: null },
              { label: 'FLAGGED', val: true },
              { label: 'SAFE', val: false },
            ].map(f => (
              <button
                key={f.label}
                onClick={() => setShowSensitive(f.val)}
                className={`iris-btn ${showSensitive === f.val ? 'iris-btn-amber' : 'iris-btn-ghost'}`}
                style={{ fontSize: 10, padding: '5px 10px' }}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-3)', fontFamily: "'Space Mono',monospace", fontSize: 12 }}>
            LOADING COLUMN REGISTRY...
          </div>
        ) : error ? (
          <div style={{ padding: 24, color: 'var(--red)', fontFamily: "'Space Mono',monospace", fontSize: 12 }}>
            // ERROR: {error}
          </div>
        ) : filteredCols.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-3)', fontFamily: "'Space Mono',monospace", fontSize: 12 }}>
            NO COLUMNS FOUND IN METADATA REGISTRY
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: 'var(--ink-3)' }}>
                  {['TABLE', 'COLUMN', 'TYPE', 'DESCRIPTION', 'SENSITIVE', 'MASKED', 'EFFECT'].map(h => (
                    <th key={h} style={{
                      padding: '10px 12px', textAlign: 'left',
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
                {filteredCols.map((col, i) => (
                  <tr
                    key={col.id}
                    style={{
                      background: col.is_masked
                        ? 'rgba(220,38,38,0.03)'
                        : col.is_sensitive
                          ? 'rgba(245,158,11,0.03)'
                          : (i % 2 === 0 ? 'var(--surface)' : 'var(--ink-2)'),
                      transition: 'background 0.15s',
                    }}
                  >
                    <td style={{ padding: '10px 12px', borderBottom: '1px solid var(--rim)' }}>
                      <code style={{ fontFamily: "'DM Mono',monospace", fontSize: 10, color: 'var(--cyan)' }}>
                        {col.table_name}
                      </code>
                    </td>
                    <td style={{ padding: '10px 12px', borderBottom: '1px solid var(--rim)' }}>
                      <code style={{
                        fontFamily: "'DM Mono',monospace", fontSize: 12, fontWeight: 600,
                        color: col.is_masked ? 'var(--red)' : col.is_sensitive ? 'var(--amber)' : 'var(--text-0)',
                      }}>
                        {col.column_name}
                      </code>
                    </td>
                    <td style={{ padding: '10px 12px', borderBottom: '1px solid var(--rim)' }}>
                      <span className="tag tag-dim" style={{ fontSize: 9 }}>{col.data_type}</span>
                    </td>
                    <td style={{ padding: '10px 12px', borderBottom: '1px solid var(--rim)', maxWidth: 200 }}>
                      <span className="coord" style={{ fontSize: 10, color: 'var(--text-2)' }}>
                        {col.description || '—'}
                      </span>
                    </td>
                    <td style={{ padding: '10px 12px', borderBottom: '1px solid var(--rim)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <Toggle
                          val={col.is_sensitive}
                          onChange={() => handleToggle(col, 'is_sensitive')}
                          disabled={toggling[`is_sensitive_${col.id}`]}
                          color="var(--amber)"
                        />
                        <span className="coord" style={{ fontSize: 9, color: col.is_sensitive ? 'var(--amber)' : 'var(--text-4)' }}>
                          {col.is_sensitive ? 'YES' : 'NO'}
                        </span>
                      </div>
                    </td>
                    <td style={{ padding: '10px 12px', borderBottom: '1px solid var(--rim)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <Toggle
                          val={col.is_masked}
                          onChange={() => handleToggle(col, 'is_masked')}
                          disabled={toggling[`is_masked_${col.id}`]}
                          color="var(--red)"
                        />
                        <span className="coord" style={{ fontSize: 9, color: col.is_masked ? 'var(--red)' : 'var(--text-4)' }}>
                          {col.is_masked ? 'MASKED' : 'NO'}
                        </span>
                      </div>
                    </td>
                    <td style={{ padding: '10px 12px', borderBottom: '1px solid var(--rim)' }}>
                      {col.is_masked ? (
                        <span style={{
                          padding: '3px 8px', fontSize: 9, fontWeight: 700,
                          fontFamily: "'Space Mono',monospace",
                          background: 'rgba(220,38,38,0.08)', border: '1px solid rgba(220,38,38,0.3)',
                          color: 'var(--red)', letterSpacing: '0.06em',
                        }}>
                          HIDDEN FROM ALL QUERIES
                        </span>
                      ) : col.is_sensitive ? (
                        <span style={{
                          padding: '3px 8px', fontSize: 9, fontWeight: 700,
                          fontFamily: "'Space Mono',monospace",
                          background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.3)',
                          color: 'var(--amber)', letterSpacing: '0.06em',
                        }}>
                          FLAGGED IN DICTIONARY
                        </span>
                      ) : (
                        <span className="coord" style={{ fontSize: 9 }}>Normal</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="panel" style={{ padding: 16 }}>
        <div className="label-sm" style={{ marginBottom: 12, color: 'var(--text-3)' }}>LEGEND</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
            <span style={{ color: 'var(--amber)', fontSize: 14, marginTop: 1 }}>⚠</span>
            <div>
              <div className="label-xs" style={{ color: 'var(--amber)', marginBottom: 4 }}>SENSITIVE</div>
              <div className="coord" style={{ fontSize: 10, color: 'var(--text-2)', lineHeight: 1.5 }}>
                Column is flagged as potentially identifying in the data dictionary.
                Still visible in query results but marked for researcher awareness.
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
            <span style={{ color: 'var(--red)', fontSize: 14, marginTop: 1 }}>🔒</span>
            <div>
              <div className="label-xs" style={{ color: 'var(--red)', marginBottom: 4 }}>MASKED</div>
              <div className="coord" style={{ fontSize: 10, color: 'var(--text-2)', lineHeight: 1.5 }}>
                Column is COMPLETELY REMOVED from ALL API responses regardless of user scope.
                This is enforced server-side in sql_guard.py and cannot be bypassed.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
