import { useNavigate } from 'react-router-dom'

export default function EmptyState({ title, message, buttonLabel, buttonPath }) {
  const navigate = useNavigate()
  return (
    <div style={{ display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', padding:'80px 24px', textAlign:'center' }}>
      <div style={{ width:64, height:64, border:'1px solid var(--rim-2)', display:'flex', alignItems:'center', justifyContent:'center', marginBottom:20, position:'relative' }}>
        <svg viewBox="0 0 32 32" fill="none" stroke="var(--text-3)" strokeWidth="1" className="w-8 h-8">
          <path d="M16 4L4 10v12l12 6 12-6V10L16 4z"/>
          <path d="M4 10l12 6M28 10l-12 6M16 16v12"/>
        </svg>
        <div style={{ position:'absolute', top:-1, left:-1, width:8, height:8, borderTop:'1px solid var(--cyan)', borderLeft:'1px solid var(--cyan)' }}></div>
        <div style={{ position:'absolute', bottom:-1, right:-1, width:8, height:8, borderBottom:'1px solid var(--cyan)', borderRight:'1px solid var(--cyan)' }}></div>
      </div>
      <div className="label-xs" style={{ color:'var(--amber)', marginBottom:8 }}>{title?.toUpperCase()}</div>
      <div className="coord" style={{ maxWidth:320, marginBottom:24, color:'var(--text-2)', lineHeight:1.8 }}>{message}</div>
      {buttonLabel && (
        <button onClick={() => navigate(buttonPath)} className="iris-btn iris-btn-cyan">
          {buttonLabel?.toUpperCase()}
        </button>
      )}
    </div>
  )
}