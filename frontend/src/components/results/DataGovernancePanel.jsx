import { useLang } from '../../hooks/useLang'

export default function DataGovernancePanel({ result }) {
  const { t } = useLang()
  if (!result) return null

  return (
    <div className="panel a-iris" style={{ overflow:'hidden' }}>

      <div style={{
        padding:'14px 20px',
        borderBottom:'1px solid var(--rim-2)',
        display:'flex', alignItems:'center', gap:10,
        background:'var(--cyan-glow)',
      }}>
        <div style={{ width:3, height:20, background:'var(--cyan)' }}></div>
        <span className="label-sm" style={{ color:'var(--cyan)', fontSize:12 }}>
          {t('result_gov')}
        </span>
      </div>

      <div style={{ padding:28, display:'flex', flexDirection:'column', gap:20 }}>

        {/* Dataset Constraint — full width, prominent */}
        <div style={{
          background:'var(--ink-2)',
          border:'1px solid var(--rim-2)',
          borderLeft:'4px solid var(--cyan)',
          padding:'20px 24px',
        }}>
          <div className="label-xs" style={{ color:'var(--cyan)', marginBottom:10, fontSize:11 }}>
            // {t('result_constraint')}
          </div>
          <p style={{
            fontFamily:"'DM Mono',monospace",
            fontSize:16,
            color:'var(--text-0)',
            marginBottom:12,
            lineHeight:1.6,
          }}>
            {t('gov_constraint_desc')}
          </p>
          <div style={{
            display:'flex', alignItems:'center', gap:12,
            background:'var(--surface)',
            border:'1px solid var(--rim-2)',
            padding:'12px 16px',
          }}>
            <svg viewBox="0 0 20 20" fill="none" stroke="var(--amber)" strokeWidth="1.5" style={{ width:22, height:22, flexShrink:0 }}>
              <path d="M14 2H6a2 2 0 00-2 2v14a2 2 0 002 2h8a2 2 0 002-2V8l-4-6zM14 2v6h6"/>
            </svg>
            <div>
              <div style={{ fontFamily:"'DM Mono',monospace", fontSize:15, color:'var(--amber)', fontWeight:500 }}>
                {result.dataset_used}
              </div>
              <div className="coord" style={{ color:'var(--text-3)', marginTop:3, fontSize:10 }}>
                {t('gov_no_external')}
              </div>
            </div>
          </div>
        </div>

        {/* Privacy status — compact */}
        <div style={{
          display:'flex', alignItems:'center', gap:16,
          background: result.privacy_safe ? 'var(--green-glow)' : 'rgba(239,68,68,0.06)',
          border:`1px solid ${result.privacy_safe ? 'rgba(5,150,105,0.35)' : 'rgba(239,68,68,0.35)'}`,
          borderLeft:`4px solid ${result.privacy_safe ? 'var(--green)' : 'var(--red)'}`,
          padding:'18px 22px',
        }}>
          <svg viewBox="0 0 24 24" fill="none" stroke={result.privacy_safe ? 'var(--green)' : 'var(--red)'} strokeWidth="1.5" style={{ width:28, height:28, flexShrink:0 }}>
            <rect x="3" y="11" width="18" height="11" rx="2"/>
            <path d="M7 11V7a5 5 0 0110 0v4"/>
          </svg>
          <div>
            <div style={{ fontFamily:"'Syne',sans-serif", fontWeight:700, fontSize:18, color: result.privacy_safe ? 'var(--green)' : 'var(--red)', marginBottom:4 }}>
              {result.privacy_safe ? t('gov_privacy_safe') : t('gov_suppressed')}
            </div>
            <div style={{ fontFamily:"'Space Mono',monospace", fontSize:13, color:'var(--text-2)', lineHeight:1.7 }}>
              {result.privacy_safe ? `${t('gov_sample_met')} · ${t('gov_aggregated')}` : result.privacy_message}
            </div>
          </div>
        </div>

        {/* Query Explanation */}
        <div style={{
          background:'var(--ink-2)',
          border:'1px solid var(--rim-2)',
          padding:'20px 24px',
        }}>
          <div className="label-xs" style={{ color:'var(--text-3)', marginBottom:12, fontSize:11 }}>
            // {t('result_explain')}
          </div>
          <p style={{
            fontFamily:"'DM Mono',monospace",
            fontSize:15,
            color:'var(--text-1)',
            lineHeight:1.9,
            margin:0,
          }}>
            Filtered{' '}
            <span style={{ color:'var(--amber)', fontWeight:500 }}>{result.dataset_used}</span>{' '}
            records for{' '}
            <span style={{ color:'var(--cyan)' }}>
              {result.traceability?.state || 'selected region'}
            </span>
            {result.traceability?.sector ? `, ${result.traceability.sector} sector` : ''}
            {result.traceability?.gender ? `, ${result.traceability.gender} respondents` : ''}.
            {' '}Computed weighted average{' '}
            <span style={{ color:'var(--text-0)', fontWeight:500 }}>
              {result.traceability?.indicator || result.indicator_name}
            </span>
            {' '}using{' '}
            <span style={{ color:'var(--green)' }}>
              {result.traceability?.aggregation || 'UPSS methodology'}
            </span>.
            Survey multipliers applied to represent population-level estimates.
          </p>
        </div>

      </div>
    </div>
  )
}