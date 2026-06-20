import { useNavigate, useParams } from 'react-router-dom'
import ExpenseForm from '../components/expenses/ExpenseForm'
import { useExpense, useUpdateExpense } from '../hooks/useExpenses'
import Spinner from '../components/ui/Spinner'
import { ArrowLeft } from 'lucide-react'

export default function EditExpensePage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { data: expense, isLoading } = useExpense(id)
  const { mutateAsync, isPending } = useUpdateExpense()

  const handleSubmit = async (data) => {
    await mutateAsync({ id, data })
    navigate('/expenses')
  }

  if (isLoading) return <Spinner size="lg" className="mt-20" />

  const defaults = expense ? {
    ...expense,
    date: expense.date ? new Date(expense.date).toISOString().split('T')[0] : '',
    tags: (expense.tags || []).join(', '),
  } : {}

  return (
    <div className="max-w-xl mx-auto space-y-4">
      <div className="flex items-center gap-3">
        <button onClick={() => navigate(-1)} className="text-gray-500 hover:text-primary transition-colors">
          <ArrowLeft size={20} />
        </button>
        <h1 className="page-title">Edit Expense</h1>
      </div>
      <div className="card">
        <ExpenseForm defaultValues={defaults} onSubmit={handleSubmit} loading={isPending} />
      </div>
    </div>
  )
}
