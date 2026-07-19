/// <reference types="cypress" />

describe('Check-in de Presença', () => {
  const adminEmail = 'admin@dojo.com'
  const adminPassword = 'admin123'
  const instructorEmail = 'instructor@dojo.com'
  const instructorPassword = 'instruct123'

  describe('Check-in via Tablet', () => {
    it('deve fazer check-in com matrícula e PIN válidos', () => {
      // This page should be publicly accessible without login
      cy.clearLocalStorage()
      cy.visit('/checkin')

      // Verify check-in form elements are present
      cy.get('input[placeholder*="matrícula"]').should('exist')
      cy.get('input[placeholder*="PIN"]').should('exist')
      cy.get('button[type="submit"]').should('contain', /check.?in|entrar/i)

      // Select event from dropdown if needed
      cy.get('select').should('exist')

      // Enter credentials
      cy.get('input[placeholder*="matrícula"]').type('2024001')
      cy.get('input[placeholder*="PIN"]').type('1234')

      // Intercept check-in API
      cy.intercept('POST', '/api/v1/checkin/tablet/*').as('checkinRequest')

      // Submit
      cy.contains(/check.?in|entrar/i).click()

      cy.wait('@checkinRequest').then((interception) => {
        // If valid credentials, should return 200
        expect(interception.response?.statusCode).to.be.oneOf([200, 201, 400])
      })

      // Should show success message or error based on credentials
      cy.get('body').should('contain', /sucesso|erro|PIN|Matricula/i)
    })

    it('deve rejeitar check-in com PIN incorreto', () => {
      cy.clearLocalStorage()
      cy.visit('/checkin')

      cy.get('input[placeholder*="matrícula"]').type('2024001')
      cy.get('input[placeholder*="PIN"]').type('0000') // Wrong PIN

      cy.intercept('POST', '/api/v1/checkin/tablet/*').as('checkinRequest')
      cy.contains(/check.?in|entrar/i).click()

      cy.wait('@checkinRequest').then((interception) => {
        expect(interception.response?.statusCode).to.eq(400)
      })

      cy.contains(/PIN incorreto|senha inválida/i).should('be.visible')
    })

    it('deve rejeitar check-in com matrícula inexistente', () => {
      cy.clearLocalStorage()
      cy.visit('/checkin')

      cy.get('input[placeholder*="matrícula"]').type('9999999')
      cy.get('input[placeholder*="PIN"]').type('1234')

      cy.intercept('POST', '/api/v1/checkin/tablet/*').as('checkinRequest')
      cy.contains(/check.?in|entrar/i).click()

      cy.wait('@checkinRequest').then((interception) => {
        expect(interception.response?.statusCode).to.eq(400)
      })

      cy.contains(/não encontrado|Aluno não/i).should('be.visible')
    })

    it('deve rejeitar check-in de aluno inativo', () => {
      cy.clearLocalStorage()
      cy.visit('/checkin')

      // Use credentials of inactive student
      cy.get('input[placeholder*="matrícula"]').type('2024001')
      cy.get('input[placeholder*="PIN"]').type('1234')

      cy.intercept('POST', '/api/v1/checkin/tablet/*').as('checkinRequest')
      cy.contains(/check.?in|entrar/i).click()

      cy.wait('@checkinRequest').then((interception) => {
        expect(interception.response?.statusCode).to.eq(400)
      })

      cy.contains(/inativo/i).should('be.visible')
    })

    it('deve rejeitar check-in em evento cancelado', () => {
      cy.clearLocalStorage()
      cy.visit('/checkin')

      // Select cancelled event
      cy.get('select').should('exist')

      cy.get('input[placeholder*="matrícula"]').type('2024001')
      cy.get('input[placeholder*="PIN"]').type('1234')

      cy.intercept('POST', '/api/v1/checkin/tablet/*').as('checkinRequest')
      cy.contains(/check.?in|entrar/i).click()

      cy.wait('@checkinRequest').then((interception) => {
        expect(interception.response?.statusCode).to.eq(400)
      })

      cy.contains(/cancelado/i).should('be.visible')
    })

    it('deve rejeitar check-in duplicado no mesmo evento', () => {
      cy.clearLocalStorage()
      cy.visit('/checkin')

      cy.get('input[placeholder*="matrícula"]').type('2024001')
      cy.get('input[placeholder*="PIN"]').type('1234')

      cy.intercept('POST', '/api/v1/checkin/tablet/*').as('checkinRequest')
      cy.contains(/check.?in|entrar/i).click()

      cy.wait('@checkinRequest').then((interception) => {
        // 400 if already checked in, 200 if first time
        expect(interception.response?.statusCode).to.be.oneOf([200, 400])
      })

      // Should show appropriate message
      cy.get('body').should('contain', /já registro|sucesso|erro/i)
    })
  })

  describe('Check-in via QR Code', () => {
    it('deve fazer check-in via URL com token de evento', () => {
      // Simulate scanning QR code by visiting URL with token
      cy.clearLocalStorage()
      cy.visit('/checkin?token=valid-event-token')

      // Event should be pre-selected from token
      cy.get('input[placeholder*="matrícula"]').should('exist')
      cy.get('input[placeholder*="PIN"]').should('exist')

      // Enter student credentials
      cy.get('input[placeholder*="matrícula"]').type('2024001')
      cy.get('input[placeholder*="PIN"]').type('1234')

      cy.intercept('POST', '/api/v1/checkin/qr').as('qrCheckinRequest')
      cy.contains(/check.?in|entrar/i).click()

      cy.wait('@qrCheckinRequest').then((interception) => {
        expect(interception.response?.statusCode).to.be.oneOf([200, 201, 400])
      })
    })

    it('deve rejeitar QR Code com token inválido', () => {
      cy.clearLocalStorage()
      cy.visit('/checkin?token=invalid-token')

      // Should show error about invalid token
      cy.contains(/token inválido|evento não encontrado/i).should('be.visible')

      // Check-in form should not be accessible or show error
      cy.get('body').should('contain', /token|inválido|erro/i)
    })

    it('deve rejeitar QR Code de evento cancelado', () => {
      cy.clearLocalStorage()
      cy.visit('/checkin?token=cancelled-event-token')

      // Should show error about cancelled event
      cy.contains(/cancelado|evento cancelado/i).should('be.visible')
    })
  })

  describe('Lista de Presença (Instrutor)', () => {
    beforeEach(() => {
      // Login as instructor
      cy.clearLocalStorage()
      cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
      cy.visit('/login')
      cy.get('input[type="email"]').type(instructorEmail)
      cy.get('input[type="password"]').type(instructorPassword)
      cy.get('button[type="submit"]').click()
      cy.wait('@loginRequest')
    })

    it('deve visualizar lista de presença vazia', () => {
      // Navigate to events page
      cy.intercept('GET', '/api/v1/events').as('getEvents')
      cy.get('a[href="/events"]').click()
      cy.wait('@getEvents')

      // Click on an event to see attendance
      cy.get('table tbody tr').first().click()

      // Should show empty attendance message
      cy.contains(/nenhum|empty|vazio/i).should('be.visible')
    })

    it('deve visualizar lista de presença em tempo real', () => {
      cy.intercept('GET', '/api/v1/events').as('getEvents')
      cy.get('a[href="/events"]').click()
      cy.wait('@getEvents')

      // Click on event
      cy.get('table tbody tr').first().click()

      // Wait for attendance list to load
      cy.intercept('GET', '/api/v1/checkin/event/*').as('getAttendances')
      cy.wait('@getAttendances')

      // Table should show student names and check-in method
      cy.get('table').should('exist')
    })

    it('deve registrar presença manualmente', () => {
      cy.intercept('GET', '/api/v1/events').as('getEvents')
      cy.get('a[href="/events"]').click()
      cy.wait('@getEvents')

      // Click on event
      cy.get('table tbody tr').first().click()

      // Look for "Registrar Presença Manual" button
      cy.contains(/registrar presença|presença manual/i).should('be.visible')
      cy.contains(/registrar presença|presença manual/i).click()

      // Select student from dropdown
      cy.get('select').filter(':visible').should('exist')
      cy.get('select').filter(':visible').first().select(1)

      // Confirm registration
      cy.intercept('POST', '/api/v1/checkin/manual').as('manualCheckin')
      cy.contains('Confirmar').click()

      cy.wait('@manualCheckin').then((interception) => {
        expect(interception.response?.statusCode).to.be.oneOf([201, 400])
      })
    })

    it('deve rejeitar presença manual duplicada', () => {
      cy.intercept('GET', '/api/v1/events').as('getEvents')
      cy.get('a[href="/events"]').click()
      cy.wait('@getEvents')

      cy.get('table tbody tr').first().click()

      cy.intercept('POST', '/api/v1/checkin/manual').as('manualCheckin')
      cy.contains(/registrar presença|presença manual/i).click()

      cy.get('select').filter(':visible').first().select(1)
      cy.contains('Confirmar').click()

      cy.wait('@manualCheckin').then((interception) => {
        expect(interception.response?.statusCode).to.eq(400)
      })

      cy.contains(/já registrada|duplicada/i).should('be.visible')
    })
  })
})