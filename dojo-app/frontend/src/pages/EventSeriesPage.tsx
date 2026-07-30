import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Edit, QrCode, RefreshCw, Ban } from 'lucide-react'
import api from '../services/api'
import { showToast } from '../components/Toast'

// Index i (0-6) is both the display order and the exact integer sent to the
// API -- matches Python's date.weekday() convention (Monday=0). This
// component never calls JS's Date.getDay() (Sunday=0) anywhere, sidestepping
// the frontend/backend weekday-numbering mismatch entirely rather than
// requiring a runtime conversion.
const WEEKDAY_LABELS = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']

interface EventType {
  id: string
  name: string
  color?: string
}

interface Belt {
  id: string
  name: string
  category: string
}

interface Dojo {
  id: string
  name: string
}

interface EventSeries {
  id: string
  title: string
  event_type_id: string
  description?: string | null
  dojo_id?: string | null
  minimum_belt_id?: string | null
  days_of_week: number[]
  start_time: string
  duration_minutes?: number | null
  series_start_date: string
  series_end_date?: string | null
  is_active: boolean
  check_in_token: string
}

interface GenerateOccurrencesResponse {
  created_count: number
  skipped_count: number
}

interface EventSeriesFormData {
  title: string
  event_type_id: string
  description: string
  dojo_id: string
  minimum_belt_id: string
  days_of_week: number[]
  start_time: string
  duration_minutes: string
  no_duration: boolean
  series_start_date: string
  series_end_date: string
  no_end_date: boolean
  is_active: boolean
}

const emptyFormData: EventSeriesFormData = {
  title: '',
  event_type_id: '',
  description: '',
  dojo_id: '',
  minimum_belt_id: '',
  days_of_week: [],
  start_time: '07:00',
  duration_minutes: '',
  no_duration: true,
  series_start_date: '',
  series_end_date: '',
  no_end_date: true,
  is_active: true,
}

function buildPayload(formData: EventSeriesFormData) {
  return {
    title: formData.title,
    event_type_id: formData.event_type_id,
    description: formData.description || undefined,
    dojo_id: formData.dojo_id || undefined,
    minimum_belt_id: formData.minimum_belt_id || undefined,
    days_of_week: formData.days_of_week,
    start_time: `${formData.start_time}:00`,
    duration_minutes: formData.no_duration
      ? undefined
      : parseInt(formData.duration_minutes, 10) || undefined,
    series_start_date: formData.series_start_date || undefined,
    series_end_date: formData.no_end_date ? undefined : formData.series_end_date || undefined,
    is_active: formData.is_active,
  }
}

