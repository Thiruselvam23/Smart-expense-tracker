import { createContext, useContext, useState, useEffect } from 'react'
import { authAPI } from '../api/auth'
import { setAccessToken, clearAccessToken } from '../api/client'

const AuthContext = createContext(null)

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

/**
 * Convert relative profile_image path → full URL.
 * e.g. "/uploads/profile_abc.jpg" → "http://localhost:8000/uploads/profile_abc.jpg"
 */
const resolveUser = (user) => {
  if (!user) return null
  const img = user.profile_image
  if (img && !img.startsWith('http')) {
    return { ...user, profile_image: `${API_BASE}${img}` }
  }
  return user
}

export function AuthProvider({ children }) {
  const [user, setUserRaw] = useState(null)
  const [loading, setLoading] = useState(true)

  // Always resolve image URL before storing in state
  const setUser = (updater) => {
    setUserRaw(prev => {
      const next = typeof updater === 'function' ? updater(prev) : updater
      return resolveUser(next)
    })
  }

  useEffect(() => {
    const tryRestore = async () => {
      const refreshToken = sessionStorage.getItem('refresh_token')
      if (!refreshToken) { setLoading(false); return }
      try {
        // Step 1: get new access token using refresh token
        const { data: tokenData } = await authAPI.refresh(refreshToken)
        setAccessToken(tokenData.access_token)

        // Step 2: fetch FULL user profile (includes profile_image from DB)
        const { data: meData } = await authAPI.me()
        setUser(meData)
      } catch {
        sessionStorage.removeItem('refresh_token')
      } finally {
        setLoading(false)
      }
    }
    tryRestore()
  }, [])

  const login = async (email, password) => {
    const { data } = await authAPI.login({ email, password })
    setAccessToken(data.access_token)
    sessionStorage.setItem('refresh_token', data.refresh_token)

    // Login response already includes profile_image from backend
    // But also call /me to get the absolute latest from DB
    try {
      const { data: meData } = await authAPI.me()
      setUser(meData)
    } catch {
      setUser(data.user)
    }
    return data
  }

  const register = async (full_name, email, password) => {
    const { data } = await authAPI.register({ full_name, email, password })
    setAccessToken(data.access_token)
    sessionStorage.setItem('refresh_token', data.refresh_token)
    setUser(data.user)
    return data
  }

  const logout = async () => {
    try { await authAPI.logout() } catch { }
    clearAccessToken()
    sessionStorage.removeItem('refresh_token')
    setUserRaw(null)
  }

  return (
    <AuthContext.Provider value={{ user, setUser, login, register, logout, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)