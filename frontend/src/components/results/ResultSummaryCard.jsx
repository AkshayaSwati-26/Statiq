import { useLang } from '../../hooks/useLang'

export default function ResultSummaryCard({ result }) {
  const { t } = useLang()
  if (!result) return null

  const cards = [
    { key:'result_indicator', value: result.indicator_name,                     accent:'amber'  },
    { key:'result_value',     value: result.result_value,                        accent:'green'  },
    { key:'result_records',   value: result.records_analyzed?.toLocaleString(),  accent:'cyan'   },
    { key:'result_time',      value: `${result.query_time_ms} ms`,               accent:'dim'    },
  ]

  const colors = {
    amber: { border:'rgba(217,119,6,0.3)',   top:'var(--amber)', val:'var(--amber)' },
    green: { border:'rgba(5,150,105,0.3)',   top:'var(--green)', val:'var(--green)' },
    cyan:  { border:'rgba(3,105,161,0.3)',   top:'var(--cyan)',  val:'var(--cyan)'  },
    dim:   { border:'var(--rim-2)',           top:'var(--text-4)',val:'var(--text-0)'},
  }

  return (
    <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:12 }}>
      {cards.map(card => {
        const c = colors[card.accent]
        return (
          <div key={card.key} className="panel a-count" style={{
            padding:20, borderColor:c.border, overflow:'hidden', position:'relative',
          }}>
            <div style={{ position:'absolute', top:0, left:0, right:0, height:3, background:c.top }}></div>
            <div className="label-xs" style={{ color:'var(--text-3)', marginBottom:10, fontSize:10 }}>
              {t(card.key)}
            </div>
            <div style={{
              fontFamily:"'DM Mono',monospace",
              fontSize: card.key === 'result_indicator' ? 14 : 22,
              fontWeight:500,
              color:c.val,
              lineHeight:1.3,
              wordBreak:'break-word',
            }}>
              {card.value}
            </div>
          </div>
        )
      })}
    </div>
  )
}