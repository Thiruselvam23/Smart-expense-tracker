import { useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { setAccessToken } from '../api/client'
import { authAPI } from '../api/auth'
import toast from 'react-hot-toast'
import Spinner from '../components/ui/Spinner'

export default function GoogleCallbackPage() {
    const [params] = useSearchParams()
    const navigate = useNavigate()
    const { setUser } = useAuth()
    const ran = useRef(false)   // prevent double-run in StrictMode

    useEffect(() => {
        if (ran.current) return
        ran.current = true

        const access_token = params.get('access_token')
        const refresh_token = params.get('refresh_token')

        if (!access_token || !refresh_token) {
            toast.error('Google login failed. Please try again.')
            navigate('/login')
            return
        }

        const finish = async () => {
            try {
                // Store tokens
                setAccessToken(access_token)
                sessionStorage.setItem('refresh_token', refresh_token)

                // Fetch full user profile (includes profile_image from Google)
                const { data } = await authAPI.me()
                setUser(data)

                toast.success(`Welcome, ${data.full_name}!`)
                navigate('/dashboard', { replace: true })
            } catch {
                toast.error('Login failed. Please try again.')
                navigate('/login')
            }
        }

        finish()
    }, [])

    return (
        <div className="min-h-screen flex flex-col items-center justify-center gap-4"
            style={{ background: 'var(--bg-base)' }}>
            <Spinner size="lg" />
            <p className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                Signing you in with Google...
            </p>
        </div>
    )
}