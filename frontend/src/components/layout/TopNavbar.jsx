import { useNavigate } from 'react-router-dom'
import { useSession } from '../../hooks/useSession'
import { useLang } from '../../hooks/useLang'
import { useState, useEffect } from 'react'

export default function TopNavbar() {
  const navigate = useNavigate()
  const { datasetReady, filename, rowCount } = useSession()
  const user = useSession(state => state.user)
  const logoutUser = useSession(state => state.logoutUser)
  const { t } = useLang()
  const [time, setTime] = useState(new Date())
  useEffect(() => { const i = setInterval(() => setTime(new Date()), 1000); return () => clearInterval(i) }, [])

  const getRoleDisplay = () => {
    if (!user) return { name: 'GUEST', color: 'var(--text-4)' }
    if (user.scope === 'admin') return { name: 'ADMIN', color: '#ef4444' }
    if (user.scope === 'research') {
      return {
        name: user.isSimulatedPremium ? 'PREMIUM (MOCK)' : 'PREMIUM USER',
        color: 'var(--cyan)'
      }
    }
    return { name: 'FREE USER', color: '#64748b' }
  }
  const role = getRoleDisplay()

  return (
    <div style={{
      height:44, background:'var(--ink-2)',
      borderBottom:'1px solid var(--rim-2)',
      display:'flex', alignItems:'center',
      justifyContent:'space-between', padding:'0 20px',
      transition:'background 0.3s',
    }}>
      <div style={{ display:'flex', alignItems:'center', gap:16 }}>
        <span className="coord" style={{ color:'var(--amber)', fontSize:9 }}>StatIQ</span>
        <span className="coord" style={{ color:'var(--text-4)' }}>//</span>
        {datasetReady ? (
          <div style={{ display:'flex', alignItems:'center', gap:8 }}>
            <span className="status-dot status-active"></span>
            <span className="data-val" style={{ fontSize:12, color:'var(--cyan)' }}>{filename}</span>
            <span className="tag tag-cyan" style={{ fontSize:9 }}>{rowCount?.toLocaleString()} REC</span>
          </div>
        ) : (
          <span className="label-xs" style={{ color:'var(--text-4)' }}>{t('no_dataset').toUpperCase()}</span>
        )}
      </div>

      <div style={{ display:'flex', alignItems:'center', gap:14 }}>
        <span className="tag tag-green" style={{ fontSize:9 }}>
          <span className="status-dot status-live" style={{ width:4, height:4 }}></span>
          {t('privacy_safe').toUpperCase()}
        </span>
        <div style={{ textAlign:'right' }}>
          <div className="data-val" style={{ fontSize:13, color:'var(--amber)', letterSpacing:'0.08em' }}>
            {time.toLocaleTimeString('en-IN', { hour12:false })}
          </div>
          <div className="coord">{time.toLocaleDateString('en-IN')}</div>
        </div>
        <div style={{ width:1, height:22, background:'var(--rim-2)' }}></div>
        <div style={{ display:'flex', alignItems:'center', gap:8 }}>
          <div style={{ width:26, height:26, border:`1px solid ${role.color}`, display:'flex', alignItems:'center', justifyContent:'center' }}>
            <svg viewBox="0 0 16 16" fill="none" stroke={role.color} strokeWidth="1.2" style={{ width:14, height:14 }}>
              <circle cx="8" cy="5" r="3"/><path d="M1 15c0-4 3-7 7-7s7 3 7 7"/>
            </svg>
          </div>
          <div>
            <div className="label-xs" style={{ color: role.color, fontSize:9, fontWeight:700 }}>{role.name}</div>
            <div className="coord" style={{ color:'var(--text-3)' }}>{user?.email || 'analyst@mospi.gov.in'}</div>
          </div>
        </div>
        <button
          onClick={() => { logoutUser(); navigate('/login') }}
          className="iris-btn iris-btn-ghost"
          style={{ padding:'4px 10px', fontSize:9 }}
        >
          {t('sign_out').toUpperCase()}
        </button>
      </div>
    </div>
  )
}