import client from './client'
export const dashboardAPI = {
  summary:      ()           => client.get('/api/dashboard/summary'),
  byCategory:   (year, month)=> client.get('/api/dashboard/by-category', { params: { year, month } }),
  monthlyTrend: (months = 6) => client.get('/api/dashboard/monthly-trend', { params: { months } }),
}
