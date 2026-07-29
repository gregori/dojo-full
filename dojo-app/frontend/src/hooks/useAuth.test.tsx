import { renderHook, act } from '@testing-library/react'
import { AuthProvider, useAuth } from './useAuth'

/** Builds a syntactically-valid JWT with the given payload; signature is irrelevant client-side. */
function fakeToken(payload: Record<string, unknown>): string {
  const base64url = (obj: object) => btoa(JSON.stringify(obj)).replace(/=+$/, '')
  return `${base64url({ alg: 'HS256' })}.${base64url(payload)}.signature`
}

describe('useAuth', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('throws when used outside an AuthProvider', () => {
    const { result } = renderHook(() => {
      try {
        return useAuth()
      } catch (error) {
        return error
      }
    })
    expect(result.current).toBeInstanceOf(Error)
  })

  it('starts with no user when there is no stored token', () => {
    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })
    expect(result.current.user).toBeNull()
    expect(result.current.isAdmin).toBe(false)
  })

  it('restores the user from a token already in localStorage', () => {
    localStorage.setItem(
      'token',
      fakeToken({ sub: 'user-1', email: 'a@b.com', name: 'Alice', role: 'admin' })
    )
    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })
    expect(result.current.user).toEqual({
      id: 'user-1',
      email: 'a@b.com',
      full_name: 'Alice',
      role: 'admin',
    })
    expect(result.current.isAdmin).toBe(true)
  })

  it('discards an unparseable stored token instead of throwing', () => {
    localStorage.setItem('token', 'not-a-jwt')
    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })
    expect(result.current.user).toBeNull()
    expect(localStorage.getItem('token')).toBeNull()
  })

  it('login() decodes the token, stores it, and sets the user', () => {
    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })

    act(() => {
      result.current.login(fakeToken({ sub: 'user-2', role: 'instructor' }))
    })

    expect(result.current.user).toEqual({
      id: 'user-2',
      email: '',
      full_name: '',
      role: 'instructor',
    })
    expect(localStorage.getItem('token')).not.toBeNull()
    expect(result.current.isAdmin).toBe(false)
  })

  it('logout() clears the user and the stored token', () => {
    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })

    act(() => {
      result.current.login(fakeToken({ sub: 'user-3', role: 'admin' }))
    })
    expect(result.current.user).not.toBeNull()

    act(() => {
      result.current.logout()
    })

    expect(result.current.user).toBeNull()
    expect(localStorage.getItem('token')).toBeNull()
  })
})
