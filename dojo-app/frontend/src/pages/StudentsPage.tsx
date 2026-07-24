import { useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient, useQueries } from '@tanstack/react-query'
import { Plus, Edit, Trash2, Search, TrendingUp, Stethoscope, Wallet, FileSignature, X } from 'lucide-react'
import api from '../services/api'
import { useAuth } from '../hooks/useAuth'
import MedicalExamBadge, { type MedicalExamStatusValue } from '../components/MedicalExamBadge'
import SignaturePad, { type SignaturePadHandle } from '../components/SignaturePad'

type ContractStatusValue = 'draft' | 'signed' | 'superseded'

const CONTRACT_BADGE: Record<ContractStatusValue, { label: string; className: string }> = {
  draft: { label: 'Rascunho', className: 'bg-yellow-100 text-yellow-800' },
  signed: { label: 'Assinado', className: 'bg-green-100 text-green-800' },
  superseded: { label: 'Substituído', className: 'bg-gray-100 text-gray-600' },
}

function ContractBadge({ status }: { status: ContractStatusValue | undefined }) {
  if (!status) return <span className="text-xs text-gray-400">Sem contrato</span>
  const badge = CONTRACT_BADGE[status]
  return (
    <span
      className={`inline-flex px-2 text-xs leading-5 font-semibold rounded-full ${badge.className}`}
    >
      {badge.label}
    </span>
  )
}

type MensalidadeStatusValue = 'open' | 'partial' | 'paid' | 'overdue'

const MENSALIDADE_BADGE: Record<MensalidadeStatusValue, { label: string; className: string }> = {
  open: { label: 'Em aberto', className: 'bg-gray-100 text-gray-700' },
  partial: { label: 'Parcial', className: 'bg-yellow-100 text-yellow-800' },
  paid: { label: 'Pago', className: 'bg-green-100 text-green-800' },
  overdue: { label: 'Vencido', className: 'bg-red-100 text-red-800' },
}

function MensalidadeBadge({ status }: { status: MensalidadeStatusValue }) {
  const badge = MENSALIDADE_BADGE[status]
  return (
    <span
      className={`inline-flex px-2 text-xs leading-5 font-semibold rounded-full ${badge.className}`}
    >
      {badge.label}
    </span>
  )
}

interface Belt {
  id: string
  name: string
  color: string
  order: number
  category?: string
}

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

interface MedicalExamStatus {
  student_id: string
  status: MedicalExamStatusValue
  exam_date: string | null
  expires_at: string | null
}

interface MedicalExamDocument {
  id: string
  mime_type: string
  size_bytes: number
  status: string
  created_at: string
}

interface MedicalExamRecord {
  id: string
  student_id: string
  exam_date: string
  expires_at: string
  status: string
  document: MedicalExamDocument | null
  created_at: string
}

interface PlanVersion {
  id: string
  plan_tier_id: string
  price: string
  status: string
  effective_from: string
}

interface StudentPlan {
  id: string
  student_id: string
  status: string
  started_at: string
  plan_version: PlanVersion
}

interface Mensalidade {
  id: string
  reference_month: string
  due_date: string
  amount: string
  paid_amount: string
  status: MensalidadeStatusValue
}

interface Balance {
  student_id: string
  balance: string
  open_count: number
  overdue_count: number
}

interface ContractDocument {
  id: string
  mime_type: string
  size_bytes: number
  status: string
  created_at: string
}

interface Contract {
  id: string
  student_id: string
  status: ContractStatusValue
  signature_method: 'on_screen' | 'uploaded' | null
  signed_at: string | null
  document: ContractDocument | null
  created_at: string
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
    pin: '' as string | undefined,
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

  const medicalExamStatusQueries = useQueries({
    queries: (students || []).map((student) => ({
      queryKey: ['medical-exam-status', student.id],
      queryFn: async () => {
        const response = await api.get(`/api/v1/medical-exams/students/${student.id}/status`)
        return { studentId: student.id, status: response.data as MedicalExamStatus }
      },
      enabled: !!students,
      staleTime: 30000,
    })),
  })

