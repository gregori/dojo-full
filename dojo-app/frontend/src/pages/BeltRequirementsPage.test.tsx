import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from '../hooks/useAuth'
import BeltRequirementsPage from './BeltRequirementsPage'
import api from '../services/api'

jest.mock('../services/api', () => ({
  __esModule: true,
  default: { get: jest.fn(), post: jest.fn(), put: jest.fn(), delete: jest.fn() },
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
        <BeltRequirementsPage />
      </AuthProvider>
    </QueryClientProvider>
  )
}

// The form's <label>s aren't associated with their inputs (no `for`/`id`), so
// getByLabelText can't find them -- query by container structure instead,
// matching the existing convention for this page (see LoginPage.test.tsx).
async function openFormForBelt() {
  const user = userEvent.setup()
  const { container } = renderPage()

  await screen.findByText('Branca (Adulto)')
  const beltSelect = screen.getByRole('combobox')
  await user.selectOptions(beltSelect, 'belt-1')
  await user.click(await screen.findByRole('button', { name: /adicionar/i }))

  const quantityInput = container.querySelector<HTMLInputElement>('input[type="number"]')!
  const eventTypeSelect = screen.getAllByRole('combobox')[1]
  const submitButton = container.querySelector<HTMLButtonElement>('button[type="submit"]')!
  return { user, container, quantityInput, eventTypeSelect, submitButton }
}

describe('BeltRequirementsPage', () => {
  beforeEach(() => {
    mockedGet.mockReset()
    mockedPost.mockReset()
    mockedGet.mockImplementation((url: string) => {
      if (url === '/api/v1/belts') {
        return Promise.resolve({ data: [{ id: 'belt-1', name: 'Branca', category: 'adult' }] })
      }
      if (url === '/api/v1/events/types') {
        return Promise.resolve({
          data: [
            { id: 'type-1', name: 'Treino', counts_for_belt: true },
            { id: 'type-2', name: 'Evento Social', counts_for_belt: false },
          ],
        })
      }
      if (url === '/api/v1/belts/belt-1/requirements') {
        return Promise.resolve({ data: [] })
      }
      return Promise.resolve({ data: [] })
    })
  })

  it('allows clearing the quantity field and typing a new value', async () => {
    const { user, quantityInput } = await openFormForBelt()

    expect(quantityInput).toHaveValue(1)

    await user.clear(quantityInput)
    expect(quantityInput).toHaveValue(null)

    await user.type(quantityInput, '5')
    expect(quantityInput).toHaveValue(5)
  })

  it('does not submit while the quantity field is empty', async () => {
    const { user, quantityInput, eventTypeSelect, submitButton } = await openFormForBelt()

    await user.selectOptions(eventTypeSelect, 'type-1')
    await user.clear(quantityInput)
    await user.click(submitButton)

    expect(mockedPost).not.toHaveBeenCalled()
  })

  it('excludes event types that do not count for belt exams from the dropdown', async () => {
    const { eventTypeSelect } = await openFormForBelt()

    const optionLabels = within(eventTypeSelect)
      .getAllByRole('option')
      .map((option) => option.textContent)

    expect(optionLabels).toEqual(['Selecione...', 'Treino'])
  })

  it('shows only the placeholder when no event type counts for belt exams', async () => {
    mockedGet.mockImplementation((url: string) => {
      if (url === '/api/v1/belts') {
        return Promise.resolve({ data: [{ id: 'belt-1', name: 'Branca', category: 'adult' }] })
      }
      if (url === '/api/v1/events/types') {
        return Promise.resolve({
          data: [{ id: 'type-2', name: 'Evento Social', counts_for_belt: false }],
        })
      }
      return Promise.resolve({ data: [] })
    })

    const { eventTypeSelect } = await openFormForBelt()

    const optionLabels = within(eventTypeSelect)
      .getAllByRole('option')
      .map((option) => option.textContent)

    expect(optionLabels).toEqual(['Selecione...'])
  })

  it('creates a requirement with the typed quantity', async () => {
    mockedPost.mockResolvedValue({ data: {} })
    const { user, quantityInput, eventTypeSelect, submitButton } = await openFormForBelt()

    await user.selectOptions(eventTypeSelect, 'type-1')
    await user.clear(quantityInput)
    await user.type(quantityInput, '5')

    await user.click(submitButton)

    await waitFor(() =>
      expect(mockedPost).toHaveBeenCalledWith('/api/v1/belts/belt-1/requirements', {
        event_type_id: 'type-1',
        required_count: 5,
        description: '',
        belt_id: 'belt-1',
      })
    )
  })

  it('shows the event type name in the "Tipo" column for an existing requirement', async () => {
    mockedGet.mockImplementation((url: string) => {
      if (url === '/api/v1/belts') {
        return Promise.resolve({ data: [{ id: 'belt-1', name: 'Branca', category: 'adult' }] })
      }
      if (url === '/api/v1/events/types') {
        return Promise.resolve({ data: [{ id: 'type-1', name: 'Treino', counts_for_belt: true }] })
      }
      if (url === '/api/v1/belts/belt-1/requirements') {
        return Promise.resolve({
          data: [
            {
              id: 'req-1',
              event_type: { name: 'Treino' },
              description: 'Treinos',
              required_count: 30,
            },
          ],
        })
      }
      return Promise.resolve({ data: [] })
    })

    const user = userEvent.setup()
    renderPage()

    await screen.findByText('Branca (Adulto)')
    await user.selectOptions(screen.getByRole('combobox'), 'belt-1')

    const row = (await screen.findByText('Treinos')).closest('tr')!
    expect(within(row).getByText('Treino')).toBeInTheDocument()
  })

  it('shows the event type name for a requirement right after creating it', async () => {
    mockedGet.mockImplementation((url: string) => {
      if (url === '/api/v1/belts') {
        return Promise.resolve({ data: [{ id: 'belt-1', name: 'Branca', category: 'adult' }] })
      }
      if (url === '/api/v1/events/types') {
        return Promise.resolve({ data: [{ id: 'type-1', name: 'Treino', counts_for_belt: true }] })
      }
      if (url === '/api/v1/belts/belt-1/requirements') {
        return Promise.resolve({
          data: mockedPost.mock.calls.length > 0
            ? [
                {
                  id: 'req-1',
                  event_type: { name: 'Treino' },
                  description: 'Treinos',
                  required_count: 5,
                },
              ]
            : [],
        })
      }
      return Promise.resolve({ data: [] })
    })
    mockedPost.mockResolvedValue({ data: {} })

    const { user, quantityInput, eventTypeSelect, submitButton } = await openFormForBelt()
    await user.selectOptions(eventTypeSelect, 'type-1')
    await user.clear(quantityInput)
    await user.type(quantityInput, '5')
    await user.click(submitButton)

    const row = (await screen.findByText('Treinos')).closest('tr')!
    expect(within(row).getByText('Treino')).toBeInTheDocument()
  })
})
