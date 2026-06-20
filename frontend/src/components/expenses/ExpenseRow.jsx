import { Pencil, Trash2 } from 'lucide-react'
import Badge from '../ui/Badge'
import { formatCurrency, formatDate } from '../../utils'
import { useNavigate } from 'react-router-dom'

export default function ExpenseRow({ expense, onDelete }) {
  const navigate = useNavigate()
  return (
    <tr className="transition-colors" style={{ borderBottom: '1px solid var(--border)' }}
      onMouseEnter={e => e.currentTarget.style.background = 'var(--hover)'}
      onMouseLeave={e => e.currentTarget.style.background = ''}>
      <td className="px-4 py-3 text-sm" style={{ color: 'var(--text-secondary)' }}>{formatDate(expense.date)}</td>
      <td className="px-4 py-3">
        <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{expense.title}</p>
        {expense.description && <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{expense.description}</p>}
      </td>
      <td className="px-4 py-3"><Badge label={expense.category} /></td>
      <td className="px-4 py-3 text-sm" style={{ color: 'var(--text-secondary)' }}>{expense.payment_method}</td>
      <td className="px-4 py-3 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{formatCurrency(expense.amount)}</td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <button onClick={() => navigate(`/expenses/${expense.id}/edit`)}
            className="hover:text-[#1E3A5F] transition-colors" style={{ color: 'var(--text-muted)' }}>
            <Pencil size={15} />
          </button>
          <button onClick={() => onDelete(expense.id)}
            className="hover:text-red-500 transition-colors" style={{ color: 'var(--text-muted)' }}>
            <Trash2 size={15} />
          </button>
        </div>
      </td>
    </tr>
  )
}
