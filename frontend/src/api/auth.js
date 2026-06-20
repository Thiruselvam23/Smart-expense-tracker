import client from './client'

export const authAPI = {
  register: (data) => client.post('/api/auth/register', data),
  login:    (data) => client.post('/api/auth/login', data),
  refresh:  (refresh_token) => client.post('/api/auth/refresh', { refresh_token }),
  logout:   () => client.post('/api/auth/logout'),
  me:       () => client.get('/api/auth/me'),
}
