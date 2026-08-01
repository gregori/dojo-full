import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import NotificationHubPage from './NotificationHubPage'
import { publicApi } from '../services/api'

jest.mock('../services/api', () => ({
  publicApi: { post: jest.fn(), get: jest.fn() },
}))

const mockedPost = publicApi.post as jest.Mock
const mockedGet = publicApi.get as jest.Mock

const VAPID_PUBLIC_KEY =
  'BEl62iUYgUivxIkv69yViEuiBIa40HI6DLOBw4OhV6gwZ7qOTpS6DAvQyF6nfjcyxeAY_1H_7VtQxTKKS9J-N0'

async function fillCredentialsAndSubmit(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText('Matrícula'), '123456')
  await user.type(screen.getByLabelText('PIN'), '1234')
  await user.click(screen.getByRole('button', { name: /Ver minhas notificações/i }))
}

/** Mocks the browser APIs the push opt-in flow depends on (absent by default in jsdom). */
function mockPushSupport() {
  const subscribeMock = jest.fn().mockResolvedValue({
    toJSON: () => ({
      endpoint: 'https://push.example/abc',
      keys: { p256dh: 'p256dh-key', auth: 'auth-key' },
    }),
  })
  const registerMock = jest.fn().mockResolvedValue({ pushManager: { subscribe: subscribeMock } })

  Object.defineProperty(navigator, 'serviceWorker', {
    value: { register: registerMock },
    configurable: true,
  })
  Object.defineProperty(window, 'PushManager', {
    value: function PushManager() {},
    configurable: true,
  })
  Object.defineProperty(window, 'Notification', {
    value: { requestPermission: jest.fn().mockResolvedValue('granted') },
    configurable: true,
  })

  return { registerMock, subscribeMock }
}

function clearPushSupport() {
  Reflect.deleteProperty(navigator, 'serviceWorker')
  Reflect.deleteProperty(window, 'PushManager')
  Reflect.deleteProperty(window, 'Notification')
}

describe('NotificationHubPage', () => {
  beforeEach(() => {
    mockedPost.mockReset()
    mockedGet.mockReset()
  })

  afterEach(() => {
    clearPushSupport()
  })

  it('renders the notification history for valid credentials', async () => {
    mockedPost.mockResolvedValueOnce({
      data: [
        {
          id: 'n1',
          notification_type: 'pre_checkin_reminder',
          message: 'Falta pouco! Faça seu pré-check-in para "Aula de Aikido".',
          created_at: '2026-07-30T10:00:00Z',
          read_at: null,
        },
      ],
    })
    const user = userEvent.setup()
    render(<NotificationHubPage />)

    await fillCredentialsAndSubmit(user)

    expect(await screen.findByText(/Falta pouco/i)).toBeInTheDocument()
    expect(screen.getByText('Não lida')).toBeInTheDocument()
    expect(mockedPost).toHaveBeenCalledWith('/api/v1/notifications/history', {
      registration_number: '123456',
      pin: '1234',
    })
  })

  it('shows the 401 error message for invalid credentials', async () => {
    mockedPost.mockRejectedValueOnce({
      response: { status: 401, data: { detail: 'Matrícula ou PIN inválidos.' } },
    })
    const user = userEvent.setup()
    render(<NotificationHubPage />)

    await fillCredentialsAndSubmit(user)

    expect(await screen.findByText('Matrícula ou PIN inválidos.')).toBeInTheDocument()
    expect(screen.queryByText(/Nenhuma notificação/i)).not.toBeInTheDocument()
  })

  it('marks an unread notification as read on click and updates its badge', async () => {
    mockedPost.mockResolvedValueOnce({
      data: [
        {
          id: 'n1',
          notification_type: 'medical_exam_expiring',
          message: 'Seu exame médico vence em 30/08/2026.',
          created_at: '2026-07-30T10:00:00Z',
          read_at: null,
        },
      ],
    })
    mockedPost.mockResolvedValueOnce({
      data: {
        id: 'n1',
        notification_type: 'medical_exam_expiring',
        message: 'Seu exame médico vence em 30/08/2026.',
        created_at: '2026-07-30T10:00:00Z',
        read_at: '2026-07-30T11:00:00Z',
      },
    })
    const user = userEvent.setup()
    render(<NotificationHubPage />)

    await fillCredentialsAndSubmit(user)
    await screen.findByText('Não lida')

    await user.click(screen.getByText(/Seu exame médico vence/i))

    await waitFor(() =>
      expect(mockedPost).toHaveBeenCalledWith('/api/v1/notifications/n1/read', {
        registration_number: '123456',
        pin: '1234',
      })
    )
    expect(await screen.findByText('Lida')).toBeInTheDocument()
    expect(screen.queryByText('Não lida')).not.toBeInTheDocument()
  })

  it('does not render the push opt-in button when serviceWorker/PushManager are unsupported', async () => {
    mockedPost.mockResolvedValueOnce({ data: [] })
    const user = userEvent.setup()
    render(<NotificationHubPage />)

    await fillCredentialsAndSubmit(user)

    await screen.findByText(/Nenhuma notificação/i)
    expect(screen.queryByRole('button', { name: /Ativar notificações/i })).not.toBeInTheDocument()
  })

  it('posts the expected subscribe payload shape when the push opt-in flow succeeds', async () => {
    const { registerMock, subscribeMock } = mockPushSupport()
    mockedPost.mockResolvedValueOnce({ data: [] }) // history
    mockedGet.mockResolvedValueOnce({ data: { public_key: VAPID_PUBLIC_KEY } })
    mockedPost.mockResolvedValueOnce({ data: { status: 'subscribed' } }) // subscribe

    const user = userEvent.setup()
    render(<NotificationHubPage />)

    await fillCredentialsAndSubmit(user)
    await screen.findByRole('button', { name: /Ativar notificações/i })

    await user.click(screen.getByRole('button', { name: /Ativar notificações/i }))

    await waitFor(() => expect(registerMock).toHaveBeenCalledWith('/sw.js'))
    await waitFor(() => expect(subscribeMock).toHaveBeenCalled())
    await waitFor(() =>
      expect(mockedPost).toHaveBeenCalledWith('/api/v1/notifications/subscribe', {
        registration_number: '123456',
        pin: '1234',
        endpoint: 'https://push.example/abc',
        keys: { p256dh: 'p256dh-key', auth: 'auth-key' },
      })
    )
  })
})
