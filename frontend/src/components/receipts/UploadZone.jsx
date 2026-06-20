import { useDropzone } from 'react-dropzone'
import { Upload, Image } from 'lucide-react'

export default function UploadZone({ onFile, loading }) {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: { 'image/jpeg': ['.jpg', '.jpeg'], 'image/png': ['.png'] },
    maxFiles: 1,
    disabled: loading,
    onDrop: (files) => files[0] && onFile(files[0]),
  })

  return (
    <div {...getRootProps()} className={`
      border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors
      ${isDragActive ? 'border-accent bg-blue-50' : 'border-gray-300 hover:border-accent hover:bg-gray-50'}
      ${loading ? 'opacity-50 cursor-not-allowed' : ''}
    `}>
      <input {...getInputProps()} />
      <div className="flex flex-col items-center gap-3">
        {loading
          ? <div className="w-10 h-10 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          : <Upload size={40} className="text-gray-400" />}
        <div>
          <p className="font-medium text-gray-700">{loading ? 'Processing receipt...' : 'Drop receipt here or click to upload'}</p>
          <p className="text-sm text-gray-400 mt-1">JPG and PNG only, max 5MB</p>
        </div>
      </div>
    </div>
  )
}
