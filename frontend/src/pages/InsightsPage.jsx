import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import Spinner from '../components/ui/Spinner'
import Button from '../components/ui/Button'
import { MONTHS } from '../constants'
import { formatCurrency } from '../utils'
import { Lightbulb, RefreshCw, TrendingUp } from 'lucide-react'
import client from '../api/client'

const fetchInsights = (month, year, force = false) =>
  client.get('/api/insights', { params: { month, year, force } }).then(r => r.data)

export default function InsightsPage() {
  const now = new Date()
  const [month, setMonth]       = useState(now.getMonth() + 1)
  const [year, setYear]         = useState(now.getFullYear())
  const [refreshing, setRefreshing] = useState(false)
  const qc = useQueryClient()

  const { data, isLoading, error } = useQuery({
    queryKey: ['insights', month, year],
    queryFn:  () => fetchInsights(month, year, false),
    staleTime: 1000 * 60 * 30,
  })

  const handleForceRefresh = async () => {
    setRefreshing(true)
    try {
      const fresh = await fetchInsights(month, year, true)
      qc.setQueryData(['insights', month, year], fresh)
    } catch {
      qc.invalidateQueries({ queryKey: ['insights', month, year] })
    } finally { setRefreshing(false) }
  }

  const stats = data?.statistics || {}
  const recs  = data?.recommendations || []

  return (
    <div className="max-w-3xl mx-auto space-y-6">

      {/* Header — subtitle removed */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="page-title">AI Insights</h1>
        <div className="flex items-center gap-2">
          <select value={month} onChange={e => setMonth(+e.target.value)} className="input-field w-36 text-sm">
            {MONTHS.map((m, i) => <option key={i} value={i+1}>{m}</option>)}
          </select>
          <select value={year} onChange={e => setYear(+e.target.value)} className="input-field w-24 text-sm">
            {[2024, 2025, 2026].map(y => <option key={y} value={y}>{y}</option>)}
          </select>
          <Button size="sm" variant="secondary" onClick={handleForceRefresh}
            disabled={refreshing || isLoading} title="Force fresh from Gemini">
            <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
          </Button>
        </div>
      </div>

      {/* Stats */}
      {stats.total_spent !== undefined && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Total Spent',   value: formatCurrency(stats.total_spent) },
            { label: 'Daily Average', value: formatCurrency(stats.avg_daily_spend) },
            { label: 'Transactions',  value: stats.transaction_count },
            {
              label: 'MoM Change',
              value: `${stats.mom_change_pct > 0 ? '+' : ''}${stats.mom_change_pct}%`,
              color: stats.mom_change_pct > 0 ? 'text-red-500' : 'text-green-500',
            },
          ].map(s => (
            <div key={s.label} className="card text-center">
              <p className="text-xs mb-1" style={{ color: 'var(--text-muted)' }}>{s.label}</p>
              <p className={`text-base font-bold break-all ${s.color || ''}`}
                style={!s.color ? { color: 'var(--text-primary)' } : {}}>{s.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Recommendations card */}
      <div className="card">
        {/* Header row */}
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-yellow-100 dark:bg-yellow-900/30 rounded-lg">
              <Lightbulb size={20} className="text-yellow-600" />
            </div>
            <div>
              {/* Heading */}
              <h2 className="section-title">Recommendations</h2>
              {/* Fresh label — replaces "✓ Fresh from Gemini" */}
              {data && !data.cached && (
                <span className="inline-block mt-0.5 text-xs font-medium px-2 py-0.5 rounded-full bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
                  Fresh Recommendation
                </span>
              )}
              {data?.cached && (
                <span className="inline-block mt-0.5 text-xs font-medium px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                  Cached · {new Date(data.generated_at).toLocaleTimeString()}
                </span>
              )}
            </div>
          </div>
          {recs.length > 0 && (
            <span className="text-xs px-2.5 py-1 rounded-full font-medium bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
              {recs.length} tips
            </span>
          )}
        </div>

        {/* Loading */}
        {(isLoading || refreshing) && (
          <div className="flex flex-col items-center gap-3 py-10">
            <Spinner />
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              {refreshing ? 'Calling Gemini for fresh insights...' : 'Loading insights...'}
            </p>
          </div>
        )}

        {/* Error */}
        {error && !refreshing && (
          <div className="text-center py-8 space-y-3">
            <p className="text-red-500 font-medium">Could not load insights</p>
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Check your Gemini API key in backend .env</p>
            <Button size="sm" onClick={handleForceRefresh}>Try Again</Button>
          </div>
        )}

        {/* Empty */}
        {!isLoading && !refreshing && !error && recs.length === 0 && (
          <p className="text-center py-10 text-sm" style={{ color: 'var(--text-muted)' }}>
            Add more expenses this month to get personalized recommendations.
          </p>
        )}

        {/* Recommendations — full text, no clipping */}
        {!isLoading && !refreshing && recs.length > 0 && (
          <div className="space-y-3">
            {recs.map((rec, i) => (
              <div key={i} className="flex gap-4 p-4 rounded-xl"
                style={{ background: 'var(--hover)', border: '1px solid var(--border)' }}>
                <div className="w-7 h-7 rounded-full bg-[#1E3A5F] text-white text-sm font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                  {i + 1}
                </div>
                {/* whitespace-normal + overflow-visible — full text always shown */}
                <p className="text-sm leading-relaxed" style={{ color: 'var(--text-primary)', whiteSpace: 'normal', wordBreak: 'break-word' }}>
                  {rec}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Over-budget */}
      {stats.over_budget_categories?.length > 0 && (
        <div className="card border-red-200 bg-red-50 dark:bg-red-900/10 dark:border-red-800">
          <h3 className="font-semibold text-red-700 dark:text-red-400 mb-3 flex items-center gap-2">
            <TrendingUp size={18} /> Over-Budget Categories
          </h3>
          <div className="space-y-2">
            {stats.over_budget_categories.map(o => (
              <div key={o.category} className="flex justify-between text-sm p-2 rounded-lg bg-white/60 dark:bg-white/5">
                <span className="font-medium text-red-700 dark:text-red-400">{o.category}</span>
                <span className="text-red-600 dark:text-red-300">Over by {formatCurrency(o.over_by)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
