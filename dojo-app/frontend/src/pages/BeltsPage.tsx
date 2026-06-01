import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Edit, Trash2 } from 'lucide-react'
import api from '../services/api'
import { useAuth } from '../hooks/useAuth'

interface Belt {
  id: string
  name: string
  category: 'child' | 'adult'
  sort_order: number
  organization_id: string | null
}

export default function BeltsPage() {
  const { isAdmin } = useAuth()
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [editingBelt, setEditingBelt] = useState<Belt | null>(null)
  const [formData, setFormData] = useState({
    name: '',
    category: 'adult' as 'child' | 'adult',
    sort_order: 1,
    organization_id: '',
  })

  const { data: belts } = useQuery<Belt[]>({
    queryKey: ['belts'],
    queryFn: async () => {
      const response = await api.get('/api/v1/belts')
      return response.data
    },
  })

  const createMutation = useMutation({
    mutationFn: (data: typeof formData) => api.post('/api/v1/belts', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['belts'] })
      setShowForm(false)
      resetForm()
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<typeof formData> }) =>
      api.put(`/api/v1/belts/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['belts'] })
      setShowForm(false)
      setEditingBelt(null)
      resetForm()
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/api/v1/belts/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['belts'] })
    },
  })

  const resetForm = () => {
    setFormData({
      name: '',
      category: 'adult',
      sort_order: 1,
      organization_id: '',
    })
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const data = {
      ...formData,
      organization_id: formData.organization_id || undefined,
    }
    if (editingBelt) {
      updateMutation.mutate({ id: editingBelt.id, data })
    } else {
      createMutation.mutate(data as any) // eslint-disable-line @typescript-eslint/no-explicit-any
    }
  }

  const handleEdit = (belt: Belt) => {
    setEditingBelt(belt)
    setFormData({
      name: belt.name,
      category: belt.category,
      sort_order: belt.sort_order,
      organization_id: belt.organization_id || '',
    })
    setShowForm(true)
  }

  if (!isAdmin) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Apenas administradores podem gerenciar faixas.</p>
      </div>
    )
  }

  const sortedBelts = belts?.sort((a, b) => {
    if (a.category !== b.category) return a.category === 'adult' ? -1 : 1
    return a.sort_order - b.sort_order
  })

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Faixas</h2>
        <button
          onClick={() => {
            setEditingBelt(null)
            resetForm()
            setShowForm(true)
          }}
          className="flex items-center bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          <Plus className="w-4 h-4 mr-2" />
          Nova Faixa
        </button>
      </div>

      {showForm && (
        <div className="bg-white p-6 rounded-lg shadow mb-6">
          <h3 className="text-lg font-semibold mb-4">
            {editingBelt ? 'Editar Faixa' : 'Nova Faixa'}
          </h3>
          <form onSubmit={handleSubmit} className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Nome</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Categoria</label>
              <select
                value={formData.category}
                onChange={(e) =>
                  setFormData({ ...formData, category: e.target.value as 'child' | 'adult' })
                }
                className="w-full px-3 py-2 border rounded-md"
              >
                <option value="adult">Adulto</option>
                <option value="child">Criança</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Ordem</label>
              <input
                type="number"
                min={1}
                value={formData.sort_order}
                onChange={(e) => setFormData({ ...formData, sort_order: parseInt(e.target.value) })}
                className="w-full px-3 py-2 border rounded-md"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Organização (opcional)
              </label>
              <input
                type="text"
                value={formData.organization_id}
                onChange={(e) => setFormData({ ...formData, organization_id: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
                placeholder="ID da organização ou vazio para global"
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
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                {editingBelt ? 'Atualizar' : 'Criar'}
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
                Ordem
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Nome
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Categoria
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Escopo
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Ações
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {sortedBelts?.map((belt) => (
              <tr key={belt.id}>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {belt.sort_order}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{belt.name}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {belt.category === 'child' ? 'Criança' : 'Adulto'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {belt.organization_id ? 'Organização' : 'Global'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <button
                    onClick={() => handleEdit(belt)}
                    className="text-blue-600 hover:text-blue-900 mr-3"
                  >
                    <Edit className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => deleteMutation.mutate(belt.id)}
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
