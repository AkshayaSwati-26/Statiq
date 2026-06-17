import { NavLink } from 'react-router-dom'
import { useSession } from '../../hooks/useSession'
import { useLang } from '../../hooks/useLang'

const NAV_KEYS = [
  { path:'/dashboard', code:'01', tkey:'nav_overview', icon:'M1 1h6v6H1zM9 1h6v6H9zM1 9h6v6H1zM9 9h6v6H9z' },
  { path:'/ingest',    code:'02', tkey:'nav_ingest',   icon:'M8 1v10M4 7l4 4 4-4', d2:'M1 13h14v2H1z' },
  { path:'/query',     code:'03', tkey:'nav_query',    icon:'M7 13A6 6 0 107 1a6 6 0 000 12zM13 13l2 2' },
  { path:'/results',   code:'04', tkey:'nav_results',  icon:'M2 12h2V8H2zM6 12h2V4H6zM10 12h2V6h-2zM14 12h-2V2h2z' },
  { path:'/history',   code:'05', tkey:'nav_history',  icon:'M8 4v4l3 2M1 8a7 7 0 1014 0A7 7 0 001 8' },
  { path:'/exports',   code:'06', tkey:'nav_export',   icon:'M8 11V1M4 7l4 4 4-4', d2:'M1 13h14v2H1z' },
  { path:'/settings',  code:'07', tkey:'nav_settings', icon:'M8 10a2 2 0 100-4 2 2 0 000 4zM13 7h.5a1 1 0 011 1v.5a1 1 0 01-.7.95l-.5.15a4 4 0 01-.35.85l.25.4a1 1 0 01-.1 1.25l-.35.35a1 1 0 01-1.25-.1l-.4-.25a4 4 0 01-.85.35l-.15.5A1 1 0 019 13h-.5a1 1 0 01-.95-.7l-.15-.5a4 4 0 01-.85-.35l-.4.25a1 1 0 01-1.25-.1l-.35-.35a1 1 0 01-.1-1.25l.25-.4a4 4 0 01-.35-.85l-.5-.15A1 1 0 013 8.5V8a1 1 0 01.7-.95l.5-.15A4 4 0 014.55 6l-.25-.4a1 1 0 01.1-1.25l.35-.35a1 1 0 011.25.1l.4.25a4 4 0 01.85-.35l.15-.5A1 1 0 018.5 3H9a1 1 0 01.95.7l.15.5a4 4 0 01.85.35l.4-.25a1 1 0 011.25.1l.35.35a1 1 0 01.1 1.25l-.25.4a4 4 0 01.35.85l.5.15z' },
]

