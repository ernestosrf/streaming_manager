import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { ROLE_ADMIN } from '@/lib/constants.js'
import { SessionExpiredError } from '@/lib/errors.js'

/* eslint-disable react-refresh/only-export-components */

const AuthContext = createContext(null)
const PENDING_REFRESH_MS = 60_000

export function AuthProvider({ children }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [token, setToken] = useState(null)
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [meta, setMeta] = useState({ admin_username: null })
  const [pendingCount, setPendingCount] = useState(0)

  const logout = useCallback(() => {
    localStorage.removeItem('auth_token')
    setIsAuthenticated(false)
    setToken(null)
    setUser(null)
    setPendingCount(0)
  }, [])

  const applySession = useCallback((newToken, userData) => {
    localStorage.setItem('auth_token', newToken)
    setIsAuthenticated(true)
    setToken(newToken)
    setUser(userData || null)
  }, [])

  useEffect(() => {
    const bootstrap = async () => {
      try {
        // Remove a chave legada que guardava o usuário (nunca era lida).
        localStorage.removeItem('auth_user')
        const savedToken = localStorage.getItem('auth_token')
        const [metaRes, verifyRes] = await Promise.all([
          fetch('/api/meta'),
          savedToken
            ? fetch('/api/auth/verify', { headers: { Authorization: `Bearer ${savedToken}` } })
            : Promise.resolve(null),
        ])

        if (metaRes.ok) {
          setMeta(await metaRes.json())
        }

        if (verifyRes?.ok) {
          const data = await verifyRes.json()
          applySession(savedToken, data.user)
        } else if (verifyRes) {
          localStorage.removeItem('auth_token')
        }
      } catch (error) {
        console.error('Erro ao verificar autenticação:', error)
      } finally {
        setLoading(false)
      }
    }

    bootstrap()
  }, [applySession])

  const login = useCallback((newToken, userData = null) => {
    applySession(newToken, userData)
  }, [applySession])

  const getAuthHeaders = useCallback(() => {
    return token ? { Authorization: `Bearer ${token}` } : {}
  }, [token])

  const refreshPendingCount = useCallback(async () => {
    if (!token || user?.role !== ROLE_ADMIN) {
      setPendingCount(0)
      return
    }
    try {
      const response = await fetch('/api/admin/users?status=pending&page=1&per_page=1', {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!response.ok) {
        setPendingCount(0)
        return
      }
      setPendingCount(Number(response.headers.get('X-Total-Count')) || 0)
    } catch {
      setPendingCount(0)
    }
  }, [token, user])

  useEffect(() => {
    refreshPendingCount()
    if (!token || user?.role !== ROLE_ADMIN) return undefined

    // Novos cadastros chegam de outros clientes; mantém o contador atualizado.
    const interval = setInterval(refreshPendingCount, PENDING_REFRESH_MS)
    window.addEventListener('focus', refreshPendingCount)
    return () => {
      clearInterval(interval)
      window.removeEventListener('focus', refreshPendingCount)
    }
  }, [refreshPendingCount, token, user])

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
      throw new SessionExpiredError()
    }

    return response
  }, [getAuthHeaders, logout])

  const value = useMemo(() => ({
    isAuthenticated,
    token,
    user,
    loading,
    meta,
    isAdmin: user?.role === ROLE_ADMIN,
    pendingCount,
    login,
    logout,
    getAuthHeaders,
    makeAuthenticatedRequest,
    refreshPendingCount,
  }), [isAuthenticated, token, user, loading, meta, pendingCount, login, logout, getAuthHeaders, makeAuthenticatedRequest, refreshPendingCount])

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
