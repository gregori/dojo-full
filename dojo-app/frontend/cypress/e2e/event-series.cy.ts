/// <reference types="cypress" />

describe('Aulas Recorrentes (Event Series)', () => {
  const testEmail = 'admin@dojo.com'
  const testPassword = 'admin123'

  beforeEach(() => {
    cy.clearLocalStorage()
    cy.intercept('GET', '/api/v1/event-series').as('getSeries')
    cy.intercept('GET', '/api/v1/events/types').as('getEventTypes')
    cy.intercept('GET', '/api/v1/belts').as('getBelts')
    cy.visit('/login')
  })

  function login(email = testEmail, password = testPassword) {
    cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
    cy.get('input[type="email"]').type(email)
    cy.get('input[type="password"]').type(password)
    cy.get('button[type="submit"]').click()
    cy.wait('@loginRequest')
  }

  it('creates a series, generates occurrences, and the generated occurrence is visible on the Events page', () => {
    login()

    cy.get('a[href="/event-series"]').click()
    cy.wait('@getSeries')
    cy.wait('@getEventTypes')

    const seriesTitle = `Aikido Geral ${Date.now()}`

    cy.contains('Nova Série').click()

    cy.contains('Título')
      .parent()
      .find('input[type="text"]')
      .type(seriesTitle)
    cy.contains('Tipo').parent().find('select').select(1)

    // Select every weekday so today's date is always a scheduled day,
    // regardless of which day the suite runs on.
    ;['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'].forEach((day) => {
      cy.contains('label', day).find('input[type="checkbox"]').check({ force: true })
    })

    cy.intercept('POST', '/api/v1/event-series').as('createSeries')
    cy.contains('button', 'Criar').click()
    cy.wait('@createSeries').then((interception) => {
      expect(interception.response?.statusCode).to.eq(201)
    })

    // Trigger "Gerar ocorrências" for the newly created series.
    cy.intercept('POST', '/api/v1/event-series/*/generate').as('generateOccurrences')
    cy.contains('tr', seriesTitle).within(() => {
      cy.get('[title="Gerar ocorrências"]').click()
    })
    cy.wait('@generateOccurrences').then((interception) => {
      expect(interception.response?.statusCode).to.eq(200)
      expect(interception.response?.body.created_count).to.be.greaterThan(0)
    })

    // The generated occurrence is an ordinary Event, manageable via the
    // existing, untouched EventsPage.tsx list (RES-07's backward-compat claim).
    cy.intercept('GET', '/api/v1/events').as('getEvents')
    cy.get('a[href="/events"]').click()
    cy.wait('@getEvents')
    cy.contains(seriesTitle).should('be.visible')
  })

  it('ends a series and confirms re-generating afterward reports created_count: 0', () => {
    login()

    cy.get('a[href="/event-series"]').click()
    cy.wait('@getSeries')
    cy.wait('@getEventTypes')

    const seriesTitle = `Encerrar Série ${Date.now()}`

    cy.contains('Nova Série').click()
    cy.contains('Título').parent().find('input[type="text"]').type(seriesTitle)
    cy.contains('Tipo').parent().find('select').select(1)
    cy.contains('label', 'Segunda').find('input[type="checkbox"]').check({ force: true })

    cy.intercept('POST', '/api/v1/event-series').as('createSeries')
    cy.contains('button', 'Criar').click()
    cy.wait('@createSeries')

    cy.intercept('DELETE', '/api/v1/event-series/*').as('deactivateSeries')
    cy.contains('tr', seriesTitle).within(() => {
      cy.get('[title="Encerrar série"]').click()
    })
    cy.wait('@deactivateSeries').then((interception) => {
      expect(interception.response?.statusCode).to.eq(204)
    })

    cy.wait('@getSeries')
    cy.contains('tr', seriesTitle).within(() => {
      cy.contains('Encerrada').should('be.visible')
    })

    cy.intercept('POST', '/api/v1/event-series/*/generate').as('generateAfterEnd')
    cy.contains('tr', seriesTitle).within(() => {
      cy.get('[title="Gerar ocorrências"]').click()
    })
    cy.wait('@generateAfterEnd').then((interception) => {
      expect(interception.response?.statusCode).to.eq(200)
      expect(interception.response?.body.created_count).to.eq(0)
    })
  })
})
