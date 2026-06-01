import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Edit, Trash2 } from 'lucide-react'
import api from '../services/api'
import { useAuth } from '../hooks/useAuth'

interface EventType {
  id: string
  name: string
  color: string
  counts_for_belt: boolean
}

const DEFAULT_COLORS = [
  '#3B82F6',
  '#8B5CF6',
  '#10B981',
  '#F59E0B',
  '#EF4444',
  '#EC4899',
  '#06B6D4',
  '#84CC16',
  '#F97316',
  '#6366F1',
]

export default function EventTypesPage() {
  const { isAdmin } = useAuth()
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [editingType, setEditingType] = useState<EventType | null>(null)
  const [formData, setFormData] = useState({
    name: '',
    color: '#3B82F6',
    counts_for_belt: true,
  })

  const { data: eventTypes } = useQuery<EventType[]>({
    queryKey: ['event-types'],
    queryFn: async () => {
      const response = await api.get('/api/v1/events/types')
      return response.data
    },
  })

  const createMutation = useMutation({
    mutationFn: (data: typeof formData) => api.post('/api/v1/events/types', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['event-types'] })
      setShowForm(false)
      resetForm()
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<typeof formData> }) =>
      api.put(`/api/v1/events/types/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['event-types'] })
      setShowForm(false)
      setEditingType(null)
      resetForm()
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/api/v1/events/types/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['event-types'] })
    },
  })

  const resetForm = () => {
    setFormData({
      name: '',
      color: '#3B82F6',
      counts_for_belt: true,
    })
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (editingType) {
      updateMutation.mutate({ id: editingType.id, data: formData })
    } else {
      createMutation.mutate(formData)
    }
  }

  const handleEdit = (eventType: EventType) => {
    setEditingType(eventType)
    setFormData({
      name: eventType.name,
      color: eventType.color,
      counts_for_belt: eventType.counts_for_belt,
    })
    setShowForm(true)
  }

  if (!isAdmin) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Apenas administradores podem gerenciar tipos de evento.</p>
      </div>
    )
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Tipos de Evento</h2>
        <button
          onClick={() => {
            setEditingType(null)
            resetForm()
            setShowForm(true)
          }}
          className="flex items-center bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          <Plus className="w-4 h-4 mr-2" />
          Novo Tipo
        </button>
      </div>

      {showForm && (
        <div className="bg-white p-6 rounded-lg shadow mb-6">
          <h3 className="text-lg font-semibold mb-4">
            {editingType ? 'Editar Tipo de Evento' : 'Novo Tipo de Evento'}
          </h3>
          <form onSubmit={handleSubmit} className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Nome</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
                required
                placeholder="Ex: Aula Regular"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Cor</label>
              <div className="flex items-center space-x-2">
                <input
                  type="color"
                  value={formData.color}
                  onChange={(e) => setFormData({ ...formData, color: e.target.value })}
                  className="w-10 h-10 border rounded cursor-pointer"
                />
                <div className="flex space-x-1">
                  {DEFAULT_COLORS.map((c) => (
                    <button
                      key={c}
                      type="button"
                      onClick={() => setFormData({ ...formData, color: c })}
                      className={`w-6 h-6 rounded-full border-2 ${formData.color === c ? 'border-gray-800' : 'border-transparent'}`}
                      style={{ backgroundColor: c }}
                    />
                  ))}
                </div>
              </div>
            </div>
            <div className="flex items-center">
              <label className="flex items-center cursor-pointer mt-6">
                <input
                  type="checkbox"
                  checked={formData.counts_for_belt}
                  onChange={(e) => setFormData({ ...formData, counts_for_belt: e.target.checked })}
                  className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
                <span className="ml-2 text-sm text-gray-700">Conta para progresso de faixa</span>
              </label>
            </div>
            <div className="col-span-3 flex justify-end space-x-2">
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                {editingType ? 'Atualizar' : 'Criar'}
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Cor
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Nome
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Conta para Faixa
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Ações
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {eventTypes?.map((eventType) => (
              <tr key={eventType.id}>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div
                    className="w-6 h-6 rounded-full border border-gray-200"
                    style={{ backgroundColor: eventType.color }}
                  />
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {eventType.name}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  <span
                    className={`inline-flex px-2 text-xs leading-5 font-semibold rounded-full ${
                      eventType.counts_for_belt
                        ? 'bg-green-100 text-green-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {eventType.counts_for_belt ? 'Sim' : 'Não'}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <button
                    onClick={() => handleEdit(eventType)}
                    className="text-blue-600 hover:text-blue-900 mr-3"
                  >
                    <Edit className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => deleteMutation.mutate(eventType.id)}
                    className="text-red-600 hover:text-red-900"
                  >
                    <Trash2 className="w-4 h-4" />
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
