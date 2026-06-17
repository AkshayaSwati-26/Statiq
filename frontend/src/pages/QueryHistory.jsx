import { useSession } from '../hooks/useSession'
import { useNavigate } from 'react-router-dom'
import { useLang } from '../hooks/useLang'
import EmptyState from '../components/common/EmptyState'

export default function QueryHistory() {
  const { queryHistory, filename, setResult } = useSession()
const { t, lang } = useLang()
  const navigate = useNavigate()

  if (!queryHistory.length) {
    return (
      <EmptyState
        title={lang === 'hi' ? 'कोई इतिहास नहीं' : 'No Query History'}
        message={lang === 'hi' ? 'प्रश्न चलाने के बाद यहाँ दिखेगा।' : 'Your query history will appear here after you run your first query.'}
        buttonLabel={t('go_query')}
        buttonPath="/query"
      />
    )
  }

  return (
    <div style={{ maxWidth:900, display:'flex', flexDirection:'column', gap:20 }}>

      <div className="a-iris">
        <div className="coord" style={{ color:'var(--amber)', marginBottom:6 }}>// {t('nav_history').toUpperCase()}</div>
        <h1 style={{ fontFamily:"'Syne',sans-serif", fontWeight:800, fontSize:26, color:'var(--text-0)' }}>
          {t('nav_history')}
        </h1>
        <div className="label-xs" style={{ marginTop:4, color:'var(--text-3)' }}>
          {queryHistory.length} queries · {filename}
        </div>
      </div>

      <div style={{ display:'flex', flexDirection:'column', gap:10 }}>
        {queryHistory.map((item, i) => (
          <div key={item.id} className={`panel a-iris d${Math.min(i+1,6)}`} style={{ padding:20 }}>
            <div style={{ display:'flex', alignItems:'flex-start', gap:16 }}>
              <div style={{
                width:36, height:36,
                background:'var(--amber-glow)',
                border:'1px solid rgba(217,119,6,0.3)',
                display:'flex', alignItems:'center', justifyContent:'center',
                flexShrink:0,
              }}>
                <span style={{ fontFamily:"'DM Mono',monospace", fontSize:13, color:'var(--amber)', fontWeight:500 }}>
                  {String(queryHistory.length - i).padStart(2,'0')}
                </span>
              </div>

              <div style={{ flex:1, minWidth:0 }}>
                <div style={{ fontFamily:"'DM Mono',monospace", fontSize:15, color:'var(--text-0)', marginBottom:8, lineHeight:1.5 }}>
                  "{item.query}"
                </div>
                <div style={{ display:'flex', alignItems:'center', gap:12, flexWrap:'wrap' }}>
                  <span className="coord" style={{ color:'var(--text-4)' }}>{item.time}</span>
                  {item.result && (
                    <>
                      <span style={{ color:'var(--rim-2)' }}>·</span>
                      <span className="tag tag-amber" style={{ fontSize:9 }}>
                        {item.result.result_value}
                      </span>
                      <span style={{ color:'var(--rim-2)' }}>·</span>
                      <span className="tag tag-green" style={{ fontSize:9 }}>
                        {item.result.confidence_score}% CONFIDENCE
                      </span>
                    </>
                  )}
                </div>
              </div>

              {item.result && (
                <button
                  onClick={() => { setResult(item.result, item.query); navigate('/results') }}
                  className="iris-btn iris-btn-ghost"
                  style={{ fontSize:10, padding:'6px 14px', flexShrink:0 }}
                >
                  VIEW →
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}