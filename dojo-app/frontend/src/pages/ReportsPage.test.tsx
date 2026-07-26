import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ReportsPage from './ReportsPage'
import api from '../services/api'

jest.mock('../services/api', () => ({
  __esModule: true,
  default: { get: jest.fn() },
}))

const mockedGet = api.get as jest.Mock

const STUDENTS = [{ id: 'student-1', full_name: 'Fulano', registration_number: '001' }]
const EVENT_TYPES = [{ id: 'et-1', name: 'Regular' }]

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <ReportsPage />
    </QueryClientProvider>
  )
}

function getSection(headingName: string): HTMLElement {
  const heading = screen.getByRole('heading', { name: headingName })
  return heading.closest('section') as HTMLElement
}

describe('ReportsPage', () => {
  beforeEach(() => {
    mockedGet.mockReset()
    window.URL.createObjectURL = jest.fn(() => 'blob:mock-url')
    window.URL.revokeObjectURL = jest.fn()
  })

  describe('Exame de Faixa section', () => {
    it('fetches and renders the belt-exam report for the selected student', async () => {
      mockedGet.mockImplementation((url: string) => {
        if (url === '/api/v1/students?is_active=true') return Promise.resolve({ data: STUDENTS })
        if (url === '/api/v1/events/types') return Promise.resolve({ data: EVENT_TYPES })
        if (url === '/api/v1/reports/belt-exams/student-1') {
          return Promise.resolve({
            data: {
              student_id: 'student-1',
              student_name: 'Fulano',
              participations: [
                {
                  exam_id: 'exam-1',
                  exam_date: '2026-01-10T00:00:00Z',
                  target_belt_name: 'Faixa Azul',
                  role: 'candidate',
                  status: 'approved',
                  override_eligibility: false,
                  override_reason: null,
                  promoted_at: '2026-01-11T00:00:00Z',
                  promoted_belt_name: 'Faixa Azul',
                },
              ],
            },
          })
        }
        return Promise.reject(new Error(`Unhandled GET ${url}`))
      })
      const user = userEvent.setup()
      renderPage()
      const section = getSection('Exame de Faixa')
      await within(section).findByText('Fulano (001)')

      await user.selectOptions(within(section).getByRole('combobox'), 'student-1')
      await user.click(within(section).getByText('Visualizar'))

      expect(await within(section).findByText('approved')).toBeInTheDocument()
      expect(within(section).getAllByText('Faixa Azul')).toHaveLength(2)
      await waitFor(() =>
        expect(mockedGet).toHaveBeenCalledWith('/api/v1/reports/belt-exams/student-1')
      )
    })

    it('renders the empty state when the student has no exam participations', async () => {
      mockedGet.mockImplementation((url: string) => {
        if (url === '/api/v1/students?is_active=true') return Promise.resolve({ data: STUDENTS })
        if (url === '/api/v1/events/types') return Promise.resolve({ data: EVENT_TYPES })
        if (url === '/api/v1/reports/belt-exams/student-1') {
          return Promise.resolve({
            data: { student_id: 'student-1', student_name: 'Fulano', participations: [] },
          })
        }
        return Promise.reject(new Error(`Unhandled GET ${url}`))
      })
      const user = userEvent.setup()
      renderPage()
      const section = getSection('Exame de Faixa')
      await within(section).findByText('Fulano (001)')

      await user.selectOptions(within(section).getByRole('combobox'), 'student-1')
      await user.click(within(section).getByText('Visualizar'))

      expect(
        await within(section).findByText('Nenhuma participação em exame encontrada.')
      ).toBeInTheDocument()
    })

    it('exports the report as a PDF blob download', async () => {
      mockedGet.mockImplementation((url: string, config?: { responseType?: string }) => {
        if (url === '/api/v1/students?is_active=true') return Promise.resolve({ data: STUDENTS })
        if (url === '/api/v1/events/types') return Promise.resolve({ data: EVENT_TYPES })
        if (url === '/api/v1/reports/belt-exams/student-1' && config?.responseType === 'blob') {
          return Promise.resolve({ data: new Blob(['%PDF-']) })
        }
        if (url === '/api/v1/reports/belt-exams/student-1') {
          return Promise.resolve({
            data: { student_id: 'student-1', student_name: 'Fulano', participations: [] },
          })
        }
        return Promise.reject(new Error(`Unhandled GET ${url}`))
      })
      const user = userEvent.setup()
      renderPage()
      const section = getSection('Exame de Faixa')
      await within(section).findByText('Fulano (001)')
      await user.selectOptions(within(section).getByRole('combobox'), 'student-1')
      await user.click(within(section).getByText('Visualizar'))
      await within(section).findByText('Nenhuma participação em exame encontrada.')

      await user.click(within(section).getByText('Exportar PDF'))

      await waitFor(() =>
        expect(mockedGet).toHaveBeenCalledWith('/api/v1/reports/belt-exams/student-1', {
          params: { format: 'pdf' },
          responseType: 'blob',
        })
      )
    })
  })

  describe('Presenças (Aluno) section', () => {
    it('fetches and renders the student attendance report, including the total count', async () => {
      mockedGet.mockImplementation((url: string) => {
        if (url === '/api/v1/students?is_active=true') return Promise.resolve({ data: STUDENTS })
        if (url === '/api/v1/events/types') return Promise.resolve({ data: EVENT_TYPES })
        if (url === '/api/v1/reports/attendance/student/student-1') {
          return Promise.resolve({
            data: {
              student_id: 'student-1',
              student_name: 'Fulano',
              total_attendances: 2,
              attendances: [
                {
                  event_title: 'Aula de Terça',
                  event_type_name: 'Regular',
                  check_in_at: '2026-01-10T10:00:00Z',
                  check_in_method: 'tablet',
                },
              ],
            },
          })
        }
        return Promise.reject(new Error(`Unhandled GET ${url}`))
      })
      const user = userEvent.setup()
      renderPage()
      const section = getSection('Presenças (Aluno)')
      await within(section).findByText('Fulano (001)')

      await user.selectOptions(within(section).getByRole('combobox'), 'student-1')
      await user.click(within(section).getByText('Visualizar'))

      expect(await within(section).findByText('2')).toBeInTheDocument()
      expect(within(section).getByText('Aula de Terça')).toBeInTheDocument()
    })

    it('renders the empty state when there are no attendances in range', async () => {
      mockedGet.mockImplementation((url: string) => {
        if (url === '/api/v1/students?is_active=true') return Promise.resolve({ data: STUDENTS })
        if (url === '/api/v1/events/types') return Promise.resolve({ data: EVENT_TYPES })
        if (url === '/api/v1/reports/attendance/student/student-1') {
          return Promise.resolve({
            data: {
              student_id: 'student-1',
              student_name: 'Fulano',
              total_attendances: 0,
              attendances: [],
            },
          })
        }
        return Promise.reject(new Error(`Unhandled GET ${url}`))
      })
      const user = userEvent.setup()
      renderPage()
      const section = getSection('Presenças (Aluno)')
      await within(section).findByText('Fulano (001)')

      await user.selectOptions(within(section).getByRole('combobox'), 'student-1')
      await user.click(within(section).getByText('Visualizar'))

      expect(
        await within(section).findByText('Nenhuma presença encontrada no período.')
      ).toBeInTheDocument()
    })

    it('exports the report as a CSV blob download', async () => {
      mockedGet.mockImplementation((url: string, config?: { responseType?: string }) => {
        if (url === '/api/v1/students?is_active=true') return Promise.resolve({ data: STUDENTS })
        if (url === '/api/v1/events/types') return Promise.resolve({ data: EVENT_TYPES })
        if (
          url === '/api/v1/reports/attendance/student/student-1' &&
          config?.responseType === 'blob'
        ) {
          return Promise.resolve({ data: new Blob(['Evento,Data']) })
        }
        if (url === '/api/v1/reports/attendance/student/student-1') {
          return Promise.resolve({
            data: {
              student_id: 'student-1',
              student_name: 'Fulano',
              total_attendances: 0,
              attendances: [],
            },
          })
        }
        return Promise.reject(new Error(`Unhandled GET ${url}`))
      })
      const user = userEvent.setup()
      renderPage()
      const section = getSection('Presenças (Aluno)')
      await within(section).findByText('Fulano (001)')
      await user.selectOptions(within(section).getByRole('combobox'), 'student-1')
      await user.click(within(section).getByText('Visualizar'))
      await within(section).findByText('Nenhuma presença encontrada no período.')

      await user.click(within(section).getByText('Exportar CSV'))

      await waitFor(() =>
        expect(mockedGet).toHaveBeenCalledWith('/api/v1/reports/attendance/student/student-1', {
          params: { format: 'csv' },
          responseType: 'blob',
        })
      )
    })
  })

  describe('Presenças (Turma) section', () => {
    it('fetches and renders per-event counts and the roster', async () => {
      mockedGet.mockImplementation((url: string) => {
        if (url === '/api/v1/students?is_active=true') return Promise.resolve({ data: STUDENTS })
        if (url === '/api/v1/events/types') return Promise.resolve({ data: EVENT_TYPES })
        if (url === '/api/v1/reports/attendance/class') {
          return Promise.resolve({
            data: {
              event_type_id: 'et-1',
              event_type_name: 'Regular',
              events: [
                {
                  event_id: 'event-1',
                  event_title: 'Aula 1',
                  start_datetime: '2026-01-10T10:00:00Z',
                  attendance_count: 3,
                },
              ],
              roster: [{ student_id: 'student-1', student_name: 'Fulano', total_attendances: 3 }],
            },
          })
        }
        return Promise.reject(new Error(`Unhandled GET ${url}`))
      })
      const user = userEvent.setup()
      renderPage()
      const section = getSection('Presenças (Turma)')
      await within(section).findByText('Regular')

      await user.selectOptions(within(section).getByRole('combobox'), 'et-1')
      await user.click(within(section).getByText('Visualizar'))

      expect(await within(section).findByText('Aula 1')).toBeInTheDocument()
      expect(within(section).getByText('Fulano')).toBeInTheDocument()
    })

    it('renders the empty state when there is no attendance in range', async () => {
      mockedGet.mockImplementation((url: string) => {
        if (url === '/api/v1/students?is_active=true') return Promise.resolve({ data: STUDENTS })
        if (url === '/api/v1/events/types') return Promise.resolve({ data: EVENT_TYPES })
        if (url === '/api/v1/reports/attendance/class') {
          return Promise.resolve({
            data: { event_type_id: 'et-1', event_type_name: 'Regular', events: [], roster: [] },
          })
        }
        return Promise.reject(new Error(`Unhandled GET ${url}`))
      })
      const user = userEvent.setup()
      renderPage()
      const section = getSection('Presenças (Turma)')
      await within(section).findByText('Regular')

      await user.selectOptions(within(section).getByRole('combobox'), 'et-1')
      await user.click(within(section).getByText('Visualizar'))

      expect(await within(section).findByText('Nenhum evento no período.')).toBeInTheDocument()
      expect(within(section).getByText('Nenhum aluno com presença no período.')).toBeInTheDocument()
    })
  })

  describe('Financeiro section', () => {
    it('fetches and renders the three financial sub-tables', async () => {
      mockedGet.mockImplementation((url: string) => {
        if (url === '/api/v1/students?is_active=true') return Promise.resolve({ data: STUDENTS })
        if (url === '/api/v1/events/types') return Promise.resolve({ data: EVENT_TYPES })
        if (url === '/api/v1/reports/finance') {
          return Promise.resolve({
            data: {
              payments: [
                {
                  id: 'payment-1',
                  student_id: 'student-1',
                  student_name: 'Fulano',
                  amount: '150.00',
                  payment_date: '2026-01-05T00:00:00Z',
                  method: 'pix',
                },
              ],
              delinquency: [
                {
                  student_id: 'student-2',
                  student_name: 'Beltrano',
                  registration_number: '002',
                  amount_owed: '50.00',
                  open_count: 1,
                  overdue_count: 1,
                  oldest_overdue_due_date: '2026-01-05T00:00:00Z',
                  medical_exam_status: 'valido',
                },
              ],
              projection: { monthly_total: '150.00', months_ahead: 3, projected_total: '450.00' },
            },
          })
        }
        return Promise.reject(new Error(`Unhandled GET ${url}`))
      })
      const user = userEvent.setup()
      renderPage()
      const section = getSection('Financeiro')

      await user.click(within(section).getByText('Visualizar'))

      expect(await within(section).findByText('Fulano')).toBeInTheDocument()
      expect(within(section).getByText('Beltrano')).toBeInTheDocument()
      expect(within(section).getByText(/R\$ 450.00/)).toBeInTheDocument()
    })

    it('renders empty sections and a zero projection when there is no qualifying data', async () => {
      mockedGet.mockImplementation((url: string) => {
        if (url === '/api/v1/students?is_active=true') return Promise.resolve({ data: STUDENTS })
        if (url === '/api/v1/events/types') return Promise.resolve({ data: EVENT_TYPES })
        if (url === '/api/v1/reports/finance') {
          return Promise.resolve({
            data: {
              payments: [],
              delinquency: [],
              projection: { monthly_total: '0', months_ahead: 3, projected_total: '0' },
            },
          })
        }
        return Promise.reject(new Error(`Unhandled GET ${url}`))
      })
      const user = userEvent.setup()
      renderPage()
      const section = getSection('Financeiro')

      await user.click(within(section).getByText('Visualizar'))

      expect(await within(section).findByText('Nenhum pagamento no período.')).toBeInTheDocument()
      expect(within(section).getByText('Nenhum aluno inadimplente.')).toBeInTheDocument()
    })

    it('exports the report as a PDF blob download with the months_ahead filter', async () => {
      mockedGet.mockImplementation((url: string, config?: { responseType?: string }) => {
        if (url === '/api/v1/students?is_active=true') return Promise.resolve({ data: STUDENTS })
        if (url === '/api/v1/events/types') return Promise.resolve({ data: EVENT_TYPES })
        if (url === '/api/v1/reports/finance' && config?.responseType === 'blob') {
          return Promise.resolve({ data: new Blob(['%PDF-']) })
        }
        if (url === '/api/v1/reports/finance') {
          return Promise.resolve({
            data: {
              payments: [],
              delinquency: [],
              projection: { monthly_total: '0', months_ahead: 3, projected_total: '0' },
            },
          })
        }
        return Promise.reject(new Error(`Unhandled GET ${url}`))
      })
      const user = userEvent.setup()
      renderPage()
      const section = getSection('Financeiro')
      await user.click(within(section).getByText('Visualizar'))
      await within(section).findByText('Nenhum pagamento no período.')

      await user.click(within(section).getByText('Exportar PDF'))

      await waitFor(() =>
        expect(mockedGet).toHaveBeenCalledWith('/api/v1/reports/finance', {
          params: { months_ahead: 3, format: 'pdf' },
          responseType: 'blob',
        })
      )
    })
  })
})
