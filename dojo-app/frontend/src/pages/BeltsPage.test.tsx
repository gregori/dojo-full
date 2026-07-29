import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from '../hooks/useAuth'
import BeltsPage from './BeltsPage'
import api from '../services/api'

jest.mock('../services/api', () => ({
  __esModule: true,
  default: { get: jest.fn(), post: jest.fn(), put: jest.fn(), delete: jest.fn() },
}))

const mockedGet = api.get as jest.Mock
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
        <BeltsPage />
      </AuthProvider>
    </QueryClientProvider>
  )
}

describe('BeltsPage', () => {
  let alertSpy: jest.SpyInstance

  beforeEach(() => {
    mockedGet.mockReset()
    mockedDelete.mockReset()
    mockedGet.mockResolvedValue({
      data: [
        { id: 'belt-1', name: 'Branca', category: 'adult', sort_order: 1, organization_id: null },
      ],
    })
    alertSpy = jest.spyOn(window, 'alert').mockImplementation(() => {})
  })

  afterEach(() => {
    alertSpy.mockRestore()
  })

  it('deletes a belt and refreshes the list on success', async () => {
    mockedDelete.mockResolvedValue({})
    const user = userEvent.setup()
    renderPage()

    const row = (await screen.findByText('Branca')).closest('tr')
    if (!row) throw new Error('belt row not found')
    const [, deleteButton] = within(row).getAllByRole('button')
    await user.click(deleteButton)

    await waitFor(() => expect(mockedDelete).toHaveBeenCalledWith('/api/v1/belts/belt-1'))
    expect(alertSpy).not.toHaveBeenCalled()
  })

  it('shows the backend error message instead of silently failing when the belt is in use', async () => {
    mockedDelete.mockRejectedValue({
      response: {
        data: { detail: 'Belt is assigned to one or more students and cannot be deleted' },
      },
    })
    const user = userEvent.setup()
    renderPage()

    const row = (await screen.findByText('Branca')).closest('tr')
    if (!row) throw new Error('belt row not found')
    const [, deleteButton] = within(row).getAllByRole('button')
    await user.click(deleteButton)

    await waitFor(() =>
      expect(alertSpy).toHaveBeenCalledWith(
        'Belt is assigned to one or more students and cannot be deleted'
      )
    )
  })

  it('falls back to a generic message when the error has no detail', async () => {
    mockedDelete.mockRejectedValue(new Error('Network error'))
    const user = userEvent.setup()
    renderPage()

    const row = (await screen.findByText('Branca')).closest('tr')
    if (!row) throw new Error('belt row not found')
    const [, deleteButton] = within(row).getAllByRole('button')
    await user.click(deleteButton)

    await waitFor(() => expect(alertSpy).toHaveBeenCalledWith('Não foi possível excluir a faixa.'))
  })
})
