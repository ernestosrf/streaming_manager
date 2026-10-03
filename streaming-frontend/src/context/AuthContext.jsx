import { createContext, useCallback, useContext, useEffect, useState } from 'react'

/* eslint-disable react-refresh/only-export-components */

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [token, setToken] = useState(null)
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [meta, setMeta] = useState({ admin_username: null })

  const logout = useCallback(() => {
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_user')
    setIsAuthenticated(false)
    setToken(null)
    setUser(null)
  }, [])

  const applySession = useCallback((newToken, userData) => {
    localStorage.setItem('auth_token', newToken)
    if (userData) {
      localStorage.setItem('auth_user', JSON.stringify(userData))
    }
    setIsAuthenticated(true)
    setToken(newToken)
    setUser(userData || null)
  }, [])

  useEffect(() => {
    const bootstrap = async () => {
      try {
        const metaRes = await fetch('/api/meta')
        if (metaRes.ok) {
          setMeta(await metaRes.json())
        }

        const savedToken = localStorage.getItem('auth_token')
        if (!savedToken) {
          return
        }

        const response = await fetch('/api/auth/verify', {
          headers: { Authorization: `Bearer ${savedToken}` },
        })

        if (response.ok) {
          const data = await response.json()
          applySession(savedToken, data.user)
        } else {
          localStorage.removeItem('auth_token')
          localStorage.removeItem('auth_user')
        }
      } catch (error) {
        console.error('Erro ao verificar autenticação:', error)
      } finally {
        setLoading(false)
      }
    }

    bootstrap()
  }, [applySession])

  const login = (newToken, userData = null) => {
    applySession(newToken, userData)
  }

  const getAuthHeaders = useCallback(() => {
    return token ? { Authorization: `Bearer ${token}` } : {}
  }, [token])

  const makeAuthenticatedRequest = useCallback(async (url, options = {}) => {
    const headers = {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
      ...(options.headers || {}),
    }

    const response = await fetch(url, {
      ...options,
      headers,
    })

    if (response.status === 401) {
      logout()
      throw new Error('Sessão expirada. Faça login novamente.')
    }

    return response
  }, [getAuthHeaders, logout])

  const value = {
    isAuthenticated,
    token,
    user,
    loading,
    meta,
    isAdmin: user?.role === 'admin',
    login,
    logout,
    getAuthHeaders,
    makeAuthenticatedRequest,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth deve ser usado dentro de AuthProvider')
  }
  return context
}

export default useAuth