export default function Sidebar() {
  const { datasetReady, filename, rowCount } = useSession()
  const { t, lang, setLang } = useLang()

  return (
    <aside style={{ width:220, background:'var(--ink-2)', borderRight:'1px solid var(--rim-2)', display:'flex', flexDirection:'column', minHeight:'100vh', transition:'background 0.3s' }}>

      {/* Logo */}
      <div style={{ padding:'18px 16px 14px', borderBottom:'1px solid var(--rim-2)' }}>
        <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:10 }}>
          <div style={{ width:30, height:30, background:'var(--amber)', display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0 }} className="a-pulse-a">
            <svg viewBox="0 0 16 16" fill="var(--surface)" width="16" height="16">
              <circle cx="8" cy="8" r="3"/>
              <circle cx="8" cy="8" r="6" fill="none" stroke="var(--surface)" strokeWidth="1.5"/>
              <line x1="8" y1="2"  x2="8" y2="0"  stroke="var(--surface)" strokeWidth="2"/>
              <line x1="8" y1="16" x2="8" y2="14" stroke="var(--surface)" strokeWidth="2"/>
              <line x1="2" y1="8"  x2="0" y2="8"  stroke="var(--surface)" strokeWidth="2"/>
              <line x1="16" y1="8" x2="14" y2="8" stroke="var(--surface)" strokeWidth="2"/>
            </svg>
          </div>
          <div>
            <div style={{ fontFamily:"'Syne',sans-serif", fontWeight:800, fontSize:15, color:'var(--text-0)', letterSpacing:'0.08em' }} className="a-flicker">
              IRIS
            </div>
            <div className="label-xs" style={{ fontSize:8, letterSpacing:'0.18em', color:'var(--text-3)' }}>
              INTELLIGENCE PLATFORM
            </div>
          </div>
        </div>
        <div className="coord" style={{ color:'var(--text-4)' }}>SYS // MoSPI-SIP-v2.1</div>
      </div>

      {/* Language switcher */}
      <div style={{ padding:'10px 16px', borderBottom:'1px solid var(--rim-2)', display:'flex', gap:6 }}>
        {[
          { code:'en', label:'EN' },
          { code:'hi', label:'हि' },
        ].map(l => (
          <button
            key={l.code}
            onClick={() => setLang(l.code)}
            style={{
              flex:1, padding:'5px 0',
              fontFamily:"'Space Mono',monospace",
              fontSize:11, letterSpacing:'0.08em',
              cursor:'pointer', borderRadius:2,
              border: lang === l.code ? '1px solid var(--amber)' : '1px solid var(--rim-2)',
              background: lang === l.code ? 'var(--amber-glow)' : 'transparent',
              color: lang === l.code ? 'var(--amber)' : 'var(--text-3)',
              fontWeight: lang === l.code ? 700 : 400,
              transition:'all 0.15s',
            }}
          >
            {l.label}
          </button>
        ))}
      </div>

      {/* Dataset status */}
      <div style={{ padding:'12px 16px', borderBottom:'1px solid var(--rim-2)' }}>
        {datasetReady ? (
          <div className="panel panel-green scanline" style={{ padding:'10px 12px' }}>
            <div style={{ display:'flex', alignItems:'center', gap:6, marginBottom:6 }}>
              <span className="status-dot status-live"></span>
              <span className="label-xs" style={{ color:'var(--green)', fontSize:9 }}>
                {t('active_dataset').toUpperCase()}
              </span>
            </div>
            <div className="data-val" style={{ fontSize:11, color:'var(--text-0)', marginBottom:3, wordBreak:'break-all' }}>
              {filename}
            </div>
            <div className="coord">{rowCount?.toLocaleString()} RECORDS</div>
          </div>
        ) : (
          <div className="panel" style={{ padding:'10px 12px' }}>
            <div style={{ display:'flex', alignItems:'center', gap:6, marginBottom:4 }}>
              <span className="status-dot status-off"></span>
              <span className="label-xs" style={{ fontSize:9 }}>{t('no_dataset').toUpperCase()}</span>
            </div>
            <div className="coord">UPLOAD TO INITIALISE</div>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav style={{ flex:1, padding:'8px 0' }}>
        {NAV_KEYS.map(item => (
          <NavLink key={item.path} to={item.path} style={{ display:'block', textDecoration:'none' }}>
            {({ isActive }) => (
              <div style={{
                display:'flex', alignItems:'center', gap:10,
                padding:'11px 16px',
                borderLeft: isActive ? '2px solid var(--amber)' : '2px solid transparent',
                background: isActive ? 'var(--amber-glow)' : 'transparent',
                transition:'all 0.15s', cursor:'pointer',
              }}>
                <span className="coord" style={{ width:18, color: isActive ? 'var(--amber)' : 'var(--text-4)', fontSize:9 }}>
                  {item.code}
                </span>
                <svg viewBox="0 0 16 16" fill="none" stroke={isActive ? 'var(--amber)' : 'var(--text-3)'} strokeWidth="1.2" style={{ width:14, height:14, flexShrink:0 }}>
                  <path d={item.icon}/>{item.d2 && <path d={item.d2}/>}
                </svg>
                <span style={{
                  fontFamily:"'Space Mono',monospace", fontSize:11,
                  letterSpacing:'0.1em',
                  color: isActive ? 'var(--amber)' : 'var(--text-2)',
                  transition:'color 0.15s',
                }}>
                  {t(item.tkey)}
                </span>
                {isActive && <span className="status-dot status-warn" style={{ marginLeft:'auto' }}></span>}
              </div>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div style={{ padding:'12px 16px', borderTop:'1px solid var(--rim-2)' }}>
        <div style={{ display:'flex', alignItems:'center', gap:6, marginBottom:5 }}>
          <span className="status-dot status-live"></span>
          <span className="label-xs" style={{ fontSize:9, color:'var(--green)' }}>ALL SYSTEMS NOMINAL</span>
        </div>
        <div className="coord" style={{ color:'var(--text-4)' }}>GOV-IN // STATATHON-2025</div>
        <div className="coord" style={{ color:'var(--text-4)', marginTop:2 }}>TEAM NEXUS // CLEARANCE: L3</div>
      </div>
    </aside>
  )
}