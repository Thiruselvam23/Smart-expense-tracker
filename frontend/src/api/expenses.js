import client from './client'
export const expensesAPI = {
  getAll: (params) => client.get('/api/expenses', { params }),
  getOne: (id)     => client.get(`/api/expenses/${id}`),
  create: (data)   => client.post('/api/expenses', data),
  update: (id, d)  => client.put(`/api/expenses/${id}`, d),
  delete: (id)     => client.delete(`/api/expenses/${id}`),
}
