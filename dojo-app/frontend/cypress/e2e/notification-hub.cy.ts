/// <reference types="cypress" />

describe('Central de Notificações', () => {
  const adminEmail = 'admin@dojo.com'
  const adminPassword = 'admin123'

  let studentData: { id: string; registration_number: string; pin: string }

  beforeEach(() => {
    cy.getAuthToken(adminEmail, adminPassword).then(() => {
      cy.createStudent({
        full_name: 'Notification Hub Test Student',
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

  it('deve exibir o histórico de notificações para matrícula e PIN válidos', () => {
    cy.visit('/notifications')

    cy.intercept('POST', '/api/v1/notifications/history').as('history')

    cy.get('input#registration').type(studentData.registration_number)
    cy.get('input#pin').type(studentData.pin)
    cy.contains(/Ver minhas notificações/i).click()

    cy.wait('@history').then((interception) => {
      expect(interception.response?.statusCode).to.eq(200)
    })

    // A newly-created student has no notifications yet -- this still exercises
    // the full valid-credentials flow: the history section renders (either
    // the empty-state message or a list item), not the credentials form/error.
    cy.contains('Histórico').should('be.visible')
    cy.contains(/Nenhuma notificação encontrada|Não lida|Lida/i).should('be.visible')
  })

  it('deve exibir uma mensagem de erro clara para matrícula ou PIN inválidos', () => {
    cy.visit('/notifications')

    cy.intercept('POST', '/api/v1/notifications/history').as('history')

    cy.get('input#registration').type(studentData.registration_number)
    cy.get('input#pin').type('0000') // wrong PIN
    cy.contains(/Ver minhas notificações/i).click()

    cy.wait('@history').then((interception) => {
      expect(interception.response?.statusCode).to.eq(401)
    })

    // NH-01: unlike pre-check-in/medical-exam, this endpoint must return a
    // clear, distinguishable error -- not a generic "accepted" message.
    cy.contains(/Matrícula ou PIN inválidos/i).should('be.visible')
    cy.contains('Histórico').should('not.exist')
  })
})
