import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { api } from './api'

const AuthContext = createContext(null)
const TOKEN_KEY = 'campuslands_ops_token'

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY) || '')
  const [user, setUser] = useState(null)
  const [booting, setBooting] = useState(true)

  useEffect(() => {
    let active = true
    async function restore() {
      if (!token) {
        if (active) {
          setUser(null)
          setBooting(false)
        }
        return
      }
      try {
        const me = await api('/auth/me', {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (active) setUser(me)
      } catch {
        localStorage.removeItem(TOKEN_KEY)
        if (active) {
          setToken('')
          setUser(null)
        }
      } finally {
        if (active) setBooting(false)
      }
    }
    restore()
    return () => {
      active = false
    }
  }, [token])

  const value = useMemo(
    () => ({
      token,
      user,
      booting,
      async login(username, password) {
        const result = await api('/auth/login', {
          method: 'POST',
          body: JSON.stringify({ username, password }),
        })
        localStorage.setItem(TOKEN_KEY, result.token)
        setToken(result.token)
        setUser(result.user)
        return result.user
      },
      async logout() {
        try {
          if (token) {
            await api('/auth/logout', {
              method: 'POST',
              headers: { Authorization: `Bearer ${token}` },
            })
          }
        } catch {
          // la sesión local se limpia de todas formas
        }
        localStorage.removeItem(TOKEN_KEY)
        setToken('')
        setUser(null)
      },
      authHeaders() {
        return token ? { Authorization: `Bearer ${token}` } : {}
      },
    }),
    [token, user, booting],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth debe usarse dentro de AuthProvider')
  return ctx
}
