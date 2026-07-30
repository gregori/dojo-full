import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from '../hooks/useAuth'
import EventsPage from './EventsPage'
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
const mockedShowToast = showToast as jest.Mock

function fakeToken(payload: Record<string, unknown>): string {
  const base64url = (obj: object) => btoa(JSON.stringify(obj)).replace(/=+$/, '')
  return `${base64url({ alg: 'HS256' })}.${base64url(payload)}.signature`
}

const sampleEvent = {
  id: 'event-1',
  title: 'Treino de Aikido',
  event_type_id: 'type-1',
  event_type: { name: 'Aula Regular', color: '#3498db' },
  start_datetime: '2026-01-05T10:00:00',
  end_datetime: '2026-01-05T12:00:00',
  description: '',
  location: 'Tatame Principal',
  status: 'scheduled',
  check_in_token: 'event-token-abc',
}

function renderPage() {
  localStorage.setItem('token', fakeToken({ sub: 'user-1', role: 'admin' }))
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <EventsPage />
      </AuthProvider>
    </QueryClientProvider>
  )
}

describe('EventsPage', () => {
  beforeEach(() => {
    mockedGet.mockReset()
    mockedShowToast.mockReset()

    mockedGet.mockImplementation((url: string) => {
      if (url === '/api/v1/events') return Promise.resolve({ data: [sampleEvent] })
      if (url === '/api/v1/events/types')
        return Promise.resolve({ data: [{ id: 'type-1', name: 'Aula Regular', color: '#3498db' }] })
      if (url.includes('/pre-checkins/')) return Promise.resolve({ data: [] })
      return Promise.resolve({ data: [] })
    })
  })

  it('clicking the QR icon on an event row opens the QR modal showing that event title', async () => {
    const user = userEvent.setup()
    renderPage()

    const row = (await screen.findByText('Treino de Aikido')).closest('tr')
    if (!row) throw new Error('event row not found')

    await user.click(within(row).getByTitle('Ver QR code de check-in'))

    const modalHeading = await screen.findByRole('heading', { name: 'Treino de Aikido' })
    expect(modalHeading).toBeInTheDocument()
  })

  it('clicking the toolbar copy-link button copies the bare precheckin URL and shows a success toast', async () => {
    const user = userEvent.setup()
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: jest.fn().mockResolvedValue(undefined) },
    })
    renderPage()

    await screen.findByText('Treino de Aikido')
    await user.click(screen.getByText('Copiar link de pré-check-in'))

    await waitFor(() =>
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        `${window.location.origin}/precheckin`
      )
    )
    expect(mockedShowToast).toHaveBeenCalledWith('Link copiado', 'success')
  })

  it("clicking a row's per-event copy-link button copies that event's precheckin URL", async () => {
    const user = userEvent.setup()
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: jest.fn().mockResolvedValue(undefined) },
    })
    renderPage()

    const row = (await screen.findByText('Treino de Aikido')).closest('tr')
    if (!row) throw new Error('event row not found')

    await user.click(within(row).getByTitle('Copiar link de pré-check-in'))

    await waitFor(() =>
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        `${window.location.origin}/precheckin?event_id=event-1`
      )
    )
    expect(mockedShowToast).toHaveBeenCalledWith('Link copiado', 'success')
  })

  it('shows an error toast when the clipboard write is denied', async () => {
    const user = userEvent.setup()
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: jest.fn().mockRejectedValue(new Error('denied')) },
    })
    renderPage()

    await screen.findByText('Treino de Aikido')
    await user.click(screen.getByText('Copiar link de pré-check-in'))

    await waitFor(() =>
      expect(mockedShowToast).toHaveBeenCalledWith('Não foi possível copiar o link', 'error')
    )
  })
})
