import client from './client'
export const receiptsAPI = {
  scan:      (formData) => client.post('/api/receipts/scan', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  jobStatus: (jobId) => client.get(`/api/receipts/jobs/${jobId}`),
}
