import { useLang } from '../../hooks/useLang'

export default function AIExplanationPanel({ result }) {
  const { t } = useLang()
  if (!result) return null

  return (
    <div className="panel a-iris" style={{ overflow:'hidden' }}>

      {/* Header */}
      <div style={{
        padding:'14px 20px',
        borderBottom:'1px solid var(--rim-2)',
        background:'linear-gradient(90deg, var(--amber-glow), transparent)',
        display:'flex', alignItems:'center', justifyContent:'space-between',
      }}>
        <div style={{ display:'flex', alignItems:'center', gap:10 }}>
          <div style={{ width:3, height:20, background:'var(--amber)' }}></div>
          <span className="label-sm" style={{ color:'var(--amber)', fontSize:12 }}>
            {t('result_meaning')}
          </span>
        </div>
        <div style={{
          display:'flex', alignItems:'center', gap:8,
          background:'var(--green-glow)',
          border:'1px solid rgba(5,150,105,0.3)',
          padding:'4px 12px',
        }}>
          <span className="status-dot status-live"></span>
          <span className="data-val" style={{ fontSize:13, color:'var(--green)' }}>
            {result.confidence_score}% {t('result_confidence')}
          </span>
        </div>
      </div>

      <div style={{ padding:28 }}>

        {/* Main explanation — big readable text */}
        <div style={{
          background:'var(--ink-2)',
          border:'1px solid var(--rim-2)',
          borderLeft:'4px solid var(--amber)',
          padding:'20px 24px',
          marginBottom:24,
        }}>
          <p style={{
            fontFamily:"'DM Mono', monospace",
            fontSize:16,
            color:'var(--text-0)',
            lineHeight:1.9,
            margin:0,
          }}>
            {result.explanation}
          </p>
        </div>

        {/* Confidence bar */}
        <div style={{ marginBottom:24 }}>
          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:10 }}>
            <span className="label-xs" style={{ color:'var(--text-2)', fontSize:11 }}>
              {t('result_confidence')}
            </span>
            <span style={{ fontFamily:"'DM Mono',monospace", fontSize:16, fontWeight:500, color:'var(--green)' }}>
              {result.confidence_score}%
            </span>
          </div>
          <div className="iris-bar-track">
            <div className="iris-bar-fill" style={{ width:`${result.confidence_score}%` }}></div>
          </div>
          <div className="coord" style={{ marginTop:8, color:'var(--text-3)', fontSize:10 }}>
            High confidence — query clearly understood and mapped to dataset columns
          </div>
        </div>

        {/* Dataset scope notice */}
        <div style={{
          display:'flex', alignItems:'center', gap:12,
          background:'var(--green-glow)',
          border:'1px solid rgba(5,150,105,0.3)',
          padding:'14px 18px',
        }}>
          <svg viewBox="0 0 20 20" fill="none" stroke="var(--green)" strokeWidth="1.5" style={{ width:20, height:20, flexShrink:0 }}>
            <rect x="4" y="9" width="12" height="10" rx="1"/>
            <path d="M7 9V6a3 3 0 016 0v3"/>
          </svg>
          <p style={{ fontFamily:"'Space Mono',monospace", fontSize:13, color:'var(--green)', margin:0 }}>
            {t('result_export')} · {result.dataset_used}
          </p>
        </div>
      </div>
    </div>
  )
}