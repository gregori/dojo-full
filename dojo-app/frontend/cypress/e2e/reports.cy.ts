/// <reference types="cypress" />
/**
 * Reports E2E Test Suite
 * Mirrors contracts.cy.ts's conventions for Epic 02 Phase 5 (Reports, REP-01-REP-05).
 */
describe('Relatórios', () => {
  const adminEmail = 'admin@dojo.com'
  const adminPassword = 'admin123'
  const instructorEmail = 'instructor@dojo.com'
  const instructorPassword = 'instruct123'
  const apiUrl = 'http://localhost:8000'

  function loginAsInstructor() {
    cy.clearLocalStorage()
    cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
    cy.visit('/login')
    cy.get('input[type="email"]').type(instructorEmail)
    cy.get('input[type="password"]').type(instructorPassword)
    cy.get('button[type="submit"]').click()
    cy.wait('@loginRequest')
  }

  describe('Scenario 1: REP-01 - Belt exam report JSON preview', () => {
    let studentData: { id: string; full_name: string; registration_number: string }
    const uniqueSuffix = `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`

    beforeEach(() => {
      cy.getAuthToken(adminEmail, adminPassword).then((token: any) => {
        cy.createBelt({ name: 'Faixa Roxa', category: 'adult', sort_order: 4 }).then(
          (belt: any) => {
            cy.createStudent({
              full_name: `ReportsScenario1Student${uniqueSuffix}`,
              birth_date: '1990-06-14',
              category: 'adult',
              belt_id: belt.id,
            }).then((student: any) => {
              if (!student || !student.id) return
              studentData = student

              cy.createEvent({
                title: `Exame de Faixa ${uniqueSuffix}`,
                start_datetime: new Date().toISOString(),
              }).then((event: any) => {
                cy.request({
                  method: 'POST',
                  url: `${apiUrl}/api/v1/exams`,
                  body: {
                    event_id: event.id,
                    belt_id: belt.id,
                    exam_date: new Date().toISOString(),
                  },
                  headers: { Authorization: `Bearer ${token}` },
                  failOnStatusCode: false,
                }).then((examResponse) => {
                  cy.request({
                    method: 'POST',
                    url: `${apiUrl}/api/v1/exams/${examResponse.body.id}/participants`,
                    body: { student_id: student.id, role: 'uke' },
                    headers: { Authorization: `Bearer ${token}` },
                    failOnStatusCode: false,
                  })
                })
              })
            })
          }
        )
      })
    })

    it('requests a belt-exam report for a seeded student and renders the expected rows', () => {
      loginAsInstructor()
      cy.visit('/reports')

      cy.contains('h3', 'Exame de Faixa')
        .parent()
        .within(() => {
          cy.get('select').select(studentData.id)
          cy.intercept('GET', `/api/v1/reports/belt-exams/${studentData.id}`).as('examReport')
          cy.contains('button', 'Visualizar').click()
          cy.wait('@examReport').its('response.statusCode').should('eq', 200)
          cy.contains('td', 'uke', { timeout: 10000 }).should('be.visible')
        })
    })
  })

  describe('Scenario 2: REP-02 - Student attendance report total matches seeded attendance', () => {
    let studentData: { id: string; full_name: string; registration_number: string }
    const uniqueSuffix = `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`

    beforeEach(() => {
      cy.getAuthToken(adminEmail, adminPassword).then((token: any) => {
        cy.createStudent({
          full_name: `ReportsScenario2Student${uniqueSuffix}`,
          birth_date: '1991-03-20',
          category: 'adult',
        }).then((student: any) => {
          if (!student || !student.id) return
          studentData = student

          cy.createEvent({
            title: `Aula Presenca ${uniqueSuffix}`,
            start_datetime: new Date().toISOString(),
          }).then((event: any) => {
            cy.request({
              method: 'POST',
              url: `${apiUrl}/api/v1/checkin/manual`,
              body: { event_id: event.id, student_id: student.id, check_in_method: 'manual' },
              headers: { Authorization: `Bearer ${token}` },
              failOnStatusCode: false,
            })
          })
        })
      })
    })

    it('renders a total attendance count matching the seeded Attendance record', () => {
      loginAsInstructor()
      cy.visit('/reports')

      cy.contains('h3', 'Presenças (Aluno)')
        .parent()
        .within(() => {
          cy.get('select').select(studentData.id)
          cy.intercept('GET', `/api/v1/reports/attendance/student/${studentData.id}*`).as(
            'attendanceReport'
          )
          cy.contains('button', 'Visualizar').click()
          cy.wait('@attendanceReport').its('response.statusCode').should('eq', 200)
          cy.contains('Total de presenças:', { timeout: 10000 }).should('be.visible')
          cy.contains('strong', '1').should('be.visible')
        })
    })
  })

  describe('Scenario 3: REP-05 - Real PDF download round trip', () => {
    let studentData: { id: string; full_name: string; registration_number: string }
    const uniqueSuffix = `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`

    beforeEach(() => {
      cy.getAuthToken(adminEmail, adminPassword).then(() => {
        cy.createStudent({
          full_name: `ReportsScenario3Student${uniqueSuffix}`,
          birth_date: '1992-07-25',
          category: 'adult',
        }).then((student: any) => {
          studentData = student
        })
      })
    })

    it('downloads a real PDF for the belt-exam report and confirms the %PDF- magic bytes', () => {
      loginAsInstructor()
      cy.visit('/reports')

      cy.contains('h3', 'Exame de Faixa')
        .parent()
        .within(() => {
          cy.get('select').select(studentData.id)
          cy.contains('button', 'Visualizar').click()
        })

      cy.intercept('GET', `/api/v1/reports/belt-exams/${studentData.id}*`).as('pdfExport')
      cy.contains('h3', 'Exame de Faixa')
        .parent()
        .within(() => {
          cy.contains('button', 'Exportar PDF').click()
        })

      cy.wait('@pdfExport', { timeout: 15000 }).then((interception) => {
        expect(interception.response?.statusCode).to.equal(200)
        expect(interception.response?.headers['content-type']).to.contain('application/pdf')
        // axios' `responseType: 'blob'` makes Cypress capture the intercepted body as an
        // ArrayBuffer rather than a string -- decode the first 5 bytes to check the magic bytes.
        const rawBody = interception.response?.body as unknown as ArrayBuffer
        const prefix = new TextDecoder().decode(new Uint8Array(rawBody).slice(0, 5))
        expect(prefix).to.equal('%PDF-')
      })
    })
  })

  describe('Scenario 4: REP-05 - Real CSV download for the financial report', () => {
    beforeEach(() => {
      cy.getAuthToken(adminEmail, adminPassword)
    })

    it('downloads a real CSV for the financial report and confirms all three section headers', () => {
      loginAsInstructor()
      cy.visit('/reports')

      cy.intercept('GET', '/api/v1/reports/finance*').as('financeView')
      cy.contains('h3', 'Financeiro')
        .parent()
        .within(() => {
          cy.contains('button', 'Visualizar').click()
        })
      cy.wait('@financeView', { timeout: 10000 })

      cy.intercept('GET', '/api/v1/reports/finance*').as('csvExport')
      cy.contains('h3', 'Financeiro')
        .parent()
        .within(() => {
          cy.contains('button', 'Exportar CSV').click()
        })

      cy.wait('@csvExport', { timeout: 15000 }).then((interception) => {
        expect(interception.response?.statusCode).to.equal(200)
        const body = interception.response?.body as string
        expect(body).to.contain('Pagamentos')
        expect(body).to.contain('Inadimplência')
        expect(body).to.contain('Projeção')
      })
    })
  })

  describe('Scenario 5: D5-equivalent - Authorization: invalid token gets 401 on report endpoints', () => {
    it('non-authorized caller gets 401 on a direct API call to a report endpoint', () => {
      cy.request({
        method: 'GET',
        url: `${apiUrl}/api/v1/reports/finance`,
        headers: { Authorization: 'Bearer invalid-token-xyz' },
        failOnStatusCode: false,
      }).then((response) => {
        expect(response.status).to.equal(401)
      })

      cy.request({
        method: 'GET',
        url: `${apiUrl}/api/v1/reports/belt-exams/some-id`,
        headers: { Authorization: 'Bearer invalid-token-xyz' },
        failOnStatusCode: false,
      }).then((response) => {
        expect(response.status).to.equal(401)
      })
    })
  })
})
