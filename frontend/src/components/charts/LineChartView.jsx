import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'

export default function LineChartView({ data, title }) {
  if (!data?.length) return null
  return (
    <div>
      {title && <div className="label-xs" style={{ color:'var(--text-3)', marginBottom:16, fontSize:10 }}>{title}</div>}
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} margin={{ top:4, right:16, left:0, bottom:44 }}>
          <CartesianGrid strokeDasharray="3 6" stroke="var(--rim)" />
          <XAxis
            dataKey="name"
            tick={{ fontSize:11, fontFamily:"'Space Mono',monospace", fill:'var(--text-3)' }}
            angle={-28} textAnchor="end" interval={0}
            axisLine={{ stroke:'var(--rim-2)' }} tickLine={false}
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
          />
          <Line
            type="monotone" dataKey="value"
            stroke="var(--amber)" strokeWidth={2}
            dot={{ r:4, fill:'var(--amber)', strokeWidth:0 }}
            activeDot={{ r:6, fill:'var(--cyan)' }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}