import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from '../hooks/useAuth'
import EventSeriesPage from './EventSeriesPage'
import api from '../services/api'
import { showToast } from '../components/Toast'

jest.mock('../services/api', () => ({
  __esModule: true,
  default: { get: jest.fn(), post: jest.fn(), put: jest.fn(), delete: jest.fn() },
}))

jest.mock('../components/Toast', () => ({
  __esModule: true,
  showToast: jest.fn(),
}))

const mockedGet = api.get as jest.Mock
const mockedPost = api.post as jest.Mock
const mockedDelete = api.delete as jest.Mock
const mockedShowToast = showToast as jest.Mock

function fakeToken(payload: Record<string, unknown>): string {
  const base64url = (obj: object) => btoa(JSON.stringify(obj)).replace(/=+$/, '')
  return `${base64url({ alg: 'HS256' })}.${base64url(payload)}.signature`
}

const sampleSeries = {
  id: 'series-1',
  title: 'Aikido Geral',
  event_type_id: 'type-1',
  description: null,
  location: 'Tatame Principal',
  minimum_belt_id: null,
  days_of_week: [0, 2, 5],
  start_time: '07:00:00',
  duration_minutes: 60,
  series_start_date: '2026-01-01',
  series_end_date: null,
  is_active: true,
  check_in_token: 'series-token-abc',
}

function renderPage() {
  localStorage.setItem('token', fakeToken({ sub: 'user-1', role: 'admin' }))
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <EventSeriesPage />
      </AuthProvider>
    </QueryClientProvider>
  )
}

describe('EventSeriesPage', () => {
  beforeEach(() => {
    mockedGet.mockReset()
    mockedPost.mockReset()
    mockedDelete.mockReset()
    mockedShowToast.mockReset()

    mockedGet.mockImplementation((url: string) => {
      if (url === '/api/v1/event-series') return Promise.resolve({ data: [sampleSeries] })
      if (url === '/api/v1/events/types')
        return Promise.resolve({ data: [{ id: 'type-1', name: 'Aula Regular', color: '#3498db' }] })
      if (url === '/api/v1/belts') return Promise.resolve({ data: [] })
      return Promise.resolve({ data: [] })
    })
  })

  it('renders the series list from the API', async () => {
    renderPage()

    expect(await screen.findByText('Aikido Geral')).toBeInTheDocument()
    expect(screen.getByText('Segunda, Quarta, Sábado')).toBeInTheDocument()
    expect(screen.getByText('07:00')).toBeInTheDocument()
    expect(screen.getByText('Ativa')).toBeInTheDocument()
  })

  it('submits the create form with days_of_week as a number[] in Monday-first order', async () => {
    mockedPost.mockResolvedValue({ data: sampleSeries })
    const user = userEvent.setup()
    renderPage()

    await screen.findByText('Aikido Geral')
    await user.click(screen.getByRole('button', { name: 'Nova Série' }))

    const formHeading = await screen.findByRole('heading', { name: 'Nova Série' })
    const formSection = formHeading.closest('div')!
    const titleInput = within(within(formSection).getByText('Título').closest('div')!).getByRole(
      'textbox'
    ) as HTMLInputElement
    await user.type(titleInput, 'Judo Infantil')

    const typeSelect = within(within(formSection).getByText('Tipo').closest('div')!).getByRole(
      'combobox'
    ) as HTMLSelectElement
    await user.selectOptions(typeSelect, 'type-1')

    // Check "Quarta" (index 2) and "Sábado" (index 5) -- order sent must be
    // [2, 5], the exact indices WEEKDAY_LABELS assigns to those days.
    await user.click(screen.getByLabelText('Quarta'))
    await user.click(screen.getByLabelText('Sábado'))

    await user.click(screen.getByText('Criar'))

    await waitFor(() =>
      expect(mockedPost).toHaveBeenCalledWith('/api/v1/event-series', expect.any(Object))
    )
    const payload = mockedPost.mock.calls[0][1]
    expect(payload.days_of_week).toEqual([2, 5])
    expect(payload.title).toBe('Judo Infantil')
  })

  it('calls generate and surfaces created/skipped counts via the toast mechanism', async () => {
    mockedPost.mockResolvedValue({ data: { created_count: 365, skipped_count: 0 } })
    const user = userEvent.setup()
    renderPage()

    const row = (await screen.findByText('Aikido Geral')).closest('tr')
    if (!row) throw new Error('series row not found')

    await user.click(within(row).getByTitle('Gerar ocorrências'))

    await waitFor(() =>
      expect(mockedPost).toHaveBeenCalledWith('/api/v1/event-series/series-1/generate')
    )
    await waitFor(() =>
      expect(mockedShowToast).toHaveBeenCalledWith(
        'Ocorrências geradas: 365 criadas, 0 já existiam.',
        'success'
      )
    )
  })

  it('calls deactivate (DELETE) when ending a series', async () => {
    mockedDelete.mockResolvedValue({})
    const user = userEvent.setup()
    renderPage()

    const row = (await screen.findByText('Aikido Geral')).closest('tr')
    if (!row) throw new Error('series row not found')

    await user.click(within(row).getByTitle('Encerrar série'))

    await waitFor(() => expect(mockedDelete).toHaveBeenCalledWith('/api/v1/event-series/series-1'))
  })

  it('clicking the QR icon opens the QR modal showing the series title', async () => {
    const user = userEvent.setup()
    renderPage()

    const row = (await screen.findByText('Aikido Geral')).closest('tr')
    if (!row) throw new Error('series row not found')

    await user.click(within(row).getByTitle('Ver QR code de check-in'))

    const modalHeading = await screen.findByRole('heading', { name: 'Aikido Geral' })
    expect(modalHeading).toBeInTheDocument()
  })

  it('shows the inline unavailable message when opening the QR modal for a series with an empty check_in_token', async () => {
    mockedGet.mockImplementation((url: string) => {
      if (url === '/api/v1/event-series')
        return Promise.resolve({ data: [{ ...sampleSeries, check_in_token: '' }] })
      if (url === '/api/v1/events/types')
        return Promise.resolve({ data: [{ id: 'type-1', name: 'Aula Regular', color: '#3498db' }] })
      if (url === '/api/v1/belts') return Promise.resolve({ data: [] })
      return Promise.resolve({ data: [] })
    })
    const user = userEvent.setup()
    renderPage()

    const row = (await screen.findByText('Aikido Geral')).closest('tr')
    if (!row) throw new Error('series row not found')

    await user.click(within(row).getByTitle('Ver QR code de check-in'))

    expect(
      await screen.findByText('Link de check-in indisponível para este item.')
    ).toBeInTheDocument()
  })
})
