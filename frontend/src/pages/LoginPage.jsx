import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useAuth } from '../context/AuthContext'
import { useNavigate, Link, useSearchParams } from 'react-router-dom'
import { useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'
import Button from '../components/ui/Button'
import toast from 'react-hot-toast'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const schema = z.object({
  email: z.string().email('Invalid email'),
  password: z.string().min(1, 'Password required'),
})

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const googleError = searchParams.get('error')
  const [loading, setLoading] = useState(false)
  const [showPass, setShowPass] = useState(false)

  const { register, handleSubmit, formState: { errors } } = useForm({
    resolver: zodResolver(schema),
  })

  const onSubmit = async (data) => {
    setLoading(true)
    try {
      await login(data.email, data.password)
      toast.success('Welcome back!')
      navigate('/dashboard')
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Login failed')
    } finally { setLoading(false) }
  }

  const handleGoogleLogin = () => {
    window.location.href = `${API_BASE}/api/auth/google`
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#1E3A5F] to-[#2E86AB] flex items-center justify-center p-4">
      <div className="rounded-2xl shadow-2xl w-full max-w-md p-8"
        style={{ background: 'var(--bg-card)' }}>

        {/* Header */}
        <div className="text-center mb-8">
          <div className="text-5xl mb-3">💰</div>
          <h1 className="text-2xl font-bold text-[#1E3A5F]">Smart Expense Tracker</h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
            Sign in to your account
          </p>
        </div>

        {/* Google error message */}
        {googleError && (
          <div className="mb-4 text-red-600 text-sm text-center p-3 bg-red-50 rounded-lg border border-red-200">
            ⚠️ {decodeURIComponent(googleError)}
          </div>
        )}

        {/* Google Sign-In Button */}
        <button
          onClick={handleGoogleLogin}
          type="button"
          className="w-full flex items-center justify-center gap-3 px-4 py-3 rounded-xl border-2 font-medium text-sm transition-all hover:shadow-md active:scale-[0.98] mb-5"
          style={{
            borderColor: 'var(--border)',
            background: 'var(--bg-card)',
            color: 'var(--text-primary)',
          }}
        >
          <svg width="20" height="20" viewBox="0 0 48 48">
            <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
            <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
            <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
            <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
          </svg>
          Continue with Google
        </button>

        {/* Divider */}
        <div className="flex items-center gap-3 mb-5">
          <div className="flex-1 h-px" style={{ background: 'var(--border)' }} />
          <span className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>
            or sign in with email
          </span>
          <div className="flex-1 h-px" style={{ background: 'var(--border)' }} />
        </div>

        {/* Email/Password Form */}
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="label">Email</label>
            <input
              type="email"
              placeholder="you@example.com"
              className={`input-field ${errors.email ? 'border-red-400' : ''}`}
              {...register('email')}
            />
            {errors.email && <p className="error-text">{errors.email.message}</p>}
          </div>

          <div>
            <label className="label">Password</label>
            <div className="relative">
              <input
                type={showPass ? 'text' : 'password'}
                placeholder="••••••••"
                className={`input-field pr-11 ${errors.password ? 'border-red-400' : ''}`}
                {...register('password')}
              />
              <button
                type="button"
                onClick={() => setShowPass(s => !s)}
                className="absolute right-3 top-1/2 -translate-y-1/2 hover:opacity-70 transition-opacity"
                style={{ color: 'var(--text-muted)' }}
                tabIndex={-1}
              >
                {showPass ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
            {errors.password && <p className="error-text">{errors.password.message}</p>}
          </div>

          <Button type="submit" loading={loading} className="w-full" size="lg">
            Sign In
          </Button>
        </form>

        <p className="text-center text-sm mt-6" style={{ color: 'var(--text-muted)' }}>
          Don't have an account?{' '}
          <Link to="/register" className="text-[#2E86AB] font-medium hover:underline">
            Register here
          </Link>
        </p>
      </div>
    </div>
  )
}