import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from '../hooks/useAuth'
import ContractTemplatesPage from './ContractTemplatesPage'
import api from '../services/api'

jest.mock('../services/api', () => ({
  __esModule: true,
  default: { get: jest.fn(), post: jest.fn() },
}))

const mockedGet = api.get as jest.Mock
const mockedPost = api.post as jest.Mock

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
        <ContractTemplatesPage />
      </AuthProvider>
    </QueryClientProvider>
  )
}

describe('ContractTemplatesPage', () => {
  beforeEach(() => {
    mockedGet.mockReset()
    mockedPost.mockReset()
    mockedGet.mockResolvedValue({ data: [] })
  })

  it('shows a message instead of the form when the user is not an admin', () => {
    localStorage.setItem('token', fakeToken({ sub: 'user-1', role: 'instructor' }))
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <ContractTemplatesPage />
        </AuthProvider>
      </QueryClientProvider>
    )

    expect(
      screen.getByText('Apenas administradores podem gerenciar o modelo de contrato.')
    ).toBeInTheDocument()
  })

  it('submitting the form calls the create-version endpoint with the entered body', async () => {
    mockedPost.mockResolvedValue({
      data: { id: 'v1', body: 'Corpo do contrato', status: 'active', effective_from: '2026-01-01', created_by: 'user-1', created_at: '2026-01-01' },
    })
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByText('Nova Versão'))
    await user.type(screen.getByLabelText('Corpo do Contrato'), 'Corpo do contrato')
    await user.type(screen.getByLabelText('Vigente a partir de'), '2026-01-15')
    await user.click(screen.getByText('Criar Versão'))

    await waitFor(() => expect(mockedPost).toHaveBeenCalledTimes(1))
    const [url, body] = mockedPost.mock.calls[0]
    expect(url).toBe('/api/v1/contract-templates')
    expect(body.body).toBe('Corpo do contrato')
  })

  it('renders the version history table', async () => {
    mockedGet.mockResolvedValue({
      data: [
        {
          id: 'v1',
          body: 'Corpo',
          status: 'active',
          effective_from: '2026-01-01T00:00:00Z',
          created_by: 'user-1',
          created_at: '2026-01-01T00:00:00Z',
        },
      ],
    })
    renderPage()

    expect(await screen.findByText('Ativo')).toBeInTheDocument()
  })
})
