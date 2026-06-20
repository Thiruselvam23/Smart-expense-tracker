import client from './client'
export const insightsAPI = {
  get: (month, year) => client.get('/api/insights', { params: { month, year } }),
}
