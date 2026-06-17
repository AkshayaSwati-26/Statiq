import { useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { useSession } from '../hooks/useSession'
import { MOCK_DASHBOARD_STATS } from '../utils/mockData'
import { uploadDataset } from '../services/api'

const S = MOCK_DASHBOARD_STATS

function StatBlock({ code, label, value, accent, delay }) {
  const color = { amber:'var(--amber)', cyan:'var(--cyan)', green:'var(--green)', dim:'var(--text-1)' }[accent]
  const bg    = { amber:'var(--amber-glow)', cyan:'var(--cyan-glow)', green:'var(--green-glow)', dim:'transparent' }[accent]
  const border= { amber:'rgba(245,158,11,0.2)', cyan:'rgba(34,211,238,0.2)', green:'rgba(16,185,129,0.2)', dim:'var(--rim)' }[accent]
  return (
    <div className={`panel a-iris d${delay}`} style={{ padding:20, borderColor:border, background:`var(--surface)`, position:'relative', overflow:'hidden' }}>
      <div style={{ position:'absolute', top:0, left:0, right:0, height:2, background:`linear-gradient(90deg, ${color}, transparent)`, opacity:0.6 }}></div>
      <div className="coord" style={{ marginBottom:10, color:'var(--text-3)' }}>{code}</div>
      <div className="a-count" style={{
        fontFamily:'var(--font-data)', fontSize:32, fontWeight:500,
        color, letterSpacing:'-0.02em', lineHeight:1, marginBottom:8,
      }}>
        {value}
      </div>
      <div className="label-xs">{label}</div>
    </div>
  )
}

export default function DashboardHome() {
  const navigate = useNavigate()
  const { datasetReady, filename, rowCount, uploadTime, datasetId, columns, setDataset, clearDataset } = useSession()
  const user = useSession(state => state.user)

  const [loadingDataset, setLoadingDataset] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')

  const handleLoadDataset = async (type) => {
    setLoadingDataset(true)
    setErrorMsg('')
    try {
      const fileName = type === 'hces' ? 'api_hces_members.csv' : 'api_plfs_person.csv'
      const mockFile = new File([], fileName)
      const result = await uploadDataset(mockFile)
      setDataset(result)
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Access Denied: You do not have permission to access this dataset.')
    } finally {
      setLoadingDataset(false)
    }
  }

  const renderDatasetSelector = () => {
    const isFree = user?.scope === 'public'
    return (
      <div style={{ display:'flex', flexDirection:'column', gap:12 }}>
        <div className="coord" style={{ color:'var(--text-3)', marginBottom:4 }}>
          // SELECT SURVEY DATASET TO INITIATE ANALYSIS
        </div>
        
        {/* PLFS Card */}
        <div
          onClick={() => !loadingDataset && handleLoadDataset('plfs')}
          style={{
            background:'var(--ink-2)', border:'1px solid var(--rim-2)',
            padding:14, cursor: loadingDataset ? 'not-allowed' : 'pointer',
            transition:'all 0.15s', position:'relative', borderRadius: 2
          }}
          onMouseEnter={e => { if (!loadingDataset) e.currentTarget.style.borderColor='var(--amber)' }}
          onMouseLeave={e => { e.currentTarget.style.borderColor='var(--rim-2)' }}
        >
          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:6 }}>
            <span className="label-sm" style={{ color:'var(--amber)', fontSize:12, fontWeight:700 }}>PLFS 2024 (Annual Survey)</span>
            <span className="tag tag-dim" style={{ fontSize:9 }}>PUBLIC / FREE</span>
          </div>
          <p className="coord" style={{ fontSize:10, margin:0, color:'var(--text-2)', lineHeight:1.4 }}>
            Periodic Labour Force Survey. Access employment rates, unemployment metrics, and labour force participation statistics.
          </p>
        </div>

        {/* HCES Card */}
        <div
          onClick={() => {
            if (isFree) {
              alert('HCES is a Premium dataset. Click "Upgrade to Premium" in the sidebar to access it.')
              return
            }
            if (!loadingDataset) handleLoadDataset('hces')
          }}
          style={{
            background: isFree ? 'rgba(255,255,255,0.01)' : 'var(--ink-2)',
            border: isFree ? '1px dashed var(--rim-2)' : '1px solid var(--rim-2)',
            padding:14,
            cursor: isFree ? 'default' : loadingDataset ? 'not-allowed' : 'pointer',
            opacity: isFree ? 0.55 : 1,
            transition:'all 0.15s', position:'relative', borderRadius: 2
          }}
          onMouseEnter={e => { if (!isFree && !loadingDataset) e.currentTarget.style.borderColor='var(--cyan)' }}
          onMouseLeave={e => { e.currentTarget.style.borderColor=isFree ? 'var(--rim-2)' : 'var(--rim-2)' }}
        >
          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:6 }}>
            <span className="label-sm" style={{ color: isFree ? 'var(--text-3)' : 'var(--cyan)', fontSize:12, fontWeight:700 }}>
              HCES 2023 (Members Survey) {isFree && '🔒'}
            </span>
            <span className="tag" style={{ fontSize:9, background:'rgba(34,211,238,0.15)', color:'var(--cyan)' }}>PREMIUM ONLY</span>
          </div>
          <p className="coord" style={{ fontSize:10, margin:0, color: isFree ? 'var(--text-4)' : 'var(--text-2)', lineHeight:1.4 }}>
            Household Consumption Expenditure Survey. Access deep analytics on household size, demographics, and consumption data.
          </p>
          {isFree && (
            <div style={{ marginTop:8, display:'flex', alignItems:'center', gap:4 }}>
              <span className="coord" style={{ color:'var(--amber)', fontSize:9, fontWeight:700 }}>✦ UPGRADE REQUIRED TO UNLOCK</span>
            </div>
          )}
        </div>

        {loadingDataset && (
          <div className="coord" style={{ color:'var(--amber)', textAlign:'center', marginTop:4 }}>
            // LOADING SECURE VIEW ENVIRONMENT...
          </div>
        )}

        {errorMsg && (
          <div style={{ color:'var(--red)', fontSize:11, fontFamily:"'Space Mono',monospace", background:'rgba(239,68,68,0.06)', border:'1px solid rgba(239,68,68,0.2)', padding:'6px 10px', marginTop:4 }}>
            {errorMsg}
          </div>
        )}
      </div>
    )
  }

  const quickActions = [
    (user?.scope === 'admin')
      ? { code:'ACT-01', label:'UPLOAD DATASET',   sub:'Ingest survey microdata',    path:'/ingest',  accent:'amber'  }
      : { code:'ACT-01', label:'SELECT DATASET',   sub:'Choose survey to analyze',    path:'/dashboard',  accent:'amber'  },
    { code:'ACT-02', label:'NATURAL LANGUAGE',  sub:'Query in plain English',     path:'/query',   accent:'cyan'   },
    { code:'ACT-03', label:'QUERY BUILDER',     sub:'Visual no-code analysis',    path:'/query',   accent:'green'  },
    { code:'ACT-04', label:'EXPORT RESULTS',    sub:'CSV · JSON · PNG report',    path:'/exports', accent:'dim'    },
  ]

  return (
    <div style={{ maxWidth:1100, display:'flex', flexDirection:'column', gap:20 }}>

      {/* Header */}
      <div className="a-iris" style={{ display:'flex', alignItems:'flex-start', justifyContent:'space-between' }}>
        <div>
          <div className="coord" style={{ color:'var(--amber)', marginBottom:6 }}>
            // SYSTEM OVERVIEW // {new Date().toLocaleDateString('en-IN')}
          </div>
          <div style={{ display:'flex', alignItems:'center', gap:10 }}>
            <h1 style={{ fontFamily:'var(--font-display)', fontWeight:800, fontSize:26, color:'var(--text-0)', letterSpacing:'0.04em', margin:0 }}>
              MISSION CONTROL
            </h1>
            {user && (
              <span className="tag" style={{
                background: user.scope === 'admin' ? 'rgba(239,68,68,0.12)' : user.scope === 'research' ? 'rgba(34,211,238,0.12)' : 'rgba(255,255,255,0.04)',
                color: user.scope === 'admin' ? '#ef4444' : user.scope === 'research' ? 'var(--cyan)' : 'var(--text-3)',
                borderColor: user.scope === 'admin' ? '#ef4444' : user.scope === 'research' ? 'var(--cyan)' : 'var(--rim-2)',
                borderWidth: 1, borderStyle: 'solid',
                fontSize: 10, padding: '3px 8px', borderRadius: 2,
                fontFamily: "'Space Mono', monospace", fontWeight: 700
              }}>
                {user.scope === 'admin' ? 'ADMIN' : user.scope === 'research' ? (user.isSimulatedPremium ? 'PREMIUM (MOCK)' : 'PREMIUM') : 'FREE'}
              </span>
            )}
          </div>
          <div className="label-xs" style={{ marginTop:4 }}>MoSPI Survey Intelligence Platform · Real-time analytics</div>
        </div>
        <div style={{ display:'flex', alignItems:'center', gap:8 }}>
          <span className="status-dot status-live"></span>
          <span className="label-xs" style={{ color:'var(--green)' }}>ALL SYSTEMS NOMINAL</span>
        </div>
      </div>

      {/* Stat blocks */}
      <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:12 }}>
        <StatBlock code="// STAT-01" label="DATASETS INGESTED"   value={S.total_datasets}      accent="amber"  delay={1} />
        <StatBlock code="// STAT-02" label="QUERIES EXECUTED"    value={S.total_queries}       accent="cyan"   delay={2} />
        <StatBlock code="// STAT-03" label="RECORDS PROCESSED"   value={S.records_processed}   accent="green"  delay={3} />
        <StatBlock code="// STAT-04" label="ACTIVE DATASET"      value={datasetReady ? '01':'00'} accent="dim" delay={4} />
      </div>

      {/* Main grid */}
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1.6fr', gap:16 }}>

        {/* Dataset panel */}
        <div className={`panel scanline a-iris d2 ${datasetReady ? 'panel-green' : ''}`} style={{ padding:0, overflow:'hidden' }}>
          <div style={{ padding:'12px 16px', borderBottom:'1px solid var(--rim)', display:'flex', alignItems:'center', gap:8 }}>
            <div style={{ width:2, height:14, background:'var(--amber)' }}></div>
            <span className="label-sm">ACTIVE DATASET</span>
            {datasetReady && <span className="tag tag-green" style={{ marginLeft:'auto' }}>LOADED</span>}
          </div>

          <div style={{ padding:16 }}>
            {datasetReady ? (
              <div style={{ display:'flex', flexDirection:'column', gap:12 }}>
                <div className="panel panel-amber" style={{ padding:14 }}>
                  <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:10 }}>
                    <svg viewBox="0 0 16 16" fill="none" stroke="var(--amber)" strokeWidth="1.2" className="w-4 h-4">
                      <path d="M9 1H3a1 1 0 00-1 1v12a1 1 0 001 1h10a1 1 0 001-1V7L9 1z"/>
                      <path d="M9 1v6h6"/>
                    </svg>
                    <span className="data-val" style={{ fontSize:12, color:'var(--amber)', wordBreak:'break-all' }}>{filename}</span>
                  </div>
                  <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:8 }}>
                    {[
                      { k:'RECORDS', v: rowCount?.toLocaleString() },
                      { k:'COLUMNS', v: columns?.length },
                      { k:'DATASET ID', v: datasetId },
                      { k:'STATUS', v: 'READY' },
                    ].map(item => (
                      <div key={item.k} style={{ background:'var(--ink-2)', padding:'6px 10px' }}>
                        <div className="coord">{item.k}</div>
                        <div className="data-val" style={{ fontSize:11, color: item.k === 'STATUS' ? 'var(--green)' : 'var(--text-0)' }}>
                          {item.v}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
                <button onClick={() => navigate('/query')} className="iris-btn iris-btn-primary" style={{ width:'100%' }}>
                  LAUNCH QUERY WORKSPACE
                </button>
                <button
                  onClick={() => {
                    if (user?.scope === 'admin') {
                      navigate('/ingest')
                    } else {
                      clearDataset()
                    }
                  }}
                  className="iris-btn iris-btn-ghost"
                  style={{ width:'100%' }}
                >
                  {user?.scope === 'admin' ? 'REPLACE DATASET' : 'CHANGE DATASET'}
                </button>
              </div>
            ) : (
              renderDatasetSelector()
            )}
          </div>
        </div>

        {/* Activity feed */}
        <div className="panel a-iris d3" style={{ padding:0, overflow:'hidden' }}>
          <div style={{ padding:'12px 16px', borderBottom:'1px solid var(--rim)', display:'flex', alignItems:'center', justifyContent:'space-between' }}>
            <div style={{ display:'flex', alignItems:'center', gap:8 }}>
              <div style={{ width:2, height:14, background:'var(--cyan)' }}></div>
              <span className="label-sm">ACTIVITY STREAM</span>
            </div>
            <div style={{ display:'flex', alignItems:'center', gap:6 }}>
              <span className="status-dot status-live"></span>
              <span className="coord" style={{ color:'var(--green)' }}>LIVE</span>
            </div>
          </div>
          <div style={{ padding:12, display:'flex', flexDirection:'column', gap:2 }}>
            {S.recent_activity.map((item, i) => (
              <div key={i} className={`a-slide d${i+1}`} style={{
                display:'flex', alignItems:'center', gap:12,
                padding:'10px 12px',
                background: i === 0 ? 'rgba(34,211,238,0.04)' : 'transparent',
                borderLeft: i === 0 ? '2px solid var(--cyan)' : '2px solid transparent',
                transition:'background 0.2s',
              }}>
                <span className="coord" style={{ width:20, color:'var(--text-3)', textAlign:'right', flexShrink:0 }}>
                  {String(i+1).padStart(2,'0')}
                </span>
                <div style={{ flex:1, minWidth:0 }}>
                  <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:2 }}>
                    <span className={`tag ${item.action.includes('upload') ? 'tag-amber' : item.action.includes('export') ? 'tag-green' : 'tag-cyan'}`} style={{ fontSize:8, padding:'1px 6px' }}>
                      {item.action.includes('upload') ? 'INGEST' : item.action.includes('export') ? 'EXPORT' : 'QUERY'}
                    </span>
                    <span className="data-val" style={{ fontSize:11, truncate:true }}>{item.detail}</span>
                  </div>
                  <span className="coord">{item.action}</span>
                </div>
                <span className="coord" style={{ flexShrink:0 }}>{item.time}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Quick actions */}
      <div className="panel a-iris d4" style={{ padding:0, overflow:'hidden' }}>
        <div style={{ padding:'12px 16px', borderBottom:'1px solid var(--rim)', display:'flex', alignItems:'center', gap:8 }}>
          <div style={{ width:2, height:14, background:'var(--green)' }}></div>
          <span className="label-sm">QUICK ACTIONS</span>
        </div>
        <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:0 }}>
          {quickActions.map((a, i) => {
            const c = { amber:'var(--amber)', cyan:'var(--cyan)', green:'var(--green)', dim:'var(--text-1)' }[a.accent]
            return (
              <button key={a.code} onClick={() => navigate(a.path)} style={{
                padding:'20px 16px',
                borderRight: i < 3 ? '1px solid var(--rim)' : 'none',
                background:'transparent', cursor:'pointer',
                textAlign:'left', transition:'background 0.15s',
                display:'flex', flexDirection:'column', gap:8,
              }}
              onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.02)'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
              >
                <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between' }}>
                  <span className="coord" style={{ color:'var(--text-3)' }}>{a.code}</span>
                  <svg viewBox="0 0 12 12" fill="none" stroke={c} strokeWidth="1.2" className="w-3 h-3" style={{ opacity:0.6 }}>
                    <path d="M2 10L10 2M10 2H5M10 2v5"/>
                  </svg>
                </div>
                <div className="label-sm" style={{ color: c, letterSpacing:'0.1em' }}>{a.label}</div>
                <div className="coord">{a.sub}</div>
              </button>
            )
          })}
        </div>
      </div>

      {/* Classification bar */}
      <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', paddingTop:8, borderTop:'1px solid var(--rim)' }}>
        <span className="coord">IRIS v2.1 // MoSPI SURVEY INTELLIGENCE PLATFORM // TEAM NEXUS</span>
        <span className="coord">CLASSIFICATION: OFFICIAL USE ONLY // DPDP ACT 2023</span>
      </div>
    </div>
  )
}