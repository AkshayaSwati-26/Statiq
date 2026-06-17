import { useState } from 'react'
import { useTheme } from '../hooks/useTheme'
import { useLang } from '../hooks/useLang'

export default function SettingsPage() {
  const { isDark, toggle } = useTheme()
  const { t, lang, setLang } = useLang()

  const [name,     setName]     = useState('Govt. Official')
  const [email,    setEmail]    = useState('analyst@mospi.gov.in')
  const [dept,     setDept]     = useState('Ministry of Statistics')
  const [role,     setRole]     = useState('Policy Analyst')
  const [saved,    setSaved]    = useState(false)
  const [notif,    setNotif]    = useState(true)
  const [auditLog, setAuditLog] = useState(true)

  const handleSave = () => { setSaved(true); setTimeout(() => setSaved(false), 2500) }

  const Section = ({ colorVar, titleKey, children }) => (
    <div className="panel a-iris" style={{ padding:0, overflow:'hidden' }}>
      <div style={{ padding:'14px 20px', borderBottom:'1px solid var(--rim-2)', display:'flex', alignItems:'center', gap:10 }}>
        <div style={{ width:3, height:16, background:colorVar }}></div>
        <span className="label-sm" style={{ fontSize:12 }}>{t(titleKey)}</span>
      </div>
      <div style={{ padding:24 }}>{children}</div>
    </div>
  )

  const Toggle = ({ val, onToggle }) => (
    <button onClick={onToggle} style={{
      width:52, height:26, borderRadius:2,
      background: val ? 'var(--green)' : 'var(--ink-2)',
      border:'1px solid var(--rim-2)', cursor:'pointer',
      position:'relative', transition:'background 0.2s', padding:2, flexShrink:0,
    }}>
      <div style={{
        width:20, height:20, background: val ? 'white' : 'var(--text-4)',
        borderRadius:1, position:'absolute', top:2,
        left: val ? 28 : 2, transition:'left 0.2s',
      }}></div>
    </button>
  )

  return (
    <div style={{ maxWidth:780, display:'flex', flexDirection:'column', gap:20 }}>

      <div className="a-iris">
        <div className="coord" style={{ color:'var(--amber)', marginBottom:6 }}>// SYSTEM SETTINGS</div>
        <h1 style={{ fontFamily:"'Syne',sans-serif", fontWeight:800, fontSize:26, color:'var(--text-0)' }}>
          {t('settings_title')}
        </h1>
        <div className="label-xs" style={{ marginTop:4, color:'var(--text-3)' }}>
          Profile, preferences, and platform configuration
        </div>
      </div>

      {/* ── LANGUAGE ── */}
      <div className="panel a-iris d1" style={{ padding:0, overflow:'hidden' }}>
        <div style={{ padding:'14px 20px', borderBottom:'1px solid var(--rim-2)', display:'flex', alignItems:'center', gap:10 }}>
          <div style={{ width:3, height:16, background:'var(--cyan)' }}></div>
          <span className="label-sm" style={{ fontSize:12 }}>{t('settings_language').toUpperCase()}</span>
        </div>
        <div style={{ padding:24 }}>
          <p style={{ fontFamily:"'Space Mono',monospace", fontSize:14, color:'var(--text-1)', marginBottom:18, lineHeight:1.8 }}>
            Switch the interface language. Uploaded data, column names, and API responses remain unchanged.
          </p>
          <div style={{ display:'flex', gap:12 }}>
            {[
              { code:'en', label:'English',  sub:'Default interface language' },
              { code:'hi', label:'हिंदी',    sub:'सम्पूर्ण इंटरफ़ेस हिंदी में' },
            ].map(l => (
              <button
                key={l.code}
                onClick={() => setLang(l.code)}
                style={{
                  flex:1, padding:'18px 20px', textAlign:'left',
                  cursor:'pointer', borderRadius:2,
                  border: lang === l.code ? '2px solid var(--amber)' : '1px solid var(--rim-2)',
                  background: lang === l.code ? 'var(--amber-glow)' : 'var(--ink-2)',
                  transition:'all 0.15s',
                }}
              >
                <div style={{ fontFamily:"'Syne',sans-serif", fontWeight:700, fontSize:20, color: lang === l.code ? 'var(--amber)' : 'var(--text-0)', marginBottom:6 }}>
                  {l.label}
                </div>
                <div className="coord" style={{ color:'var(--text-3)' }}>{l.sub}</div>
                {lang === l.code && (
                  <div style={{ marginTop:10, display:'flex', alignItems:'center', gap:6 }}>
                    <svg viewBox="0 0 12 12" fill="none" stroke="var(--green)" strokeWidth="2" style={{ width:12, height:12 }}>
                      <polyline points="2 6 5 9 10 3"/>
                    </svg>
                    <span className="coord" style={{ color:'var(--green)' }}>ACTIVE</span>
                  </div>
                )}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── APPEARANCE ── */}
      <Section colorVar="var(--amber)" titleKey="settings_appearance">
        <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:20 }}>
          <div>
            <div className="data-val" style={{ fontSize:15, marginBottom:6 }}>{t('settings_theme')}</div>
            <div className="coord" style={{ color:'var(--text-3)' }}>
              {isDark ? 'Dark Mode — IRIS Terminal' : 'Light Mode — IRIS Clarity'}
            </div>
          </div>
          <div style={{ display:'flex', alignItems:'center', gap:12 }}>
            <span className="label-xs" style={{ color: !isDark ? 'var(--amber)' : 'var(--text-4)', fontSize:11 }}>
              {t('settings_light')}
            </span>
            <button onClick={toggle} style={{
              width:56, height:28, borderRadius:2,
              background: isDark ? 'var(--amber)' : 'var(--ink-2)',
              border:'1px solid var(--rim-2)', cursor:'pointer',
              position:'relative', transition:'background 0.25s', padding:2,
            }}>
              <div style={{
                width:22, height:22,
                background: isDark ? 'var(--ink)' : 'var(--text-0)',
                borderRadius:1, position:'absolute', top:2,
                left: isDark ? 30 : 2, transition:'left 0.25s',
              }}></div>
            </button>
            <span className="label-xs" style={{ color: isDark ? 'var(--amber)' : 'var(--text-4)', fontSize:11 }}>
              {t('settings_dark')}
            </span>
          </div>
        </div>
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:12 }}>
          {[
            { id:'light', label:'Light Mode',  bg:'#f0f4f8', surface:'#ffffff', accent:'#d97706', text:'#0f172a' },
            { id:'dark',  label:'Dark Mode',   bg:'#030712', surface:'#0f1f35', accent:'#f59e0b', text:'#f1f5f9' },
          ].map(m => (
            <div key={m.id} onClick={() => { if ((m.id==='dark') !== isDark) toggle() }} style={{
              background:m.bg, padding:14, cursor:'pointer',
              border:`2px solid ${(isDark ? m.id==='dark' : m.id==='light') ? m.accent : 'rgba(0,0,0,0.08)'}`,
              borderRadius:2, transition:'border-color 0.15s',
            }}>
              <div style={{ background:m.surface, border:'1px solid rgba(0,0,0,0.06)', padding:'8px 12px', marginBottom:10 }}>
                <div style={{ fontFamily:"'Space Mono',monospace", fontSize:9, color:m.accent, marginBottom:4 }}>// IRIS PLATFORM</div>
                <div style={{ display:'flex', gap:4 }}>
                  {[m.accent,'rgba(3,105,161,0.7)','rgba(100,116,139,0.4)'].map((c,i) => (
                    <div key={i} style={{ height:5, flex:1, background:c, borderRadius:1 }}></div>
                  ))}
                </div>
              </div>
              <div style={{ fontFamily:"'Syne',sans-serif", fontWeight:700, fontSize:13, color:m.text, textTransform:'uppercase' }}>{m.label}</div>
            </div>
          ))}
        </div>
      </Section>

      {/* ── PROFILE ── */}
      <Section colorVar="var(--cyan)" titleKey="settings_profile">
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:16 }}>
          {[
            { lkey:'settings_name',  val:name,  set:setName,  ph:'Your full name'        },
            { lkey:'settings_email', val:email, set:setEmail, ph:'official@mospi.gov.in' },
            { lkey:'settings_dept',  val:dept,  set:setDept,  ph:'Ministry / Department' },
            { lkey:'settings_role',  val:role,  set:setRole,  ph:'Your designation'      },
          ].map(f => (
            <div key={f.lkey}>
              <label className="label-xs" style={{ display:'block', marginBottom:8, color:'var(--text-3)', fontSize:10 }}>
                // {t(f.lkey).toUpperCase()}
              </label>
              <input value={f.val} onChange={e => f.set(e.target.value)} placeholder={f.ph} className="iris-input" style={{ fontSize:14 }} />
            </div>
          ))}
        </div>
      </Section>

      {/* ── PREFERENCES ── */}
      <Section colorVar="var(--green)" titleKey="settings_prefs">
        <div style={{ display:'flex', flexDirection:'column', gap:16 }}>
          {[
            { label:'Activity Notifications', sub:'Notify when query completes', val:notif,    set:setNotif    },
            { label:'Audit Log',               sub:'Maintain full query trail',   val:auditLog, set:setAuditLog },
          ].map(p => (
            <div key={p.label} style={{ display:'flex', alignItems:'center', justifyContent:'space-between', padding:'14px 0', borderBottom:'1px solid var(--rim)' }}>
              <div>
                <div className="data-val" style={{ fontSize:15, marginBottom:4 }}>{p.label}</div>
                <div className="coord" style={{ color:'var(--text-3)' }}>{p.sub}</div>
              </div>
              <Toggle val={p.val} onToggle={() => p.set(v => !v)} />
            </div>
          ))}
        </div>
      </Section>

      {/* ── SECURITY ── */}
      <Section colorVar="var(--red)" titleKey="settings_security">
        <div style={{ display:'flex', gap:10, flexWrap:'wrap', marginBottom:12 }}>
          <button className="iris-btn iris-btn-ghost" style={{ fontSize:12 }}>CHANGE PASSPHRASE</button>
          <button className="iris-btn iris-btn-ghost" style={{ fontSize:12 }}>VIEW ACTIVE SESSIONS</button>
          <button className="iris-btn iris-btn-ghost" style={{ fontSize:12, color:'var(--red)', borderColor:'rgba(220,38,38,0.3)' }}>
            REVOKE ALL TOKENS
          </button>
        </div>
        <div className="coord" style={{ color:'var(--text-3)', lineHeight:2, fontSize:10 }}>
          Last sign-in: Today 10:32 AM · analyst@mospi.gov.in · Clearance Level 3 · Session timeout: 30 min
        </div>
        <div style={{ marginTop:16, background:'var(--ink-2)', border:'1px solid var(--rim-2)', padding:'14px 18px' }}>
          <div className="label-xs" style={{ color:'var(--text-3)', marginBottom:10, fontSize:10 }}>// FRONTEND SECURITY MEASURES ACTIVE</div>
          <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
            {[
              'Session data stored in memory only — cleared on tab close',
              'No sensitive data written to localStorage or cookies',
              'Automatic session timeout after 30 minutes of inactivity',
              'All queries scoped to active dataset session ID',
              'Input sanitization before every API call',
              'Only aggregated data displayed — no raw microdata',
            ].map(item => (
              <div key={item} style={{ display:'flex', alignItems:'flex-start', gap:10 }}>
                <svg viewBox="0 0 12 12" fill="none" stroke="var(--green)" strokeWidth="2" style={{ width:12, height:12, flexShrink:0, marginTop:2 }}>
                  <polyline points="2 6 5 9 10 3"/>
                </svg>
                <span style={{ fontFamily:"'Space Mono',monospace", fontSize:12, color:'var(--text-2)', lineHeight:1.6 }}>{item}</span>
              </div>
            ))}
          </div>
        </div>
      </Section>

      {/* Save */}
      <div style={{ display:'flex', alignItems:'center', gap:14 }}>
        <button onClick={handleSave} className="iris-btn iris-btn-primary" style={{ minWidth:200, fontSize:13, padding:'12px 24px' }}>
          {saved ? '✓ ' + t('settings_saved').toUpperCase() : t('settings_save').toUpperCase()}
        </button>
        {saved && <span className="tag tag-green">{t('settings_saved')}</span>}
      </div>
    </div>
  )
}