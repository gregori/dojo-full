import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2 } from 'lucide-react'
import api from '../services/api'
import { useAuth } from '../hooks/useAuth'

interface Belt {
  id: string
  name: string
  category: string
}

interface EventType {
  id: string
  name: string
  counts_for_belt: boolean
}

interface Requirement {
  id: string
  event_type?: { name: string }
  description: string
  required_count: number
}

export default function BeltRequirementsPage() {
  const { isAdmin } = useAuth()
  const queryClient = useQueryClient()
  const [selectedBelt, setSelectedBelt] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState({
    event_type_id: '',
    required_count: 1,
    description: '',
  })

  const { data: belts } = useQuery({
    queryKey: ['belts'],
    queryFn: async () => {
      const response = await api.get('/api/v1/belts')
      return response.data
    },
  })

  const { data: requirements } = useQuery({
    queryKey: ['requirements', selectedBelt],
    queryFn: async () => {
      if (!selectedBelt) return []
      const response = await api.get(`/api/v1/belts/${selectedBelt}/requirements`)
      return response.data
    },
    enabled: !!selectedBelt,
  })

  const { data: eventTypes } = useQuery({
    queryKey: ['event-types'],
    queryFn: async () => {
      const response = await api.get('/api/v1/events/types')
      return response.data
    },
  })

  const createMutation = useMutation({
    mutationFn: (data: typeof formData & { belt_id: string }) =>
      api.post(`/api/v1/belts/${selectedBelt}/requirements`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['requirements', selectedBelt] })
      setShowForm(false)
      setFormData({ event_type_id: '', required_count: 1, description: '' })
    },
    onError: (error: Error) => {
      alert(error.message)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/api/v1/belts/requirements/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['requirements', selectedBelt] })
    },
    onError: (error: Error) => {
      alert(error.message)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.required_count || formData.required_count < 1) return
    createMutation.mutate({ ...formData, belt_id: selectedBelt })
  }

  if (!isAdmin) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">
          Apenas administradores podem configurar requisitos de faixa.
        </p>
      </div>
    )
  }

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Requisitos de Faixa</h2>

      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">Selecione a Faixa</label>
        <select
          value={selectedBelt}
          onChange={(e) => setSelectedBelt(e.target.value)}
          className="w-full max-w-md px-3 py-2 border rounded-md"
        >
          <option value="">Selecione uma faixa...</option>
          {belts?.map((belt: Belt) => (
            <option key={belt.id} value={belt.id}>
              {belt.name} ({belt.category === 'child' ? 'Criança' : 'Adulto'})
            </option>
          ))}
        </select>
      </div>

      {selectedBelt && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold">Requisitos</h3>
            <button
              onClick={() => setShowForm(true)}
              className="flex items-center bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700"
            >
              <Plus className="w-4 h-4 mr-1" />
              Adicionar
            </button>
          </div>

          {showForm && (
            <form onSubmit={handleSubmit} className="mb-6 p-4 bg-gray-50 rounded-lg">
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Tipo de Evento
                  </label>
                  <select
                    value={formData.event_type_id}
                    onChange={(e) => setFormData({ ...formData, event_type_id: e.target.value })}
                    className="w-full px-3 py-2 border rounded-md"
                    required
                  >
                    <option value="">Selecione...</option>
                    {eventTypes
                      ?.filter((type: EventType) => type.counts_for_belt)
                      .map((type: EventType) => (
                        <option key={type.id} value={type.id}>
                          {type.name}
                        </option>
                      ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Quantidade</label>
                  <input
                    type="number"
                    min={1}
                    value={formData.required_count === 0 ? '' : formData.required_count}
                    onChange={(e) => {
                      const raw = e.target.value
                      setFormData({
                        ...formData,
                        required_count: raw === '' ? 0 : parseInt(raw, 10),
                      })
                    }}
                    className="w-full px-3 py-2 border rounded-md"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Descrição</label>
                  <input
                    type="text"
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    className="w-full px-3 py-2 border rounded-md"
                    placeholder="Ex: Treinos normais"
                  />
                </div>
              </div>
              <div className="mt-4 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="px-3 py-1 border border-gray-300 rounded text-sm"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="px-3 py-1 bg-blue-600 text-white rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {createMutation.isPending ? 'Salvando...' : 'Adicionar'}
                </button>
              </div>
            </form>
          )}

          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Tipo
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Descrição
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Quantidade
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Ações
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {requirements?.map((req: Requirement) => (
                <tr key={req.id}>
                  <td className="px-4 py-3 text-sm text-gray-900">{req.event_type?.name}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{req.description || '-'}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{req.required_count}</td>
                  <td className="px-4 py-3 text-sm">
                    <button
                      onClick={() => deleteMutation.mutate(req.id)}
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
      )}
    </div>
  )
}
