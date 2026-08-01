import { useState } from 'react'
import { Bell, BellRing, CircleAlert, LoaderCircle, Search } from 'lucide-react'
import { publicApi } from '../services/api'

interface StudentCredentials {
  registration_number: string
  pin: string
}

interface NotificationItem {
  id: string
  notification_type: string
  message: string
  created_at: string
  read_at: string | null
}

const NOTIFICATION_TYPE_LABELS: Record<string, string> = {
  pre_checkin_reminder: 'Pré-check-in',
  medical_exam_expiring: 'Exame médico',
  mensalidade_due: 'Mensalidade',
}

type PushOptInState = 'idle' | 'requesting' | 'subscribed' | 'unavailable'

/**
 * Converts a URL-safe base64 VAPID public key into the Uint8Array shape
 * required by `PushManager.subscribe`'s `applicationServerKey` option.
 */
function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = window.atob(base64)
  const outputArray = new Uint8Array(rawData.length)
  for (let i = 0; i < rawData.length; i += 1) {
    outputArray[i] = rawData.charCodeAt(i)
  }
  return outputArray
}

function formatDate(isoDate: string): string {
  return new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(
    new Date(isoDate)
  )
}

const pushSupported = () => 'serviceWorker' in navigator && 'PushManager' in window

export default function NotificationHubPage() {
  const [registrationNumber, setRegistrationNumber] = useState('')
  const [pin, setPin] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [feedback, setFeedback] = useState<{ kind: 'error'; message: string } | null>(null)
  const [credentials, setCredentials] = useState<StudentCredentials | null>(null)
  const [notifications, setNotifications] = useState<NotificationItem[] | null>(null)
  const [pushState, setPushState] = useState<PushOptInState>('idle')
  const [pushMessage, setPushMessage] = useState<string | null>(null)

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setFeedback(null)
    setSubmitting(true)

    const nextCredentials: StudentCredentials = {
      registration_number: registrationNumber.trim(),
      pin,
    }

    try {
      const response = await publicApi.post<NotificationItem[]>(
        '/api/v1/notifications/history',
        nextCredentials
      )
      setCredentials(nextCredentials)
      setNotifications(response.data)
    } catch (error) {
      const detail = (error as { response?: { status?: number; data?: { detail?: string } } })
        ?.response?.data?.detail
      setFeedback({
        kind: 'error',
        message: detail || 'Matrícula ou PIN inválidos.',
      })
    } finally {
      setSubmitting(false)
    }
  }

  const handleMarkRead = async (notificationId: string) => {
    if (!credentials) return
    try {
      await publicApi.post(`/api/v1/notifications/${notificationId}/read`, credentials)
      setNotifications(
        (current) =>
          current?.map((notification) =>
            notification.id === notificationId
              ? { ...notification, read_at: notification.read_at ?? new Date().toISOString() }
              : notification
          ) ?? null
      )
    } catch {
      // Marking as read is a non-critical, best-effort action -- a transient
      // failure here should not disrupt the visible history.
    }
  }

  const handleActivatePush = async () => {
    if (!credentials) return
    setPushMessage(null)
    setPushState('requesting')

    try {
      const registration = await navigator.serviceWorker.register('/sw.js')
      const permission = await Notification.requestPermission()

      if (permission !== 'granted') {
        setPushState('unavailable')
        setPushMessage(
          'Notificações push indisponíveis neste dispositivo, mas você pode continuar acompanhando seu histórico aqui.'
        )
        return
      }

      const { data } = await publicApi.get<{ public_key: string }>(
        '/api/v1/notifications/vapid-public-key'
      )
      const applicationServerKey = urlBase64ToUint8Array(data.public_key)
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: applicationServerKey as BufferSource,
      })
      const subscriptionJson = subscription.toJSON()

      await publicApi.post('/api/v1/notifications/subscribe', {
        ...credentials,
        endpoint: subscriptionJson.endpoint,
        keys: subscriptionJson.keys,
      })

      setPushState('subscribed')
      setPushMessage('Notificações push ativadas com sucesso.')
    } catch {
      setPushState('unavailable')
      setPushMessage(
        'Notificações push indisponíveis neste dispositivo, mas você pode continuar acompanhando seu histórico aqui.'
      )
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 px-4 py-10 text-slate-100 sm:px-6">
      <section className="mx-auto max-w-xl overflow-hidden rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl shadow-black/30">
        <header className="border-b border-slate-700 bg-slate-900 px-6 py-8 sm:px-10">
          <p className="mb-2 text-xs font-bold tracking-[0.24em] text-cyan-300 uppercase">
            Dojo Admin
          </p>
          <h1 className="text-3xl font-bold tracking-tight text-white">Central de Notificações</h1>
          <p className="mt-3 text-sm leading-6 text-slate-300">
            Acompanhe seus lembretes de pré-check-in, exame médico e mensalidade, e ative
            notificações push para não perder nenhum aviso.
          </p>
        </header>

        <form onSubmit={handleSubmit} className="space-y-6 px-6 py-8 sm:px-10">
          {feedback && (
            <div
              role="status"
              className="flex gap-3 rounded-lg border border-rose-500/40 bg-rose-500/10 p-4 text-sm leading-5 text-rose-100"
            >
              <CircleAlert className="mt-0.5 h-5 w-5 shrink-0" />
              <span>{feedback.message}</span>
            </div>
          )}

          <div className="grid gap-5 sm:grid-cols-[1fr_9rem]">
            <div>
              <label
                htmlFor="registration"
                className="mb-2 block text-sm font-medium text-slate-200"
              >
                Matrícula
              </label>
              <input
                id="registration"
                value={registrationNumber}
                onChange={(event) => setRegistrationNumber(event.target.value)}
                className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-3 text-white outline-none transition focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/30"
                placeholder="Ex.: 2024001"
                autoComplete="username"
                required
              />
            </div>
            <div>
              <label htmlFor="pin" className="mb-2 block text-sm font-medium text-slate-200">
                PIN
              </label>
              <input
                id="pin"
                type="password"
                value={pin}
                onChange={(event) => setPin(event.target.value)}
                className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-3 text-white outline-none transition focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/30"
                inputMode="numeric"
                maxLength={4}
                autoComplete="current-password"
                required
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-cyan-400 px-4 py-3 font-bold text-slate-950 transition hover:bg-cyan-300 focus:outline-none focus:ring-2 focus:ring-cyan-200 focus:ring-offset-2 focus:ring-offset-slate-900 disabled:cursor-not-allowed disabled:bg-slate-600 disabled:text-slate-300"
          >
            {submitting ? (
              <LoaderCircle className="h-5 w-5 animate-spin" />
            ) : (
              <Search className="h-5 w-5" />
            )}
            {submitting ? 'Buscando...' : 'Ver minhas notificações'}
          </button>
        </form>

        {notifications !== null && (
          <div className="space-y-6 border-t border-slate-700 px-6 py-8 sm:px-10">
            {pushSupported() && (
              <div className="rounded-lg border border-slate-700 bg-slate-800/60 p-4">
                <button
                  type="button"
                  onClick={handleActivatePush}
                  disabled={pushState === 'requesting' || pushState === 'subscribed'}
                  className="flex w-full items-center justify-center gap-2 rounded-lg bg-slate-700 px-4 py-3 font-semibold text-white transition hover:bg-slate-600 disabled:cursor-not-allowed disabled:opacity-70"
                >
                  {pushState === 'requesting' ? (
                    <LoaderCircle className="h-5 w-5 animate-spin" />
                  ) : (
                    <BellRing className="h-5 w-5" />
                  )}
                  {pushState === 'subscribed' ? 'Notificações ativadas' : 'Ativar notificações'}
                </button>
                {pushMessage && <p className="mt-3 text-sm text-slate-300">{pushMessage}</p>}
              </div>
            )}

            <div>
              <h2 className="mb-4 text-lg font-semibold text-white">Histórico</h2>
              {notifications.length === 0 ? (
                <p className="text-sm text-slate-400">Nenhuma notificação encontrada.</p>
              ) : (
                <ul className="space-y-3">
                  {notifications.map((notification) => {
                    const isUnread = notification.read_at === null
                    return (
                      <li key={notification.id}>
                        <button
                          type="button"
                          onClick={() => isUnread && handleMarkRead(notification.id)}
                          className="w-full rounded-lg border border-slate-700 bg-slate-800/60 p-4 text-left transition hover:border-cyan-400/50"
                        >
                          <div className="flex items-center justify-between gap-3">
                            <span className="text-xs font-bold tracking-wide text-cyan-300 uppercase">
                              {NOTIFICATION_TYPE_LABELS[notification.notification_type] ??
                                notification.notification_type}
                            </span>
                            <span
                              className={`flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold ${
                                isUnread
                                  ? 'bg-cyan-400/20 text-cyan-200'
                                  : 'bg-slate-700 text-slate-300'
                              }`}
                            >
                              <Bell className="h-3 w-3" />
                              {isUnread ? 'Não lida' : 'Lida'}
                            </span>
                          </div>
                          <p className="mt-2 text-sm leading-5 text-slate-200">
                            {notification.message}
                          </p>
                          <p className="mt-2 text-xs text-slate-400">
                            {formatDate(notification.created_at)}
                          </p>
                        </button>
                      </li>
                    )
                  })}
                </ul>
              )}
            </div>
          </div>
        )}
      </section>
    </main>
  )
}
