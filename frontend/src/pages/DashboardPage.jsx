import { useDashboardSummary, useCategoryBreakdown, useMonthlyTrend } from '../hooks/useDashboard'
import { useCurrentBudget } from '../hooks/useBudget'
import { useExpenses } from '../hooks/useExpenses'
import CategoryPieChart from '../components/charts/CategoryPieChart'
import MonthlyTrendChart from '../components/charts/MonthlyTrendChart'
import BudgetProgressBar from '../components/charts/BudgetProgressBar'
import Spinner from '../components/ui/Spinner'
import { formatCurrency, formatDate } from '../utils'
import { CATEGORIES, CATEGORY_COLORS } from '../constants'
import { useNavigate } from 'react-router-dom'
import { ArrowUpRight, ArrowDownRight, Wallet, TrendingUp, Receipt, PiggyBank } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'

// ── KPI Card — never truncates values ────────────────────────────────────────
function KPICard({ title, value, sub, trend, icon: Icon, iconBg }) {
  const isUp = trend > 0
  return (
    <div className="card">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium mb-2" style={{ color: 'var(--text-muted)' }}>{title}</p>
          {/* break-all ensures long ₹ values wrap instead of truncating */}
          <p className="font-bold leading-tight break-all" style={{ fontSize: 'clamp(1rem, 2.5vw, 1.35rem)', color: 'var(--text-primary)' }}>
            {value}
          </p>
          {sub && <p className="text-xs mt-1.5" style={{ color: 'var(--text-muted)' }}>{sub}</p>}
        </div>
        <div className={`p-2.5 rounded-xl flex-shrink-0 ${iconBg}`}>
          <Icon size={19} className="text-white" />
        </div>
      </div>
      {trend !== undefined && (
        <div className={`flex items-center gap-1 text-xs mt-3 font-medium ${isUp ? 'text-red-500' : 'text-green-500'}`}>
          {isUp ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
          {Math.abs(trend)}% vs last month
        </div>
      )}
    </div>
  )
}

// ── Daily Spending Bar Chart — date-shift fix ─────────────────────────────────
function DailySpendingChart({ expenses = [] }) {
  const days = {}
  const today = new Date()

  for (let i = 29; i >= 0; i--) {
    const d = new Date(today)
    d.setDate(today.getDate() - i)
    // Use local date string (YYYY-MM-DD) to avoid UTC shift
    const key = [
      d.getFullYear(),
      String(d.getMonth() + 1).padStart(2, '0'),
      String(d.getDate()).padStart(2, '0'),
    ].join('-')
    days[key] = {
      date: key,
      label: `${d.getDate()}/${d.getMonth() + 1}`,
      amount: 0,
    }
  }

  expenses.forEach(exp => {
    // Parse expense date as LOCAL date — avoids UTC midnight → previous day shift
    const raw = exp.date  // e.g. "2026-06-16T00:00:00" or "2026-06-16"
    const dateOnly = typeof raw === 'string' ? raw.split('T')[0] : new Date(raw).toISOString().split('T')[0]
    if (days[dateOnly]) days[dateOnly].amount += exp.amount
  })

  const data = Object.values(days)
  const hasData = data.some(d => d.amount > 0)
  const max = Math.max(...data.map(d => d.amount), 1)

  if (!hasData) return (
    <div className="flex items-center justify-center h-48 text-sm" style={{ color: 'var(--text-muted)' }}>
      No expenses in the last 30 days
    </div>
  )

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} margin={{ top: 5, right: 10, left: 5, bottom: 5 }} barSize={10}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
        <XAxis dataKey="label" tick={{ fontSize: 9, fill: 'var(--text-muted)' }} interval={4} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 9, fill: 'var(--text-muted)' }} tickFormatter={v => `₹${(v/1000).toFixed(0)}k`} axisLine={false} tickLine={false} />
        <Tooltip
          formatter={v => formatCurrency(v)}
          contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 }}
        />
        <Bar dataKey="amount" name="Spent" radius={[3, 3, 0, 0]}>
          {data.map((entry, i) => (
            <Cell key={i} fill={entry.amount === max ? '#2E86AB' : '#2E86AB66'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

// ── Recent Expenses — latest 2 only ─────────────────────────────────────────
function RecentExpenses({ items = [] }) {
  const navigate = useNavigate()
  const latest = items.slice(0, 2)

  if (!latest.length) return (
    <p className="text-sm text-center py-4" style={{ color: 'var(--text-muted)' }}>No recent expenses</p>
  )
  return (
    <div className="space-y-1">
      {latest.map(exp => (
        <div key={exp.id} className="flex items-center justify-between py-2.5 border-b last:border-0"
          style={{ borderColor: 'var(--border)' }}>
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
              style={{ background: (CATEGORY_COLORS[exp.category] || '#C8D6E5') + '33' }}>
              <span className="text-xs" style={{ color: CATEGORY_COLORS[exp.category] || '#888' }}>●</span>
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium truncate" style={{ color: 'var(--text-primary)' }}>{exp.title}</p>
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{exp.category} · {formatDate(exp.date)}</p>
            </div>
          </div>
          <span className="text-sm font-semibold flex-shrink-0 ml-2" style={{ color: 'var(--text-primary)' }}>
            {formatCurrency(exp.amount)}
          </span>
        </div>
      ))}
      <button
        onClick={() => navigate('/expenses')}
        className="w-full mt-3 text-xs font-medium py-2 rounded-lg transition-colors text-[#2E86AB] hover:bg-blue-50 dark:hover:bg-blue-900/20"
      >
        View All Expenses →
      </button>
    </div>
  )
}

// ── Main Dashboard ────────────────────────────────────────────────────────────
export default function DashboardPage() {
  const { data: summary, isLoading } = useDashboardSummary()
  const { data: categories }         = useCategoryBreakdown()
  const { data: trend }              = useMonthlyTrend()
  const { data: budget }             = useCurrentBudget()
  const { data: expData }            = useExpenses({ limit: 100, sort_by: 'date', order: 'desc' })
  const navigate = useNavigate()

  if (isLoading) return <Spinner size="lg" className="mt-20" />

  const catBudgets = budget?.budget?.category_budgets || {}
  const catActual  = budget?.actual || {}
  const expenses   = expData?.items || []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="page-title">Dashboard</h1>
        <button onClick={() => navigate('/expenses/add')} className="btn-primary text-sm">
          + Add Expense
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <KPICard title="Total Spent"
          value={formatCurrency(summary?.total_spent || 0)}
          sub={`${summary?.transaction_count || 0} transactions`}
          trend={summary?.mom_change_pct}
          icon={Wallet} iconBg="bg-[#1E3A5F]" />
        <KPICard title="Daily Average"
          value={formatCurrency(summary?.avg_per_day || 0)}
          sub="This month"
          icon={TrendingUp} iconBg="bg-[#2E86AB]" />
        <KPICard title="Budget Remaining"
          value={formatCurrency(summary?.budget_remaining || 0)}
          sub={`${summary?.budget_used_pct || 0}% used`}
          icon={PiggyBank} iconBg="bg-green-500" />
        <KPICard title="Monthly Budget"
          value={formatCurrency(summary?.total_budget || 0)}
          sub="Set in Budgets"
          icon={Receipt} iconBg="bg-purple-500" />
      </div>

      {/* Daily Spending + Recent */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="card lg:col-span-2">
          <h2 className="section-title mb-4">Daily Spending (Last 30 Days)</h2>
          <DailySpendingChart expenses={expenses} />
        </div>
        <div className="card">
          <h2 className="section-title mb-4">Recent Expenses</h2>
          <RecentExpenses items={expenses} />
        </div>
      </div>

      {/* Category + Monthly Trend */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="section-title mb-4">Spending by Category</h2>
          <CategoryPieChart data={categories || []} />
        </div>
        <div className="card">
          <h2 className="section-title mb-4">Monthly Trend</h2>
          <MonthlyTrendChart data={trend || []} />
        </div>
      </div>

      {/* Budget vs Actual */}
      {budget?.budget ? (
        <div className="card">
          <div className="flex items-center justify-between mb-5 flex-wrap gap-2">
            <h2 className="section-title">Budget vs Actual</h2>
            <span className={`text-sm font-medium px-3 py-1 rounded-full ${
              budget.percentage_used >= 100 ? 'bg-red-100 text-red-600' :
              budget.percentage_used >= 80  ? 'bg-orange-100 text-orange-600' :
              'bg-green-100 text-green-600'
            }`}>
              {budget.percentage_used}% used
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {CATEGORIES.map(cat => catBudgets[cat] > 0 && (
              <BudgetProgressBar key={cat} category={cat}
                spent={catActual[cat] || 0} budget={catBudgets[cat]} />
            ))}
          </div>
        </div>
      ) : (
        <div className="card text-center py-8">
          <p className="mb-3" style={{ color: 'var(--text-muted)' }}>No budget set for this month.</p>
          <button onClick={() => navigate('/budgets')} className="btn-primary text-sm">
            Set Monthly Budget
          </button>
        </div>
      )}
    </div>
  )
}
