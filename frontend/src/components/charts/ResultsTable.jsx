import { useLang } from '../../hooks/useLang'

export default function ResultsTable({ data }) {
  const { lang } = useLang()
  if (!data?.length) return null
  const headers = Object.keys(data[0])
  return (
    <div style={{ overflowX:'auto', border:'1px solid var(--rim-2)' }}>
      <table style={{ width:'100%', borderCollapse:'collapse' }}>
        <thead>
          <tr style={{ background:'var(--ink-2)' }}>
            <th style={{ padding:'11px 14px', fontFamily:"'Space Mono',monospace", fontSize:10, color:'var(--text-4)', textAlign:'left', borderBottom:'1px solid var(--rim-2)', letterSpacing:'0.08em' }}>
              #
            </th>
            {headers.map(h => (
              <th key={h} style={{ padding:'11px 14px', fontFamily:"'Space Mono',monospace", fontSize:10, color:'var(--text-3)', textAlign:'left', borderBottom:'1px solid var(--rim-2)', letterSpacing:'0.08em', textTransform:'uppercase' }}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={i} style={{ background: i%2===0 ? 'var(--surface)' : 'var(--ink-2)', transition:'background 0.1s' }}
              onMouseEnter={e => e.currentTarget.style.background='var(--amber-glow)'}
              onMouseLeave={e => e.currentTarget.style.background = i%2===0 ? 'var(--surface)' : 'var(--ink-2)'}
            >
              <td style={{ padding:'11px 14px', fontFamily:"'DM Mono',monospace", fontSize:12, color:'var(--text-4)', borderBottom:'1px solid var(--rim)' }}>
                {String(i+1).padStart(2,'0')}
              </td>
              {Object.values(row).map((val, j) => (
                <td key={j} style={{ padding:'11px 14px', fontFamily:"'DM Mono',monospace", fontSize:14, color:'var(--text-1)', borderBottom:'1px solid var(--rim)' }}>
                  {typeof val === 'number' ? val.toLocaleString() : val}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}