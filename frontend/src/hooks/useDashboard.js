import { useQuery } from '@tanstack/react-query'
import { dashboardAPI } from '../api/index'

export function useDashboardSummary() {
  return useQuery({ queryKey: ['dashboard', 'summary'], queryFn: () => dashboardAPI.summary().then(r => r.data) })
}

export function useCategoryBreakdown(year, month) {
  return useQuery({ queryKey: ['dashboard', 'category', year, month], queryFn: () => dashboardAPI.byCategory(year, month).then(r => r.data) })
}

export function useMonthlyTrend(months = 6) {
  return useQuery({ queryKey: ['dashboard', 'trend', months], queryFn: () => dashboardAPI.monthlyTrend(months).then(r => r.data) })
}
