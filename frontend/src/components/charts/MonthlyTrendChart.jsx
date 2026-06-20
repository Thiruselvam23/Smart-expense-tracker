import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell
} from 'recharts'
import { formatCurrency } from '../../utils'

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-xl px-4 py-3 shadow-lg text-sm"
      style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}>
      <p className="font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>{label}</p>
      <p style={{ color: '#2E86AB' }}>Spent: {formatCurrency(payload[0]?.value)}</p>
      <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>{payload[0]?.payload?.count} transactions</p>
    </div>
  )
}

export default function MonthlyTrendChart({ data = [] }) {
  if (!data.length) return (
    <div className="flex items-center justify-center h-64 text-sm" style={{ color: 'var(--text-muted)' }}>
      No trend data available
    </div>
  )

  const max = Math.max(...data.map(d => d.total), 1)

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 5 }} barSize={28}>
        <defs>
          {data.map((_, i) => (
            <linearGradient key={i} id={`bar-${i}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%"   stopColor="#2E86AB" stopOpacity={0.9} />
              <stop offset="100%" stopColor="#1E3A5F" stopOpacity={0.7} />
            </linearGradient>
          ))}
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
        <XAxis
          dataKey="month_name"
          tick={{ fontSize: 12, fill: 'var(--text-secondary)' }}
          axisLine={false} tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
          tickFormatter={v => `₹${(v / 1000).toFixed(0)}k`}
          axisLine={false} tickLine={false}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: 'var(--hover)', radius: 6 }} />
        <Bar dataKey="total" name="Spent" radius={[6, 6, 0, 0]}>
          {data.map((entry, i) => (
            <Cell
              key={i}
              fill={`url(#bar-${i})`}
              opacity={entry.total === max ? 1 : 0.65}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
