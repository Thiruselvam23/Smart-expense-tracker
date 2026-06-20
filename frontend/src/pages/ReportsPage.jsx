import { useState } from 'react'
import { reportsAPI } from '../api/index'
import Button from '../components/ui/Button'
import { MONTHS } from '../constants'
import toast from 'react-hot-toast'
import { FileText, FileSpreadsheet, Download } from 'lucide-react'

function downloadBlob(blob, filename) {
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename; a.click()
  window.URL.revokeObjectURL(url)
}

export default function ReportsPage() {
  const now = new Date()
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [year, setYear]   = useState(now.getFullYear())
  const [pdfLoading, setPdfLoading]     = useState(false)
  const [excelLoading, setExcelLoading] = useState(false)

  const downloadPDF = async () => {
    setPdfLoading(true)
    try {
      const { data } = await reportsAPI.downloadPDF(month, year)
      downloadBlob(data, `expense_report_${MONTHS[month-1]}_${year}.pdf`)
      toast.success('PDF downloaded!')
    } catch { toast.error('Failed to generate PDF') }
    finally { setPdfLoading(false) }
  }

  const downloadExcel = async () => {
    setExcelLoading(true)
    try {
      const { data } = await reportsAPI.downloadExcel(month, year)
      downloadBlob(data, `expense_report_${MONTHS[month-1]}_${year}.xlsx`)
      toast.success('Excel downloaded!')
    } catch { toast.error('Failed to generate Excel') }
    finally { setExcelLoading(false) }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="page-title">Reports</h1>
        <p className="text-gray-500 text-sm mt-1">Download monthly expense reports as PDF or Excel</p>
      </div>

      {/* Month/Year selector */}
      <div className="card">
        <h2 className="section-title mb-4">Select Period</h2>
        <div className="flex gap-3">
          <select value={month} onChange={e => setMonth(+e.target.value)} className="input-field flex-1">
            {MONTHS.map((m, i) => <option key={i} value={i + 1}>{m}</option>)}
          </select>
          <select value={year} onChange={e => setYear(+e.target.value)} className="input-field w-28">
            {[2024, 2025, 2026].map(y => <option key={y} value={y}>{y}</option>)}
          </select>
        </div>
        <p className="text-sm text-gray-500 mt-2">
          Generating report for: <strong>{MONTHS[month - 1]} {year}</strong>
        </p>
      </div>

      {/* Download Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="card text-center space-y-4 border-2 hover:border-red-300 transition-colors">
          <div className="flex justify-center">
            <div className="p-4 bg-red-100 rounded-full"><FileText size={36} className="text-red-600" /></div>
          </div>
          <div>
            <h3 className="font-semibold text-gray-800">PDF Report</h3>
            <p className="text-sm text-gray-500 mt-1">Formatted monthly summary with expense table and totals</p>
          </div>
          <Button onClick={downloadPDF} loading={pdfLoading} variant="danger" className="w-full">
            <Download size={16} /> Download PDF
          </Button>
        </div>

        <div className="card text-center space-y-4 border-2 hover:border-green-300 transition-colors">
          <div className="flex justify-center">
            <div className="p-4 bg-green-100 rounded-full"><FileSpreadsheet size={36} className="text-green-600" /></div>
          </div>
          <div>
            <h3 className="font-semibold text-gray-800">Excel Report</h3>
            <p className="text-sm text-gray-500 mt-1">Spreadsheet with all expenses, summary, and category totals</p>
          </div>
          <Button onClick={downloadExcel} loading={excelLoading}
            className="w-full bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg">
            <Download size={16} /> Download Excel
          </Button>
        </div>
      </div>

      <div className="card bg-blue-50 border-blue-200">
        <h3 className="font-semibold text-blue-800 mb-2">📋 What's included in reports</h3>
        <ul className="text-sm text-blue-700 space-y-1">
          <li>• Complete expense listing with dates, titles, categories and amounts</li>
          <li>• Monthly summary: total spent, transaction count, daily average</li>
          <li>• Budget vs actual comparison</li>
          <li>• Category-wise subtotals</li>
        </ul>
      </div>
    </div>
  )
}
