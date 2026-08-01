import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Edit, Ban } from 'lucide-react'
import api from '../services/api'
import { useAuth } from '../hooks/useAuth'

interface User {
  id: string
  email: string
  full_name: string
  role: 'admin' | 'instructor'
  is_active: boolean
}

interface UserFormData {
  email: string
  full_name: string
  role: 'admin' | 'instructor'
  is_active: boolean
  password: string
}

const emptyFormData: UserFormData = {
  email: '',
  full_name: '',
  role: 'instructor',
  is_active: true,
  password: '',
}

export default function UsersPage() {
  const { isAdmin, user: currentUser } = useAuth()
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [editingUser, setEditingUser] = useState<User | null>(null)
  const [formData, setFormData] = useState<UserFormData>(emptyFormData)

  const { data: users } = useQuery<User[]>({
    queryKey: ['users'],
    queryFn: async () => (await api.get('/api/v1/users')).data,
  })

  const resetForm = () => setFormData(emptyFormData)

  const createMutation = useMutation({
    mutationFn: (data: UserFormData) => api.post('/api/v1/users', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      setShowForm(false)
      resetForm()
    },
    onError: (error: unknown) => {
      const err = error as { response?: { data?: { detail?: string } } }
      alert(err?.response?.data?.detail || 'Não foi possível salvar o usuário.')
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<UserFormData> }) =>
      api.put(`/api/v1/users/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      setShowForm(false)
      setEditingUser(null)
      resetForm()
    },
    onError: (error: unknown) => {
      const err = error as { response?: { data?: { detail?: string } } }
      alert(err?.response?.data?.detail || 'Não foi possível salvar o usuário.')
    },
  })

  const deactivateMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/api/v1/users/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
    onError: (error: unknown) => {
      const err = error as { response?: { data?: { detail?: string } } }
      alert(err?.response?.data?.detail || 'Não foi possível desativar o usuário.')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (editingUser) {
      const data: Partial<UserFormData> = {
        email: formData.email,
        full_name: formData.full_name,
        role: formData.role,
        is_active: formData.is_active,
      }
      if (formData.password) {
        data.password = formData.password
      }
      updateMutation.mutate({ id: editingUser.id, data })
    } else {
      createMutation.mutate(formData)
    }
  }

  const handleEdit = (user: User) => {
    setEditingUser(user)
    setFormData({
      email: user.email,
      full_name: user.full_name,
      role: user.role,
      is_active: user.is_active,
      password: '',
    })
    setShowForm(true)
  }

  if (!isAdmin) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Apenas administradores podem gerenciar usuários.</p>
      </div>
    )
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Usuários</h2>
        <button
          onClick={() => {
            setEditingUser(null)
            resetForm()
            setShowForm(true)
          }}
          className="flex items-center bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          <Plus className="w-4 h-4 mr-2" />
          Novo Usuário
        </button>
      </div>

      {showForm && (
        <div className="bg-white p-6 rounded-lg shadow mb-6">
          <h3 className="text-lg font-semibold mb-4">
            {editingUser ? 'Editar Usuário' : 'Novo Usuário'}
          </h3>
          <form onSubmit={handleSubmit} className="grid grid-cols-2 gap-4">
            <div>
              <label
                htmlFor="user-full-name"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Nome
              </label>
              <input
                id="user-full-name"
                type="text"
                value={formData.full_name}
                onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
                required
              />
            </div>
            <div>
              <label htmlFor="user-email" className="block text-sm font-medium text-gray-700 mb-1">
                Email
              </label>
              <input
                id="user-email"
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
                required
              />
            </div>
            <div>
              <label htmlFor="user-role" className="block text-sm font-medium text-gray-700 mb-1">
                Perfil
              </label>
              <select
                id="user-role"
                value={formData.role}
                onChange={(e) =>
                  setFormData({ ...formData, role: e.target.value as 'admin' | 'instructor' })
                }
                className="w-full px-3 py-2 border rounded-md"
              >
                <option value="instructor">Instrutor</option>
                <option value="admin">Administrador</option>
              </select>
            </div>
            <div>
              <label
                htmlFor="user-password"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                {editingUser ? 'Nova senha (deixe em branco para manter)' : 'Senha'}
              </label>
              <input
                id="user-password"
                type="password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
                required={!editingUser}
                minLength={8}
              />
            </div>
            <div className="col-span-2">
              <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                <input
                  type="checkbox"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                />
                Usuário ativo
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
                  : editingUser
                    ? 'Atualizar'
                    : 'Criar'}
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
                Nome
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Email
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Perfil
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
            {users?.map((user) => (
              <tr key={user.id}>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {user.full_name}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{user.email}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {user.role === 'admin' ? 'Administrador' : 'Instrutor'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={`inline-flex px-2 text-xs leading-5 font-semibold rounded-full ${
                      user.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    }`}
                  >
                    {user.is_active ? 'Ativo' : 'Inativo'}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <button
                    onClick={() => handleEdit(user)}
                    className="text-blue-600 hover:text-blue-900 mr-3"
                    title="Editar usuário"
                  >
                    <Edit className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => deactivateMutation.mutate(user.id)}
                    className="text-red-600 hover:text-red-900 disabled:opacity-30 disabled:cursor-not-allowed"
                    title="Desativar usuário"
                    disabled={!user.is_active || user.id === currentUser?.id}
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
