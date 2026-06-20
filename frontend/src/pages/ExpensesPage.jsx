import { useState } from 'react'
import { useExpenses, useDeleteExpense } from '../hooks/useExpenses'
import ExpenseFilters from '../components/expenses/ExpenseFilters'
import ExpenseRow from '../components/expenses/ExpenseRow'
import Spinner from '../components/ui/Spinner'
import Button from '../components/ui/Button'
import Modal from '../components/ui/Modal'
import { useNavigate } from 'react-router-dom'
import { ChevronLeft, ChevronRight, PlusCircle } from 'lucide-react'

const EMPTY_FILTERS = { page: 1, limit: 20 }

export default function ExpensesPage() {
  const navigate = useNavigate()
  // filterParams holds ONLY non-empty values sent to API
  const [filterParams, setFilterParams] = useState({ ...EMPTY_FILTERS })
  const [deleteId, setDeleteId] = useState(null)
  const { data, isLoading } = useExpenses(filterParams)
  const deleteMutation = useDeleteExpense()

  // When filters change, strip empty strings before sending to API
  const handleFilterChange = (raw) => {
    const clean = { page: 1, limit: 20 }
    Object.entries(raw).forEach(([k, v]) => {
      if (v !== '' && v !== null && v !== undefined) clean[k] = v
    })
    setFilterParams(clean)
  }

  const handleDelete = async () => {
    await deleteMutation.mutateAsync(deleteId)
    setDeleteId(null)
  }

  const setPage = (p) => setFilterParams(f => ({ ...f, page: p }))

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="page-title">Expenses</h1>
        <Button onClick={() => navigate('/expenses/add')} size="sm">
          <PlusCircle size={16} /> Add Expense
        </Button>
      </div>

      <ExpenseFilters filters={{}} onChange={handleFilterChange} />

      <div className="card p-0 overflow-hidden">
        {isLoading ? <Spinner className="py-16" /> : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead style={{ background: 'var(--hover)', borderBottom: '1px solid var(--border)' }}>
                  <tr>
                    {['Date','Title','Category','Payment','Amount','Actions'].map(h => (
                      <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider"
                        style={{ color: 'var(--text-muted)' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {!data?.items?.length && (
                    <tr><td colSpan={6} className="text-center py-12" style={{ color: 'var(--text-muted)' }}>
                      No expenses found. Add your first one!
                    </td></tr>
                  )}
                  {data?.items?.map(exp => (
                    <ExpenseRow key={exp.id} expense={exp} onDelete={setDeleteId} />
                  ))}
                </tbody>
              </table>
            </div>

            {data?.pages > 1 && (
              <div className="flex items-center justify-between px-4 py-3"
                style={{ borderTop: '1px solid var(--border)' }}>
                <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
                  {((filterParams.page - 1) * filterParams.limit) + 1}–{Math.min(filterParams.page * filterParams.limit, data.total)} of {data.total}
                </p>
                <div className="flex gap-2 items-center">
                  <Button size="sm" variant="ghost" disabled={filterParams.page <= 1} onClick={() => setPage(filterParams.page - 1)}>
                    <ChevronLeft size={16} />
                  </Button>
                  <span className="text-sm px-3 py-1 rounded" style={{ background: 'var(--hover)', color: 'var(--text-primary)' }}>
                    {filterParams.page} / {data.pages}
                  </span>
                  <Button size="sm" variant="ghost" disabled={filterParams.page >= data.pages} onClick={() => setPage(filterParams.page + 1)}>
                    <ChevronRight size={16} />
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      <Modal open={!!deleteId} onClose={() => setDeleteId(null)} title="Delete Expense" size="sm">
        <p className="mb-6" style={{ color: 'var(--text-secondary)' }}>Are you sure? This cannot be undone.</p>
        <div className="flex gap-3">
          <Button variant="danger" loading={deleteMutation.isPending} onClick={handleDelete} className="flex-1">Delete</Button>
          <Button variant="secondary" onClick={() => setDeleteId(null)} className="flex-1">Cancel</Button>
        </div>
      </Modal>
    </div>
  )
}