  const medicalExamStatusMap: Record<string, MedicalExamStatus> = {}
  medicalExamStatusQueries.forEach((q) => {
    if (q.data) {
      medicalExamStatusMap[q.data.studentId] = q.data.status
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

  const [medicalExamStudent, setMedicalExamStudent] = useState<Student | null>(null)
  const [medicalExamForm, setMedicalExamForm] = useState<{ exam_date: string; file: File | null }>({
    exam_date: '',
    file: null,
  })

  const { data: medicalExamHistory } = useQuery<MedicalExamRecord[]>({
    queryKey: ['medical-exam-history', medicalExamStudent?.id],
    queryFn: async () => {
      const response = await api.get(`/api/v1/medical-exams/students/${medicalExamStudent!.id}`)
      return response.data
    },
    enabled: !!medicalExamStudent,
  })

  const recordMedicalExamMutation = useMutation({
    mutationFn: ({
      studentId,
      examDate,
      file,
    }: {
      studentId: string
      examDate: string
      file: File | null
    }) => {
      const body = new FormData()
      body.append('exam_date', examDate)
      if (file) body.append('file', file)
      // The `api` instance defaults to Content-Type: application/json, which would make
      // axios serialize this FormData as JSON instead of a real multipart body. Clearing
      // the header (rather than setting a static string) lets axios/the browser compute
      // the correct `multipart/form-data; boundary=...` value itself.
      return api.post(`/api/v1/medical-exams/students/${studentId}`, body, {
        headers: { 'Content-Type': undefined },
      })
    },
    onSuccess: (_response, variables) => {
      queryClient.invalidateQueries({ queryKey: ['medical-exam-status', variables.studentId] })
      queryClient.invalidateQueries({ queryKey: ['medical-exam-history', variables.studentId] })
      queryClient.invalidateQueries({ queryKey: ['medical-exam-dashboard'] })
      setMedicalExamForm({ exam_date: '', file: null })
    },
  })

  const handleMedicalExamSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!medicalExamStudent) return
    recordMedicalExamMutation.mutate({
      studentId: medicalExamStudent.id,
      examDate: medicalExamForm.exam_date,
      file: medicalExamForm.file,
    })
  }

  const [financeStudent, setFinanceStudent] = useState<Student | null>(null)
  const [paymentForm, setPaymentForm] = useState({ amount: '', payment_date: '', method: '' })

  const { data: studentPlanHistory } = useQuery<StudentPlan[]>({
    queryKey: ['student-plan', financeStudent?.id],
    queryFn: async () => {
      const response = await api.get(`/api/v1/students/${financeStudent!.id}/plan`)
      return response.data
    },
    enabled: !!financeStudent,
  })

  const { data: mensalidades } = useQuery<Mensalidade[]>({
    queryKey: ['student-mensalidades', financeStudent?.id],
    queryFn: async () => {
      const response = await api.get(`/api/v1/students/${financeStudent!.id}/mensalidades`)
      return response.data
    },
    enabled: !!financeStudent,
  })

  const { data: balance } = useQuery<Balance>({
    queryKey: ['student-balance', financeStudent?.id],
    queryFn: async () => {
      const response = await api.get(`/api/v1/students/${financeStudent!.id}/balance`)
      return response.data
    },
    enabled: !!financeStudent,
  })

  const matricularMutation = useMutation({
    mutationFn: (studentId: string) => api.post(`/api/v1/students/${studentId}/contracts/matricular`),
    onSuccess: (_response, studentId) => {
      queryClient.invalidateQueries({ queryKey: ['student-plan', studentId] })
      queryClient.invalidateQueries({ queryKey: ['contract-current', studentId] })
      queryClient.invalidateQueries({ queryKey: ['contract-history', studentId] })
    },
  })

  const recordPaymentMutation = useMutation({
    mutationFn: ({ studentId, data }: { studentId: string; data: typeof paymentForm }) =>
      api.post('/api/v1/payments', { student_id: studentId, ...data }),
    onSuccess: (_response, variables) => {
      queryClient.invalidateQueries({ queryKey: ['student-mensalidades', variables.studentId] })
      queryClient.invalidateQueries({ queryKey: ['student-balance', variables.studentId] })
      setPaymentForm({ amount: '', payment_date: '', method: '' })
    },
  })

  const handlePaymentSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!financeStudent) return
    recordPaymentMutation.mutate({ studentId: financeStudent.id, data: paymentForm })
  }

  const currentStudentPlan = studentPlanHistory?.find((plan) => plan.status === 'active')

  const [contractStudent, setContractStudent] = useState<Student | null>(null)
  const signaturePadRef = useRef<SignaturePadHandle>(null)
  const [uploadFile, setUploadFile] = useState<File | null>(null)

  const { data: currentContract } = useQuery<Contract | null>({
    queryKey: ['contract-current', contractStudent?.id],
    queryFn: async () => {
      try {
        const response = await api.get(`/api/v1/students/${contractStudent!.id}/contracts/current`)
        return response.data
      } catch {
        // No current draft/signed contract for this student yet.
        return null
      }
    },
    enabled: !!contractStudent,
  })

  const { data: contractHistory } = useQuery<Contract[]>({
    queryKey: ['contract-history', contractStudent?.id],
    queryFn: async () => {
      const response = await api.get(`/api/v1/students/${contractStudent!.id}/contracts`)
      return response.data
    },
    enabled: !!contractStudent,
  })

  const invalidateContractQueries = (studentId: string) => {
    queryClient.invalidateQueries({ queryKey: ['contract-current', studentId] })
    queryClient.invalidateQueries({ queryKey: ['contract-history', studentId] })
  }

  const regenerateDraftMutation = useMutation({
    mutationFn: (contractId: string) => api.post(`/api/v1/contracts/${contractId}/regenerate`),
    onSuccess: () => {
      if (contractStudent) invalidateContractQueries(contractStudent.id)
    },
  })

  const signOnScreenMutation = useMutation({
    mutationFn: ({ contractId, signaturePng }: { contractId: string; signaturePng: string }) =>
      api.post(`/api/v1/contracts/${contractId}/sign/on-screen`, { signature_png: signaturePng }),
    onSuccess: () => {
      if (contractStudent) invalidateContractQueries(contractStudent.id)
      signaturePadRef.current?.clear()
    },
  })

  const signByUploadMutation = useMutation({
    mutationFn: ({ contractId, file }: { contractId: string; file: File }) => {
      const body = new FormData()
      body.append('file', file)
      return api.post(`/api/v1/contracts/${contractId}/sign/upload`, body, {
        headers: { 'Content-Type': undefined },
      })
    },
    onSuccess: () => {
      if (contractStudent) invalidateContractQueries(contractStudent.id)
      setUploadFile(null)
    },
  })

  const handleSignOnScreen = () => {
    if (!currentContract || signaturePadRef.current?.isEmpty()) return
    signOnScreenMutation.mutate({
      contractId: currentContract.id,
      signaturePng: signaturePadRef.current!.toDataURL(),
    })
  }

  const handleSignByUpload = () => {
    if (!currentContract || !uploadFile) return
    signByUploadMutation.mutate({ contractId: currentContract.id, file: uploadFile })
  }

  const handleDownloadContract = async (contractId: string) => {
    const response = await api.get(`/api/v1/contracts/${contractId}/download`, { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.download = `contrato-${contractId}.pdf`
    link.click()
    window.URL.revokeObjectURL(url)
  }

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
                {belts?.map((belt: Belt) => (
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
        <div className="overflow-x-auto">
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
                Exame Médico
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Financeiro
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Contrato
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
                        {!progress.next_belt && <TrendingUp className="w-4 h-4 text-green-500" />}
                      </div>
                    ) : (
                      <span className="text-xs text-gray-400">Carregando...</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {student.classes_per_week || '-'}/sem{' '}
                    {student.class_days ? `(${student.class_days})` : ''}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <div className="flex items-center gap-2">
                      <MedicalExamBadge status={medicalExamStatusMap[student.id]?.status} />
                      <button
                        onClick={() => {
                          setMedicalExamStudent(student)
                          setMedicalExamForm({ exam_date: '', file: null })
                        }}
                        title="Exame médico"
                        className="text-gray-500 hover:text-blue-600"
                      >
                        <Stethoscope className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <button
                      onClick={() => {
                        setFinanceStudent(student)
                        setPaymentForm({ amount: '', payment_date: '', method: '' })
                      }}
                      title="Financeiro"
                      className="text-gray-500 hover:text-blue-600"
                    >
                      <Wallet className="w-4 h-4" />
                    </button>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <button
                      onClick={() => {
                        setContractStudent(student)
                        setUploadFile(null)
                      }}
                      title="Contrato"
                      className="text-gray-500 hover:text-blue-600"
                    >
                      <FileSignature className="w-4 h-4" />
                    </button>
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

      {medicalExamStudent && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-40 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-gray-800">
                Exame Médico — {medicalExamStudent.full_name}
              </h3>
              <button
                onClick={() => setMedicalExamStudent(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="mb-4 flex items-center gap-2">
              <span className="text-sm text-gray-600">Status atual:</span>
              <MedicalExamBadge status={medicalExamStatusMap[medicalExamStudent.id]?.status} />
            </div>

            <form onSubmit={handleMedicalExamSubmit} className="grid grid-cols-2 gap-4 mb-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Data do Exame
                </label>
                <input
                  type="date"
                  value={medicalExamForm.exam_date}
                  onChange={(e) =>
                    setMedicalExamForm({ ...medicalExamForm, exam_date: e.target.value })
                  }
                  className="w-full px-3 py-2 border rounded-md"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Arquivo (PDF, JPEG ou PNG, até 10MB)
                </label>
                <input
                  type="file"
                  accept="application/pdf,image/jpeg,image/png"
                  onChange={(e) =>
                    setMedicalExamForm({
                      ...medicalExamForm,
                      file: e.target.files?.[0] || null,
                    })
                  }
                  className="w-full text-sm"
                />
              </div>
              <div className="col-span-2 flex justify-end">
                <button
                  type="submit"
                  disabled={recordMedicalExamMutation.isPending}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-60"
                >
                  {recordMedicalExamMutation.isPending ? 'Enviando...' : 'Registrar'}
                </button>
              </div>
            </form>

            <h4 className="text-sm font-semibold text-gray-700 mb-2">Histórico</h4>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      Data do Exame
                    </th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      Validade
                    </th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      Situação
                    </th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      Documento
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {medicalExamHistory?.length ? (
                    medicalExamHistory.map((record) => (
                      <tr key={record.id}>
                        <td className="px-3 py-2 whitespace-nowrap">
                          {new Date(record.exam_date).toLocaleDateString('pt-BR')}
                        </td>
                        <td className="px-3 py-2 whitespace-nowrap">
                          {new Date(record.expires_at).toLocaleDateString('pt-BR')}
                        </td>
                        <td className="px-3 py-2 whitespace-nowrap">
                          {record.status === 'active' ? 'Ativo' : 'Substituído'}
                        </td>
                        <td className="px-3 py-2 whitespace-nowrap text-gray-500">
                          {record.document
                            ? `${record.document.mime_type} (${Math.round(record.document.size_bytes / 1024)} KB)`
                            : '-'}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={4} className="px-3 py-4 text-center text-gray-400">
                        Nenhum registro encontrado.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {financeStudent && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-40 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-gray-800">
                Financeiro — {financeStudent.full_name}
              </h3>
              <button
                onClick={() => setFinanceStudent(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="mb-4 bg-gray-50 rounded-md p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-semibold text-gray-700">Plano Atual</span>
                <button
                  onClick={() => matricularMutation.mutate(financeStudent.id)}
                  disabled={matricularMutation.isPending}
                  className="px-3 py-1 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-60"
                >
                  {matricularMutation.isPending ? 'Enviando...' : 'Matricular/Renovar (Plano + Contrato)'}
                </button>
              </div>
              {currentStudentPlan ? (
                <p className="text-sm text-gray-600">
                  R$ {currentStudentPlan.plan_version.price} desde{' '}
                  {new Date(currentStudentPlan.started_at).toLocaleDateString('pt-BR')}
                </p>
              ) : (
                <p className="text-sm text-gray-400">Nenhum plano atribuído.</p>
              )}
              {matricularMutation.isError && (
                <p className="text-sm text-red-600 mt-1">
                  Não foi possível matricular/renovar (verifique se existe um plano e um modelo de
                  contrato para as aulas por semana deste aluno).
                </p>
              )}
              {balance && (
                <p className="text-sm text-gray-700 mt-2">
                  Saldo:{' '}
                  <span
                    className={
                      Number(balance.balance) > 0 ? 'text-red-600 font-semibold' : 'text-green-600'
                    }
                  >
                    R$ {balance.balance}
                  </span>{' '}
                  ({balance.overdue_count} vencida(s), {balance.open_count} em aberto)
                </p>
              )}
            </div>

            <h4 className="text-sm font-semibold text-gray-700 mb-2">Registrar Pagamento</h4>
            <form onSubmit={handlePaymentSubmit} className="grid grid-cols-3 gap-4 mb-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Valor (R$)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={paymentForm.amount}
                  onChange={(e) => setPaymentForm({ ...paymentForm, amount: e.target.value })}
                  className="w-full px-3 py-2 border rounded-md"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Data</label>
                <input
                  type="date"
                  value={paymentForm.payment_date}
                  onChange={(e) => setPaymentForm({ ...paymentForm, payment_date: e.target.value })}
                  className="w-full px-3 py-2 border rounded-md"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Forma (opcional)
                </label>
                <input
                  type="text"
                  value={paymentForm.method}
                  onChange={(e) => setPaymentForm({ ...paymentForm, method: e.target.value })}
                  className="w-full px-3 py-2 border rounded-md"
                  placeholder="Ex: PIX, dinheiro"
                />
              </div>
              <div className="col-span-3 flex justify-end">
                <button
                  type="submit"
                  disabled={recordPaymentMutation.isPending}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-60"
                >
                  {recordPaymentMutation.isPending ? 'Enviando...' : 'Registrar Pagamento'}
                </button>
              </div>
            </form>

            <h4 className="text-sm font-semibold text-gray-700 mb-2">Mensalidades</h4>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      Referência
                    </th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      Vencimento
                    </th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      Valor
                    </th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      Pago
                    </th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      Situação
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {mensalidades?.length ? (
                    mensalidades.map((mensalidade) => (
                      <tr key={mensalidade.id}>
                        <td className="px-3 py-2 whitespace-nowrap">
                          {new Date(mensalidade.reference_month).toLocaleDateString('pt-BR', {
                            month: '2-digit',
                            year: 'numeric',
                          })}
                        </td>
                        <td className="px-3 py-2 whitespace-nowrap">
                          {new Date(mensalidade.due_date).toLocaleDateString('pt-BR')}
                        </td>
                        <td className="px-3 py-2 whitespace-nowrap">R$ {mensalidade.amount}</td>
                        <td className="px-3 py-2 whitespace-nowrap">
                          R$ {mensalidade.paid_amount}
                        </td>
                        <td className="px-3 py-2 whitespace-nowrap">
                          <MensalidadeBadge status={mensalidade.status} />
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={5} className="px-3 py-4 text-center text-gray-400">
                        Nenhuma mensalidade encontrada.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {contractStudent && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-40 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-gray-800">
                Contrato — {contractStudent.full_name}
              </h3>
              <button
                onClick={() => setContractStudent(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="mb-4 flex items-center justify-between bg-gray-50 rounded-md p-4">
              <div className="flex flex-col gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-600">Status atual:</span>
                  <ContractBadge status={currentContract?.status} />
                </div>
              </div>
              <button
                onClick={() => matricularMutation.mutate(contractStudent.id)}
                disabled={matricularMutation.isPending}
                className="px-3 py-1 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-60"
              >
                {matricularMutation.isPending ? 'Enviando...' : 'Matricular/Renovar'}
              </button>
            </div>

            {currentContract?.status === 'draft' && (
              <div className="mb-6 space-y-4">
                <div>
                  <button
                    onClick={() => regenerateDraftMutation.mutate(currentContract.id)}
                    disabled={regenerateDraftMutation.isPending}
                    className="px-3 py-1 text-sm border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-60"
                  >
                    {regenerateDraftMutation.isPending ? 'Regenerando...' : 'Regenerar Rascunho'}
                  </button>
                </div>

                <div>
                  <h4 className="text-sm font-semibold text-gray-700 mb-2">
                    Assinar na Tela
                  </h4>
                  <SignaturePad ref={signaturePadRef} />
                  <div className="flex gap-2 mt-2">
                    <button
                      onClick={() => signaturePadRef.current?.clear()}
                      className="px-3 py-1 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
                    >
                      Limpar
                    </button>
                    <button
                      onClick={handleSignOnScreen}
                      disabled={signOnScreenMutation.isPending}
                      className="px-3 py-1 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-60"
                    >
                      {signOnScreenMutation.isPending ? 'Enviando...' : 'Assinar'}
                    </button>
                  </div>
                </div>

                <div>
                  <h4 className="text-sm font-semibold text-gray-700 mb-2">
                    Ou Enviar Contrato Assinado (PDF, JPEG ou PNG, até 10MB)
                  </h4>
                  <div className="flex gap-2">
                    <input
                      type="file"
                      accept="application/pdf,image/jpeg,image/png"
                      onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                      className="text-sm"
                    />
                    <button
                      onClick={handleSignByUpload}
                      disabled={!uploadFile || signByUploadMutation.isPending}
                      className="px-3 py-1 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-60"
                    >
                      {signByUploadMutation.isPending ? 'Enviando...' : 'Enviar'}
                    </button>
                  </div>
                </div>
              </div>
            )}

            {currentContract?.document && (
              <div className="mb-6">
                <button
                  onClick={() => handleDownloadContract(currentContract.id)}
                  className="px-3 py-1 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
                >
                  Baixar Contrato Atual
                </button>
              </div>
            )}

            <h4 className="text-sm font-semibold text-gray-700 mb-2">Histórico</h4>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      Criado em
                    </th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      Situação
                    </th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      Assinatura
                    </th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      Documento
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {contractHistory?.length ? (
                    contractHistory.map((contract) => (
                      <tr key={contract.id}>
                        <td className="px-3 py-2 whitespace-nowrap">
                          {new Date(contract.created_at).toLocaleDateString('pt-BR')}
                        </td>
                        <td className="px-3 py-2 whitespace-nowrap">
                          <ContractBadge status={contract.status} />
                        </td>
                        <td className="px-3 py-2 whitespace-nowrap text-gray-500">
                          {contract.signature_method === 'on_screen'
                            ? 'Na tela'
                            : contract.signature_method === 'uploaded'
                              ? 'Upload'
                              : '-'}
                        </td>
                        <td className="px-3 py-2 whitespace-nowrap text-gray-500">
                          {contract.document
                            ? `${contract.document.mime_type} (${Math.round(contract.document.size_bytes / 1024)} KB)`
                            : '-'}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={4} className="px-3 py-4 text-center text-gray-400">
                        Nenhum contrato encontrado.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
