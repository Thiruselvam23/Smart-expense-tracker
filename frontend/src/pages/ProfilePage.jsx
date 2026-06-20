import { useState, useRef, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { formatDate } from '../utils'
import { User, Mail, Calendar, Camera } from 'lucide-react'
import toast from 'react-hot-toast'
import client from '../api/client'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const resolveImageUrl = (path) => {
  if (!path) return null
  if (path.startsWith('http')) return path
  return `${API_BASE}${path}`
}

export default function ProfilePage() {
  const { user, setUser } = useAuth()
  const [uploading, setUploading] = useState(false)
  const [imgError, setImgError] = useState(false)
  const fileRef = useRef(null)

  const resolvedSrc = resolveImageUrl(user?.profile_image)
  const showImage = resolvedSrc && !imgError
  const initial = user?.full_name?.trim()?.[0]?.toUpperCase() || 'U'

  // Reset error when image changes
  useEffect(() => { setImgError(false) }, [user?.profile_image])

  const handleImageChange = async (e) => {
    const file = e.target.files[0]
    if (!file) return

    if (!file.type.startsWith('image/')) {
      toast.error('Please select an image file')
      return
    }
    if (file.size > 2 * 1024 * 1024) {
      toast.error('Image must be under 2MB')
      return
    }

    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const { data } = await client.post('/api/auth/profile-image', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })

      // Update user context — TopBar also refreshes
      setUser(prev => ({ ...prev, profile_image: data.profile_image_url }))
      setImgError(false)
      toast.success('Profile picture updated!')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to upload image')
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  return (
    <div className="max-w-xl mx-auto space-y-6">
      <h1 className="page-title">Profile</h1>

      <div className="card text-center">
        <div className="relative w-28 h-28 mx-auto mb-4">

          {/* Avatar — image or initial letter */}
          {showImage ? (
            <img
              src={resolvedSrc}
              alt="Profile"
              className="w-28 h-28 rounded-full object-cover ring-4 ring-[#1E3A5F]/20"
              onError={() => setImgError(true)}
            />
          ) : (
            <div className="w-28 h-28 rounded-full bg-[#1E3A5F] flex items-center justify-center text-white font-bold select-none"
              style={{ fontSize: '2.5rem' }}>
              {initial}
            </div>
          )}

          {/* Camera button */}
          <button
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
            className="absolute bottom-1 right-1 w-9 h-9 rounded-full bg-[#2E86AB] flex items-center justify-center text-white shadow-lg hover:bg-[#1E6A8A] transition-colors border-2 border-white"
            title="Change profile picture"
          >
            {uploading
              ? <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              : <Camera size={15} />
            }
          </button>

          <input
            ref={fileRef}
            type="file"
            accept="image/jpeg,image/png,image/webp,image/gif,image/bmp"
            className="hidden"
            onChange={handleImageChange}
          />
        </div>

        <h2 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>
          {user?.full_name}
        </h2>
        <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>{user?.email}</p>
        <p className="text-xs mt-2" style={{ color: 'var(--text-muted)' }}>
          Click the 📷 camera icon to update your profile picture
        </p>
      </div>

      <div className="card space-y-3">
        <h2 className="section-title">Account Details</h2>
        {[
          { icon: User, label: 'Full Name', value: user?.full_name },
          { icon: Mail, label: 'Email', value: user?.email },
          { icon: Calendar, label: 'Member Since', value: formatDate(user?.created_at) },
        ].map(({ icon: Icon, label, value }) => (
          <div key={label} className="flex items-center gap-3 p-3 rounded-lg"
            style={{ background: 'var(--hover)' }}>
            <Icon size={17} style={{ color: 'var(--text-muted)' }} />
            <div>
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{label}</p>
              <p className="font-medium text-sm" style={{ color: 'var(--text-primary)' }}>{value}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="card">
        <h2 className="section-title mb-3">Preferences</h2>
        <div className="flex items-center justify-between p-3 rounded-lg"
          style={{ background: 'var(--hover)' }}>
          <span className="text-sm" style={{ color: 'var(--text-primary)' }}>Currency</span>
          <span className="font-medium text-sm" style={{ color: 'var(--text-primary)' }}>₹ INR</span>
        </div>
      </div>
    </div>
  )
}