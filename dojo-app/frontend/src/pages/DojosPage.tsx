import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Edit, Trash2 } from 'lucide-react'
import api from '../services/api'
import { useAuth } from '../hooks/useAuth'

interface Organization {
  id: string
  name: string
}

interface Dojo {
  id: string
  name: string
  address: string | null
  organization_id: string
  organization?: Organization
}

export default function DojosPage() {
  const { isAdmin } = useAuth()
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [editingDojo, setEditingDojo] = useState<Dojo | null>(null)
  const [selectedOrg, setSelectedOrg] = useState('')
  const [formData, setFormData] = useState({
    name: '',
    address: '',
    organization_id: '',
  })

  const { data: organizations } = useQuery<Organization[]>({
    queryKey: ['organizations'],
    queryFn: async () => {
      const response = await api.get('/api/v1/organizations')
      return response.data
    },
  })

  const { data: dojos } = useQuery<Dojo[]>({
    queryKey: ['dojos', selectedOrg],
    queryFn: async () => {
      if (!selectedOrg) return []
      const response = await api.get(`/api/v1/organizations/${selectedOrg}/dojos`)
      return response.data
    },
    enabled: !!selectedOrg,
  })

  const createMutation = useMutation({
    mutationFn: (data: typeof formData) =>
      api.post(`/api/v1/organizations/${data.organization_id}/dojos`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dojos', selectedOrg] })
      setShowForm(false)
      resetForm()
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({
      org_id,
      id,
      data,
    }: {
      org_id: string
      id: string
      data: Partial<typeof formData>
    }) => api.put(`/api/v1/organizations/${org_id}/dojos/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dojos', selectedOrg] })
      setShowForm(false)
      setEditingDojo(null)
      resetForm()
    },
  })

  const deleteMutation = useMutation({
    mutationFn: ({ org_id, id }: { org_id: string; id: string }) =>
      api.delete(`/api/v1/organizations/${org_id}/dojos/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dojos', selectedOrg] })
    },
  })

  const resetForm = () => {
    setFormData({
      name: '',
      address: '',
      organization_id: selectedOrg,
    })
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const data = {
      ...formData,
      address: formData.address || undefined,
    }
    if (editingDojo) {
      updateMutation.mutate({ org_id: editingDojo.organization_id, id: editingDojo.id, data })
    } else {
      createMutation.mutate(data as any) // eslint-disable-line @typescript-eslint/no-explicit-any
    }
  }

  const handleEdit = (dojo: Dojo) => {
    setEditingDojo(dojo)
    setFormData({
      name: dojo.name,
      address: dojo.address || '',
      organization_id: dojo.organization_id,
    })
    setShowForm(true)
  }

  if (!isAdmin) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Apenas administradores podem gerenciar dojos.</p>
      </div>
    )
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Dojos</h2>
        {selectedOrg && (
          <button
            onClick={() => {
              setEditingDojo(null)
              resetForm()
              setShowForm(true)
            }}
            className="flex items-center bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          >
            <Plus className="w-4 h-4 mr-2" />
            Novo Dojo
          </button>
        )}
      </div>

      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">Organização</label>
        <select
          value={selectedOrg}
          onChange={(e) => {
            setSelectedOrg(e.target.value)
            setFormData({ ...formData, organization_id: e.target.value })
          }}
          className="w-full max-w-md px-3 py-2 border rounded-md"
        >
          <option value="">Selecione uma organização...</option>
          {organizations?.map((org: Organization) => (
            <option key={org.id} value={org.id}>
              {org.name}
            </option>
          ))}
        </select>
      </div>

      {showForm && (
        <div className="bg-white p-6 rounded-lg shadow mb-6">
          <h3 className="text-lg font-semibold mb-4">
            {editingDojo ? 'Editar Dojo' : 'Novo Dojo'}
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
              <label className="block text-sm font-medium text-gray-700 mb-1">Endereço</label>
              <input
                type="text"
                value={formData.address}
                onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
                placeholder="Endereço do dojo"
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
                {editingDojo ? 'Atualizar' : 'Criar'}
              </button>
            </div>
          </form>
        </div>
      )}

      {selectedOrg && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Nome
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Endereço
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Ações
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {dojos?.map((dojo) => (
                <tr key={dojo.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{dojo.name}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {dojo.address || '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <button
                      onClick={() => handleEdit(dojo)}
                      className="text-blue-600 hover:text-blue-900 mr-3"
                    >
                      <Edit className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() =>
                        deleteMutation.mutate({ org_id: dojo.organization_id, id: dojo.id })
                      }
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
