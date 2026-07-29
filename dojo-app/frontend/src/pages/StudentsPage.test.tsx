import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from '../hooks/useAuth'
import StudentsPage from './StudentsPage'
import api from '../services/api'

jest.mock('../services/api', () => ({
  __esModule: true,
  default: { get: jest.fn(), post: jest.fn(), put: jest.fn(), delete: jest.fn() },
}))

const mockedGet = api.get as jest.Mock
const mockedPost = api.post as jest.Mock

const STUDENT = {
  id: 'student-1',
  full_name: 'Aluno Teste',
  registration_number: 'REG001',
  email: null,
  phone: '11999999999',
  birth_date: null,
  category: 'adult',
  current_belt: { name: 'Branca', id: 'belt-1' },
  is_active: true,
  contract_name: null,
  contract_cpf: null,
  address_street: null,
  address_neighborhood: null,
  address_city: null,
  address_zip: null,
  classes_per_week: 2,
  class_days: null,
}

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
        <StudentsPage />
      </AuthProvider>
    </QueryClientProvider>
  )
}

let currentContract: Record<string, unknown> | null

function setupApiMocks() {
  currentContract = null

  mockedGet.mockImplementation((url: string) => {
    if (url === '/api/v1/students') return Promise.resolve({ data: [STUDENT] })
    if (url === '/api/v1/belts') {
      return Promise.resolve({
        data: [{ id: 'belt-1', name: 'Branca', color: '#ffffff', order: 1, category: 'adult' }],
      })
    }
    if (url.endsWith('/progress')) {
      return Promise.resolve({
        data: {
          current_belt: 'Branca',
          next_belt: null,
          requirements: [],
          overall_progress: { total_required: 0, total_complete: 0, percentage: 100 },
          last_promotion_date: null,
        },
      })
    }
    if (url.includes('/medical-exams/students/') && url.endsWith('/status')) {
      return Promise.resolve({ data: { student_id: STUDENT.id, status: 'sem_registro' } })
    }
    if (url.endsWith('/plan')) return Promise.resolve({ data: [] })
    if (url.endsWith('/mensalidades')) return Promise.resolve({ data: [] })
    if (url.endsWith('/balance')) {
      return Promise.resolve({
        data: { student_id: STUDENT.id, balance: '0', open_count: 0, overdue_count: 0 },
      })
    }
    if (url.endsWith('/contracts/current')) {
      return currentContract
        ? Promise.resolve({ data: currentContract })
        : Promise.reject(new Error('404'))
    }
    if (url.endsWith('/contracts')) {
      return Promise.resolve({ data: currentContract ? [currentContract] : [] })
    }
    return Promise.reject(new Error(`Unhandled GET ${url}`))
  })
}

