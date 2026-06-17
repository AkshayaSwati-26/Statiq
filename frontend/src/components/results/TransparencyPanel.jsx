import { useState } from 'react'
import { useLang } from '../../hooks/useLang'

export default function TransparencyPanel({ result }) {
  const { t } = useLang()
  const [sqlOpen, setSqlOpen] = useState(false)
  if (!result) return null

  return (
    <div className="panel a-iris" style={{ overflow:'hidden' }}>

      <div style={{
        padding:'14px 20px',
        borderBottom:'1px solid var(--rim-2)',
        display:'flex', alignItems:'center', gap:10,
        background:'var(--surface-2)',
      }}>
        <div style={{ width:3, height:20, background:'var(--cyan)' }}></div>
        <span className="label-sm" style={{ fontSize:12 }}>
          TRANSPARENCY &amp; TRACEABILITY
        </span>
      </div>

      <div style={{ padding:28, display:'flex', flexDirection:'column', gap:28 }}>

        {/* Formula — large, prominent */}
        <div>
          <div className="label-xs" style={{ color:'var(--amber)', marginBottom:12, fontSize:11 }}>
            // {t('result_formula')}
          </div>
          <div style={{
            background:'var(--amber-glow)',
            border:'1px solid rgba(217,119,6,0.3)',
            borderLeft:'4px solid var(--amber)',
            padding:'20px 24px',
          }}>
            <p style={{
              fontFamily:"'DM Mono',monospace",
              fontSize:17,
              fontWeight:500,
              color:'var(--amber)',
              margin:0,
              lineHeight:1.6,
            }}>
              {result.formula}
            </p>
            {result.formula_note && (
              <p style={{
                fontFamily:"'Space Mono',monospace",
                fontSize:12,
                color:'var(--text-2)',
                margin:'12px 0 0',
                lineHeight:1.7,
              }}>
                {result.formula_note}
              </p>
            )}
          </div>
        </div>

        {/* Traceability — clean grid */}
        <div>
          <div className="label-xs" style={{ color:'var(--text-3)', marginBottom:12, fontSize:11 }}>
            // {t('result_trace')}
          </div>
          <div style={{
            display:'grid',
            gridTemplateColumns:'repeat(auto-fill, minmax(180px, 1fr))',
            gap:10,
          }}>
            {result.traceability && Object.entries(result.traceability).map(([key, val]) => (
              <div key={key} style={{
                background:'var(--ink-2)',
                border:'1px solid var(--rim-2)',
                padding:'14px 16px',
              }}>
                <div className="coord" style={{ color:'var(--text-3)', fontSize:10, marginBottom:6 }}>
                  {key.toUpperCase()}
                </div>
                <div className="data-val" style={{ fontSize:15, color:'var(--text-0)' }}>
                  {val}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* SQL — collapsible */}
        <div>
          <button
            onClick={() => setSqlOpen(o => !o)}
            style={{
              display:'flex', alignItems:'center', gap:10,
              background:'none', border:'none', cursor:'pointer',
              padding:0, width:'100%',
            }}
          >
            <div className="label-xs" style={{ color:'var(--text-3)', fontSize:11 }}>
              // {t('result_sql')}
            </div>
            <div style={{ flex:1, height:1, background:'var(--rim-2)' }}></div>
            <span style={{
              fontFamily:"'Space Mono',monospace", fontSize:11,
              color:'var(--cyan)', border:'1px solid var(--rim-2)',
              padding:'2px 10px', borderRadius:2,
            }}>
              {sqlOpen ? 'HIDE' : 'SHOW'}
            </span>
          </button>

          {sqlOpen && (
            <div style={{
              marginTop:12,
              background:'#010812',
              border:'1px solid rgba(34,211,238,0.2)',
              padding:20,
              overflowX:'auto',
            }}>
              <pre style={{
                fontFamily:"'DM Mono',monospace",
                fontSize:14,
                color:'#4ade80',
                lineHeight:1.8,
                margin:0,
                whiteSpace:'pre-wrap',
                wordBreak:'break-word',
              }}>
                {result.sql}
              </pre>
            </div>
          )}
        </div>

        {/* How generated — readable paragraph */}
        <div>
          <div className="label-xs" style={{ color:'var(--text-3)', marginBottom:12, fontSize:11 }}>
            // {t('result_how')}
          </div>
          <div style={{
            background:'var(--cyan-glow)',
            border:'1px solid rgba(3,105,161,0.25)',
            borderLeft:'4px solid var(--cyan)',
            padding:'18px 22px',
          }}>
            <p style={{
              fontFamily:"'Space Mono',monospace",
              fontSize:14,
              color:'var(--text-1)',
              lineHeight:1.9,
              margin:0,
            }}>
              The system parsed your query, identified the indicator{' '}
              <strong style={{ color:'var(--text-0)' }}>"{result.indicator_name}"</strong>,
              matched it to the uploaded dataset{' '}
              <strong style={{ color:'var(--amber)' }}>{result.dataset_used}</strong>,
              applied weighted aggregation using survey multipliers,
              and returned aggregated population-level estimates.
              No individual records were accessed or exposed.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}