import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Download, FileText } from 'lucide-react'
import api from '../services/api'

interface StudentOption {
  id: string
  full_name: string
  registration_number: string
}

interface EventTypeOption {
  id: string
  name: string
}

interface BeltExamParticipation {
  exam_id: string
  exam_date: string
  target_belt_name: string
  role: string
  status: string
  override_eligibility: boolean
  override_reason: string | null
  promoted_at: string | null
  promoted_belt_name: string | null
}

interface BeltExamReport {
  student_id: string
  student_name: string
  participations: BeltExamParticipation[]
}

interface AttendanceItem {
  event_title: string
  event_type_name: string
  check_in_at: string
  check_in_method: string
}

interface StudentAttendanceReport {
  student_id: string
  student_name: string
  total_attendances: number
  attendances: AttendanceItem[]
}

interface ClassEventCount {
  event_id: string
  event_title: string
  start_datetime: string
  attendance_count: number
}

interface ClassRosterItem {
  student_id: string
  student_name: string
  total_attendances: number
}

interface ClassAttendanceReport {
  event_type_id: string
  event_type_name: string
  events: ClassEventCount[]
  roster: ClassRosterItem[]
}

interface FinancialPaymentItem {
  id: string
  student_id: string
  student_name: string
  amount: string
  payment_date: string
  method: string | null
}

interface OverdueDashboardItem {
  student_id: string
  student_name: string
  registration_number: string
  amount_owed: string
  open_count: number
  overdue_count: number
  oldest_overdue_due_date: string | null
  medical_exam_status: string
}

interface FinancialProjection {
  monthly_total: string
  months_ahead: number
  projected_total: string
}

interface FinancialReport {
  payments: FinancialPaymentItem[]
  delinquency: OverdueDashboardItem[]
  projection: FinancialProjection
}

function downloadBlob(data: BlobPart, filename: string) {
  const url = window.URL.createObjectURL(new Blob([data]))
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  window.URL.revokeObjectURL(url)
}

async function exportReport(endpoint: string, format: 'pdf' | 'csv', filenameStem: string) {
  const response = await api.get(endpoint, {
    params: { format },
    responseType: 'blob',
  })
  downloadBlob(response.data, `${filenameStem}.${format}`)
}

function ExportButtons({ onExport }: { onExport: (format: 'pdf' | 'csv') => void }) {
  return (
    <div className="flex gap-2">
      <button
        type="button"
        onClick={() => onExport('pdf')}
        className="flex items-center px-3 py-1.5 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
      >
        <Download className="w-4 h-4 mr-1" />
        Exportar PDF
      </button>
      <button
        type="button"
        onClick={() => onExport('csv')}
        className="flex items-center px-3 py-1.5 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
      >
        <Download className="w-4 h-4 mr-1" />
        Exportar CSV
      </button>
    </div>
  )
}

