import { useState, useEffect, useCallback } from 'react'
import { useSession } from '../hooks/useSession'
import axios from 'axios'

const API = axios.create({ baseURL: '', withCredentials: true })

const SCOPE_COLORS = {
  admin:    { color: '#ef4444', bg: 'rgba(239,68,68,0.08)',  border: 'rgba(239,68,68,0.3)'  },
  research: { color: 'var(--cyan)', bg: 'rgba(34,211,238,0.08)', border: 'rgba(34,211,238,0.3)' },
  public:   { color: 'var(--text-3)', bg: 'rgba(255,255,255,0.03)', border: 'var(--rim-2)' },
}

function ScopeBadge({ scope }) {
  const s = SCOPE_COLORS[scope] || SCOPE_COLORS.public
  return (
    <span style={{
      padding: '3px 10px', fontSize: 10, fontWeight: 700,
      fontFamily: "'Space Mono',monospace", letterSpacing: '0.08em',
      border: `1px solid ${s.border}`, color: s.color, background: s.bg,
    }}>
      {scope?.toUpperCase() || 'PUBLIC'}
    </span>
  )
}

function ActiveDot({ active }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <span style={{
        width: 8, height: 8, borderRadius: '50%',
        background: active ? 'var(--green)' : 'var(--red)',
        display: 'inline-block',
        boxShadow: active ? '0 0 6px rgba(16,185,129,0.4)' : '0 0 6px rgba(220,38,38,0.4)',
      }} />
      <span style={{
        fontFamily: "'Space Mono',monospace", fontSize: 10,
        color: active ? 'var(--green)' : 'var(--red)',
        letterSpacing: '0.06em',
      }}>
        {active ? 'ACTIVE' : 'DISABLED'}
      </span>
    </div>
  )
}

