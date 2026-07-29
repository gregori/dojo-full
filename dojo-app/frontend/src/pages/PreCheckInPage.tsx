import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { CheckCircle2, CircleAlert, LoaderCircle, LogOut } from 'lucide-react'
import { publicApi } from '../services/api'

interface PreCheckInResponse {
  message?: string
}

interface PublicEvent {
  id: string
  title: string
  start_datetime: string
  location?: string | null
}

type Action = 'confirm' | 'cancel'

export default function PreCheckInPage() {
  const [searchParams] = useSearchParams()
  const [eventId, setEventId] = useState(() => searchParams.get('event_id') ?? '')
  const [registrationNumber, setRegistrationNumber] = useState('')
  const [pin, setPin] = useState('')
  const [events, setEvents] = useState<PublicEvent[]>([])
  const [loadingEvents, setLoadingEvents] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [action, setAction] = useState<Action>('confirm')
  const [feedback, setFeedback] = useState<{ kind: 'success' | 'error'; message: string } | null>(
    null
  )

  useEffect(() => {
    const loadEvents = async () => {
      try {
        const response = await publicApi.get<PublicEvent[]>('/api/v1/pre-checkins/events')
        setEvents(response.data)
      } catch {
        setFeedback({
          kind: 'error',
          message: 'Não foi possível carregar os eventos disponíveis. Tente novamente mais tarde.',
        })
      } finally {
        setLoadingEvents(false)
      }
    }

    void loadEvents()
  }, [])

  const selectedEvent = events.find((event) => event.id === eventId)

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setFeedback(null)
    setSubmitting(true)

    try {
      const response = await publicApi.post<PreCheckInResponse>(`/api/v1/pre-checkins/${action}`, {
        event_id: eventId,
        registration_number: registrationNumber.trim(),
        pin,
      })
      setFeedback({
        kind: 'success',
        message:
          response.data.message ||
          (action === 'confirm'
            ? 'Pré-check-in confirmado. Lembre-se de fazer o check-in presencial no evento.'
            : 'Pré-check-in cancelado.'),
      })
      setPin('')
    } catch {
      setFeedback({
        kind: 'error',
        message:
          'Não foi possível concluir esta solicitação. Confira os dados e se o prazo do evento ainda está aberto.',
      })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 px-4 py-10 text-slate-100 sm:px-6">
      <section className="mx-auto max-w-xl overflow-hidden rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl shadow-black/30">
        <header className="border-b border-slate-700 bg-slate-900 px-6 py-8 sm:px-10">
          <p className="mb-2 text-xs font-bold tracking-[0.24em] text-cyan-300 uppercase">
            Dojo Admin
          </p>
          <h1 className="text-3xl font-bold tracking-tight text-white">Pré-check-in</h1>
          <p className="mt-3 text-sm leading-6 text-slate-300">
            Confirme sua intenção de participar. A presença oficial continua sendo registrada no
            check-in presencial.
          </p>
        </header>

        <form onSubmit={handleSubmit} className="space-y-6 px-6 py-8 sm:px-10">
          {feedback && (
            <div
              role="status"
              className={`flex gap-3 rounded-lg border p-4 text-sm leading-5 ${
                feedback.kind === 'success'
                  ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-100'
                  : 'border-rose-500/40 bg-rose-500/10 text-rose-100'
              }`}
            >
              {feedback.kind === 'success' ? (
                <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0" />
              ) : (
                <CircleAlert className="mt-0.5 h-5 w-5 shrink-0" />
              )}
              <span>{feedback.message}</span>
            </div>
          )}

          <div>
            <label htmlFor="event" className="mb-2 block text-sm font-medium text-slate-200">
              Evento
            </label>
            <select
              id="event"
              value={eventId}
              onChange={(event) => setEventId(event.target.value)}
              disabled={loadingEvents || events.length === 0}
              className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-3 text-white outline-none transition focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/30 disabled:cursor-not-allowed disabled:opacity-60"
              required
            >
              <option value="">
                {loadingEvents ? 'Carregando eventos...' : 'Selecione um evento'}
              </option>
              {events.map((event) => (
                <option key={event.id} value={event.id}>
                  {event.title}
                </option>
              ))}
            </select>
            {selectedEvent && (
              <p className="mt-2 text-xs text-slate-400">
                {new Intl.DateTimeFormat('pt-BR', { dateStyle: 'full', timeStyle: 'short' }).format(
                  new Date(selectedEvent.start_datetime)
                )}
                {selectedEvent.location ? ` · ${selectedEvent.location}` : ''}
              </p>
            )}
          </div>

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

          <div
            className="rounded-lg bg-slate-800/70 p-1"
            role="group"
            aria-label="Ação de pré-check-in"
          >
            <button
              type="button"
              onClick={() => setAction('confirm')}
              className={`w-1/2 rounded-md px-3 py-2 text-sm font-semibold transition ${
                action === 'confirm'
                  ? 'bg-cyan-400 text-slate-950'
                  : 'text-slate-300 hover:text-white'
              }`}
            >
              Confirmar
            </button>
            <button
              type="button"
              onClick={() => setAction('cancel')}
              className={`w-1/2 rounded-md px-3 py-2 text-sm font-semibold transition ${
                action === 'cancel' ? 'bg-slate-600 text-white' : 'text-slate-300 hover:text-white'
              }`}
            >
              Cancelar
            </button>
          </div>

          <button
            type="submit"
            disabled={submitting || loadingEvents || events.length === 0}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-cyan-400 px-4 py-3 font-bold text-slate-950 transition hover:bg-cyan-300 focus:outline-none focus:ring-2 focus:ring-cyan-200 focus:ring-offset-2 focus:ring-offset-slate-900 disabled:cursor-not-allowed disabled:bg-slate-600 disabled:text-slate-300"
          >
            {submitting ? (
              <LoaderCircle className="h-5 w-5 animate-spin" />
            ) : (
              <LogOut className="h-5 w-5" />
            )}
            {submitting
              ? 'Processando...'
              : action === 'confirm'
                ? 'Confirmar pré-check-in'
                : 'Cancelar pré-check-in'}
          </button>
        </form>
      </section>
    </main>
  )
}
