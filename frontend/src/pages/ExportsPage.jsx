import { useRef } from 'react'
import { useSession } from '../hooks/useSession'
import { useLang } from '../hooks/useLang'
import EmptyState from '../components/common/EmptyState'
import html2canvas from 'html2canvas'

export default function ExportsPage() {
  const { lastResult, filename, datasetReady } = useSession()
  const { t } = useLang()
  const previewRef = useRef()

  if (!datasetReady || !lastResult) {
    return (
      <EmptyState
        title="Nothing to Export"
        message="Run a query first, then come back here to export your results."
        buttonLabel={t('go_query')}
        buttonPath="/query"
      />
    )
  }

  const downloadCSV = () => {
    const headers = Object.keys(lastResult.data[0]).join(',')
    const rows    = lastResult.data.map(r => Object.values(r).join(',')).join('\n')
    trigger(new Blob([headers+'\n'+rows], { type:'text/csv' }), `${filename}_results.csv`)
  }

  const downloadJSON = () => {
    const payload = {
      metadata: { dataset:lastResult.dataset_used, indicator:lastResult.indicator_name, exported_at:new Date().toISOString(), records:lastResult.records_analyzed },
      formula: lastResult.formula,
      traceability: lastResult.traceability,
      data: lastResult.data,
    }
    trigger(new Blob([JSON.stringify(payload,null,2)], { type:'application/json' }), `${filename}_results.json`)
  }

  const downloadPNG = async () => {
    if (!previewRef.current) return
    const canvas = await html2canvas(previewRef.current, { scale:2 })
    trigger(await new Promise(r => canvas.toBlob(r)), `${filename}_chart.png`)
  }

  const trigger = (blob, name) => {
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = name; a.click()
    URL.revokeObjectURL(url)
  }

  const copyLink = () => {
    navigator.clipboard.writeText(window.location.href)
    alert('Link copied!')
  }

  const EXPORTS = [
    { title: t('export_csv'),  sub:'Tabular data for Excel, Stata, R',           action:downloadCSV,  accent:'amber'  },
    { title: t('export_json'), sub:'Structured data with metadata',               action:downloadJSON, accent:'cyan'   },
    { title: t('export_png'),  sub:'High-resolution chart for presentations',     action:downloadPNG,  accent:'green'  },
    { title: t('export_link'), sub:'Share this result with colleagues',            action:copyLink,     accent:'dim'    },
  ]

  const accentBorder = { amber:'rgba(217,119,6,0.3)', cyan:'rgba(3,105,161,0.3)', green:'rgba(5,150,105,0.3)', dim:'var(--rim-2)' }
  const accentColor  = { amber:'var(--amber)', cyan:'var(--cyan)', green:'var(--green)', dim:'var(--text-2)' }

  return (
    <div style={{ maxWidth:860, display:'flex', flexDirection:'column', gap:20 }}>

      <div className="a-iris">
        <div className="coord" style={{ color:'var(--amber)', marginBottom:6 }}>// {t('nav_export').toUpperCase()}</div>
        <h1 style={{ fontFamily:"'Syne',sans-serif", fontWeight:800, fontSize:26, color:'var(--text-0)' }}>
          Export Center
        </h1>
        <div className="label-xs" style={{ marginTop:4, color:'var(--text-3)' }}>
          {lastResult.dataset_used}
        </div>
      </div>

      {/* Result preview card */}
      <div ref={previewRef} className="panel a-iris d1" style={{ padding:24 }}>
        <div style={{ display:'flex', alignItems:'flex-start', justifyContent:'space-between', marginBottom:20 }}>
          <div>
            <div style={{ fontFamily:"'Syne',sans-serif", fontWeight:700, fontSize:18, color:'var(--text-0)', marginBottom:6 }}>
              {lastResult.indicator_name}
            </div>
            <div className="coord" style={{ color:'var(--text-3)' }}>{lastResult.dataset_used}</div>
          </div>
          <div style={{ textAlign:'right' }}>
            <div style={{ fontFamily:"'DM Mono',monospace", fontSize:36, fontWeight:500, color:'var(--amber)', lineHeight:1 }}>
              {lastResult.result_value}
            </div>
            <div className="coord" style={{ color:'var(--text-4)', marginTop:4 }}>Result Value</div>
          </div>
        </div>
        <div style={{ background:'var(--ink-2)', border:'1px solid var(--rim-2)', borderLeft:'3px solid var(--amber)', padding:'16px 20px', marginBottom:16 }}>
          <p style={{ fontFamily:"'DM Mono',monospace", fontSize:15, color:'var(--text-1)', lineHeight:1.9, margin:0 }}>
            {lastResult.explanation}
          </p>
        </div>
        <div style={{ background:'var(--amber-glow)', border:'1px solid rgba(217,119,6,0.25)', padding:'12px 16px' }}>
          <span style={{ fontFamily:"'DM Mono',monospace", fontSize:13, color:'var(--amber)' }}>
            {lastResult.formula}
          </span>
        </div>
      </div>

      {/* Export options */}
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:14 }}>
        {EXPORTS.map(exp => (
          <div key={exp.title} className="panel a-iris" style={{
            padding:20,
            borderColor: accentBorder[exp.accent],
            cursor:'pointer', transition:'transform 0.15s',
          }}
          onClick={exp.action}
          onMouseEnter={e => e.currentTarget.style.transform='translateY(-2px)'}
          onMouseLeave={e => e.currentTarget.style.transform='translateY(0)'}
          >
            <div style={{ marginBottom:14, opacity:0.7 }}>
              <svg viewBox="0 0 20 20" fill="none" stroke={accentColor[exp.accent]} strokeWidth="1.5" style={{ width:24, height:24 }}>
                <path d="M19 15v3a2 2 0 01-2 2H3a2 2 0 01-2-2v-3M10 14V2M5 9l5 5 5-5"/>
              </svg>
            </div>
            <div style={{ fontFamily:"'Syne',sans-serif", fontWeight:700, fontSize:16, color:'var(--text-0)', marginBottom:6 }}>
              {exp.title}
            </div>
            <div className="coord" style={{ color:'var(--text-3)', lineHeight:1.8 }}>{exp.sub}</div>
          </div>
        ))}
      </div>

      {/* Governance */}
      <div style={{
        background:'var(--ink-2)', border:'1px solid var(--rim-2)',
        borderLeft:'4px solid var(--cyan)',
        padding:'16px 20px', display:'flex', alignItems:'flex-start', gap:14,
      }}>
        <svg viewBox="0 0 20 20" fill="none" stroke="var(--cyan)" strokeWidth="1.5" style={{ width:22, height:22, flexShrink:0 }}>
          <rect x="3" y="11" width="14" height="8" rx="1"/><path d="M7 11V7a3 3 0 016 0v4"/>
        </svg>
        <div>
          <div className="label-xs" style={{ color:'var(--cyan)', marginBottom:6, fontSize:10 }}>
            // EXPORT GOVERNANCE NOTICE
          </div>
          <p style={{ fontFamily:"'Space Mono',monospace", fontSize:13, color:'var(--text-2)', lineHeight:1.8, margin:0 }}>
            All exported data contains only aggregated statistics.
            No individual microdata records are included.
            Dataset: <span style={{ color:'var(--amber)' }}>{filename}</span> · DPDP Act 2023 Compliant.
          </p>
        </div>
      </div>
    </div>
  )
}