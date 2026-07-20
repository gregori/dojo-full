import { useQuery } from '@tanstack/react-query'
import { Users, Calendar, Award } from 'lucide-react'
import api from '../services/api'
import MedicalExamBadge, { type MedicalExamStatusValue } from '../components/MedicalExamBadge'

interface MedicalExamDashboardItem {
  student_id: string
  student_name: string
  registration_number: string
  status: MedicalExamStatusValue
  exam_date: string | null
  expires_at: string | null
}

export default function DashboardPage() {
  const { data: stats } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: async () => {
      const [students, events, exams] = await Promise.all([
        api.get('/api/v1/students?limit=1'),
        api.get('/api/v1/events?limit=1'),
        api.get('/api/v1/exams?limit=1'),
      ])
      return {
        totalStudents: students.data.length || 0,
        totalEvents: events.data.length || 0,
        totalExams: exams.data.length || 0,
      }
    },
  })

  const { data: medicalExamAlerts } = useQuery<MedicalExamDashboardItem[]>({
    queryKey: ['medical-exam-dashboard'],
    queryFn: async () => {
      const response = await api.get('/api/v1/medical-exams/dashboard')
      return response.data
    },
  })

  const cards = [
    {
      title: 'Total de Alunos',
      value: stats?.totalStudents || 0,
      icon: Users,
      color: 'bg-blue-500',
    },
    {
      title: 'Eventos Realizados',
      value: stats?.totalEvents || 0,
      icon: Calendar,
      color: 'bg-green-500',
    },
    {
      title: 'Exames Realizados',
      value: stats?.totalExams || 0,
      icon: Award,
      color: 'bg-purple-500',
    },
  ]

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Dashboard</h2>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {cards.map((card) => {
          const Icon = card.icon
          return (
            <div key={card.title} className="bg-white p-6 rounded-lg shadow">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">{card.title}</p>
                  <p className="text-3xl font-bold text-gray-800 mt-1">{card.value}</p>
                </div>
                <div className={`${card.color} p-3 rounded-lg`}>
                  <Icon className="w-6 h-6 text-white" />
                </div>
              </div>
            </div>
          )
        })}
      </div>

      <div className="bg-white rounded-lg shadow p-6 mb-8">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">
          Exames Médicos Vencendo/Vencidos
        </h3>
        {medicalExamAlerts && medicalExamAlerts.length > 0 ? (
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Aluno
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Matrícula
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Validade
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Situação
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {medicalExamAlerts.map((item) => (
                <tr key={item.student_id}>
                  <td className="px-4 py-2 whitespace-nowrap text-gray-900">{item.student_name}</td>
                  <td className="px-4 py-2 whitespace-nowrap text-gray-500">
                    {item.registration_number}
                  </td>
                  <td className="px-4 py-2 whitespace-nowrap text-gray-500">
                    {item.expires_at ? new Date(item.expires_at).toLocaleDateString('pt-BR') : '-'}
                  </td>
                  <td className="px-4 py-2 whitespace-nowrap">
                    <MedicalExamBadge status={item.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="text-gray-500 text-center py-8">
            Nenhum exame médico vencendo ou vencido.
          </div>
        )}
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">Próximos Eventos</h3>
        <div className="text-gray-500 text-center py-8">Em breve: lista de próximos eventos</div>
      </div>
    </div>
  )
}
