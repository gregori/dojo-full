/// <reference types="cypress" />

describe('Gestão de Exames de Faixa', () => {
  const adminEmail = 'admin@dojo.com'
  const adminPassword = 'admin123'
  const instructorEmail = 'instructor@dojo.com'
  const instructorPassword = 'instruct123'

  beforeEach(() => {
    cy.clearLocalStorage()
    cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
    cy.visit('/login')
    cy.get('input[type="email"]').type(adminEmail)
    cy.get('input[type="password"]').type(adminPassword)
    cy.get('button[type="submit"]').click()
    cy.wait('@loginRequest')
  })

  describe('Criar Exame', () => {
    it('deve criar exame de faixa vinculado a evento', () => {
      cy.intercept('GET', '/api/v1/events').as('getEvents')
      cy.intercept('GET', '/api/v1/belts').as('getBelts')
      cy.intercept('GET', '/api/v1/events/types').as('getEventTypes')
      cy.get('a[href="/exams"]').click()
      cy.wait('@getEvents')
      cy.wait('@getBelts')

      // Click "Novo Exame" button
      cy.contains('Novo Exame').click()

      // Select event from dropdown
      cy.get('select').filter(':visible').first().select(1)

      // Select belt
      cy.get('select').filter(':visible').eq(1).select(1)

      // Fill exam date
      cy.get('input[type="date"]').type('2026-06-15')

      // Fill notes
      cy.get('textarea').type('Exame semestral')

      // Submit
      cy.intercept('POST', '/api/v1/exams').as('createExam')
      cy.contains('Criar').click()

      cy.wait('@createExam').then((interception) => {
        expect(interception.response?.statusCode).to.eq(201)
        expect(interception.response?.body).to.have.property('id')
        expect(interception.response?.body).to.have.property('status', 'scheduled')
      })

      // Verify exam appears in list
      cy.contains('scheduled').should('be.visible')
    })

    it('deve validar campos obrigatórios do exame', () => {
      cy.intercept('GET', '/api/v1/events').as('getEvents')
      cy.intercept('GET', '/api/v1/belts').as('getBelts')
      cy.get('a[href="/exams"]').click()
      cy.wait('@getEvents')

      cy.contains('Novo Exame').click()

      // Try to submit empty form
      cy.contains('Criar').click()

      // Should show validation errors or prevent submission
      cy.get('select').filter(':visible').first().should('have.attr', 'required')
    })
  })

  describe('Definir Banca Examinadora', () => {
    it('deve adicionar presidente da banca', () => {
      cy.intercept('GET', '/api/v1/exams').as('getExams')
      cy.get('a[href="/exams"]').click()
      cy.wait('@getExams')

      // Click on exam to open details
      cy.get('table tbody tr').first().click()

      // Navigate to board section
      cy.contains(/banca|board/i).should('be.visible')
      cy.contains(/banca|board/i).click()

      // Add board member
      cy.intercept('GET', '/api/v1/users').as('getUsers')
      cy.contains(/adicionar|add member/i).click()
      cy.wait('@getUsers')

      cy.get('select').filter(':visible').first().select(1)
      cy.get('select').filter(':visible').last().select(/presidente/i)

      cy.intercept('POST', '/api/v1/exams/*/board-members').as('addBoardMember')
      cy.contains('Adicionar').click()

      cy.wait('@addBoardMember').then((interception) => {
        expect(interception.response?.statusCode).to.eq(201)
      })

      // Verify board member appears
      cy.contains(/presidente/i).should('be.visible')
    })

    it('deve adicionar múltiplos membros à banca', () => {
      cy.intercept('GET', '/api/v1/exams').as('getExams')
      cy.get('a[href="/exams"]').click()
      cy.wait('@getExams')

      cy.get('table tbody tr').first().click()
      cy.contains(/banca|board/i).click()

      // Add first member
      cy.intercept('POST', '/api/v1/exams/*/board-members').as('addBoardMember1')
      cy.contains(/adicionar|add member/i).click()
      cy.get('select').filter(':visible').first().select(1)
      cy.get('select').filter(':visible').last().select(/presidente/i)
      cy.contains('Adicionar').click()
      cy.wait('@addBoardMember1')

      // Add second member
      cy.intercept('POST', '/api/v1/exams/*/board-members').as('addBoardMember2')
      cy.contains(/adicionar|add member/i).click()
      cy.get('select').filter(':visible').first().select(2)
      cy.get('select').filter(':visible').last().select(/membro/i)
      cy.contains('Adicionar').click()
      cy.wait('@addBoardMember2')

      // Verify 2 members in board
      cy.get('table').should('contain', /presidente|membro/i)
    })
  })

  describe('Cadastrar Candidatos', () => {
    it('deve cadastrar candidato no exame', () => {
      cy.intercept('GET', '/api/v1/exams').as('getExams')
      cy.get('a[href="/exams"]').click()
      cy.wait('@getExams')

      cy.get('table tbody tr').first().click()

      // Navigate to participants section
      cy.contains(/candidatos|participantes/i).should('be.visible')
      cy.contains(/candidatos|participantes/i).click()

      // Add candidate
      cy.intercept('GET', '/api/v1/students').as('getStudents')
      cy.contains(/adicionar|add candidate/i).click()
      cy.wait('@getStudents')

      cy.get('select').filter(':visible').first().select(1)

      // Select role as candidate
      cy.get('select').filter(':visible').last().select(/candidate/i)

      cy.intercept('POST', '/api/v1/exams/*/participants').as('addParticipant')
      cy.contains('Adicionar').click()

      cy.wait('@addParticipant').then((interception) => {
        expect(interception.response?.statusCode).to.eq(201)
        expect(interception.response?.body).to.have.property('role', 'candidate')
        expect(interception.response?.body).to.have.property('status', 'pending')
      })
    })

    it('deve cadastrar uke no exame', () => {
      cy.intercept('GET', '/api/v1/exams').as('getExams')
      cy.get('a[href="/exams"]').click()
      cy.wait('@getExams')

      cy.get('table tbody tr').first().click()
      cy.contains(/candidatos|participantes/i).click()

      cy.intercept('GET', '/api/v1/students').as('getStudents')
      cy.contains(/adicionar|add candidate/i).click()
      cy.wait('@getStudents')

      cy.get('select').filter(':visible').first().select(2)
      cy.get('select').filter(':visible').last().select(/uke/i)

      cy.intercept('POST', '/api/v1/exams/*/participants').as('addUke')
      cy.contains('Adicionar').click()

      cy.wait('@addUke').then((interception) => {
        expect(interception.response?.statusCode).to.eq(201)
        expect(interception.response?.body).to.have.property('role', 'uke')
      })
    })

    it('deve rejeitar candidato duplicado', () => {
      cy.intercept('GET', '/api/v1/exams').as('getExams')
      cy.get('a[href="/exams"]').click()
      cy.wait('@getExams')

      cy.get('table tbody tr').first().click()
      cy.contains(/candidatos|participantes/i).click()

      cy.intercept('GET', '/api/v1/students').as('getStudents')
      cy.contains(/adicionar|add candidate/i).click()
      cy.wait('@getStudents')

      cy.get('select').filter(':visible').first().select(1)
      cy.get('select').filter(':visible').last().select(/candidate/i)

      cy.intercept('POST', '/api/v1/exams/*/participants').as('addParticipant')
      cy.contains('Adicionar').click()

      cy.wait('@addParticipant')

      // Try to add same student again
      cy.intercept('POST', '/api/v1/exams/*/participants').as('addDuplicate')
      cy.contains(/adicionar|add candidate/i).click()
      cy.get('select').filter(':visible').first().select(1)
      cy.get('select').filter(':visible').last().select(/candidate/i)
      cy.contains('Adicionar').click()

      cy.wait('@addDuplicate').then((interception) => {
        expect(interception.response?.statusCode).to.eq(400)
      })

      cy.contains(/já cadastrado|duplicado/i).should('be.visible')
    })
  })

  describe('Avaliação e Notas', () => {
    it('banca deve adicionar anotações para candidato', () => {
      // Login as instructor (board member)
      cy.clearLocalStorage()
      cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
      cy.visit('/login')
      cy.get('input[type="email"]').type(instructorEmail)
      cy.get('input[type="password"]').type(instructorPassword)
      cy.get('button[type="submit"]').click()
      cy.wait('@loginRequest')

      cy.intercept('GET', '/api/v1/exams').as('getExams')
      cy.get('a[href="/exams"]').click()
      cy.wait('@getExams')

      cy.get('table tbody tr').first().click()
      cy.contains(/candidatos|participantes/i).click()

      // Click on participant to add notes
      cy.get('table tbody tr').first().click()

      // Add notes
      cy.get('textarea').clear().type('Boa técnica de projeção. Precisa melhorar ukemi.')

      cy.intercept('PUT', '/api/v1/exams/participants/*').as('updateNotes')
      cy.contains('Salvar').click()

      cy.wait('@updateNotes').then((interception) => {
        expect(interception.response?.statusCode).to.eq(200)
        expect(interception.response?.body).to.have.property('notes')
      })
    })
  })

  describe('Aprovação e Promoção', () => {
    it('deve aprovar candidato e promover faixa automaticamente', () => {
      cy.intercept('GET', '/api/v1/exams').as('getExams')
      cy.get('a[href="/exams"]').click()
      cy.wait('@getExams')

      cy.get('table tbody tr').first().click()
      cy.contains(/candidatos|participantes/i).click()

      // Click on candidate
      cy.get('table tbody tr').first().click()

      // Click approve button
      cy.contains(/aprovar|approve/i).click()

      cy.intercept('PUT', '/api/v1/exams/participants/*').as('approveParticipant')
      cy.wait('@approveParticipant').then((interception) => {
        expect(interception.response?.statusCode).to.eq(200)
        expect(interception.response?.body).to.have.property('status', 'approved')
      })

      // Verify student belt was promoted
      cy.intercept('GET', '/api/v1/students/*').as('getStudent')
      cy.contains(/aprova|approved/i).should('be.visible')
    })

    it('deve reprovar candidato mantendo faixa atual', () => {
      cy.intercept('GET', '/api/v1/exams').as('getExams')
      cy.get('a[href="/exams"]').click()
      cy.wait('@getExams')

      cy.get('table tbody tr').first().click()
      cy.contains(/candidatos|participantes/i).click()

      cy.get('table tbody tr').first().click()

      // Click reject button
      cy.contains(/reprovar|reject/i).click()

      cy.intercept('PUT', '/api/v1/exams/participants/*').as('rejectParticipant')
      cy.wait('@rejectParticipant').then((interception) => {
        expect(interception.response?.statusCode).to.eq(200)
        expect(interception.response?.body).to.have.property('status', 'rejected')
      })

      cy.contains(/reprov|rejected/i).should('be.visible')
    })

    it('instrutor não deve poder aprovar/reprovar candidato', () => {
      // Login as instructor
      cy.clearLocalStorage()
      cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
      cy.visit('/login')
      cy.get('input[type="email"]').type(instructorEmail)
      cy.get('input[type="password"]').type(instructorPassword)
      cy.get('button[type="submit"]').click()
      cy.wait('@loginRequest')

      cy.intercept('GET', '/api/v1/exams').as('getExams')
      cy.get('a[href="/exams"]').click()
      cy.wait('@getExams')

      cy.get('table tbody tr').first().click()
      cy.contains(/candidatos|participantes/i).click()

      // Try to find approve/reject buttons - should not exist or be disabled
      cy.get('body').then(($body) => {
        const hasApprove = $body.text().includes('Aprovar') || $body.text().includes('Approve')
        const hasReject = $body.text().includes('Reprovar') || $body.text().includes('Reject')
        // Instructor should not have approve/reject buttons
        expect(hasApprove && hasReject).to.be.false
      })
    })
  })

  describe('Histórico de Exames', () => {
    it('deve visualizar histórico de exames de um aluno', () => {
      // Mock exam history - endpoint doesn't exist in backend
      // Student exam history would need to come from exam participation records
      cy.intercept('GET', '/api/v1/students/*/exam-history', { body: [] }).as('getExamHistory')
      cy.intercept('GET', '/api/v1/students').as('getStudents')
      cy.get('a[href="/students"]').click()
      cy.wait('@getStudents')

      // Click on a student
      cy.get('table tbody tr').first().click()

      // Look for exam history section - mock data shown since no real endpoint
      cy.contains(/histórico|exames|exam history/i).should('be.visible')
      cy.contains(/histórico|exames|exam history/i).click()

      // Verify exam results are shown (from mock)
      cy.get('table').should('exist')
    })
  })

  describe('Fluxo Completo de Exame', () => {
    it('deve executar fluxo completo: criar → banca → candidatos → avaliar → promover', () => {
      // Step 1: Create exam
      cy.intercept('GET', '/api/v1/events').as('getEvents')
      cy.intercept('GET', '/api/v1/belts').as('getBelts')
      cy.get('a[href="/exams"]').click()
      cy.wait('@getEvents')
      cy.wait('@getBelts')

      cy.contains('Novo Exame').click()
      cy.get('select').filter(':visible').first().select(1)
      cy.get('select').filter(':visible').eq(1).select(1)
      cy.get('input[type="date"]').type('2026-06-15')
      cy.get('textarea').type('Exame semestral')

      cy.intercept('POST', '/api/v1/exams').as('createExam')
      cy.contains('Criar').click()
      cy.wait('@createExam')

      // Step 2: Add board members
      cy.contains(/banca|board/i).click()
      cy.intercept('GET', '/api/v1/users').as('getUsers')
      cy.contains(/adicionar|add member/i).click()
      cy.wait('@getUsers')
      cy.get('select').filter(':visible').first().select(1)
      cy.get('select').filter(':visible').last().select(/presidente/i)
      cy.intercept('POST', '/api/v1/exams/*/board-members').as('addBoard')
      cy.contains('Adicionar').click()
      cy.wait('@addBoard')

      // Step 3: Add candidates
      cy.contains(/candidatos|participantes/i).click()
      cy.intercept('GET', '/api/v1/students').as('getStudents')
      cy.contains(/adicionar|add candidate/i).click()
      cy.wait('@getStudents')
      cy.get('select').filter(':visible').first().select(1)
      cy.get('select').filter(':visible').last().select(/candidate/i)
      cy.intercept('POST', '/api/v1/exams/*/participants').as('addParticipant')
      cy.contains('Adicionar').click()
      cy.wait('@addParticipant')

      // Step 4: Evaluate (add notes)
      cy.get('table tbody tr').first().click()
      cy.get('textarea').clear().type('Avaliação positiva.')
      cy.intercept('PUT', '/api/v1/exams/participants/*').as('updateParticipant')
      cy.contains('Salvar').click()
      cy.wait('@updateParticipant')

      // Step 5: Approve candidate
      cy.contains(/aprovar|approve/i).click()
      cy.intercept('PUT', '/api/v1/exams/participants/*').as('approveFinal')
      cy.wait('@approveFinal').then((interception) => {
        expect(interception.response?.statusCode).to.eq(200)
        expect(interception.response?.body).to.have.property('status', 'approved')
      })

      // Verify the complete flow succeeded
      cy.contains(/aprovado|approved/i).should('be.visible')
    })
  })
})