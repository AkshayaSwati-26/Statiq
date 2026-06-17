import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'

const COLORS = ['#f59e0b','#22d3ee','#10b981','#8b5cf6','#f97316','#ec4899']

export default function PieChartView({ data, title }) {
  if (!data?.length) return null
  return (
    <div>
      {title && <div className="label-xs" style={{ color:'var(--text-3)', marginBottom:16, fontSize:10 }}>{title}</div>}
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={data} dataKey="value" nameKey="name"
            cx="50%" cy="48%" outerRadius={110}
            label={({ name, value }) => `${name}: ${value}%`}
            labelLine={{ stroke:'var(--rim-2)', strokeWidth:1 }}
          >
            {data.map((_,i) => <Cell key={i} fill={COLORS[i%COLORS.length]} />)}
          </Pie>
          <Tooltip
            contentStyle={{
              background:'var(--surface)', border:'1px solid var(--rim-2)',
              fontFamily:"'Space Mono',monospace", fontSize:11,
              color:'var(--text-0)', borderRadius:2,
            }}
            formatter={val => [`${val}%`]}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}