import { useState } from 'react'
import { useQuery, useMutation, useQueryClient, useQueries } from '@tanstack/react-query'
import { Plus, Edit, Trash2, Search, TrendingUp } from 'lucide-react'
import api from '../services/api'
import { useAuth } from '../hooks/useAuth'

interface Student {
  id: string
  full_name: string
  registration_number: string
  email: string | null
  phone: string | null
  birth_date: string | null
  category: 'child' | 'adult'
  current_belt: { name: string; id: string }
  is_active: boolean
  contract_name: string | null
  contract_cpf: string | null
  address_street: string | null
  address_neighborhood: string | null
  address_city: string | null
  address_zip: string | null
  classes_per_week: number | null
  class_days: string | null
}

interface StudentProgress {
  current_belt: string
  next_belt: string | null
  requirements: Array<{
    description: string
    required: number
    completed: number
    remaining: number
    is_complete: boolean
  }>
  overall_progress: {
    total_required: number
    total_complete: number
    percentage: number
  }
  last_promotion_date: string | null
}

export default function StudentsPage() {
  const { isAdmin } = useAuth()
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editingStudent, setEditingStudent] = useState<Student | null>(null)
  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    phone: '',
    birth_date: '',
    category: 'adult' as 'child' | 'adult',
    current_belt_id: '',
    pin: '',
    contract_name: '',
    contract_cpf: '',
    address_street: '',
    address_neighborhood: '',
    address_city: '',
    address_zip: '',
    classes_per_week: 2,
    class_days: '',
  })

  const { data: students } = useQuery<Student[]>({
    queryKey: ['students'],
    queryFn: async () => {
      const response = await api.get('/api/v1/students')
      return response.data
    },
  })

  const { data: belts } = useQuery({
    queryKey: ['belts'],
    queryFn: async () => {
      const response = await api.get('/api/v1/belts')
      return response.data
    },
  })

  const progressQueries = useQueries({
    queries: (students || []).map((student) => ({
      queryKey: ['student-progress', student.id],
      queryFn: async () => {
        const response = await api.get(`/api/v1/students/${student.id}/progress`)
        return { studentId: student.id, progress: response.data as StudentProgress }
      },
      enabled: !!students,
      staleTime: 30000,
    })),
  })

  const progressMap: Record<string, StudentProgress> = {}
  progressQueries.forEach((q) => {
    if (q.data) {
      progressMap[q.data.studentId] = q.data.progress
    }
  })

  const createMutation = useMutation({
    mutationFn: (data: typeof formData) => api.post('/api/v1/students', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['students'] })
      queryClient.invalidateQueries({ queryKey: ['student-progress'] })
      setShowForm(false)
      resetForm()
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<typeof formData> }) =>
      api.put(`/api/v1/students/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['students'] })
      queryClient.invalidateQueries({ queryKey: ['student-progress'] })
      setShowForm(false)
      setEditingStudent(null)
      resetForm()
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/api/v1/students/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['students'] })
      queryClient.invalidateQueries({ queryKey: ['student-progress'] })
    },
  })

  const resetForm = () => {
    setFormData({
      full_name: '',
      email: '',
      phone: '',
      birth_date: '',
      category: 'adult',
      current_belt_id: '',
      pin: '',
      contract_name: '',
      contract_cpf: '',
      address_street: '',
      address_neighborhood: '',
      address_city: '',
      address_zip: '',
      classes_per_week: 2,
      class_days: '',
    })
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (editingStudent) {
      const updateData = { ...formData }
      if (!updateData.pin) delete updateData.pin
      updateMutation.mutate({ id: editingStudent.id, data: updateData })
    } else {
      createMutation.mutate(formData)
    }
  }

  const handleEdit = (student: Student) => {
    setEditingStudent(student)
    setFormData({
      full_name: student.full_name,
      email: student.email || '',
      phone: student.phone || '',
      birth_date: student.birth_date
        ? new Date(student.birth_date).toISOString().split('T')[0]
        : '',
      category: student.category,
      current_belt_id: student.current_belt?.id || '',
      pin: '',
      contract_name: student.contract_name || '',
      contract_cpf: student.contract_cpf || '',
      address_street: student.address_street || '',
      address_neighborhood: student.address_neighborhood || '',
      address_city: student.address_city || '',
      address_zip: student.address_zip || '',
      classes_per_week: student.classes_per_week || 2,
      class_days: student.class_days || '',
    })
    setShowForm(true)
  }

  const filteredStudents = students?.filter(
    (s) =>
      s.full_name.toLowerCase().includes(search.toLowerCase()) ||
      s.registration_number.includes(search)
  )

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Alunos</h2>
        {isAdmin && (
          <button
            onClick={() => {
              setEditingStudent(null)
              resetForm()
              setShowForm(true)
            }}
            className="flex items-center bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          >
            <Plus className="w-4 h-4 mr-2" />
            Novo Aluno
          </button>
        )}
      </div>

      <div className="mb-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
          <input
            type="text"
            placeholder="Buscar por nome ou matrícula..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {showForm && (
        <div className="bg-white p-6 rounded-lg shadow mb-6">
          <h3 className="text-lg font-semibold mb-4">
            {editingStudent ? 'Editar Aluno' : 'Novo Aluno'}
          </h3>
          <form onSubmit={handleSubmit} className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Nome</label>
              <input
                type="text"
                value={formData.full_name}
                onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
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
              <label className="block text-sm font-medium text-gray-700 mb-1">Faixa</label>
              <select
                value={formData.current_belt_id}
                onChange={(e) => setFormData({ ...formData, current_belt_id: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
                required
              >
                <option value="">Selecione...</option>
                {belts?.map((belt: any) => (
                  <option key={belt.id} value={belt.id}>
                    {belt.name} ({belt.category === 'child' ? 'Criança' : 'Adulto'})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                PIN {editingStudent && '(deixe em branco para manter)'}
              </label>
              <input
                type="password"
                value={formData.pin}
                onChange={(e) => setFormData({ ...formData, pin: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
                required={!editingStudent}
                maxLength={4}
                placeholder="4 dígitos"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Celular</label>
              <input
                type="tel"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
                placeholder="(11) 99999-9999"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Data de Nascimento
              </label>
              <input
                type="date"
                value={formData.birth_date}
                onChange={(e) => setFormData({ ...formData, birth_date: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Contratante (se menor de idade)
              </label>
              <input
                type="text"
                value={formData.contract_name}
                onChange={(e) => setFormData({ ...formData, contract_name: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
                placeholder="Nome do responsável legal"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                CPF do Contratante
              </label>
              <input
                type="text"
                value={formData.contract_cpf}
                onChange={(e) => setFormData({ ...formData, contract_cpf: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
                placeholder="000.000.000-00"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Rua</label>
              <input
                type="text"
                value={formData.address_street}
                onChange={(e) => setFormData({ ...formData, address_street: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
                placeholder="Rua, número, complemento"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Bairro</label>
              <input
                type="text"
                value={formData.address_neighborhood}
                onChange={(e) => setFormData({ ...formData, address_neighborhood: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Cidade</label>
              <input
                type="text"
                value={formData.address_city}
                onChange={(e) => setFormData({ ...formData, address_city: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">CEP</label>
              <input
                type="text"
                value={formData.address_zip}
                onChange={(e) => setFormData({ ...formData, address_zip: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
                placeholder="00000-000"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Aulas por Semana
              </label>
              <input
                type="number"
                min={1}
                max={7}
                value={formData.classes_per_week}
                onChange={(e) =>
                  setFormData({ ...formData, classes_per_week: parseInt(e.target.value) })
                }
                className="w-full px-3 py-2 border rounded-md"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Dias de Aula</label>
              <input
                type="text"
                value={formData.class_days}
                onChange={(e) => setFormData({ ...formData, class_days: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
                placeholder="Ex: Seg, Qua, Sex"
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
                {editingStudent ? 'Atualizar' : 'Criar'}
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
                Matrícula
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Nome
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Celular
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Contratante
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Categoria
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Faixa
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Progresso
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Aulas
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Status
              </th>
              {isAdmin && (
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Ações
                </th>
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {filteredStudents?.map((student) => {
              const progress = progressMap[student.id]
              return (
                <tr key={student.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {student.registration_number}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {student.full_name}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {student.phone || '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {student.contract_name || (student.category === 'adult' ? 'Próprio' : '-')}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {student.category === 'child' ? 'Criança' : 'Adulto'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {student.current_belt?.name}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    {progress ? (
                      <div className="flex items-center space-x-2">
                        <div className="flex-1 min-w-[80px]">
                          <div className="bg-gray-200 rounded-full h-2">
                            <div
                              className={`rounded-full h-2 transition-all ${
                                progress.overall_progress.percentage >= 100
                                  ? 'bg-green-500'
                                  : progress.overall_progress.percentage >= 50
                                    ? 'bg-yellow-500'
                                    : 'bg-blue-500'
                              }`}
                              style={{
                                width: `${Math.min(100, progress.overall_progress.percentage)}%`,
                              }}
                            />
                          </div>
                        </div>
                        <span className="text-xs text-gray-600 whitespace-nowrap">
                          {progress.overall_progress.total_complete}/
                          {progress.overall_progress.total_required}
                        </span>
                        {!progress.next_belt && (
                          <TrendingUp className="w-4 h-4 text-green-500" title="Faixa máxima!" />
                        )}
                      </div>
                    ) : (
                      <span className="text-xs text-gray-400">Carregando...</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {student.classes_per_week || '-'}/sem{' '}
                    {student.class_days ? `(${student.class_days})` : ''}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`inline-flex px-2 text-xs leading-5 font-semibold rounded-full ${
                        student.is_active
                          ? 'bg-green-100 text-green-800'
                          : 'bg-red-100 text-red-800'
                      }`}
                    >
                      {student.is_active ? 'Ativo' : 'Inativo'}
                    </span>
                  </td>
                  {isAdmin && (
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <button
                        onClick={() => handleEdit(student)}
                        className="text-blue-600 hover:text-blue-900 mr-3"
                      >
                        <Edit className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => deleteMutation.mutate(student.id)}
                        className="text-red-600 hover:text-red-900"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  )}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
