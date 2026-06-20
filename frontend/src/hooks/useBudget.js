import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { budgetsAPI } from '../api/budgets'
import toast from 'react-hot-toast'

export function useBudgets() {
  return useQuery({ queryKey: ['budgets'], queryFn: () => budgetsAPI.getAll().then(r => r.data) })
}

export function useCurrentBudget() {
  return useQuery({ queryKey: ['budget', 'current'], queryFn: () => budgetsAPI.getCurrent().then(r => r.data) })
}

export function useUpsertBudget() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) => budgetsAPI.upsert(data).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['budget'] }); toast.success('Budget saved!') },
    onError: (e) => toast.error(e.response?.data?.detail || 'Failed to save budget'),
  })
}

export function useDeleteBudget() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id) => budgetsAPI.delete(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['budgets'] }); toast.success('Budget deleted') },
    onError: () => toast.error('Failed to delete budget'),
  })
}
