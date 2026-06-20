import { useState } from 'react'
import { useDropzone } from 'react-dropzone'
import OCRResultCard from '../components/receipts/OCRResultCard'
import { receiptsAPI } from '../api/index'
import { useCreateExpense } from '../hooks/useExpenses'
import toast from 'react-hot-toast'
import { Upload } from 'lucide-react'

// All common image formats including HEIC/HEIF, WebP, BMP, GIF
const ACCEPTED = {
  'image/jpeg':    ['.jpg', '.jpeg'],
  'image/png':     ['.png'],
  'image/webp':    ['.webp'],
  'image/bmp':     ['.bmp'],
  'image/gif':     ['.gif'],
  'image/heic':    ['.heic'],
  'image/heif':    ['.heif'],
}

function UploadZone({ onFile, loading }) {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: ACCEPTED,
    maxFiles: 1,
    disabled: loading,
    onDrop: (files) => files[0] && onFile(files[0]),
    onDropRejected: () => toast.error('Unsupported file type. Please upload an image file.'),
  })

  return (
    <div {...getRootProps()} className={`
      border-2 border-dashed rounded-xl p-14 text-center cursor-pointer transition-all
      ${isDragActive ? 'border-[#2E86AB] bg-blue-50 dark:bg-blue-900/20' : 'hover:border-[#2E86AB]'}
      ${loading ? 'opacity-50 cursor-not-allowed' : ''}
    `} style={{ borderColor: isDragActive ? '#2E86AB' : 'var(--border)' }}>
      <input {...getInputProps()} />
      <div className="flex flex-col items-center gap-3">
        {loading
          ? <div className="w-10 h-10 border-2 border-[#2E86AB] border-t-transparent rounded-full animate-spin" />
          : <Upload size={40} style={{ color: 'var(--text-muted)' }} />
        }
        <div>
          <p className="font-medium" style={{ color: 'var(--text-primary)' }}>
            {loading ? 'Processing receipt...' : 'Drop receipt here or click to upload'}
          </p>
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
            JPG, JPEG, PNG, WebP, BMP, GIF, HEIC — max 5MB
          </p>
        </div>
      </div>
    </div>
  )
}

export default function ReceiptsPage() {
  const [scanning, setScanning] = useState(false)
  const [result, setResult] = useState(null)
  const { mutateAsync: createExpense, isPending } = useCreateExpense()

  const handleFile = async (file) => {
    setScanning(true)
    setResult(null)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const { data } = await receiptsAPI.scan(formData)
      setResult(data.parsed)
    } catch (e) {
      toast.error(e.response?.data?.detail || 'OCR scan failed. Please try again.')
    } finally { setScanning(false) }
  }

  const handleConfirm = async (form) => {
    try {
      await createExpense({
        title:    form.merchant || 'Receipt expense',
        amount:   parseFloat(form.amount),
        category: form.category,
        date:     form.date || new Date().toISOString().split('T')[0],
        source:   'ocr',
      })
      setResult(null)
      toast.success('Expense saved from receipt!')
    } catch {}
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="page-title">Receipts Upload</h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
          Upload a receipt image to automatically extract expense details
        </p>
      </div>

      {!result && <UploadZone onFile={handleFile} loading={scanning} />}

      {result && (
        <OCRResultCard
          result={result}
          onConfirm={handleConfirm}
          onRetry={() => setResult(null)}
          loading={isPending}
        />
      )}

      <div className="card" style={{ background: 'var(--bg-card)' }}>
        <h3 className="font-semibold mb-2 text-[#1E3A5F] dark:text-blue-300">💡 Tips for better results</h3>
        <ul className="text-sm space-y-1" style={{ color: 'var(--text-secondary)' }}>
          <li>• Place receipt on a flat, well-lit surface</li>
          <li>• Keep the camera straight — avoid angles</li>
          <li>• Ensure the total amount is clearly visible</li>
          <li>• Higher resolution images give better accuracy</li>
          <li>• Supported: JPG, PNG, WebP, BMP, GIF, HEIC</li>
        </ul>
      </div>
    </div>
  )
}
