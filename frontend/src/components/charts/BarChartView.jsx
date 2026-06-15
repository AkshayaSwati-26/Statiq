import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'

const COLORS = ['#f59e0b','#22d3ee','#10b981','#8b5cf6','#f97316','#ec4899']

export default function BarChartView({ data, title }) {
  if (!data?.length) return null
  return (
    <div>
      {title && <div className="label-xs" style={{ color:'var(--text-3)', marginBottom:16, fontSize:10 }}>{title}</div>}
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data} margin={{ top:4, right:16, left:0, bottom:44 }}>
          <XAxis
            dataKey="name"
            tick={{ fontSize:11, fontFamily:"'Space Mono',monospace", fill:'var(--text-3)' }}
            angle={-28} textAnchor="end" interval={0}
            axisLine={{ stroke:'var(--rim-2)' }}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize:11, fontFamily:"'Space Mono',monospace", fill:'var(--text-3)' }}
            axisLine={false} tickLine={false}
          />
          <Tooltip
            contentStyle={{
              background:'var(--surface)', border:'1px solid var(--rim-2)',
              fontFamily:"'Space Mono',monospace", fontSize:11,
              color:'var(--text-0)', borderRadius:2,
            }}
            formatter={val => [`${val}%`, 'Value']}
            cursor={{ fill:'rgba(255,255,255,0.03)' }}
          />
          <Bar dataKey="value" radius={[2,2,0,0]}>
            {data.map((_,i) => <Cell key={i} fill={COLORS[i%COLORS.length]} opacity={0.85} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}