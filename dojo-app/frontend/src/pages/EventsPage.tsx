import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Edit, Trash2, QrCode, Users, X } from 'lucide-react'
import api from '../services/api'

interface EventType {
  id: string
  name: string
  color: string
}

interface Event {
  id: string
  title: string
  event_type_id: string
  event_type: { name: string; color: string }
  start_datetime: string
  end_datetime?: string
  description?: string
  location?: string
  status: string
  check_in_token: string
}

interface PreCheckInCount {
  confirmed_count?: number
  count?: number
}

interface PreCheckInStudent {
  id?: string
  student_id?: string
  name?: string
  student_name?: string
  registration_number: string
  confirmed_at?: string
}

function PreCheckInCountBadge({ eventId }: { eventId: string }) {
  const { data, isLoading } = useQuery<PreCheckInCount>({
    queryKey: ['events', eventId, 'precheckins', 'count'],
    queryFn: async () => (await api.get(`/api/v1/pre-checkins/events/${eventId}/count`)).data,
    staleTime: 30_000,
  })

  const count = data?.confirmed_count ?? data?.count ?? 0

  return (
    <span className="inline-flex min-w-8 items-center justify-center rounded-full bg-cyan-100 px-2 py-1 text-xs font-semibold text-cyan-800">
      {isLoading ? '…' : count}
    </span>
  )
}

