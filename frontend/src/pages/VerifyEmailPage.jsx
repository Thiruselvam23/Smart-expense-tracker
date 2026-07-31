import { useEffect, useRef, useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { setAccessToken } from '../api/client'
import axios from 'axios'
import toast from 'react-hot-toast'
import Spinner from '../components/ui/Spinner'
import { CheckCircle, XCircle } from 'lucide-react'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export default function VerifyEmailPage() {
    const [params] = useSearchParams()
    const navigate = useNavigate()
    const { setUser } = useAuth()
    const ran = useRef(false)
    const [status, setStatus] = useState('verifying') // verifying | success | error
    const [message, setMessage] = useState('')

    useEffect(() => {
        if (ran.current) return
        ran.current = true

        const token = params.get('token')

        if (!token) {
            setStatus('error')
            setMessage('Invalid verification link. Please register again.')
            return
        }

        const verify = async () => {
            try {
                setStatus('verifying')

                // Call backend verify endpoint — returns access_token + refresh_token
                const { data } = await axios.get(
                    `${API_BASE}/api/auth/verify-email?token=${token}`
                )

                // Store tokens
                setAccessToken(data.access_token)
                sessionStorage.setItem('refresh_token', data.refresh_token)

                // Fetch user profile
                const { data: userData } = await axios.get(`${API_BASE}/api/auth/me`, {
                    headers: { Authorization: `Bearer ${data.access_token}` },
                })

                setUser(userData)
                setStatus('success')
                toast.success('Email verified! Welcome to Smart Expense Tracker 🎉')

                // Redirect to dashboard after 1.5 seconds
                setTimeout(() => navigate('/dashboard', { replace: true }), 1500)

            } catch (e) {
                const msg = e.response?.data?.detail || 'Verification failed. Please try again.'
                setStatus('error')
                setMessage(msg)
            }
        }

        verify()
    }, [])

    return (
        <div className="min-h-screen bg-gradient-to-br from-[#1E3A5F] to-[#2E86AB] flex items-center justify-center p-4">
            <div className="rounded-2xl shadow-2xl w-full max-w-md p-8 text-center"
                style={{ background: 'var(--bg-card)' }}>

                {/* Verifying */}
                {status === 'verifying' && (
                    <>
                        <Spinner size="lg" className="mx-auto mb-6" />
                        <h1 className="text-xl font-bold text-[#1E3A5F] mb-2">Verifying Your Email</h1>
                        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
                            Please wait...
                        </p>
                    </>
                )}

                {/* Success */}
                {status === 'success' && (
                    <>
                        <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
                            <CheckCircle size={40} className="text-green-600" />
                        </div>
                        <h1 className="text-xl font-bold text-[#1E3A5F] mb-2">Email Verified!</h1>
                        <p className="text-sm mb-4" style={{ color: 'var(--text-muted)' }}>
                            Your account is now active. Redirecting to dashboard...
                        </p>
                        <Spinner size="sm" className="mx-auto" />
                    </>
                )}

                {/* Error */}
                {status === 'error' && (
                    <>
                        <div className="w-20 h-20 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-6">
                            <XCircle size={40} className="text-red-500" />
                        </div>
                        <h1 className="text-xl font-bold text-[#1E3A5F] mb-2">Verification Failed</h1>
                        <p className="text-sm mb-6" style={{ color: 'var(--text-muted)' }}>
                            {message}
                        </p>
                        <button
                            onClick={() => navigate('/register')}
                            className="btn-primary w-full"
                        >
                            Register Again
                        </button>
                        <button
                            onClick={() => navigate('/login')}
                            className="block w-full mt-3 text-sm text-[#2E86AB] hover:underline"
                        >
                            Back to Login
                        </button>
                    </>
                )}
            </div>
        </div>
    )
}