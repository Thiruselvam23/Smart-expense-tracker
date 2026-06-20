import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { expensesAPI } from '../api/expenses'
import toast from 'react-hot-toast'

export function useExpenses(filters = {}) {
  return useQuery({
    queryKey: ['expenses', filters],
    queryFn: () => expensesAPI.getAll(filters).then(r => r.data),
  })
}

export function useExpense(id) {
  return useQuery({
    queryKey: ['expense', id],
    queryFn: () => expensesAPI.getOne(id).then(r => r.data),
    enabled: !!id,
  })
}

export function useCreateExpense() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) => expensesAPI.create(data).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['expenses'] }); qc.invalidateQueries({ queryKey: ['dashboard'] }); toast.success('Expense added!') },
    onError: (e) => toast.error(e.response?.data?.detail || 'Failed to add expense'),
  })
}

export function useUpdateExpense() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }) => expensesAPI.update(id, data).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['expenses'] }); qc.invalidateQueries({ queryKey: ['dashboard'] }); toast.success('Expense updated!') },
    onError: (e) => toast.error(e.response?.data?.detail || 'Failed to update expense'),
  })
}

export function useDeleteExpense() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id) => expensesAPI.delete(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['expenses'] }); qc.invalidateQueries({ queryKey: ['dashboard'] }); toast.success('Expense deleted') },
    onError: (e) => toast.error(e.response?.data?.detail || 'Failed to delete'),
  })
}
