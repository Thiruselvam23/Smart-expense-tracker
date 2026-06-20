import { useNavigate } from 'react-router-dom'
import ExpenseForm from '../components/expenses/ExpenseForm'
import { useCreateExpense } from '../hooks/useExpenses'
import { ArrowLeft } from 'lucide-react'

export default function AddExpensePage() {
  const navigate = useNavigate()
  const { mutateAsync, isPending } = useCreateExpense()

  const handleSubmit = async (data) => {
    await mutateAsync(data)
    navigate('/expenses')
  }

  return (
    <div className="max-w-xl mx-auto space-y-4">
      <div className="flex items-center gap-3">
        <button onClick={() => navigate(-1)} className="text-gray-500 hover:text-primary transition-colors">
          <ArrowLeft size={20} />
        </button>
        <h1 className="page-title">Add Expense</h1>
      </div>
      <div className="card">
        <ExpenseForm onSubmit={handleSubmit} loading={isPending} />
      </div>
    </div>
  )
}
