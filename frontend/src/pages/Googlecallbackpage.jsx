import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { setAccessToken } from '../api/client'
import axios from 'axios'
import toast from 'react-hot-toast'
import Spinner from '../components/ui/Spinner'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export default function GoogleCallbackPage() {
    const [params] = useSearchParams()
    const navigate = useNavigate()
    const { setUser } = useAuth()
    const ran = useRef(false)
    const [status, setStatus] = useState('Signing you in with Google...')

    useEffect(() => {
        if (ran.current) return
        ran.current = true

        const access_token = params.get('access_token')
        const refresh_token = params.get('refresh_token')
        const error = params.get('error')

        // Backend sent an error
        if (error) {
            toast.error(decodeURIComponent(error))
            navigate('/login', { replace: true })
            return
        }

        // Missing tokens
        if (!access_token || !refresh_token) {
            toast.error('Missing tokens from Google login. Please try again.')
            navigate('/login', { replace: true })
            return
        }

        const finish = async () => {
            try {
                setStatus('Storing your session...')

                // Step 1 — Store tokens
                setAccessToken(access_token)
                sessionStorage.setItem('refresh_token', refresh_token)

                setStatus('Loading your profile...')

                // Step 2 — Call /me with fresh access token directly
                // Use axios directly to avoid any interceptor issues
                const { data: userData } = await axios.get(`${API_BASE}/api/auth/me`, {
                    headers: { Authorization: `Bearer ${access_token}` },
                })

                setStatus('Almost there...')

                // Step 3 — Set user in context
                setUser(userData)

                toast.success(`Welcome, ${userData.full_name || 'User'}! 🎉`)

                // Step 4 — Navigate to dashboard
                navigate('/dashboard', { replace: true })

            } catch (e) {
                console.error('Google callback error details:', {
                    status: e.response?.status,
                    data: e.response?.data,
                    message: e.message,
                })

                setStatus('Retrying...')

                // Wait 2 seconds and retry once
                await new Promise(res => setTimeout(res, 2000))

                try {
                    const { data: userData } = await axios.get(`${API_BASE}/api/auth/me`, {
                        headers: { Authorization: `Bearer ${access_token}` },
                    })
                    setUser(userData)
                    toast.success(`Welcome, ${userData.full_name || 'User'}! 🎉`)
                    navigate('/dashboard', { replace: true })
                } catch (retryErr) {
                    const errMsg = retryErr.response?.data?.detail || retryErr.message || 'Unknown error'
                    console.error('Retry failed:', errMsg)
                    toast.error(`Login failed: ${errMsg}`)
                    // Clear bad tokens
                    sessionStorage.removeItem('refresh_token')
                    navigate('/login', { replace: true })
                }
            }
        }

        finish()
    }, [])

    return (
        <div className="min-h-screen flex flex-col items-center justify-center gap-4"
            style={{ background: 'var(--bg-base)' }}>
            <Spinner size="lg" />
            <p className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                {status}
            </p>
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                Please wait, do not close this page
            </p>
        </div>
    )
}