export default function EventSeriesPage() {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [editingSeries, setEditingSeries] = useState<EventSeries | null>(null)
  const [formData, setFormData] = useState<EventSeriesFormData>(emptyFormData)

  const { data: seriesList } = useQuery<EventSeries[]>({
    queryKey: ['event-series'],
    queryFn: async () => (await api.get('/api/v1/event-series')).data,
  })

  const { data: eventTypes } = useQuery<EventType[]>({
    queryKey: ['event-types'],
    queryFn: async () => (await api.get('/api/v1/events/types')).data,
  })

  const { data: belts } = useQuery<Belt[]>({
    queryKey: ['belts'],
    queryFn: async () => (await api.get('/api/v1/belts')).data,
  })

  const { data: dojos } = useQuery<Dojo[]>({
    queryKey: ['dojos'],
    queryFn: async () => (await api.get('/api/v1/dojos')).data,
  })

  const resetForm = () => setFormData(emptyFormData)

  const createMutation = useMutation({
    mutationFn: (data: ReturnType<typeof buildPayload>) => api.post('/api/v1/event-series', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['event-series'] })
      setShowForm(false)
      resetForm()
    },
    onError: (error: Error) => {
      alert(error.message)
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: ReturnType<typeof buildPayload> }) =>
      api.put(`/api/v1/event-series/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['event-series'] })
      setShowForm(false)
      setEditingSeries(null)
      resetForm()
    },
    onError: (error: Error) => {
      alert(error.message)
    },
  })

  const generateMutation = useMutation({
    mutationFn: (id: string) =>
      api.post<GenerateOccurrencesResponse>(`/api/v1/event-series/${id}/generate`),
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ['event-series'] })
      const { created_count, skipped_count } = response.data
      showToast(
        `Ocorrências geradas: ${created_count} criadas, ${skipped_count} já existiam.`,
        'success'
      )
    },
    onError: (error: Error) => {
      alert(error.message)
    },
  })

  const deactivateMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/api/v1/event-series/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['event-series'] })
    },
    onError: (error: Error) => {
      alert(error.message)
    },
  })

  const toggleDay = (day: number) => {
    setFormData((prev) => ({
      ...prev,
      days_of_week: prev.days_of_week.includes(day)
        ? prev.days_of_week.filter((d) => d !== day)
        : [...prev.days_of_week, day].sort((a, b) => a - b),
    }))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (formData.days_of_week.length === 0) {
      alert('Selecione ao menos um dia da semana.')
      return
    }
    const payload = buildPayload(formData)
    if (editingSeries) {
      updateMutation.mutate({ id: editingSeries.id, data: payload })
    } else {
      createMutation.mutate(payload)
    }
  }

  const handleEdit = (series: EventSeries) => {
    setEditingSeries(series)
    setFormData({
      title: series.title,
      event_type_id: series.event_type_id,
      description: series.description || '',
      dojo_id: series.dojo_id || '',
      minimum_belt_id: series.minimum_belt_id || '',
      days_of_week: series.days_of_week,
      start_time: series.start_time.slice(0, 5),
      duration_minutes: series.duration_minutes ? String(series.duration_minutes) : '',
      no_duration: !series.duration_minutes,
      series_start_date: series.series_start_date,
      series_end_date: series.series_end_date || '',
      no_end_date: !series.series_end_date,
      is_active: series.is_active,
    })
    setShowForm(true)
  }

  const formatDaysOfWeek = (days: number[]) =>
    [...days]
      .sort((a, b) => a - b)
      .map((d) => WEEKDAY_LABELS[d])
      .join(', ')

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Aulas Recorrentes</h2>
        <button
          onClick={() => {
            setEditingSeries(null)
            resetForm()
            setShowForm(true)
          }}
          className="flex items-center bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          <Plus className="w-4 h-4 mr-2" />
          Nova Série
        </button>
      </div>

      {showForm && (
        <div className="bg-white p-6 rounded-lg shadow mb-6">
          <h3 className="text-lg font-semibold mb-4">
            {editingSeries ? 'Editar Série' : 'Nova Série'}
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
                {eventTypes?.map((type) => (
                  <option key={type.id} value={type.id}>
                    {type.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Dojo</label>
              <select
                value={formData.dojo_id}
                onChange={(e) => setFormData({ ...formData, dojo_id: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
              >
                <option value="">Sem dojo definido</option>
                {dojos?.map((dojo) => (
                  <option key={dojo.id} value={dojo.id}>
                    {dojo.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Faixa mínima (opcional)
              </label>
              <select
                value={formData.minimum_belt_id}
                onChange={(e) => setFormData({ ...formData, minimum_belt_id: e.target.value })}
                className="w-full max-w-md px-3 py-2 border rounded-md"
              >
                <option value="">Sem restrição</option>
                {belts?.map((belt) => (
                  <option key={belt.id} value={belt.id}>
                    {belt.name} ({belt.category === 'child' ? 'Criança' : 'Adulto'})
                  </option>
                ))}
              </select>
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-2">Dias da semana</label>
              <div className="flex flex-wrap gap-3">
                {WEEKDAY_LABELS.map((label, day) => (
                  <label key={day} className="flex items-center gap-1 text-sm text-gray-700">
                    <input
                      type="checkbox"
                      checked={formData.days_of_week.includes(day)}
                      onChange={() => toggleDay(day)}
                    />
                    {label}
                  </label>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Horário</label>
              <input
                type="time"
                value={formData.start_time}
                onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Duração (minutos)
              </label>
              <input
                type="number"
                min={1}
                value={formData.duration_minutes}
                disabled={formData.no_duration}
                onChange={(e) => setFormData({ ...formData, duration_minutes: e.target.value })}
                className="w-full px-3 py-2 border rounded-md disabled:bg-gray-100"
              />
              <label className="mt-1 flex items-center gap-1 text-xs text-gray-600">
                <input
                  type="checkbox"
                  checked={formData.no_duration}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      no_duration: e.target.checked,
                      duration_minutes: '',
                    })
                  }
                />
                Sem hora de término
              </label>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Data de início da série
              </label>
              <input
                type="date"
                value={formData.series_start_date}
                onChange={(e) => setFormData({ ...formData, series_start_date: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Data de término da série
              </label>
              <input
                type="date"
                value={formData.series_end_date}
                disabled={formData.no_end_date}
                onChange={(e) => setFormData({ ...formData, series_end_date: e.target.value })}
                className="w-full px-3 py-2 border rounded-md disabled:bg-gray-100"
              />
              <label className="mt-1 flex items-center gap-1 text-xs text-gray-600">
                <input
                  type="checkbox"
                  checked={formData.no_end_date}
                  onChange={(e) =>
                    setFormData({ ...formData, no_end_date: e.target.checked, series_end_date: '' })
                  }
                />
                Sem data de término / até cancelar
              </label>
            </div>
            <div className="col-span-2">
              <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                <input
                  type="checkbox"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                />
                Série ativa
              </label>
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
                  : editingSeries
                    ? 'Atualizar'
                    : 'Criar'}
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Título
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Dias
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Horário
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Ações
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {seriesList?.map((series) => (
              <tr key={series.id}>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {series.title}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {formatDaysOfWeek(series.days_of_week)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {series.start_time.slice(0, 5)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={`inline-flex px-2 text-xs leading-5 font-semibold rounded-full ${
                      series.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    }`}
                  >
                    {series.is_active ? 'Ativa' : 'Encerrada'}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <button
                    onClick={() => handleEdit(series)}
                    className="text-blue-600 hover:text-blue-900 mr-3"
                    title="Editar série"
                  >
                    <Edit className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => generateMutation.mutate(series.id)}
                    className="text-purple-600 hover:text-purple-900 mr-3"
                    title="Gerar ocorrências"
                    disabled={generateMutation.isPending}
                  >
                    <RefreshCw className="w-4 h-4" />
                  </button>
                  <a
                    href={`/checkin?token=${series.check_in_token}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-green-600 hover:text-green-900 mr-3"
                    title="Link de Check-in"
                  >
                    <QrCode className="w-4 h-4" />
                  </a>
                  <button
                    onClick={() => deactivateMutation.mutate(series.id)}
                    className="text-red-600 hover:text-red-900"
                    title="Encerrar série"
                    disabled={!series.is_active}
                  >
                    <Ban className="w-4 h-4" />
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
