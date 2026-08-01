import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from '../hooks/useAuth'
import UsersPage from './UsersPage'
import api from '../services/api'

jest.mock('../services/api', () => ({
  __esModule: true,
  default: { get: jest.fn(), post: jest.fn(), put: jest.fn(), delete: jest.fn() },
}))

const mockedGet = api.get as jest.Mock
const mockedPost = api.post as jest.Mock
const mockedPut = api.put as jest.Mock
const mockedDelete = api.delete as jest.Mock

function fakeToken(payload: Record<string, unknown>): string {
  const base64url = (obj: object) => btoa(JSON.stringify(obj)).replace(/=+$/, '')
  return `${base64url({ alg: 'HS256' })}.${base64url(payload)}.signature`
}

function renderPage() {
  localStorage.setItem('token', fakeToken({ sub: 'user-1', role: 'admin' }))
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <UsersPage />
      </AuthProvider>
    </QueryClientProvider>
  )
}

describe('UsersPage', () => {
  let alertSpy: jest.SpyInstance

  beforeEach(() => {
    mockedGet.mockReset()
    mockedPost.mockReset()
    mockedPut.mockReset()
    mockedDelete.mockReset()
    mockedGet.mockResolvedValue({
      data: [
        {
          id: 'user-1',
          email: 'admin@dojo.com',
          full_name: 'Admin',
          role: 'admin',
          is_active: true,
        },
        {
          id: 'user-2',
          email: 'instrutor@dojo.com',
          full_name: 'Carlos Instrutor',
          role: 'instructor',
          is_active: true,
        },
      ],
    })
    alertSpy = jest.spyOn(window, 'alert').mockImplementation(() => {})
  })

  afterEach(() => {
    alertSpy.mockRestore()
  })

  it('lists existing users', async () => {
    renderPage()

    expect(await screen.findByText('Admin')).toBeInTheDocument()
    expect(screen.getByText('Carlos Instrutor')).toBeInTheDocument()
    expect(screen.getByText('instrutor@dojo.com')).toBeInTheDocument()
  })

  it('creates a new user with the submitted form data', async () => {
    mockedPost.mockResolvedValue({ data: {} })
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: /novo usuário/i }))
    await user.type(screen.getByLabelText('Nome'), 'Novo Instrutor')
    await user.type(screen.getByLabelText('Email'), 'novo@dojo.com')
    await user.type(screen.getByLabelText('Senha'), 'senha12345')
    await user.click(screen.getByRole('button', { name: /^criar$/i }))

    await waitFor(() =>
      expect(mockedPost).toHaveBeenCalledWith('/api/v1/users', {
        email: 'novo@dojo.com',
        full_name: 'Novo Instrutor',
        role: 'instructor',
        is_active: true,
        password: 'senha12345',
      })
    )
  })

  it('updates a user without sending a password when the field is left blank', async () => {
    mockedPut.mockResolvedValue({ data: {} })
    const user = userEvent.setup()
    renderPage()

    const row = (await screen.findByText('Carlos Instrutor')).closest('tr')
    if (!row) throw new Error('user row not found')
    const [editButton] = within(row).getAllByRole('button')
    await user.click(editButton)
    await user.click(screen.getByRole('button', { name: /atualizar/i }))

    await waitFor(() =>
      expect(mockedPut).toHaveBeenCalledWith('/api/v1/users/user-2', {
        email: 'instrutor@dojo.com',
        full_name: 'Carlos Instrutor',
        role: 'instructor',
        is_active: true,
      })
    )
  })

  it('deactivates a user and refreshes the list on success', async () => {
    mockedDelete.mockResolvedValue({})
    const user = userEvent.setup()
    renderPage()

    const row = (await screen.findByText('Carlos Instrutor')).closest('tr')
    if (!row) throw new Error('user row not found')
    const [, deactivateButton] = within(row).getAllByRole('button')
    await user.click(deactivateButton)

    await waitFor(() => expect(mockedDelete).toHaveBeenCalledWith('/api/v1/users/user-2'))
    expect(alertSpy).not.toHaveBeenCalled()
  })

  it('cannot deactivate its own account', async () => {
    renderPage()

    const row = (await screen.findByText('Admin')).closest('tr')
    if (!row) throw new Error('user row not found')
    const [, deactivateButton] = within(row).getAllByRole('button')

    expect(deactivateButton).toBeDisabled()
  })

  it('shows the backend error message instead of silently failing', async () => {
    mockedDelete.mockRejectedValue({
      response: { data: { detail: 'Cannot deactivate the last active admin' } },
    })
    const user = userEvent.setup()
    renderPage()

    const row = (await screen.findByText('Carlos Instrutor')).closest('tr')
    if (!row) throw new Error('user row not found')
    const [, deactivateButton] = within(row).getAllByRole('button')
    await user.click(deactivateButton)

    await waitFor(() =>
      expect(alertSpy).toHaveBeenCalledWith('Cannot deactivate the last active admin')
    )
  })
})
