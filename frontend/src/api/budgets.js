import client from './client'
export const budgetsAPI = {
  getAll:     ()            => client.get('/api/budgets'),
  upsert:     (data)        => client.post('/api/budgets', data),
  getCurrent: ()            => client.get('/api/budgets/current'),
  getByMonth: (year, month) => client.get(`/api/budgets/${year}/${month}`),
  delete:     (id)          => client.delete(`/api/budgets/${id}`),
}
