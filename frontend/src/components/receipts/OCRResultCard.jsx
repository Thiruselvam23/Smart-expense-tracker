import { useState } from 'react'
import Input from '../ui/Input'
import Select from '../ui/Select'
import Button from '../ui/Button'
import { CATEGORIES } from '../../constants'
import { CheckCircle, AlertCircle } from 'lucide-react'

export default function OCRResultCard({ result, onConfirm, onRetry, loading }) {
  const [form, setForm] = useState({
    merchant: result?.merchant || '',
    amount:   result?.amount || '',
    date:     result?.date || '',
    category: result?.suggested_category || 'Other',
  })

  const confidence = result?.confidence || 0
  const confColor = confidence >= 0.8 ? 'text-green-600' : confidence >= 0.5 ? 'text-orange-500' : 'text-red-500'

  return (
    <div className="card space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-gray-800">OCR Result</h3>
        <div className={`flex items-center gap-1 text-sm ${confColor}`}>
          {confidence >= 0.7 ? <CheckCircle size={16} /> : <AlertCircle size={16} />}
          Confidence: {(confidence * 100).toFixed(0)}%
        </div>
      </div>

      {confidence < 0.5 && (
        <div className="bg-orange-50 border border-orange-200 rounded-lg p-3 text-sm text-orange-700">
          Low confidence — please review and correct the fields below before saving.
        </div>
      )}

      <Input label="Merchant Name" value={form.merchant} onChange={e => setForm(p => ({ ...p, merchant: e.target.value }))} />
      <div className="grid grid-cols-2 gap-4">
        <Input label="Amount (₹)" type="number" value={form.amount} onChange={e => setForm(p => ({ ...p, amount: e.target.value }))} />
        <Input label="Date" type="date" value={form.date} onChange={e => setForm(p => ({ ...p, date: e.target.value }))} />
      </div>
      <Select label="Category" value={form.category} onChange={e => setForm(p => ({ ...p, category: e.target.value }))}
        options={CATEGORIES.map(c => ({ value: c, label: c }))} />

      <div className="flex gap-3">
        <Button onClick={() => onConfirm(form)} loading={loading} className="flex-1">✅ Confirm & Save</Button>
        <Button variant="secondary" onClick={onRetry}>Upload Another</Button>
      </div>
    </div>
  )
}
