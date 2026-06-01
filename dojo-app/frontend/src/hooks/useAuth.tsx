import { createContext, useContext, useState, useCallback, ReactNode } from 'react'

interface User {
  id: string
  email: string
  full_name: string
  role: 'admin' | 'instructor'
}

interface AuthContextType {
  user: User | null
  login: (token: string) => void
  logout: () => void
  isAdmin: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    const token = localStorage.getItem('token')
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]))
        return {
          id: payload.sub,
          email: payload.email || '',
          full_name: payload.name || '',
          role: payload.role || 'instructor',
        }
      } catch {
        localStorage.removeItem('token')
      }
    }
    return null
  })

  const login = useCallback((token: string) => {
    localStorage.setItem('token', token)
    try {
      const payload = JSON.parse(atob(token.split('.')[1]))
      setUser({
        id: payload.sub,
        email: payload.email || '',
        full_name: payload.name || '',
        role: payload.role || 'instructor',
      })
    } catch {
      setUser(null)
    }
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    setUser(null)
  }, [])

  const value = {
    user,
    login,
    logout,
    isAdmin: user?.role === 'admin',
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