describe('StudentsPage contract integration', () => {
  beforeEach(() => {
    // jsdom has no real canvas rendering context; the embedded SignaturePad
    // only needs a handful of drawing primitives at construction/clear() time.
    HTMLCanvasElement.prototype.getContext = jest.fn(() => ({
      fillStyle: '',
      clearRect: jest.fn(),
      fillRect: jest.fn(),
    })) as unknown as typeof HTMLCanvasElement.prototype.getContext
    mockedGet.mockReset()
    mockedPost.mockReset()
    setupApiMocks()
  })

  it('repoints the "Matricular/Renovar" button in the Financeiro modal at the combined endpoint', async () => {
    mockedPost.mockResolvedValue({
      data: {
        id: 'contract-1',
        status: 'draft',
        signature_method: null,
        signed_at: null,
        document: null,
      },
    })
    const user = userEvent.setup()
    renderPage()

    await screen.findByText('Aluno Teste')
    await user.click(screen.getByTitle('Financeiro'))
    await user.click(await screen.findByText('Matricular/Renovar (Plano + Contrato)'))

    await waitFor(() =>
      expect(mockedPost).toHaveBeenCalledWith(`/api/v1/students/${STUDENT.id}/contracts/matricular`)
    )
    expect(mockedPost).not.toHaveBeenCalledWith(`/api/v1/students/${STUDENT.id}/plan`)
  })

  it('opens the contract modal, generates a draft, and shows the updated status badge', async () => {
    mockedPost.mockImplementation((url: string) => {
      if (url.endsWith('/contracts/matricular')) {
        currentContract = {
          id: 'contract-1',
          status: 'draft',
          signature_method: null,
          signed_at: null,
          document: {
            id: 'doc-1',
            mime_type: 'application/pdf',
            size_bytes: 10,
            status: 'active',
            created_at: '2026-01-01',
          },
          created_at: '2026-01-01',
        }
        return Promise.resolve({ data: currentContract })
      }
      return Promise.reject(new Error(`Unhandled POST ${url}`))
    })
    const user = userEvent.setup()
    renderPage()

    await screen.findByText('Aluno Teste')
    await user.click(screen.getByTitle('Contrato'))

    const modal = await screen.findByText(/Contrato — Aluno Teste/)
    const dialog = modal.closest('div')!.parentElement as HTMLElement
    expect(within(dialog).getByText('Sem contrato')).toBeInTheDocument()

    await user.click(within(dialog).getByText('Matricular/Renovar'))

    await waitFor(() =>
      expect(mockedPost).toHaveBeenCalledWith(`/api/v1/students/${STUDENT.id}/contracts/matricular`)
    )
    await waitFor(() => expect(screen.getAllByText('Rascunho').length).toBeGreaterThan(0))
  })

  it('calls the regenerate endpoint from the contract modal', async () => {
    currentContract = {
      id: 'contract-1',
      status: 'draft',
      signature_method: null,
      signed_at: null,
      document: {
        id: 'doc-1',
        mime_type: 'application/pdf',
        size_bytes: 10,
        status: 'active',
        created_at: '2026-01-01',
      },
      created_at: '2026-01-01',
    }
    mockedPost.mockResolvedValue({ data: currentContract })
    const user = userEvent.setup()
    renderPage()

    await screen.findByText('Aluno Teste')
    await user.click(screen.getByTitle('Contrato'))
    await waitFor(() => expect(screen.getAllByText('Rascunho').length).toBeGreaterThan(0))

    await user.click(screen.getByText('Regenerar Rascunho'))

    await waitFor(() =>
      expect(mockedPost).toHaveBeenCalledWith('/api/v1/contracts/contract-1/regenerate')
    )
  })

  it('prefills the edit form with the registration number and current belt, and sends edits to the API', async () => {
    mockedPost.mockResolvedValue({})
    const mockedPut = api.put as jest.Mock
    mockedPut.mockResolvedValue({ data: { ...STUDENT } })
    const user = userEvent.setup()
    renderPage()

    await screen.findByText('Aluno Teste')
    await user.click(screen.getByTitle('Editar'))

    const formSection = (await screen.findByText('Editar Aluno')).closest('div')!
    const registrationLabel = within(formSection).getByText(/Matrícula/)
    const registrationInput = within(registrationLabel.closest('div')!).getByRole(
      'textbox'
    ) as HTMLInputElement
    expect(registrationInput).toHaveValue('REG001')

    const beltLabel = within(formSection).getByText('Faixa')
    const beltSelect = within(beltLabel.closest('div')!).getByRole('combobox') as HTMLSelectElement
    expect(beltSelect.value).toBe('belt-1')

    await user.clear(registrationInput)
    await user.type(registrationInput, 'REG999')
    await user.click(screen.getByText('Atualizar'))

    await waitFor(() =>
      expect(mockedPut).toHaveBeenCalledWith(
        `/api/v1/students/${STUDENT.id}`,
        expect.objectContaining({ registration_number: 'REG999' })
      )
    )
  })

  it('calls the download endpoint when "Baixar Contrato Atual" is clicked', async () => {
    currentContract = {
      id: 'contract-1',
      status: 'signed',
      signature_method: 'on_screen',
      signed_at: '2026-01-01',
      document: {
        id: 'doc-1',
        mime_type: 'application/pdf',
        size_bytes: 10,
        status: 'active',
        created_at: '2026-01-01',
      },
      created_at: '2026-01-01',
    }
    mockedGet.mockImplementation((url: string, config?: { responseType?: string }) => {
      if (url === '/api/v1/contracts/contract-1/download') {
        expect(config?.responseType).toBe('blob')
        return Promise.resolve({ data: new Blob(['%PDF-1.4']) })
      }
      if (url === '/api/v1/students') return Promise.resolve({ data: [STUDENT] })
      if (url === '/api/v1/belts') return Promise.resolve({ data: [] })
      if (url.endsWith('/progress')) {
        return Promise.resolve({
          data: {
            current_belt: 'Branca',
            next_belt: null,
            requirements: [],
            overall_progress: { total_required: 0, total_complete: 0, percentage: 100 },
            last_promotion_date: null,
          },
        })
      }
      if (url.includes('/medical-exams/students/') && url.endsWith('/status')) {
        return Promise.resolve({ data: { student_id: STUDENT.id, status: 'sem_registro' } })
      }
      if (url.endsWith('/contracts/current')) return Promise.resolve({ data: currentContract })
      if (url.endsWith('/contracts')) return Promise.resolve({ data: [currentContract] })
      return Promise.reject(new Error(`Unhandled GET ${url}`))
    })
    window.URL.createObjectURL = jest.fn(() => 'blob:mock-url')
    window.URL.revokeObjectURL = jest.fn()
    const user = userEvent.setup()
    renderPage()

    await screen.findByText('Aluno Teste')
    await user.click(screen.getByTitle('Contrato'))
    await waitFor(() => expect(screen.getAllByText('Assinado').length).toBeGreaterThan(0))

    await user.click(screen.getByText('Baixar Contrato Atual'))

    await waitFor(() =>
      expect(mockedGet).toHaveBeenCalledWith('/api/v1/contracts/contract-1/download', {
        responseType: 'blob',
      })
    )
  })
})
