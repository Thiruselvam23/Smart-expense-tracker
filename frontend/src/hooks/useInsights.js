import { useQuery } from '@tanstack/react-query'
import { insightsAPI } from '../api/index'

export function useInsights(month, year) {
  return useQuery({
    queryKey: ['insights', month, year],
    queryFn: () => insightsAPI.get(month, year).then(r => r.data),
    staleTime: 1000 * 60 * 30,
  })
}
