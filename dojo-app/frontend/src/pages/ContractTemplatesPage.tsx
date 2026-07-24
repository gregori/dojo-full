import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import api from '../services/api'
import { useAuth } from '../hooks/useAuth'

interface ContractTemplateVersion {
  id: string
  body: string
  status: string
  effective_from: string
  created_by: string
  created_at: string
}

export default function ContractTemplatesPage() {
  const { isAdmin } = useAuth()
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [body, setBody] = useState('')
  const [effectiveFrom, setEffectiveFrom] = useState('')

  const { data: history } = useQuery<ContractTemplateVersion[]>({
    queryKey: ['contract-template-versions'],
    queryFn: async () => {
      const response = await api.get('/api/v1/contract-templates')
      return response.data
    },
  })

  const createMutation = useMutation({
    mutationFn: (data: { body: string; effective_from: string }) =>
      api.post('/api/v1/contract-templates', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contract-template-versions'] })
      setShowForm(false)
      setBody('')
      setEffectiveFrom('')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    createMutation.mutate({ body, effective_from: new Date(effectiveFrom).toISOString() })
  }

  if (!isAdmin) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Apenas administradores podem gerenciar o modelo de contrato.</p>
      </div>
    )
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Modelo de Contrato</h2>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          <Plus className="w-4 h-4 mr-2" />
          Nova Versão
        </button>
      </div>

      {showForm && (
        <div className="bg-white p-6 rounded-lg shadow mb-6">
          <h3 className="text-lg font-semibold mb-2">Nova Versão do Contrato</h3>
          <p className="text-sm text-gray-500 mb-4">
            Placeholders disponíveis: <code>{'{{ student.contract_name }}'}</code>,{' '}
            <code>{'{{ student.contract_cpf }}'}</code>, <code>{'{{ student.address }}'}</code>,{' '}
            <code>{'{{ student.birth_date }}'}</code>, <code>{'{{ student.phone }}'}</code>,{' '}
            <code>{'{{ plan_tier.name }}'}</code>, <code>{'{{ plan_tier.weekly_frequency }}'}</code>,{' '}
            <code>{'{{ plan_version.price }}'}</code>.
          </p>
          <form onSubmit={handleSubmit}>
            <div className="mb-4">
              <label htmlFor="contract-template-body" className="block text-sm font-medium text-gray-700 mb-1">
                Corpo do Contrato
              </label>
              <textarea
                id="contract-template-body"
                value={body}
                onChange={(e) => setBody(e.target.value)}
                rows={10}
                className="w-full px-3 py-2 border rounded-md"
                required
              />
            </div>
            <div className="mb-4">
              <label htmlFor="contract-template-effective-from" className="block text-sm font-medium text-gray-700 mb-1">
                Vigente a partir de
              </label>
              <input
                id="contract-template-effective-from"
                type="date"
                value={effectiveFrom}
                onChange={(e) => setEffectiveFrom(e.target.value)}
                className="w-full px-3 py-2 border rounded-md"
                required
              />
            </div>
            <div className="flex justify-end space-x-2">
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={createMutation.isPending}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-60"
              >
                {createMutation.isPending ? 'Salvando...' : 'Criar Versão'}
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
                Vigente desde
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Criado em
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {history?.length ? (
              history.map((version) => (
                <tr key={version.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {new Date(version.effective_from).toLocaleDateString('pt-BR')}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {new Date(version.created_at).toLocaleDateString('pt-BR')}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`inline-flex px-2 text-xs leading-5 font-semibold rounded-full ${
                        version.status === 'active'
                          ? 'bg-green-100 text-green-800'
                          : 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      {version.status === 'active' ? 'Ativo' : 'Substituído'}
                    </span>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={3} className="px-6 py-4 text-center text-gray-400">
                  Nenhuma versão cadastrada.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
