export const formatCurrency = (amount) =>
  new Intl.NumberFormat('en-IN', { style:'currency', currency:'INR', minimumFractionDigits:2 }).format(amount || 0)

export const formatDate = (dateStr) => {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('en-IN', { day:'2-digit', month:'short', year:'numeric' })
}

export const formatDateInput = (dateStr) => {
  if (!dateStr) return ''
  return new Date(dateStr).toISOString().split('T')[0]
}

export const getMonthYear = (date = new Date()) => ({ month: date.getMonth() + 1, year: date.getFullYear() })

export const budgetBarColor = (pct) => {
  if (pct >= 100) return 'bg-red-500'
  if (pct >= 80)  return 'bg-orange-400'
  return 'bg-green-500'
}

export const budgetTextColor = (pct) => {
  if (pct >= 100) return 'text-red-600'
  if (pct >= 80)  return 'text-orange-500'
  return 'text-green-600'
}

export const downloadBlob = (blob, filename) => {
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  window.URL.revokeObjectURL(url)
}
