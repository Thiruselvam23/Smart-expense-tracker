import client from './client'

export const receiptsAPI = {
  scan:      (formData) => client.post('/api/receipts/scan', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  jobStatus: (jobId) => client.get(`/api/receipts/jobs/${jobId}`),
}

export const dashboardAPI = {
  summary:      ()                       => client.get('/api/dashboard/summary'),
  byCategory:   (year, month)            => client.get('/api/dashboard/by-category', { params: { year, month } }),
  monthlyTrend: (months = 6)             => client.get('/api/dashboard/monthly-trend', { params: { months } }),
}

export const insightsAPI = {
  get: (month, year) => client.get('/api/insights', { params: { month, year } }),
}

export const reportsAPI = {
  downloadPDF:   (month, year) => client.get('/api/reports/pdf',   { params: { month, year }, responseType: 'blob' }),
  downloadExcel: (month, year) => client.get('/api/reports/excel', { params: { month, year }, responseType: 'blob' }),
}
