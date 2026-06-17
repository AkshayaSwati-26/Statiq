import { useLang } from '../../hooks/useLang'

export default function LoadingSpinner({ message }) {
  const { t } = useLang()
  return (
    <div style={{ display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', padding:'72px 24px', gap:24 }}>
      <div style={{ position:'relative', width:52, height:52 }}>
        <div style={{ position:'absolute', inset:0, border:'1px solid var(--rim-2)', borderRadius:'50%' }}></div>
        <div style={{ position:'absolute', inset:0, border:'2px solid transparent', borderTopColor:'var(--amber)', borderRadius:'50%', animation:'spin 0.9s linear infinite' }}></div>
        <div style={{ position:'absolute', inset:7, border:'2px solid transparent', borderTopColor:'var(--cyan)', borderRadius:'50%', animation:'spin 0.55s linear infinite reverse' }}></div>
        <div style={{ position:'absolute', inset:0, display:'flex', alignItems:'center', justifyContent:'center' }}>
          <div style={{ width:7, height:7, background:'var(--amber)', borderRadius:'50%' }} className="a-pulse-a"></div>
        </div>
      </div>
      <div style={{ textAlign:'center' }}>
        <div className="label-xs" style={{ color:'var(--amber)', fontSize:12, marginBottom:6 }}>
          {message || t('loading')}
        </div>
        <div className="coord" style={{ color:'var(--text-3)', fontSize:10 }}>
          {t('loading_sub')}
        </div>
      </div>
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  )
}