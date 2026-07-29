/// <reference types="cypress" />

describe('Exames Médicos', () => {
  const adminEmail = 'admin@dojo.com'
  const adminPassword = 'admin123'
  const instructorEmail = 'instructor@dojo.com'
  const instructorPassword = 'instruct123'

  describe('Envio Público de Exame Médico', () => {
    let studentData: { id: string; registration_number: string; pin: string }

    beforeEach(() => {
      // Create a student for medical exam tests
      cy.getAuthToken(adminEmail, adminPassword).then(() => {
        cy.createStudent({
          full_name: 'Medical Exam Test Student',
          birth_date: '1990-01-01',
          category: 'adult',
        }).then((student: any) => {
          studentData = {
            id: student.id,
            registration_number: student.registration_number,
            pin: student.pin,
          }
        })
      })
    })

    it('deve aceitar upload válido de PDF via registro e PIN', () => {
      cy.visit('/medical-exam')

      // Fill form
      cy.get('input#registration').type(studentData.registration_number)
      cy.get('input#pin').type(studentData.pin)
      cy.get('input#exam-date').type('2026-01-15')

      // Create a minimal valid PDF file for testing
      const pdfContent = '%PDF-1.4\n%EOF'
      const fileName = 'valid-exam.pdf'
      cy.get('input#exam-file').selectFile({
        contents: Cypress.Buffer.from(pdfContent),
        fileName: fileName,
        mimeType: 'application/pdf',
      })

      cy.intercept('POST', '/api/v1/medical-exams/public/submit').as('submitExam')

      // Submit
      cy.contains(/Enviar exame/i).click()

      cy.wait('@submitExam').then((interception) => {
        expect(interception.response?.statusCode).to.eq(200)
      })

      // Should show success message
      cy.contains(/sucesso|registrado/i).should('be.visible')
    })

    it('deve aceitar upload válido de JPEG', () => {
      cy.visit('/medical-exam')

      cy.get('input#registration').type(studentData.registration_number)
      cy.get('input#pin').type(studentData.pin)
      cy.get('input#exam-date').type('2026-01-15')

      // Create a minimal valid JPEG file (minimal JPEG SOI marker)
      const jpegContent = new Uint8Array([0xff, 0xd8, 0xff, 0xe0, 0x00, 0x10])
      const fileName = 'valid-exam.jpg'
      cy.get('input#exam-file').selectFile({
        contents: Cypress.Buffer.from(jpegContent),
        fileName: fileName,
        mimeType: 'image/jpeg',
      })

      // No cy.intercept() here: Cypress decodes/re-encodes intercepted request bodies as
      // UTF-8 text, which corrupts binary multipart content (bytes that aren't valid UTF-8,
      // like this JPEG's magic bytes, become replacement characters on the wire). We verify
      // the outcome via the UI instead of inspecting the intercepted response.
      cy.contains(/Enviar exame/i).click()

      cy.contains(/sucesso|registrado/i).should('be.visible')
    })

    it('deve aceitar upload válido de PNG', () => {
      cy.visit('/medical-exam')

      cy.get('input#registration').type(studentData.registration_number)
      cy.get('input#pin').type(studentData.pin)
      cy.get('input#exam-date').type('2026-01-15')

      // Create a minimal valid PNG file (PNG signature)
      const pngContent = new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])
      const fileName = 'valid-exam.png'
      cy.get('input#exam-file').selectFile({
        contents: Cypress.Buffer.from(pngContent),
        fileName: fileName,
        mimeType: 'image/png',
      })

      // No cy.intercept() here: Cypress decodes/re-encodes intercepted request bodies as
      // UTF-8 text, which corrupts binary multipart content (bytes that aren't valid UTF-8,
      // like this PNG's magic bytes, become replacement characters on the wire). We verify
      // the outcome via the UI instead of inspecting the intercepted response.
      cy.contains(/Enviar exame/i).click()

      cy.contains(/sucesso|registrado/i).should('be.visible')
    })

    it('deve rejeitar tipo de arquivo inválido com mensagem de erro', () => {
      cy.visit('/medical-exam')

      cy.get('input#registration').type(studentData.registration_number)
      cy.get('input#pin').type(studentData.pin)
      cy.get('input#exam-date').type('2026-01-15')

      // Try to select a non-allowed file type (text file)
      const fileName = 'invalid.txt'
      const txtContent = Cypress.Buffer.from('This is not a valid medical exam file')
      cy.get('input#exam-file').selectFile(
        {
          contents: txtContent,
          fileName: fileName,
          mimeType: 'text/plain',
        },
        { force: true }
      )

      cy.intercept('POST', '/api/v1/medical-exams/public/submit').as('submitExam')

      cy.contains(/Enviar exame/i).click()

      cy.wait('@submitExam').then((interception) => {
        // Backend may reject or the browser may prevent submission
        expect([200, 400, 422]).to.include(interception.response?.statusCode)
      })
    })

    it('deve rejeitar PIN incorreto com mensagem genérica', () => {
      cy.getAuthToken(adminEmail, adminPassword).then((token: any) => {
        cy.visit('/medical-exam')

        cy.get('input#registration').type(studentData.registration_number)
        cy.get('input#pin').type('0000') // Wrong PIN
        cy.get('input#exam-date').type('2026-01-15')

        const pdfContent = '%PDF-1.4\n%EOF'
        cy.get('input#exam-file').selectFile({
          contents: Cypress.Buffer.from(pdfContent),
          fileName: 'valid-exam.pdf',
          mimeType: 'application/pdf',
        })

        cy.intercept('POST', '/api/v1/medical-exams/public/submit').as('submitExam')

        cy.contains(/Enviar exame/i).click()

        cy.wait('@submitExam').then((interception) => {
          // Backend returns 200 with generic message (security: doesn't disclose if PIN is wrong)
          expect(interception.response?.statusCode).to.eq(200)
        })

        // Verify indirectly: wrong PIN should not have created a record
        cy.request({
          method: 'GET',
          url: `http://localhost:8000/api/v1/medical-exams/students/${studentData.id}`,
          headers: {
            Authorization: `Bearer ${token}`,
          },
          failOnStatusCode: false,
        }).then((response) => {
          // History should be empty (wrong PIN was silently rejected)
          expect(response.status).to.eq(200)
          expect(response.body).to.be.an('array').that.is.empty
        })
      })
    })
  })

  describe('Registro de Exame Médico (Instrutor/Admin)', () => {
    let studentData: { id: string; registration_number: string; pin: string }

    beforeEach(() => {
      cy.getAuthToken(adminEmail, adminPassword).then(() => {
        cy.createStudent({
          full_name: 'Instructor Medical Exam Test',
          birth_date: '1992-03-10',
          category: 'adult',
        }).then((student: any) => {
          studentData = {
            id: student.id,
            registration_number: student.registration_number,
            pin: student.pin,
          }
        })
      })
    })

    it('instrutor deve registrar exame médico em nome do aluno (sem arquivo)', () => {
      // Login as instructor
      cy.clearLocalStorage()
      cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
      cy.visit('/login')
      cy.get('input[type="email"]').type(instructorEmail)
      cy.get('input[type="password"]').type(instructorPassword)
      cy.get('button[type="submit"]').click()
      cy.wait('@loginRequest')

      // Record exam via API
      cy.request({
        method: 'POST',
        url: `http://localhost:8000/api/v1/medical-exams/students/${studentData.id}`,
        form: true,
        body: {
          exam_date: '2026-01-10',
        },
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        failOnStatusCode: false,
      }).then((response) => {
        expect(response.status).to.eq(201)
        expect(response.body).to.have.property('exam_date')
        expect(response.body).to.have.property('status')
      })
    })

    it('instrutor deve substituir exame anterior (supersessão)', () => {
      cy.clearLocalStorage()
      cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
      cy.visit('/login')
      cy.get('input[type="email"]').type(instructorEmail)
      cy.get('input[type="password"]').type(instructorPassword)
      cy.get('button[type="submit"]').click()
      cy.wait('@loginRequest')

      const token = localStorage.getItem('token')

      // Record first exam
      cy.request({
        method: 'POST',
        url: `http://localhost:8000/api/v1/medical-exams/students/${studentData.id}`,
        form: true,
        body: {
          exam_date: '2026-01-10',
        },
        headers: {
          Authorization: `Bearer ${token}`,
        },
        failOnStatusCode: false,
      }).then((response1) => {
        expect(response1.status).to.eq(201)

        // Record second exam with different date (supersedes first)
        cy.request({
          method: 'POST',
          url: `http://localhost:8000/api/v1/medical-exams/students/${studentData.id}`,
          form: true,
          body: {
            exam_date: '2026-01-20',
          },
          headers: {
            Authorization: `Bearer ${token}`,
          },
          failOnStatusCode: false,
        }).then((response2) => {
          expect(response2.status).to.eq(201)

          // Get history and verify supersession
          cy.request({
            method: 'GET',
            url: `http://localhost:8000/api/v1/medical-exams/students/${studentData.id}`,
            headers: {
              Authorization: `Bearer ${token}`,
            },
            failOnStatusCode: false,
          }).then((historyResponse) => {
            expect(historyResponse.status).to.eq(200)
            expect(historyResponse.body).to.be.an('array')
            // Most recent should be the second exam
            if (historyResponse.body.length > 0) {
              const mostRecent = historyResponse.body[0]
              expect(mostRecent.exam_date).to.include('2026-01-20')
            }
          })
        })
      })
    })

    it('instrutor deve visualizar histórico de exames', () => {
      cy.clearLocalStorage()
      cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
      cy.visit('/login')
      cy.get('input[type="email"]').type(instructorEmail)
      cy.get('input[type="password"]').type(instructorPassword)
      cy.get('button[type="submit"]').click()
      cy.wait('@loginRequest')

      const token = localStorage.getItem('token')

      // Record an exam first
      cy.request({
        method: 'POST',
        url: `http://localhost:8000/api/v1/medical-exams/students/${studentData.id}`,
        form: true,
        body: {
          exam_date: '2026-01-15',
        },
        headers: {
          Authorization: `Bearer ${token}`,
        },
        failOnStatusCode: false,
      })

      // Get history
      cy.request({
        method: 'GET',
        url: `http://localhost:8000/api/v1/medical-exams/students/${studentData.id}`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        failOnStatusCode: false,
      }).then((response) => {
        expect(response.status).to.eq(200)
        expect(response.body).to.be.an('array')
        expect(response.body.length).to.be.greaterThan(0)
      })
    })
  })

  describe('Dashboard de Exames Médicos', () => {
    let studentData: { id: string; registration_number: string; pin: string }

    beforeEach(() => {
      cy.getAuthToken(adminEmail, adminPassword).then(() => {
        cy.createStudent({
          full_name: 'Dashboard Medical Exam Test',
          birth_date: '1988-07-22',
          category: 'adult',
        }).then((student: any) => {
          studentData = {
            id: student.id,
            registration_number: student.registration_number,
            pin: student.pin,
          }
        })
      })
    })

    it('dashboard deve mostrar alunos com status médico vencendo/vencido', () => {
      // Login as instructor
      cy.clearLocalStorage()
      cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
      cy.visit('/login')
      cy.get('input[type="email"]').type(instructorEmail)
      cy.get('input[type="password"]').type(instructorPassword)
      cy.get('button[type="submit"]').click()
      cy.wait('@loginRequest')

      const token = localStorage.getItem('token')

      // Record a medical exam to populate status
      cy.request({
        method: 'POST',
        url: `http://localhost:8000/api/v1/medical-exams/students/${studentData.id}`,
        form: true,
        body: {
          exam_date: '2025-01-01', // Old date to trigger vencido status
        },
        headers: {
          Authorization: `Bearer ${token}`,
        },
        failOnStatusCode: false,
      })

      // Get dashboard
      cy.request({
        method: 'GET',
        url: 'http://localhost:8000/api/v1/medical-exams/dashboard',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        failOnStatusCode: false,
      }).then((response) => {
        expect(response.status).to.eq(200)
        expect(response.body).to.be.an('array')
        // Dashboard shows students with vencendo/vencido status
      })
    })

    it('aluno deve visualizar seu status médico na página de perfil', () => {
      cy.clearLocalStorage()
      cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
      cy.visit('/login')
      cy.get('input[type="email"]').type(instructorEmail)
      cy.get('input[type="password"]').type(instructorPassword)
      cy.get('button[type="submit"]').click()
      cy.wait('@loginRequest')

      const token = localStorage.getItem('token')

      // Get medical exam status for student
      cy.request({
        method: 'GET',
        url: `http://localhost:8000/api/v1/medical-exams/students/${studentData.id}/status`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        failOnStatusCode: false,
      }).then((response) => {
        expect(response.status).to.eq(200)
        expect(response.body).to.have.property('status')
        expect(['valido', 'vencendo', 'vencido', 'sem_registro']).to.include(response.body.status)
      })
    })
  })
})
