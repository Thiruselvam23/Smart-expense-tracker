import { useState, useRef, useEffect } from 'react'
import { Menu, User, LogOut, ChevronDown } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'

export default function TopBar({ onMenuClick }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [imgError, setImgError] = useState(false)
  const ref = useRef(null)

  // Reset imgError whenever user.profile_image changes
  useEffect(() => { setImgError(false) }, [user?.profile_image])

  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleLogout = async () => {
    setOpen(false)
    await logout()
    toast.success('Logged out successfully')
    navigate('/login')
  }

  const initial = user?.full_name?.trim()?.[0]?.toUpperCase() || 'U'
  const showImage = user?.profile_image && !imgError

  return (
    <header className="border-b px-6 py-3 flex items-center justify-between"
      style={{ background: 'var(--bg-card)', borderColor: 'var(--border)' }}>

      <div className="flex items-center gap-4">
        <button onClick={onMenuClick} className="lg:hidden"
          style={{ color: 'var(--text-secondary)' }}>
          <Menu size={22} />
        </button>
        <div>
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Welcome back,</p>
          <p className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>
            {user?.full_name || 'User'}
          </p>
        </div>
      </div>

      <div className="relative" ref={ref}>
        <button onClick={() => setOpen(o => !o)}
          className="flex items-center gap-2 hover:opacity-80 transition-opacity">

          {/* Avatar — image OR fallback initial */}
          {showImage ? (
            <img
              src={user.profile_image}
              alt="avatar"
              className="w-9 h-9 rounded-full object-cover ring-2 ring-[#1E3A5F]/20 flex-shrink-0"
              onError={() => setImgError(true)}
            />
          ) : (
            <div className="w-9 h-9 rounded-full bg-[#1E3A5F] flex items-center justify-center text-white text-sm font-bold select-none flex-shrink-0">
              {initial}
            </div>
          )}

          <ChevronDown size={14} style={{ color: 'var(--text-secondary)' }}
            className={`transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
        </button>

        {open && (
          <div className="absolute right-0 mt-2 w-48 rounded-xl shadow-xl border z-50 overflow-hidden"
            style={{ background: 'var(--bg-card)', borderColor: 'var(--border)' }}>

            <div className="px-4 py-3 border-b" style={{ borderColor: 'var(--border)' }}>
              <p className="text-xs font-semibold truncate" style={{ color: 'var(--text-primary)' }}>
                {user?.full_name}
              </p>
              <p className="text-xs truncate" style={{ color: 'var(--text-muted)' }}>
                {user?.email}
              </p>
            </div>

            <button onClick={() => { setOpen(false); navigate('/profile') }}
              className="w-full flex items-center gap-3 px-4 py-2.5 text-sm font-medium transition-colors hover:opacity-80"
              style={{ color: 'var(--text-primary)' }}>
              <User size={15} /> Profile
            </button>

            <div style={{ borderTop: '1px solid var(--border)' }} />

            <button onClick={handleLogout}
              className="w-full flex items-center gap-3 px-4 py-2.5 text-sm font-medium text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors">
              <LogOut size={15} /> Logout
            </button>
          </div>
        )}
      </div>
    </header>
  )
}