export default function ErrorCard({ message, onRetry }) {
  return (
    <div style={{
      background:'rgba(239,68,68,0.05)', border:'1px solid rgba(239,68,68,0.2)',
      padding:16, display:'flex', alignItems:'flex-start', gap:12,
    }}>
      <div style={{ width:2, height:'100%', minHeight:40, background:'var(--red)', flexShrink:0 }}></div>
      <div style={{ flex:1 }}>
        <div className="label-xs" style={{ color:'var(--red)', marginBottom:6 }}>QUERY FAILED</div>
        <div className="coord" style={{ color:'rgba(239,68,68,0.7)', lineHeight:1.8 }}>{message}</div>
        {onRetry && (
          <button onClick={onRetry} className="iris-btn iris-btn-ghost" style={{ marginTop:12, padding:'4px 12px' }}>
            RETRY
          </button>
        )}
      </div>
    </div>
  )
}