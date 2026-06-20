import client from './client'
export const reportsAPI = {
  downloadPDF:   (month, year) => client.get('/api/reports/pdf',   { params: { month, year }, responseType: 'blob' }),
  downloadExcel: (month, year) => client.get('/api/reports/excel', { params: { month, year }, responseType: 'blob' }),
}
