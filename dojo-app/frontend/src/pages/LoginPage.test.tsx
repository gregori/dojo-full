import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import LoginPage from './LoginPage'
import { AuthProvider } from '../hooks/useAuth'
import api from '../services/api'

jest.mock('../services/api', () => ({
  __esModule: true,
  default: { post: jest.fn() },
}))

const mockedPost = api.post as jest.Mock

function renderLoginPage() {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={['/login']}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<div>Home Page</div>} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>
  )
}

async function submitLogin(user: ReturnType<typeof userEvent.setup>, container: HTMLElement) {
  // The form's <label>s aren't associated with their inputs (no `for`/`id`), so
  // getByLabelText can't find them -- query by input type instead, matching the
  // existing Cypress e2e test's convention for this same page.
  const emailInput = container.querySelector('input[type="email"]')!
  const passwordInput = container.querySelector('input[type="password"]')!
  await user.type(emailInput, 'admin@dojo.com')
  await user.type(passwordInput, 'admin123')
  await user.click(screen.getByRole('button', { name: /entrar/i }))
}

describe('LoginPage', () => {
  beforeEach(() => {
    mockedPost.mockReset()
    localStorage.clear()
  })

  it('logs in and navigates to the home page on success', async () => {
    mockedPost.mockResolvedValueOnce({ data: { access_token: 'a.b.c' } })
    const user = userEvent.setup()
    const { container } = renderLoginPage()

    await submitLogin(user, container)

    expect(await screen.findByText('Home Page')).toBeInTheDocument()
    expect(localStorage.getItem('token')).toBe('a.b.c')
  })

  it('sends credentials as application/x-www-form-urlencoded', async () => {
    mockedPost.mockResolvedValueOnce({ data: { access_token: 'a.b.c' } })
    const user = userEvent.setup()
    const { container } = renderLoginPage()

    await submitLogin(user, container)

    await waitFor(() => expect(mockedPost).toHaveBeenCalledTimes(1))
    const [url, body, config] = mockedPost.mock.calls[0]
    expect(url).toBe('/api/v1/auth/login')
    expect(body).toBeInstanceOf(URLSearchParams)
    expect(body.get('username')).toBe('admin@dojo.com')
    expect(body.get('password')).toBe('admin123')
    expect(config.headers['Content-Type']).toBe('application/x-www-form-urlencoded')
  })

  it('shows the backend error message and stays on the login page on failure', async () => {
    mockedPost.mockRejectedValueOnce({ response: { data: { detail: 'Credenciais inválidas' } } })
    const user = userEvent.setup()
    const { container } = renderLoginPage()

    await submitLogin(user, container)

    expect(await screen.findByText('Credenciais inválidas')).toBeInTheDocument()
    expect(screen.queryByText('Home Page')).not.toBeInTheDocument()
    expect(localStorage.getItem('token')).toBeNull()
  })

  it('falls back to a generic error message when the backend gives no detail', async () => {
    mockedPost.mockRejectedValueOnce(new Error('network down'))
    const user = userEvent.setup()
    const { container } = renderLoginPage()

    await submitLogin(user, container)

    expect(await screen.findByText('Erro ao fazer login')).toBeInTheDocument()
  })
})
