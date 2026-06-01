/// <reference types="cypress" />

describe('Events Page', () => {
  const testEmail = 'admin@dojo.com'
  const testPassword = 'admin123'

  beforeEach(() => {
    // Intercept API calls for event types
    cy.intercept('GET', '/api/v1/events/types').as('getEventTypes')
    cy.intercept('GET', '/api/v1/events').as('getEvents')

    // Clear auth and visit login page
    cy.clearLocalStorage()
    cy.visit('/login')
  })

  it('should create a new event with all required fields', () => {
    // Login
    cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
    cy.get('input[type="email"]').type(testEmail)
    cy.get('input[type="password"]').type(testPassword)
    cy.get('button[type="submit"]').click()
    cy.wait('@loginRequest')

    // Navigate to Events page
    cy.intercept('GET', '/api/v1/events').as('getEvents')
    cy.intercept('GET', '/api/v1/events/types').as('getEventTypes')
    cy.get('a[href="/events"]').click()
    cy.wait('@getEvents')
    cy.wait('@getEventTypes')

    // Click "Novo Evento" button
    cy.contains('Novo Evento').click()

    // Fill in the form
    cy.get('input[type="text"]').first().type('Treino de Aikido') // title
    cy.get('select').first().select(0) // event type

    // Fill location
    cy.get('input[placeholder=""], input[type="text"]').filter(':visible').last().type('Dojo Principal')

    // Fill start datetime
    const futureDate = '2030-12-01T10:00'
    cy.get('input[type="datetime-local"]').first().type(futureDate)

    // Fill end datetime
    cy.get('input[type="datetime-local"]').last().type('2030-12-01T12:00')

    // Fill description
    cy.get('textarea').type('Treino semanal de aikido para iniciantes')

    // Submit - intercept the create request
    cy.intercept('POST', '/api/v1/events').as('createEvent')
    cy.contains('Criar').click()
    cy.wait('@createEvent')

    // Verify event appears in the table
    cy.contains('Treino de Aikido').should('be.visible')
    cy.contains('Dojo Principal').should('be.visible')
  })

  it('should edit an existing event and preserve required fields', () => {
    // Login
    cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
    cy.get('input[type="email"]').type(testEmail)
    cy.get('input[type="password"]').type(testPassword)
    cy.get('button[type="submit"]').click()
    cy.wait('@loginRequest')

    // Navigate to Events page
    cy.intercept('GET', '/api/v1/events').as('getEvents')
    cy.intercept('GET', '/api/v1/events/types').as('getEventTypes')
    cy.get('a[href="/events"]').click()
    cy.wait('@getEvents')
    cy.wait('@getEventTypes')

    // Click "Novo Evento" to create an event first
    cy.contains('Novo Evento').click()
    cy.get('input[type="text"]').first().type('Evento para Editar')
    cy.get('select').first().select(0)
    cy.get('input[type="datetime-local"]').first().type('2030-12-01T10:00')

    cy.intercept('POST', '/api/v1/events').as('createEvent')
    cy.contains('Criar').click()
    cy.wait('@createEvent')

    // Now edit the event - click the edit (pencil) icon
    cy.intercept('GET', '/api/v1/events').as('getEventsAfterCreate')
    cy.wait('@getEventsAfterCreate')
    cy.get('table tbody tr').first().within(() => {
      cy.get('button').first().click() // Edit button
    })

    // Verify form is populated with existing values
    cy.get('input[type="text"]').first().should('have.value', 'Evento para Editar')
    cy.get('select').first().should('not.have.value', '') // event_type_id should be preserved
    cy.get('textarea').should('exist') // description field exists

    // Verify event_type_id is preserved (bug fix verification)
    cy.get('select').first().invoke('val').should('not.equal', '')

    // Change location
    cy.get('input[type="text"]').filter(':visible').last().clear().type('Dojo Secundário')

    // Submit update
    cy.intercept('PUT', '/api/v1/events/*').as('updateEvent')
    cy.contains('Atualizar').click()
    cy.wait('@updateEvent')

    // Verify the change is reflected
    cy.contains('Dojo Secundário').should('be.visible')
  })

  it('should show validation error when submitting empty required fields', () => {
    // Login
    cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
    cy.get('input[type="email"]').type(testEmail)
    cy.get('input[type="password"]').type(testPassword)
    cy.get('button[type="submit"]').click()
    cy.wait('@loginRequest')

    // Navigate to Events page
    cy.get('a[href="/events"]').click()
    cy.wait('@getEvents')

    // Click "Novo Evento" button
    cy.contains('Novo Evento').click()

    // Try to submit with empty required fields (title is required)
    cy.contains('Criar').click()

    // HTML5 validation should prevent submission
    // Check that the title input has required attribute and is empty
    cy.get('input[type="text"]').first().should('have.attr', 'required')
  })

  it('should delete an event', () => {
    // Login
    cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
    cy.get('input[type="email"]').type(testEmail)
    cy.get('input[type="password"]').type(testPassword)
    cy.get('button[type="submit"]').click()
    cy.wait('@loginRequest')

    // Navigate to Events page
    cy.intercept('GET', '/api/v1/events').as('getEvents')
    cy.intercept('GET', '/api/v1/events/types').as('getEventTypes')
    cy.get('a[href="/events"]').click()
    cy.wait('@getEvents')
    cy.wait('@getEventTypes')

    // Create an event first
    cy.contains('Novo Evento').click()
    cy.get('input[type="text"]').first().type('Evento para Deletar')
    cy.get('select').first().select(0)
    cy.get('input[type="datetime-local"]').first().type('2030-12-01T10:00')
    cy.intercept('POST', '/api/v1/events').as('createEvent')
    cy.contains('Criar').click()
    cy.wait('@createEvent')

    // Wait for event to appear and delete it
    cy.intercept('DELETE', '/api/v1/events/*').as('deleteEvent')
    cy.intercept('GET', '/api/v1/events').as('getEventsAfterDelete')
    cy.get('table tbody tr').first().within(() => {
      cy.get('button').eq(1).click() // Delete button (second button)
    })
    cy.wait('@deleteEvent')
    cy.wait('@getEventsAfterDelete')

    // Verify event is deleted
    cy.contains('Evento para Deletar').should('not.exist')
  })
})