export default function AdminUsers() {
  const user = useSession(s => s.user)

  const [users, setUsers]       = useState([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState('')
  const [toast, setToast]       = useState(null)
  const [showCreate, setShowCreate] = useState(false)

  // Create user form
  const [newEmail, setNewEmail]     = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [newScope, setNewScope]     = useState('public')
  const [newPasscode, setNewPasscode] = useState('')
  const [creating, setCreating]     = useState(false)

  // Editing
  const [editingScope, setEditingScope] = useState({}) // uid -> newScope
  const [toggling, setToggling] = useState({})

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3500)
  }

  const fetchUsers = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const r = await API.get('/v1/admin/users')
      setUsers(r.data)
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to load users')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchUsers() }, [fetchUsers])

  if (!user || user.scope !== 'admin') {
    return (
      <div style={{ padding: 40, color: 'var(--red)', fontFamily: "'Space Mono',monospace" }}>
        ACCESS RESTRICTED — ADMIN ONLY
      </div>
    )
  }

  const handleCreate = async (e) => {
    e.preventDefault()
    if (!newEmail || !newPassword) { showToast('Email and password are required', 'error'); return }
    setCreating(true)
    try {
      const body = { email: newEmail, password: newPassword, scope: newScope }
      if (newScope === 'admin') body.admin_passcode = newPasscode
      await API.post('/v1/admin/users', body)
      showToast(`User "${newEmail}" created successfully`)
      setNewEmail(''); setNewPassword(''); setNewScope('public'); setNewPasscode('')
      setShowCreate(false)
      fetchUsers()
    } catch (e) {
      showToast(e?.response?.data?.detail || 'Failed to create user', 'error')
    } finally {
      setCreating(false)
    }
  }

  const handleScopeChange = async (uid, newScope) => {
    if (!window.confirm(`Change ${uid}'s scope to ${newScope.toUpperCase()}?`)) return
    setToggling(t => ({ ...t, [`scope_${uid}`]: true }))
    try {
      await API.patch(`/v1/admin/users/${uid}/scope`, { scope: newScope })
      setUsers(us => us.map(u => u.user_id === uid ? { ...u, scope: newScope } : u))
      setEditingScope(es => { const n = { ...es }; delete n[uid]; return n })
      showToast(`${uid} scope updated to ${newScope.toUpperCase()}`)
    } catch (e) {
      showToast(e?.response?.data?.detail || 'Failed to update scope', 'error')
    } finally {
      setToggling(t => ({ ...t, [`scope_${uid}`]: false }))
    }
  }

  const handleToggleActive = async (u) => {
    const newActive = !u.is_active
    const action = newActive ? 'activate' : 'deactivate'
    if (!window.confirm(`${action.charAt(0).toUpperCase() + action.slice(1)} user "${u.user_id}"?`)) return
    setToggling(t => ({ ...t, [`active_${u.user_id}`]: true }))
    try {
      await API.patch(`/v1/admin/users/${u.user_id}/active`, { is_active: newActive })
      setUsers(us => us.map(x => x.user_id === u.user_id ? { ...x, is_active: newActive } : x))
      showToast(`User "${u.user_id}" ${action}d`)
    } catch (e) {
      showToast(e?.response?.data?.detail || 'Failed to update user', 'error')
    } finally {
      setToggling(t => ({ ...t, [`active_${u.user_id}`]: false }))
    }
  }

  const fmtDate = (iso) => {
    if (!iso) return '—'
    return new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
  }
  const fmtDateTime = (iso) => {
    if (!iso) return 'Never'
    return new Date(iso).toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
  }

  const inputStyle = {
    width: '100%', boxSizing: 'border-box',
    padding: '10px 12px', background: 'var(--ink-2)',
    border: '1px solid var(--rim-2)', color: 'var(--text-0)',
    fontFamily: "'Space Mono',monospace", fontSize: 12, outline: 'none',
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
        }}>
          {toast.msg}
        </div>
      )}

      {/* Header */}
      <div className="a-iris">
        <div className="coord" style={{ color: 'var(--amber)', marginBottom: 6 }}>
          // ADM-03 / USER MANAGEMENT
        </div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h1 style={{ fontFamily: "'Syne',sans-serif", fontWeight: 800, fontSize: 26, color: 'var(--text-0)', margin: 0 }}>
            USER MANAGEMENT
          </h1>
          <button
            onClick={() => setShowCreate(v => !v)}
            className="iris-btn iris-btn-amber"
            style={{ fontSize: 12 }}
          >
            {showCreate ? '✕ CANCEL' : '+ CREATE USER'}
          </button>
        </div>
        <div className="label-xs" style={{ marginTop: 4, color: 'var(--text-3)' }}>
          Create accounts · Manage scopes · Activate / deactivate users
        </div>
      </div>

      {/* Create User Modal */}
      {showCreate && (
        <div className="panel a-iris d1" style={{ overflow: 'hidden' }}>
          <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--rim)', display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ width: 3, height: 16, background: 'var(--green)' }}></div>
            <span className="label-sm">NEW USER ACCOUNT</span>
          </div>
          <form onSubmit={handleCreate} style={{ padding: 24 }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20 }}>
              <div>
                <div className="coord" style={{ marginBottom: 6, fontSize: 9, color: 'var(--text-4)' }}>EMAIL ADDRESS *</div>
                <input
                  type="email"
                  required
                  value={newEmail}
                  onChange={e => setNewEmail(e.target.value)}
                  placeholder="user@mospi.gov.in"
                  style={inputStyle}
                  onFocus={e => e.target.style.borderColor = 'var(--green)'}
                  onBlur={e => e.target.style.borderColor = 'var(--rim-2)'}
                />
              </div>
              <div>
                <div className="coord" style={{ marginBottom: 6, fontSize: 9, color: 'var(--text-4)' }}>PASSWORD *</div>
                <input
                  type="password"
                  required
                  value={newPassword}
                  onChange={e => setNewPassword(e.target.value)}
                  placeholder="Min 6 chars, upper+lower+digit+special"
                  style={inputStyle}
                  onFocus={e => e.target.style.borderColor = 'var(--green)'}
                  onBlur={e => e.target.style.borderColor = 'var(--rim-2)'}
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20 }}>
              <div>
                <div className="coord" style={{ marginBottom: 6, fontSize: 9, color: 'var(--text-4)' }}>ACCESS SCOPE</div>
                <div style={{ display: 'flex', gap: 8 }}>
                  {['public', 'research', 'admin'].map(s => (
                    <button
                      key={s}
                      type="button"
                      onClick={() => setNewScope(s)}
                      style={{
                        flex: 1, padding: '10px 0', cursor: 'pointer', fontSize: 11,
                        fontFamily: "'Space Mono',monospace", fontWeight: 700,
                        letterSpacing: '0.08em',
                        background: newScope === s ? (SCOPE_COLORS[s]?.bg || 'transparent') : 'transparent',
                        border: `1px solid ${newScope === s ? (SCOPE_COLORS[s]?.color || 'var(--rim-2)') : 'var(--rim-2)'}`,
                        color: newScope === s ? (SCOPE_COLORS[s]?.color || 'var(--text-2)') : 'var(--text-3)',
                        transition: 'all 0.15s',
                      }}
                    >
                      {s === 'public' ? 'FREE' : s === 'research' ? 'PREMIUM' : 'ADMIN'}
                    </button>
                  ))}
                </div>
              </div>
              {newScope === 'admin' && (
                <div>
                  <div className="coord" style={{ marginBottom: 6, fontSize: 9, color: 'var(--red)' }}>ADMIN PASSCODE *</div>
                  <input
                    type="password"
                    required={newScope === 'admin'}
                    value={newPasscode}
                    onChange={e => setNewPasscode(e.target.value)}
                    placeholder="Admin creation passcode"
                    style={{ ...inputStyle, borderColor: 'rgba(239,68,68,0.3)' }}
                    onFocus={e => e.target.style.borderColor = '#ef4444'}
                    onBlur={e => e.target.style.borderColor = 'rgba(239,68,68,0.3)'}
                  />
                </div>
              )}
            </div>

            <div style={{ display: 'flex', gap: 12 }}>
              <button type="submit" disabled={creating} className="iris-btn iris-btn-primary" style={{ fontSize: 13, padding: '12px 28px' }}>
                {creating ? 'CREATING...' : 'CREATE USER'}
              </button>
              <button type="button" onClick={() => setShowCreate(false)} className="iris-btn iris-btn-ghost" style={{ fontSize: 12 }}>
                CANCEL
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Summary Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        {[
          { label: 'TOTAL USERS', val: users.length, color: 'var(--amber)' },
          { label: 'FREE', val: users.filter(u => u.scope === 'public').length, color: 'var(--text-2)' },
          { label: 'PREMIUM', val: users.filter(u => u.scope === 'research').length, color: 'var(--cyan)' },
          { label: 'ADMINS', val: users.filter(u => u.scope === 'admin').length, color: '#ef4444' },
        ].map(s => (
          <div key={s.label} className="panel" style={{ padding: '14px 18px', position: 'relative', overflow: 'hidden' }}>
            <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, background: `linear-gradient(90deg, ${s.color}, transparent)`, opacity: 0.6 }}></div>
            <div className="coord" style={{ fontSize: 9, marginBottom: 8, color: 'var(--text-4)' }}>{s.label}</div>
            <div style={{ fontFamily: "'DM Mono',monospace", fontSize: 28, fontWeight: 500, color: s.color }}>{s.val}</div>
          </div>
        ))}
      </div>

      {/* Users Table */}
      <div className="panel a-iris d2" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '12px 20px', borderBottom: '1px solid var(--rim)', display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 2, height: 14, background: '#ef4444' }}></div>
          <span className="label-sm">ALL USERS</span>
          <button onClick={fetchUsers} className="iris-btn iris-btn-ghost" style={{ marginLeft: 'auto', fontSize: 10 }}>
            ↻ REFRESH
          </button>
        </div>

        {loading ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-3)', fontFamily: "'Space Mono',monospace", fontSize: 12 }}>
            LOADING...
          </div>
        ) : error ? (
          <div style={{ padding: 24, color: 'var(--red)', fontFamily: "'Space Mono',monospace", fontSize: 12 }}>
            // ERROR: {error}
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: 'var(--ink-3)' }}>
                  {['USER ID', 'EMAIL', 'SCOPE', 'STATUS', 'CREATED', 'LAST LOGIN', 'ACTIONS'].map(h => (
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
                {users.map((u, i) => (
                  <tr
                    key={u.user_id}
                    style={{ background: i % 2 === 0 ? 'var(--surface)' : 'var(--ink-2)', transition: 'background 0.15s' }}
                    onMouseEnter={e => e.currentTarget.style.background = 'rgba(239,68,68,0.02)'}
                    onMouseLeave={e => e.currentTarget.style.background = i % 2 === 0 ? 'var(--surface)' : 'var(--ink-2)'}
                  >
                    <td style={{ padding: '12px 14px', borderBottom: '1px solid var(--rim)' }}>
                      <code style={{ fontFamily: "'DM Mono',monospace", fontSize: 12, color: 'var(--text-0)' }}>
                        {u.user_id}
                      </code>
                    </td>
                    <td style={{ padding: '12px 14px', borderBottom: '1px solid var(--rim)' }}>
                      <span style={{ fontFamily: "'Space Mono',monospace", fontSize: 11, color: 'var(--text-1)' }}>
                        {u.email || '—'}
                      </span>
                    </td>
                    <td style={{ padding: '12px 14px', borderBottom: '1px solid var(--rim)' }}>
                      {editingScope[u.user_id] !== undefined ? (
                        <div style={{ display: 'flex', gap: 4 }}>
                          <select
                            value={editingScope[u.user_id]}
                            onChange={e => setEditingScope(es => ({ ...es, [u.user_id]: e.target.value }))}
                            style={{
                              padding: '4px 6px', fontSize: 10,
                              background: 'var(--ink-2)', border: '1px solid var(--amber)',
                              color: 'var(--text-0)', fontFamily: "'Space Mono',monospace",
                              outline: 'none', cursor: 'pointer',
                            }}
                          >
                            <option value="public">PUBLIC</option>
                            <option value="research">RESEARCH</option>
                            <option value="admin">ADMIN</option>
                          </select>
                          <button
                            onClick={() => handleScopeChange(u.user_id, editingScope[u.user_id])}
                            disabled={toggling[`scope_${u.user_id}`]}
                            style={{
                              padding: '4px 8px', fontSize: 9, cursor: 'pointer',
                              background: 'rgba(16,185,129,0.1)', border: '1px solid var(--green)',
                              color: 'var(--green)', fontFamily: "'Space Mono',monospace",
                            }}
                          >
                            ✓
                          </button>
                          <button
                            onClick={() => setEditingScope(es => { const n = { ...es }; delete n[u.user_id]; return n })}
                            style={{
                              padding: '4px 8px', fontSize: 9, cursor: 'pointer',
                              background: 'transparent', border: '1px solid var(--rim-2)',
                              color: 'var(--text-3)', fontFamily: "'Space Mono',monospace",
                            }}
                          >
                            ✕
                          </button>
                        </div>
                      ) : (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}
                             onClick={() => setEditingScope(es => ({ ...es, [u.user_id]: u.scope }))}>
                          <ScopeBadge scope={u.scope} />
                          <span style={{ color: 'var(--text-4)', fontSize: 10 }}>✎</span>
                        </div>
                      )}
                    </td>
                    <td style={{ padding: '12px 14px', borderBottom: '1px solid var(--rim)' }}>
                      <ActiveDot active={u.is_active} />
                    </td>
                    <td style={{ padding: '12px 14px', borderBottom: '1px solid var(--rim)' }}>
                      <span className="coord" style={{ fontSize: 10 }}>{fmtDate(u.created_at)}</span>
                    </td>
                    <td style={{ padding: '12px 14px', borderBottom: '1px solid var(--rim)' }}>
                      <span className="coord" style={{ fontSize: 10 }}>{fmtDateTime(u.last_login_at)}</span>
                    </td>
                    <td style={{ padding: '12px 14px', borderBottom: '1px solid var(--rim)' }}>
                      <button
                        onClick={() => handleToggleActive(u)}
                        disabled={toggling[`active_${u.user_id}`] || u.user_id === user?.sub}
                        style={{
                          padding: '5px 12px', fontSize: 10, cursor: u.user_id === user?.sub ? 'not-allowed' : 'pointer',
                          fontFamily: "'Space Mono',monospace", letterSpacing: '0.06em',
                          background: 'transparent',
                          border: `1px solid ${u.is_active ? 'rgba(220,38,38,0.3)' : 'rgba(16,185,129,0.3)'}`,
                          color: u.is_active ? 'var(--red)' : 'var(--green)',
                          opacity: (toggling[`active_${u.user_id}`] || u.user_id === user?.sub) ? 0.4 : 1,
                          transition: 'all 0.15s',
                        }}
                        onMouseEnter={e => { if (u.user_id !== user?.sub) e.currentTarget.style.background = u.is_active ? 'rgba(220,38,38,0.06)' : 'rgba(16,185,129,0.06)' }}
                        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                      >
                        {toggling[`active_${u.user_id}`] ? '...' : (u.is_active ? 'DEACTIVATE' : 'ACTIVATE')}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
