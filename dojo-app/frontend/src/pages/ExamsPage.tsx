import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2, Users, Award, Eye, X, Check, AlertTriangle } from 'lucide-react'
import api from '../services/api'
import { useAuth } from '../hooks/useAuth'

interface Belt {
  id: string
  name: string
  color: string
  order: number
}

interface ExamEvent {
  id: string
  title: string
  event_date: string
}

interface Exam {
  id: string
  event: { title: string }
  belt: { name: string; id: string }
  exam_date: string
  status: string
  participants_count: number
}

interface ExamParticipant {
  id: string
  exam_id: string
  student_id: string
  student_name?: string
  role: string
  status: string
  is_eligible: boolean
  override_eligibility: boolean
  override_reason: string | null
  overridden_by: string | null
  notes: string | null
  created_at: string
  updated_at: string
}

interface Student {
  id: string
  full_name: string
  registration_number: string
  current_belt?: { name: string }
}

interface BoardMember {
  id: string
  student_id: string
  student_name?: string
  role: string
}

interface ExamDetail extends Exam {
  participants: ExamParticipant[]
  board_members: BoardMember[]
  event_title?: string
  belt_name?: string
}

export default function ExamsPage() {
  const { isAdmin, user } = useAuth()
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [selectedExam, setSelectedExam] = useState<ExamDetail | null>(null)
  const [showParticipantForm, setShowParticipantForm] = useState(false)
  const [showPromoteForm, setShowPromoteForm] = useState<string | null>(null)
  const [formData, setFormData] = useState({
    event_id: '',
    belt_id: '',
    exam_date: '',
    notes: '',
  })
  const [participantData, setParticipantData] = useState({
    student_id: '',
    role: 'candidate' as 'candidate' | 'uke',
    override_eligibility: false,
    override_reason: '',
  })
  const [promoteBeltId, setPromoteBeltId] = useState('')

  const { data: exams } = useQuery<Exam[]>({
    queryKey: ['exams'],
    queryFn: async () => {
      const response = await api.get('/api/v1/exams')
      return response.data
    },
  })

  const { data: events } = useQuery({
    queryKey: ['events-for-exams'],
    queryFn: async () => {
      const response = await api.get('/api/v1/events?status=scheduled')
      return response.data
    },
  })

  const { data: belts } = useQuery({
    queryKey: ['belts-for-exams'],
    queryFn: async () => {
      const response = await api.get('/api/v1/belts')
      return response.data
    },
  })

  const { data: students } = useQuery({
    queryKey: ['students-for-participants'],
    queryFn: async () => {
      const response = await api.get('/api/v1/students?is_active=true')
      return response.data
    },
  })

  const createMutation = useMutation({
    mutationFn: (data: typeof formData) => api.post('/api/v1/exams', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exams'] })
      setShowForm(false)
      resetForm()
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/api/v1/exams/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exams'] })
      setSelectedExam(null)
    },
  })

  const addParticipantMutation = useMutation({
    mutationFn: (data: typeof participantData & { exam_id: string }) =>
      api.post(`/api/v1/exams/${data.exam_id}/participants`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exam-detail'] })
      queryClient.invalidateQueries({ queryKey: ['exams'] })
      setShowParticipantForm(false)
      resetParticipantForm()
      if (selectedExam) loadExamDetail(selectedExam.id)
    },
    onError: (error: unknown) => {
      const err = error as {
        response?: { data?: { detail?: { message?: string; reasons?: string[] } } }
      }
      const detail = err?.response?.data?.detail
      if (detail?.message) {
        alert(`Requisitos não atendidos:\n${detail.reasons?.join('\n') || detail.message}`)
      }
    },
  })

  const promoteMutation = useMutation({
    mutationFn: ({ participantId, newBeltId }: { participantId: string; newBeltId: string }) =>
      api.post(`/api/v1/exams/participants/${participantId}/promote?new_belt_id=${newBeltId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exam-detail'] })
      queryClient.invalidateQueries({ queryKey: ['exams'] })
      setShowPromoteForm(null)
      if (selectedExam) loadExamDetail(selectedExam.id)
    },
  })

  const loadExamDetail = async (examId: string) => {
    try {
      const response = await api.get(`/api/v1/exams/${examId}`)
      setSelectedExam(response.data)
    } catch {
      // silently fail
    }
  }

  const resetForm = () => {
    setFormData({
      event_id: '',
      belt_id: '',
      exam_date: '',
      notes: '',
    })
  }

  const resetParticipantForm = () => {
    setParticipantData({
      student_id: '',
      role: 'candidate',
      override_eligibility: false,
      override_reason: '',
    })
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    createMutation.mutate(formData)
  }

  const handleAddParticipant = (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedExam) return
    addParticipantMutation.mutate({ ...participantData, exam_id: selectedExam.id })
  }

  const handlePromote = (participantId: string) => {
    if (!promoteBeltId) return
    promoteMutation.mutate({ participantId, newBeltId: promoteBeltId })
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'scheduled':
        return 'bg-blue-100 text-blue-800'
      case 'in_progress':
        return 'bg-yellow-100 text-yellow-800'
      case 'completed':
        return 'bg-green-100 text-green-800'
      case 'cancelled':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getEligibilityBadge = (p: ExamParticipant) => {
    if (p.override_eligibility) {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
          <AlertTriangle className="w-3 h-3 mr-1" />
          Override
        </span>
      )
    }
    if (p.is_eligible) {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
          <Check className="w-3 h-3 mr-1" />
          Elegível
        </span>
      )
    }
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
        <X className="w-3 h-3 mr-1" />
        Não Elegível
      </span>
    )
  }

  const canOverride = isAdmin || user?.role === 'instructor'

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Exames de Faixa</h2>
        {isAdmin && (
          <button
            onClick={() => {
              setSelectedExam(null)
              resetForm()
              setShowForm(true)
            }}
            className="flex items-center bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          >
            <Plus className="w-4 h-4 mr-2" />
            Novo Exame
          </button>
        )}
      </div>

      {showForm && (
        <div className="bg-white p-6 rounded-lg shadow mb-6">
          <h3 className="text-lg font-semibold mb-4">Criar Exame</h3>
          <form onSubmit={handleSubmit} className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Evento</label>
              <select
                value={formData.event_id}
                onChange={(e) => setFormData({ ...formData, event_id: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
                required
              >
                <option value="">Selecione...</option>
                {events?.map((event: ExamEvent) => (
                  <option key={event.id} value={event.id}>
                    {event.title}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Faixa</label>
              <select
                value={formData.belt_id}
                onChange={(e) => setFormData({ ...formData, belt_id: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
                required
              >
                <option value="">Selecione...</option>
                {belts?.map((belt: Belt) => (
                  <option key={belt.id} value={belt.id}>
                    {belt.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Data do Exame</label>
              <input
                type="datetime-local"
                value={formData.exam_date}
                onChange={(e) => setFormData({ ...formData, exam_date: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Observações</label>
              <textarea
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
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
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                Criar Exame
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
                Evento
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Faixa
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Data
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Participantes
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Ações
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {exams?.map((exam) => (
              <tr key={exam.id}>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {exam.event?.title}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                    <Award className="w-3 h-3 mr-1" />
                    {exam.belt?.name}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {new Date(exam.exam_date).toLocaleString('pt-BR')}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={`inline-flex px-2 text-xs leading-5 font-semibold rounded-full ${getStatusColor(exam.status)}`}
                  >
                    {exam.status === 'scheduled'
                      ? 'Agendado'
                      : exam.status === 'in_progress'
                        ? 'Em Andamento'
                        : exam.status === 'completed'
                          ? 'Concluído'
                          : exam.status === 'cancelled'
                            ? 'Cancelado'
                            : exam.status}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  <div className="flex items-center">
                    <Users className="w-4 h-4 mr-1" />
                    {exam.participants_count || 0}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <button
                    onClick={() => loadExamDetail(exam.id)}
                    className="text-blue-600 hover:text-blue-900 mr-3"
                    title="Ver detalhes"
                  >
                    <Eye className="w-4 h-4" />
                  </button>
                  {isAdmin && (
                    <button
                      onClick={() => deleteMutation.mutate(exam.id)}
                      className="text-red-600 hover:text-red-900"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selectedExam && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center p-6 border-b">
              <h3 className="text-xl font-bold text-gray-800">
                {selectedExam.event_title || 'Detalhes do Exame'}
              </h3>
              <button
                onClick={() => {
                  setSelectedExam(null)
                  setShowParticipantForm(false)
                  setShowPromoteForm(null)
                }}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="p-6">
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div>
                  <span className="text-sm text-gray-500">Faixa</span>
                  <p className="font-semibold">
                    {selectedExam.belt_name || selectedExam.belt?.name}
                  </p>
                </div>
                <div>
                  <span className="text-sm text-gray-500">Data</span>
                  <p className="font-semibold">
                    {new Date(selectedExam.exam_date).toLocaleString('pt-BR')}
                  </p>
                </div>
                <div>
                  <span className="text-sm text-gray-500">Status</span>
                  <p>
                    <span
                      className={`inline-flex px-2 text-xs leading-5 font-semibold rounded-full ${getStatusColor(selectedExam.status)}`}
                    >
                      {selectedExam.status === 'scheduled'
                        ? 'Agendado'
                        : selectedExam.status === 'in_progress'
                          ? 'Em Andamento'
                          : selectedExam.status === 'completed'
                            ? 'Concluído'
                            : selectedExam.status === 'cancelled'
                              ? 'Cancelado'
                              : selectedExam.status}
                    </span>
                  </p>
                </div>
              </div>

              <div className="flex justify-between items-center mb-4">
                <h4 className="text-lg font-semibold text-gray-700">Participantes</h4>
                {isAdmin && (
                  <button
                    onClick={() => setShowParticipantForm(true)}
                    className="flex items-center bg-green-600 text-white px-3 py-1.5 rounded hover:bg-green-700 text-sm"
                  >
                    <Plus className="w-4 h-4 mr-1" />
                    Adicionar
                  </button>
                )}
              </div>

              {showParticipantForm && (
                <form
                  onSubmit={handleAddParticipant}
                  className="bg-gray-50 p-4 rounded-lg mb-4 grid grid-cols-2 gap-4"
                >
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Aluno</label>
                    <select
                      value={participantData.student_id}
                      onChange={(e) =>
                        setParticipantData({ ...participantData, student_id: e.target.value })
                      }
                      className="w-full px-3 py-2 border rounded-md"
                      required
                    >
                      <option value="">Selecione...</option>
                      {students?.map((s: Student) => (
                        <option key={s.id} value={s.id}>
                          {s.full_name} ({s.registration_number})
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Função</label>
                    <select
                      value={participantData.role}
                      onChange={(e) =>
                        setParticipantData({
                          ...participantData,
                          role: e.target.value as 'candidate' | 'uke',
                        })
                      }
                      className="w-full px-3 py-2 border rounded-md"
                    >
                      <option value="candidate">Candidato</option>
                      <option value="uke">Uke</option>
                    </select>
                  </div>
                  {participantData.role === 'candidate' && (
                    <>
                      <div className="flex items-center space-x-2">
                        <input
                          type="checkbox"
                          id="override"
                          checked={participantData.override_eligibility}
                          onChange={(e) =>
                            setParticipantData({
                              ...participantData,
                              override_eligibility: e.target.checked,
                            })
                          }
                          className="rounded"
                        />
                        <label htmlFor="override" className="text-sm font-medium text-gray-700">
                          Ignorar requisitos (override)
                        </label>
                      </div>
                      {participantData.override_eligibility && (
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Motivo do override
                          </label>
                          <input
                            type="text"
                            value={participantData.override_reason}
                            onChange={(e) =>
                              setParticipantData({
                                ...participantData,
                                override_reason: e.target.value,
                              })
                            }
                            className="w-full px-3 py-2 border rounded-md"
                            placeholder="Ex: Sensei autorizou"
                            required
                          />
                        </div>
                      )}
                    </>
                  )}
                  <div className="col-span-2 flex justify-end space-x-2">
                    <button
                      type="button"
                      onClick={() => setShowParticipantForm(false)}
                      className="px-3 py-1.5 border border-gray-300 rounded-md hover:bg-gray-50 text-sm"
                    >
                      Cancelar
                    </button>
                    <button
                      type="submit"
                      className="px-3 py-1.5 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm"
                    >
                      Adicionar
                    </button>
                  </div>
                </form>
              )}

              {selectedExam.participants?.length > 0 ? (
                <table className="w-full mb-4">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                        Aluno
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                        Função
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                        Status
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                        Elegibilidade
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                        Ações
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {selectedExam.participants.map((p) => (
                      <tr key={p.id}>
                        <td className="px-4 py-3 text-sm text-gray-900">
                          {(p as { student?: { full_name: string } }).student?.full_name ||
                            p.student_id}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <span
                            className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                              p.role === 'candidate'
                                ? 'bg-blue-100 text-blue-800'
                                : 'bg-gray-100 text-gray-800'
                            }`}
                          >
                            {p.role === 'candidate' ? 'Candidato' : 'Uke'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <span
                            className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                              p.status === 'approved'
                                ? 'bg-green-100 text-green-800'
                                : p.status === 'rejected'
                                  ? 'bg-red-100 text-red-800'
                                  : 'bg-yellow-100 text-yellow-800'
                            }`}
                          >
                            {p.status === 'approved'
                              ? 'Aprovado'
                              : p.status === 'rejected'
                                ? 'Rejeitado'
                                : 'Pendente'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm">
                          {getEligibilityBadge(p)}
                          {p.override_reason && (
                            <p className="text-xs text-gray-500 mt-1">{p.override_reason}</p>
                          )}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          {p.role === 'candidate' && p.status === 'approved' && (
                            <>
                              {showPromoteForm === p.id ? (
                                <div className="flex items-center space-x-2">
                                  <select
                                    value={promoteBeltId}
                                    onChange={(e) => setPromoteBeltId(e.target.value)}
                                    className="px-2 py-1 border rounded text-xs"
                                  >
                                    <option value="">Nova faixa...</option>
                                    {belts?.map((belt: Belt) => (
                                      <option key={belt.id} value={belt.id}>
                                        {belt.name}
                                      </option>
                                    ))}
                                  </select>
                                  <button
                                    onClick={() => handlePromote(p.id)}
                                    disabled={!promoteBeltId}
                                    className="px-2 py-1 bg-green-600 text-white rounded text-xs hover:bg-green-700 disabled:opacity-50"
                                  >
                                    Promover
                                  </button>
                                  <button
                                    onClick={() => {
                                      setShowPromoteForm(null)
                                      setPromoteBeltId('')
                                    }}
                                    className="px-2 py-1 border rounded text-xs"
                                  >
                                    Cancelar
                                  </button>
                                </div>
                              ) : (
                                canOverride && (
                                  <button
                                    onClick={() => setShowPromoteForm(p.id)}
                                    className="text-green-600 hover:text-green-900 text-xs font-medium"
                                  >
                                    <Award className="w-4 h-4 inline mr-1" />
                                    Promover
                                  </button>
                                )
                              )}
                            </>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="text-gray-500 text-sm mb-4">Nenhum participante adicionado.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
