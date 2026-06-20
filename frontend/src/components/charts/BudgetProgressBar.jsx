import { formatCurrency } from '../../utils'
import { CATEGORY_COLORS, CATEGORY_ICONS } from '../../constants'

export default function BudgetProgressBar({ category, spent = 0, budget = 0 }) {
  const pct = budget > 0 ? Math.min((spent / budget) * 100, 100) : 0
  const overBudget = budget > 0 && spent > budget
  const barColor = spent >= budget ? 'bg-red-500' : pct >= 80 ? 'bg-orange-400' : 'bg-green-500'
  const textColor = spent >= budget ? 'text-red-600' : pct >= 80 ? 'text-orange-500' : 'text-green-600'

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-2">
          <span>{CATEGORY_ICONS[category] || '📦'}</span>
          <span className="font-medium text-gray-700">{category}</span>
          {overBudget && <span className="text-xs bg-red-100 text-red-600 px-1.5 py-0.5 rounded">Over!</span>}
        </div>
        <div className="text-right">
          <span className={`font-semibold text-xs ${textColor}`}>{formatCurrency(spent)}</span>
          <span className="text-gray-400 text-xs"> / {formatCurrency(budget)}</span>
        </div>
      </div>
      <div className="w-full bg-gray-100 rounded-full h-2">
        <div className={`h-2 rounded-full transition-all ${barColor}`} style={{ width: `${pct}%` }} />
      </div>
      <p className={`text-xs ${textColor} text-right`}>{pct.toFixed(0)}% used</p>
    </div>
  )
}
