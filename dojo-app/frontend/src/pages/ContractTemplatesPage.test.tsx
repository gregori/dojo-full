import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from '../hooks/useAuth'
import ContractTemplatesPage from './ContractTemplatesPage'
import api from '../services/api'

jest.mock('../services/api', () => ({
  __esModule: true,
  default: { get: jest.fn(), post: jest.fn() },
}))

jest.mock('react-markdown', () => ({
  __esModule: true,
  default: ({ children }: { children: string }) => (
    <div data-testid="markdown-body">{children}</div>
  ),
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
      data: {
        id: 'v1',
        body: 'Corpo do contrato',
        status: 'active',
        effective_from: '2026-01-01',
        created_by: 'user-1',
        created_at: '2026-01-01',
      },
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

  it('opens a modal with the version body when "Ver conteúdo" is clicked', async () => {
    const body =
      '# Contrato\n\nAluno: {{ student.contract_name }}\n\n**Cláusula 1** - Texto completo do contrato'
    mockedGet.mockResolvedValue({
      data: [
        {
          id: 'v1',
          body,
          status: 'active',
          effective_from: '2026-01-01T00:00:00Z',
          created_by: 'user-1',
          created_at: '2026-01-01T00:00:00Z',
        },
      ],
    })
    const user = userEvent.setup()
    renderPage()

    await screen.findByText('Ativo')
    expect(screen.queryByText('Fechar')).not.toBeInTheDocument()

    await user.click(screen.getByTitle('Ver conteúdo'))

    expect(screen.getByText('Fechar')).toBeInTheDocument()
    // The raw, unsubstituted Markdown-with-placeholders body is passed straight through
    // to ReactMarkdown, unmodified (CTM-02/CTM-10: no client-side substitution).
    expect(screen.getByTestId('markdown-body').textContent).toBe(body)
  })

  it('no longer renders the version body inside a whitespace-pre-wrap element', async () => {
    mockedGet.mockResolvedValue({
      data: [
        {
          id: 'v1',
          body: 'Corpo do contrato',
          status: 'active',
          effective_from: '2026-01-01T00:00:00Z',
          created_by: 'user-1',
          created_at: '2026-01-01T00:00:00Z',
        },
      ],
    })
    const user = userEvent.setup()
    renderPage()

    await screen.findByText('Ativo')
    await user.click(screen.getByTitle('Ver conteúdo'))

    expect(document.querySelector('.whitespace-pre-wrap')).not.toBeInTheDocument()
    expect(screen.getByTestId('markdown-body')).toBeInTheDocument()
  })

  it('shows Markdown-syntax guidance in the authoring helper text', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByText('Nova Versão'))

    expect(
      screen.getByText(
        (_, element) =>
          element?.tagName.toLowerCase() === 'p' &&
          Boolean(
            element.textContent?.includes(
              'Você pode usar **negrito**, _itálico_, # e ## para títulos, - para listas, e --- para uma linha divisória.'
            )
          )
      )
    ).toBeInTheDocument()
  })

  it('shows a placeholder message in the live preview when the body is empty', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByText('Nova Versão'))

    expect(screen.getByText('A pré-visualização aparecerá aqui.')).toBeInTheDocument()
    expect(screen.queryByTestId('markdown-body')).not.toBeInTheDocument()
  })

  it('updates the live preview as the user types in the authoring textarea', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByText('Nova Versão'))
    await user.type(screen.getByLabelText('Corpo do Contrato'), '# Título')

    expect(screen.queryByText('A pré-visualização aparecerá aqui.')).not.toBeInTheDocument()
    expect(screen.getByTestId('markdown-body').textContent).toBe('# Título')

    await user.type(screen.getByLabelText('Corpo do Contrato'), '\n\n**negrito**')

    expect(screen.getByTestId('markdown-body').textContent).toBe('# Título\n\n**negrito**')
  })

  it('shows unsubstituted placeholders in the live preview, matching the view-modal guarantee', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByText('Nova Versão'))
    fireEvent.change(screen.getByLabelText('Corpo do Contrato'), {
      target: { value: 'Aluno: {{ student.contract_name }}' },
    })

    expect(screen.getByTestId('markdown-body').textContent).toBe(
      'Aluno: {{ student.contract_name }}'
    )
  })

  it('closes the modal when "Fechar" is clicked', async () => {
    mockedGet.mockResolvedValue({
      data: [
        {
          id: 'v1',
          body: 'Corpo da versão',
          status: 'superseded',
          effective_from: '2026-01-01T00:00:00Z',
          created_by: 'user-1',
          created_at: '2026-01-01T00:00:00Z',
        },
      ],
    })
    const user = userEvent.setup()
    renderPage()

    await screen.findByText('Substituído')
    await user.click(screen.getByTitle('Ver conteúdo'))
    expect(screen.getByText('Fechar')).toBeInTheDocument()

    await user.click(screen.getByText('Fechar'))

    expect(screen.queryByText('Fechar')).not.toBeInTheDocument()
    expect(screen.queryByText('Corpo da versão')).not.toBeInTheDocument()
  })

  it("shows each version's own body when switching between rows", async () => {
    mockedGet.mockResolvedValue({
      data: [
        {
          id: 'v1',
          body: 'Corpo da versão ativa',
          status: 'active',
          effective_from: '2026-02-01T00:00:00Z',
          created_by: 'user-1',
          created_at: '2026-02-01T00:00:00Z',
        },
        {
          id: 'v2',
          body: 'Corpo da versão antiga',
          status: 'superseded',
          effective_from: '2026-01-01T00:00:00Z',
          created_by: 'user-1',
          created_at: '2026-01-01T00:00:00Z',
        },
      ],
    })
    const user = userEvent.setup()
    renderPage()

    await screen.findByText('Ativo')
    const viewButtons = screen.getAllByTitle('Ver conteúdo')
    expect(viewButtons).toHaveLength(2)

    await user.click(viewButtons[0])
    expect(screen.getByText('Corpo da versão ativa')).toBeInTheDocument()
    await user.click(screen.getByText('Fechar'))

    await user.click(viewButtons[1])
    expect(screen.getByText('Corpo da versão antiga')).toBeInTheDocument()
  })
})