function PreCheckInRosterPanel({ event, onClose }: { event: Event; onClose: () => void }) {
  const {
    data: students = [],
    isLoading,
    isError,
  } = useQuery<PreCheckInStudent[]>({
    queryKey: ['events', event.id, 'precheckins', 'roster'],
    queryFn: async () => (await api.get(`/api/v1/pre-checkins/events/${event.id}`)).data,
  })

  return (
    <div className="mb-6 rounded-lg border border-cyan-100 bg-cyan-50 p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-bold tracking-wide text-cyan-800 uppercase">Pré-check-in</p>
          <h3 className="mt-1 text-lg font-semibold text-slate-800">Confirmados — {event.title}</h3>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded p-1 text-slate-500 hover:bg-cyan-100 hover:text-slate-800"
          aria-label="Fechar lista de confirmados"
        >
          <X className="h-5 w-5" />
        </button>
      </div>
      {isLoading ? (
        <p className="mt-4 text-sm text-slate-600">Carregando confirmados...</p>
      ) : isError ? (
        <p className="mt-4 text-sm text-rose-700">
          Não foi possível carregar a lista de confirmados.
        </p>
      ) : students.length === 0 ? (
        <p className="mt-4 text-sm text-slate-600">Ainda não há pré-check-ins confirmados.</p>
      ) : (
        <ul className="mt-4 divide-y divide-cyan-100 rounded-md bg-white">
          {students.map((student) => (
            <li
              key={student.id ?? student.student_id ?? student.registration_number}
              className="flex items-center justify-between gap-4 px-4 py-3 text-sm"
            >
              <span className="font-medium text-slate-800">
                {student.name ?? student.student_name}
              </span>
              <span className="font-mono text-xs text-slate-500">
                {student.registration_number}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default function EventsPage() {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [editingEvent, setEditingEvent] = useState<Event | null>(null)
  const [rosterEvent, setRosterEvent] = useState<Event | null>(null)
  const [formData, setFormData] = useState({
    title: '',
    event_type_id: '',
    start_datetime: '',
    end_datetime: '',
    description: '',
    location: '',
  })

  const { data: events } = useQuery<Event[]>({
    queryKey: ['events'],
    queryFn: async () => {
      const response = await api.get('/api/v1/events')
      return response.data
    },
  })

  const { data: eventTypes } = useQuery({
    queryKey: ['event-types'],
    queryFn: async () => {
      const response = await api.get('/api/v1/events/types')
      return response.data
    },
  })

  const createMutation = useMutation({
    mutationFn: (data: typeof formData) => api.post('/api/v1/events', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['events'] })
      setShowForm(false)
      resetForm()
    },
    onError: (error: Error) => {
      alert(error.message)
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<typeof formData> }) =>
      api.put(`/api/v1/events/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['events'] })
      setShowForm(false)
      setEditingEvent(null)
      resetForm()
    },
    onError: (error: Error) => {
      alert(error.message)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/api/v1/events/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['events'] })
    },
    onError: (error: Error) => {
      alert(error.message)
    },
  })

  const resetForm = () => {
    setFormData({
      title: '',
      event_type_id: '',
      start_datetime: '',
      end_datetime: '',
      description: '',
      location: '',
    })
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (editingEvent) {
      updateMutation.mutate({ id: editingEvent.id, data: formData })
    } else {
      createMutation.mutate(formData)
    }
  }

  const handleEdit = (event: Event) => {
    setEditingEvent(event)
    setFormData({
      title: event.title,
      event_type_id: event.event_type_id,
      start_datetime: event.start_datetime.slice(0, 16),
      end_datetime: event.end_datetime ? event.end_datetime.slice(0, 16) : '',
      description: event.description || '',
      location: event.location || '',
    })
    setShowForm(true)
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('pt-BR')
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'scheduled':
        return 'bg-blue-100 text-blue-800'
      case 'in_progress':
        return 'bg-yellow-100 text-yellow-800'
      case 'finished':
        return 'bg-green-100 text-green-800'
      case 'cancelled':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Eventos</h2>
        <button
          onClick={() => {
            setEditingEvent(null)
            resetForm()
            setShowForm(true)
          }}
          className="flex items-center bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          <Plus className="w-4 h-4 mr-2" />
          Novo Evento
        </button>
      </div>

      {showForm && (
        <div className="bg-white p-6 rounded-lg shadow mb-6">
          <h3 className="text-lg font-semibold mb-4">
            {editingEvent ? 'Editar Evento' : 'Novo Evento'}
          </h3>
          <form onSubmit={handleSubmit} className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Título</label>
              <input
                type="text"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tipo</label>
              <select
                value={formData.event_type_id}
                onChange={(e) => setFormData({ ...formData, event_type_id: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
                required
              >
                <option value="">Selecione...</option>
                {eventTypes?.map((type: EventType) => (
                  <option key={type.id} value={type.id}>
                    {type.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Local</label>
              <input
                type="text"
                value={formData.location}
                onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Início</label>
              <input
                type="datetime-local"
                value={formData.start_datetime}
                onChange={(e) => setFormData({ ...formData, start_datetime: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Fim</label>
              <input
                type="datetime-local"
                value={formData.end_datetime}
                onChange={(e) => setFormData({ ...formData, end_datetime: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
              />
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Descrição</label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
                rows={3}
              />
            </div>
            <div className="col-span-2 flex justify-end space-x-2">
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={createMutation.isPending || updateMutation.isPending}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {createMutation.isPending || updateMutation.isPending
                  ? 'Salvando...'
                  : editingEvent
                    ? 'Atualizar'
                    : 'Criar'}
              </button>
            </div>
          </form>
        </div>
      )}

      {rosterEvent && (
        <PreCheckInRosterPanel event={rosterEvent} onClose={() => setRosterEvent(null)} />
      )}

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Título
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Tipo
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Data
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Status
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                Pré-check-ins
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Ações
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {events?.map((event) => (
              <tr key={event.id}>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{event.title}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  <span
                    className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium"
                    style={{
                      backgroundColor: event.event_type?.color + '20',
                      color: event.event_type?.color,
                    }}
                  >
                    {event.event_type?.name}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {formatDate(event.start_datetime)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={`inline-flex px-2 text-xs leading-5 font-semibold rounded-full ${getStatusColor(event.status)}`}
                  >
                    {event.status === 'scheduled'
                      ? 'Agendado'
                      : event.status === 'in_progress'
                        ? 'Em Andamento'
                        : event.status === 'finished'
                          ? 'Finalizado'
                          : event.status === 'cancelled'
                            ? 'Cancelado'
                            : event.status}
                  </span>
                </td>
                <td className="px-6 py-4 text-center">
                  <PreCheckInCountBadge eventId={event.id} />
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <button
                    onClick={() => handleEdit(event)}
                    className="text-blue-600 hover:text-blue-900 mr-3"
                  >
                    <Edit className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => deleteMutation.mutate(event.id)}
                    className="text-red-600 hover:text-red-900 mr-3"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                  <a
                    href={`/checkin?token=${event.check_in_token}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-green-600 hover:text-green-900"
                    title="Link de Check-in"
                  >
                    <QrCode className="w-4 h-4" />
                  </a>
                  <button
                    type="button"
                    onClick={() => setRosterEvent(event)}
                    className="ml-3 text-cyan-700 hover:text-cyan-900"
                    title="Ver pré-check-ins confirmados"
                    aria-label={`Ver pré-check-ins confirmados de ${event.title}`}
                  >
                    <Users className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
