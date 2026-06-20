import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { CATEGORY_COLORS } from '../../constants'
import { formatCurrency } from '../../utils'

// No percentage labels — clean visualization
export default function CategoryPieChart({ data = [] }) {
  if (!data.length) return (
    <div className="flex items-center justify-center h-64 text-sm" style={{ color: 'var(--text-muted)' }}>
      No expense data for this period
    </div>
  )
  const chartData = data.map(d => ({ name: d.category, value: d.total, count: d.count }))
  return (
    <ResponsiveContainer width="100%" height={280}>
      <PieChart>
        <Pie
          data={chartData}
          cx="50%" cy="50%"
          outerRadius={95}
          innerRadius={40}
          dataKey="value"
          labelLine={false}
          label={false}
        >
          {chartData.map(entry => (
            <Cell key={entry.name} fill={CATEGORY_COLORS[entry.name] || '#C8D6E5'} />
          ))}
        </Pie>
        <Tooltip
          formatter={(v) => formatCurrency(v)}
          contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8 }}
          labelStyle={{ color: 'var(--text-primary)' }}
        />
        <Legend iconType="circle" iconSize={9} />
      </PieChart>
    </ResponsiveContainer>
  )
}
