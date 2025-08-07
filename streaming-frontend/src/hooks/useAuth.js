import { useState, useEffect } from 'react'

const useAuth = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [token, setToken] = useState(null)
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    checkAuthStatus()
  }, [])

  const checkAuthStatus = async () => {
    try {
      const savedToken = localStorage.getItem('auth_token')
      const savedUser = localStorage.getItem('auth_user')

      if (savedToken) {
        // Verificar se o token ainda é válido
        const response = await fetch('/api/auth/verify', {
          headers: {
            'Authorization': `Bearer ${savedToken}`
          }
        })

        if (response.ok) {
          setIsAuthenticated(true)
          setToken(savedToken)
          setUser(savedUser)
        } else {
          // Token inválido, remover do localStorage
          localStorage.removeItem('auth_token')
          localStorage.removeItem('auth_user')
        }
      }
    } catch (error) {
      console.error('Erro ao verificar autenticação:', error)
    } finally {
      setLoading(false)
    }
  }

  const login = (newToken, userData = null) => {
    setIsAuthenticated(true)
    setToken(newToken)
    setUser(userData || localStorage.getItem('auth_user'))
  }

  const logout = () => {
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_user')
    setIsAuthenticated(false)
    setToken(null)
    setUser(null)
  }

  const getAuthHeaders = () => {
    return token ? { 'Authorization': `Bearer ${token}` } : {}
  }

  const makeAuthenticatedRequest = async (url, options = {}) => {
    const headers = {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
      ...(options.headers || {})
    }

    const response = await fetch(url, {
      ...options,
      headers
    })

    // Se receber 401, significa que o token expirou
    if (response.status === 401) {
      logout()
      throw new Error('Sessão expirada. Faça login novamente.')
    }

    return response
  }

  return {
    isAuthenticated,
    token,
    user,
    loading,
    login,
    logout,
    getAuthHeaders,
    makeAuthenticatedRequest,
    checkAuthStatus
  }
}

export default useAuth
