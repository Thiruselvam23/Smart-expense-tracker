import { useState } from 'react'
import { useBudgets, useCurrentBudget, useUpsertBudget, useDeleteBudget } from '../hooks/useBudget'
import BudgetForm from '../components/budget/BudgetForm'
import BudgetProgressBar from '../components/charts/BudgetProgressBar'
import Modal from '../components/ui/Modal'
import Button from '../components/ui/Button'
import Spinner from '../components/ui/Spinner'
import { formatCurrency } from '../utils'
import { CATEGORIES } from '../constants'
import { PlusCircle, Trash2 } from 'lucide-react'

export default function BudgetsPage() {
  const [showForm, setShowForm] = useState(false)
  const { data: current, isLoading: curLoading } = useCurrentBudget()
  const { data: allBudgets, isLoading: listLoading } = useBudgets()
  const upsert = useUpsertBudget()
  const deleteBudget = useDeleteBudget()

  const handleSubmit = async (data) => {
    await upsert.mutateAsync(data)
    setShowForm(false)
  }

  const catBudgets = current?.budget?.category_budgets || {}
  const catActual  = current?.actual || {}

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="page-title">Budgets</h1>
        <Button size="sm" onClick={() => setShowForm(true)}>
          <PlusCircle size={16} /> Set Budget
        </Button>
      </div>

      {/* Current Month */}
      {curLoading ? <Spinner /> : current?.budget ? (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="section-title">This Month</h2>
            <div className="text-right">
              <p className="text-sm text-gray-500">Total Budget</p>
              <p className="font-bold text-primary text-lg">{formatCurrency(current.budget.total_budget)}</p>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4 mb-4 p-4 bg-gray-50 rounded-xl">
            <div className="text-center">
              <p className="text-xs text-gray-500">Spent</p>
              <p className="text-xl font-bold text-gray-800">{formatCurrency(current.total_spent)}</p>
            </div>
            <div className="text-center">
              <p className="text-xs text-gray-500">Remaining</p>
              <p className={`text-xl font-bold ${current.total_variance < 0 ? 'text-red-600' : 'text-green-600'}`}>
                {formatCurrency(Math.abs(current.total_variance))}
                {current.total_variance < 0 ? ' over' : ' left'}
              </p>
            </div>
          </div>
          <div className="space-y-4">
            {CATEGORIES.map(cat => catBudgets[cat] > 0 && (
              <BudgetProgressBar key={cat} category={cat}
                spent={catActual[cat] || 0} budget={catBudgets[cat]} />
            ))}
          </div>
        </div>
      ) : (
        <div className="card text-center py-10">
          <p className="text-gray-500 mb-4">No budget set for this month.</p>
          <Button onClick={() => setShowForm(true)}>Set Your First Budget</Button>
        </div>
      )}

      {/* Budget History */}
      {!listLoading && allBudgets?.length > 0 && (
        <div className="card">
          <h2 className="section-title mb-4">Budget History</h2>
          <div className="space-y-2">
            {allBudgets.map(b => (
              <div key={b.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div>
                  <p className="font-medium text-gray-700">
                    {new Date(b.year, b.month - 1).toLocaleString('default', { month: 'long', year: 'numeric' })}
                  </p>
                  <p className="text-sm text-gray-500">Budget: {formatCurrency(b.total_budget)}</p>
                </div>
                <button onClick={() => deleteBudget.mutate(b.id)} className="text-gray-400 hover:text-red-500">
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <Modal open={showForm} onClose={() => setShowForm(false)} title="Set Monthly Budget" size="lg">
        <BudgetForm onSubmit={handleSubmit} loading={upsert.isPending} />
      </Modal>
    </div>
  )
}
