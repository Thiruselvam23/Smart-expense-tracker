import { createContext, useContext, useState, useEffect } from 'react'
import { authAPI } from '../api/auth'
import { setAccessToken, clearAccessToken } from '../api/client'

const AuthContext = createContext(null)

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

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

  const setUser = (updater) => {
    setUserRaw(prev => {
      const next = typeof updater === 'function' ? updater(prev) : updater
      return resolveUser(next)
    })
  }

  useEffect(() => {
    const tryRestore = async () => {
      const refreshToken = sessionStorage.getItem('refresh_token')
      if (!refreshToken) {
        setLoading(false)
        return
      }

      try {
        // Get new access token
        const { data: tokenData } = await authAPI.refresh(refreshToken)
        setAccessToken(tokenData.access_token)

        // Get user profile
        const { data: meData } = await authAPI.me()
        setUser(meData)
      } catch (e) {
        console.error('Session restore failed:', e.response?.data || e.message)
        // Clear bad session
        sessionStorage.removeItem('refresh_token')
        clearAccessToken()
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