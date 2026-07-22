import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, DollarSign } from 'lucide-react'
import api from '../services/api'
import { useAuth } from '../hooks/useAuth'

interface PlanTier {
  id: string
  weekly_frequency: number
  name: string
  is_active: boolean
  current_price: string | null
}

export default function PlansPage() {
  const { isAdmin } = useAuth()
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState({ weekly_frequency: 1, name: '', price: '' })
  const [priceEditTier, setPriceEditTier] = useState<PlanTier | null>(null)
  const [newPrice, setNewPrice] = useState('')

  const { data: tiers } = useQuery<PlanTier[]>({
    queryKey: ['plan-tiers'],
    queryFn: async () => {
      const response = await api.get('/api/v1/plans')
      return response.data
    },
  })

  const createMutation = useMutation({
    mutationFn: (data: typeof formData) => api.post('/api/v1/plans', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['plan-tiers'] })
      setShowForm(false)
      setFormData({ weekly_frequency: 1, name: '', price: '' })
    },
  })

  const setPriceMutation = useMutation({
    mutationFn: ({ tierId, price }: { tierId: string; price: string }) =>
      api.put(`/api/v1/plans/${tierId}/price`, { price }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['plan-tiers'] })
      setPriceEditTier(null)
      setNewPrice('')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    createMutation.mutate(formData)
  }

  const handlePriceSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!priceEditTier) return
    setPriceMutation.mutate({ tierId: priceEditTier.id, price: newPrice })
  }

  if (!isAdmin) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Apenas administradores podem gerenciar planos.</p>
      </div>
    )
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Planos</h2>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          <Plus className="w-4 h-4 mr-2" />
          Novo Plano
        </button>
      </div>

      {showForm && (
        <div className="bg-white p-6 rounded-lg shadow mb-6">
          <h3 className="text-lg font-semibold mb-4">Novo Plano</h3>
          <form onSubmit={handleSubmit} className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Aulas por Semana
              </label>
              <input
                type="number"
                min={1}
                max={7}
                value={formData.weekly_frequency}
                onChange={(e) =>
                  setFormData({ ...formData, weekly_frequency: parseInt(e.target.value) })
                }
                className="w-full px-3 py-2 border rounded-md"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Nome</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
                placeholder="Ex: 2x por semana"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Preço (R$)</label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={formData.price}
                onChange={(e) => setFormData({ ...formData, price: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
                required
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
                Criar
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
                Aulas/Semana
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Nome
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Preço Atual
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
            {tiers?.map((tier) => (
              <tr key={tier.id}>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {tier.weekly_frequency}x
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{tier.name}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {tier.current_price ? `R$ ${tier.current_price}` : '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={`inline-flex px-2 text-xs leading-5 font-semibold rounded-full ${
                      tier.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
                    }`}
                  >
                    {tier.is_active ? 'Ativo' : 'Inativo'}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <button
                    onClick={() => {
                      setPriceEditTier(tier)
                      setNewPrice(tier.current_price || '')
                    }}
                    title="Alterar preço"
                    className="text-blue-600 hover:text-blue-900"
                  >
                    <DollarSign className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {priceEditTier && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-40 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-2">
              Alterar Preço — {priceEditTier.name}
            </h3>
            <p className="text-sm text-gray-500 mb-4">
              Isso cria uma nova versão do plano. Alunos já matriculados mantêm o preço em que foram
              matriculados; o novo valor só se aplica a novas matrículas ou reatribuições.
            </p>
            <form onSubmit={handlePriceSubmit}>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Novo Preço (R$)
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={newPrice}
                onChange={(e) => setNewPrice(e.target.value)}
                className="w-full px-3 py-2 border rounded-md mb-4"
                required
              />
              <div className="flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setPriceEditTier(null)}
                  className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                  Confirmar Nova Versão
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