export default function ReportsPage() {
  const { data: students } = useQuery<StudentOption[]>({
    queryKey: ['students-for-reports'],
    queryFn: async () => {
      const response = await api.get('/api/v1/students?is_active=true')
      return response.data
    },
  })

  const { data: eventTypes } = useQuery<EventTypeOption[]>({
    queryKey: ['event-types-for-reports'],
    queryFn: async () => {
      const response = await api.get('/api/v1/events/types')
      return response.data
    },
  })

  // Section 1: Exame de Faixa
  const [examStudentId, setExamStudentId] = useState('')
  const [examReport, setExamReport] = useState<BeltExamReport | null>(null)

  const viewExamReport = async () => {
    if (!examStudentId) return
    const response = await api.get<BeltExamReport>(`/api/v1/reports/belt-exams/${examStudentId}`)
    setExamReport(response.data)
  }

  const exportExamReport = (format: 'pdf' | 'csv') =>
    exportReport(
      `/api/v1/reports/belt-exams/${examStudentId}`,
      format,
      `exame-faixa-${examStudentId}`
    )

  // Section 2: Presenças (Aluno)
  const [attStudentId, setAttStudentId] = useState('')
  const [attStartDate, setAttStartDate] = useState('')
  const [attEndDate, setAttEndDate] = useState('')
  const [attReport, setAttReport] = useState<StudentAttendanceReport | null>(null)

  const attParams = () => ({
    ...(attStartDate ? { start_date: attStartDate } : {}),
    ...(attEndDate ? { end_date: attEndDate } : {}),
  })

  const viewAttReport = async () => {
    if (!attStudentId) return
    const response = await api.get<StudentAttendanceReport>(
      `/api/v1/reports/attendance/student/${attStudentId}`,
      { params: attParams() }
    )
    setAttReport(response.data)
  }

  const exportAttReport = async (format: 'pdf' | 'csv') => {
    const response = await api.get(`/api/v1/reports/attendance/student/${attStudentId}`, {
      params: { ...attParams(), format },
      responseType: 'blob',
    })
    downloadBlob(response.data, `presencas-aluno-${attStudentId}.${format}`)
  }

  // Section 3: Presenças (Turma)
  const [classEventTypeId, setClassEventTypeId] = useState('')
  const [classStartDate, setClassStartDate] = useState('')
  const [classEndDate, setClassEndDate] = useState('')
  const [classReport, setClassReport] = useState<ClassAttendanceReport | null>(null)

  const classParams = () => ({
    event_type_id: classEventTypeId,
    ...(classStartDate ? { start_date: classStartDate } : {}),
    ...(classEndDate ? { end_date: classEndDate } : {}),
  })

  const viewClassReport = async () => {
    if (!classEventTypeId) return
    const response = await api.get<ClassAttendanceReport>('/api/v1/reports/attendance/class', {
      params: classParams(),
    })
    setClassReport(response.data)
  }

  const exportClassReport = async (format: 'pdf' | 'csv') => {
    const response = await api.get('/api/v1/reports/attendance/class', {
      params: { ...classParams(), format },
      responseType: 'blob',
    })
    downloadBlob(response.data, `presencas-turma-${classEventTypeId}.${format}`)
  }

  // Section 4: Financeiro
  const [finStartDate, setFinStartDate] = useState('')
  const [finEndDate, setFinEndDate] = useState('')
  const [finMonthsAhead, setFinMonthsAhead] = useState(3)
  const [finReport, setFinReport] = useState<FinancialReport | null>(null)

  const finParams = () => ({
    ...(finStartDate ? { start_date: finStartDate } : {}),
    ...(finEndDate ? { end_date: finEndDate } : {}),
    months_ahead: finMonthsAhead,
  })

  const viewFinReport = async () => {
    const response = await api.get<FinancialReport>('/api/v1/reports/finance', {
      params: finParams(),
    })
    setFinReport(response.data)
  }

  const exportFinReport = async (format: 'pdf' | 'csv') => {
    const response = await api.get('/api/v1/reports/finance', {
      params: { ...finParams(), format },
      responseType: 'blob',
    })
    downloadBlob(response.data, `relatorio-financeiro.${format}`)
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center mb-2">
        <FileText className="w-6 h-6 mr-2 text-gray-700" />
        <h2 className="text-2xl font-bold text-gray-800">Relatórios</h2>
      </div>

      {/* Exame de Faixa */}
      <section className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">Exame de Faixa</h3>
        <div className="flex flex-wrap items-end gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Aluno</label>
            <select
              value={examStudentId}
              onChange={(e) => setExamStudentId(e.target.value)}
              className="px-3 py-2 border rounded-md min-w-[220px]"
            >
              <option value="">Selecione...</option>
              {students?.map((student) => (
                <option key={student.id} value={student.id}>
                  {student.full_name} ({student.registration_number})
                </option>
              ))}
            </select>
          </div>
          <button
            type="button"
            onClick={viewExamReport}
            disabled={!examStudentId}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            Visualizar
          </button>
          {examReport && <ExportButtons onExport={exportExamReport} />}
        </div>

        {examReport && (
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Data
                </th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Faixa Alvo
                </th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Papel
                </th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Status
                </th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Faixa Promovida
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {examReport.participations.length ? (
                examReport.participations.map((participation) => (
                  <tr key={participation.exam_id}>
                    <td className="px-3 py-2">
                      {new Date(participation.exam_date).toLocaleDateString('pt-BR')}
                    </td>
                    <td className="px-3 py-2">{participation.target_belt_name}</td>
                    <td className="px-3 py-2">{participation.role}</td>
                    <td className="px-3 py-2">{participation.status}</td>
                    <td className="px-3 py-2">{participation.promoted_belt_name || '-'}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="px-3 py-4 text-center text-gray-400">
                    Nenhuma participação em exame encontrada.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </section>

      {/* Presenças (Aluno) */}
      <section className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">Presenças (Aluno)</h3>
        <div className="flex flex-wrap items-end gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Aluno</label>
            <select
              value={attStudentId}
              onChange={(e) => setAttStudentId(e.target.value)}
              className="px-3 py-2 border rounded-md min-w-[220px]"
            >
              <option value="">Selecione...</option>
              {students?.map((student) => (
                <option key={student.id} value={student.id}>
                  {student.full_name} ({student.registration_number})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Data Inicial</label>
            <input
              type="date"
              value={attStartDate}
              onChange={(e) => setAttStartDate(e.target.value)}
              className="px-3 py-2 border rounded-md"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Data Final</label>
            <input
              type="date"
              value={attEndDate}
              onChange={(e) => setAttEndDate(e.target.value)}
              className="px-3 py-2 border rounded-md"
            />
          </div>
          <button
            type="button"
            onClick={viewAttReport}
            disabled={!attStudentId}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            Visualizar
          </button>
          {attReport && <ExportButtons onExport={exportAttReport} />}
        </div>

        {attReport && (
          <>
            <p className="text-sm text-gray-600 mb-2">
              Total de presenças: <strong>{attReport.total_attendances}</strong>
            </p>
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Evento
                  </th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Tipo
                  </th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Data/Hora
                  </th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Método
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {attReport.attendances.length ? (
                  attReport.attendances.map((attendance, index) => (
                    <tr key={index}>
                      <td className="px-3 py-2">{attendance.event_title}</td>
                      <td className="px-3 py-2">{attendance.event_type_name}</td>
                      <td className="px-3 py-2">
                        {new Date(attendance.check_in_at).toLocaleString('pt-BR')}
                      </td>
                      <td className="px-3 py-2">{attendance.check_in_method}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={4} className="px-3 py-4 text-center text-gray-400">
                      Nenhuma presença encontrada no período.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </>
        )}
      </section>

      {/* Presenças (Turma) */}
      <section className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">Presenças (Turma)</h3>
        <div className="flex flex-wrap items-end gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de Evento</label>
            <select
              value={classEventTypeId}
              onChange={(e) => setClassEventTypeId(e.target.value)}
              className="px-3 py-2 border rounded-md min-w-[220px]"
            >
              <option value="">Selecione...</option>
              {eventTypes?.map((eventType) => (
                <option key={eventType.id} value={eventType.id}>
                  {eventType.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Data Inicial</label>
            <input
              type="date"
              value={classStartDate}
              onChange={(e) => setClassStartDate(e.target.value)}
              className="px-3 py-2 border rounded-md"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Data Final</label>
            <input
              type="date"
              value={classEndDate}
              onChange={(e) => setClassEndDate(e.target.value)}
              className="px-3 py-2 border rounded-md"
            />
          </div>
          <button
            type="button"
            onClick={viewClassReport}
            disabled={!classEventTypeId}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            Visualizar
          </button>
          {classReport && <ExportButtons onExport={exportClassReport} />}
        </div>

        {classReport && (
          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Eventos</h4>
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      Evento
                    </th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      Presenças
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {classReport.events.length ? (
                    classReport.events.map((event) => (
                      <tr key={event.event_id}>
                        <td className="px-3 py-2">{event.event_title}</td>
                        <td className="px-3 py-2">{event.attendance_count}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={2} className="px-3 py-4 text-center text-gray-400">
                        Nenhum evento no período.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Roster</h4>
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      Aluno
                    </th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      Total de Presenças
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {classReport.roster.length ? (
                    classReport.roster.map((rosterItem) => (
                      <tr key={rosterItem.student_id}>
                        <td className="px-3 py-2">{rosterItem.student_name}</td>
                        <td className="px-3 py-2">{rosterItem.total_attendances}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={2} className="px-3 py-4 text-center text-gray-400">
                        Nenhum aluno com presença no período.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>

      {/* Financeiro */}
      <section className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">Financeiro</h3>
        <div className="flex flex-wrap items-end gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Data Inicial</label>
            <input
              type="date"
              value={finStartDate}
              onChange={(e) => setFinStartDate(e.target.value)}
              className="px-3 py-2 border rounded-md"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Data Final</label>
            <input
              type="date"
              value={finEndDate}
              onChange={(e) => setFinEndDate(e.target.value)}
              className="px-3 py-2 border rounded-md"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Meses de Projeção
            </label>
            <input
              type="number"
              min={1}
              value={finMonthsAhead}
              onChange={(e) => setFinMonthsAhead(parseInt(e.target.value) || 1)}
              className="px-3 py-2 border rounded-md w-28"
            />
          </div>
          <button
            type="button"
            onClick={viewFinReport}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Visualizar
          </button>
          {finReport && <ExportButtons onExport={exportFinReport} />}
        </div>

        {finReport && (
          <div className="space-y-6">
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Pagamentos</h4>
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      Aluno
                    </th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      Valor
                    </th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      Data
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {finReport.payments.length ? (
                    finReport.payments.map((payment) => (
                      <tr key={payment.id}>
                        <td className="px-3 py-2">{payment.student_name}</td>
                        <td className="px-3 py-2">R$ {payment.amount}</td>
                        <td className="px-3 py-2">
                          {new Date(payment.payment_date).toLocaleDateString('pt-BR')}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={3} className="px-3 py-4 text-center text-gray-400">
                        Nenhum pagamento no período.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Inadimplência</h4>
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      Aluno
                    </th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      Valor Devido
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {finReport.delinquency.length ? (
                    finReport.delinquency.map((item) => (
                      <tr key={item.student_id}>
                        <td className="px-3 py-2">{item.student_name}</td>
                        <td className="px-3 py-2">R$ {item.amount_owed}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={2} className="px-3 py-4 text-center text-gray-400">
                        Nenhum aluno inadimplente.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Projeção</h4>
              <p className="text-sm text-gray-600">
                Total mensal: <strong>R$ {finReport.projection.monthly_total}</strong> ×{' '}
                {finReport.projection.months_ahead} meses ={' '}
                <strong>R$ {finReport.projection.projected_total}</strong>
              </p>
            </div>
          </div>
        )}
      </section>
    </div>
  )
}
