/// <reference types="cypress" />

describe('QR Codes de Check-in e Links de Pré-Check-in', () => {
  const testEmail = 'admin@dojo.com'
  const testPassword = 'admin123'

  function login() {
    cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
    cy.visit('/login')
    cy.get('input[type="email"]').type(testEmail)
    cy.get('input[type="password"]').type(testPassword)
    cy.get('button[type="submit"]').click()
    cy.wait('@loginRequest')
  }

  beforeEach(() => {
    cy.clearLocalStorage()
  })

  it('opens the QR modal from the Events page showing the event title and a QR image (QRL-01)', () => {
    login()

    cy.intercept('GET', '/api/v1/events').as('getEvents')
    cy.intercept('GET', '/api/v1/events/types').as('getEventTypes')
    cy.get('a[href="/events"]').click()
    cy.wait('@getEvents')
    cy.wait('@getEventTypes')

    const eventTitle = `Evento QR ${Date.now()}`

    cy.contains('Novo Evento').click()
    cy.get('input[type="text"]').first().type(eventTitle)
    cy.get('select').first().select(0)
    cy.get('input[type="datetime-local"]').first().type('2030-12-01T10:00')

    cy.intercept('POST', '/api/v1/events').as('createEvent')
    cy.contains('button', 'Criar').click()
    cy.wait('@createEvent')

    cy.contains('tr', eventTitle).within(() => {
      cy.get('[title="Ver QR code de check-in"]').click()
    })

    cy.contains('h3', eventTitle).should('be.visible')
    cy.get('[role="img"][aria-label^="QR code de check-in"]').should('be.visible')
  })

  it('opens the QR modal from the Event Series page showing the series title and a QR image (QRL-01, series variant)', () => {
    login()

    cy.intercept('GET', '/api/v1/event-series').as('getSeries')
    cy.intercept('GET', '/api/v1/events/types').as('getEventTypes')
    cy.get('a[href="/event-series"]').click()
    cy.wait('@getSeries')
    cy.wait('@getEventTypes')

    const seriesTitle = `Serie QR ${Date.now()}`

    cy.contains('Nova Série').click()
    cy.contains('Título').parent().find('input[type="text"]').type(seriesTitle)
    cy.contains('Tipo').parent().find('select').select(1)
    cy.contains('label', 'Segunda').find('input[type="checkbox"]').check({ force: true })

    cy.intercept('POST', '/api/v1/event-series').as('createSeries')
    cy.contains('button', 'Criar').click()
    cy.wait('@createSeries')

    cy.contains('tr', seriesTitle).within(() => {
      cy.get('[title="Ver QR code de check-in"]').click()
    })

    cy.contains('h3', seriesTitle).should('be.visible')
    cy.get('[role="img"][aria-label^="QR code de check-in"]').should('be.visible')
  })

  it('print control opens in a new tab and the print page renders the title, QR image, and triggers window.print() (QRL-04, QRL-05)', () => {
    login()

    cy.intercept('GET', '/api/v1/events').as('getEvents')
    cy.intercept('GET', '/api/v1/events/types').as('getEventTypes')
    cy.get('a[href="/events"]').click()
    cy.wait('@getEvents')
    cy.wait('@getEventTypes')

    const eventTitle = `Evento Print ${Date.now()}`

    cy.contains('Novo Evento').click()
    cy.get('input[type="text"]').first().type(eventTitle)
    cy.get('select').first().select(0)
    cy.get('input[type="datetime-local"]').first().type('2030-12-01T10:00')

    cy.intercept('POST', '/api/v1/events').as('createEvent')
    cy.contains('button', 'Criar').click()
    cy.wait('@createEvent')

    cy.contains('tr', eventTitle).within(() => {
      cy.get('[title="Ver QR code de check-in"]').click()
    })

    cy.contains('a', 'Imprimir')
      .should('have.attr', 'target', '_blank')
      .and('have.attr', 'href')
      .and('include', '/checkin-print?token=')

    // Cypress cannot drive a second real browser tab, so the target
    // attribute is removed to make the click navigate in the current tab.
    // The title is stored in localStorage (not the URL) by the anchor's
    // onClick handler, so clicking (rather than just visiting the href) is
    // required: it proves the handler runs before navigation, since the
    // print page below would fall back to "Check-in" instead of the real
    // title otherwise. The target="_blank" assertion above already proves
    // the link would open in a new tab (QRL-05).
    cy.contains('a', 'Imprimir').invoke('removeAttr', 'target').click()

    cy.contains('h1', eventTitle).should('be.visible')
    cy.get('[role="img"][aria-label^="QR code de check-in"]').should('be.visible')

    cy.window().then((win) => cy.stub(win, 'print').as('printStub'))
    cy.contains('button', 'Imprimir').click()
    cy.get('@printStub').should('have.been.calledOnce')
  })

  it('copies the generic pre-check-in link from the toolbar (QRL-06, QRL-08)', () => {
    login()

    cy.intercept('GET', '/api/v1/events').as('getEvents')
    cy.intercept('GET', '/api/v1/events/types').as('getEventTypes')
    cy.get('a[href="/events"]').click()
    cy.wait('@getEvents')
    cy.wait('@getEventTypes')

    cy.window().then((win) => {
      cy.stub(win.navigator.clipboard, 'writeText').resolves().as('copyStub')
    })

    cy.contains('button', 'Copiar link de pré-check-in').click()

    cy.window().then((win) => {
      cy.get('@copyStub').should('have.been.calledWith', `${win.location.origin}/precheckin`)
    })
    cy.contains('Link copiado').should('be.visible')
  })

  it("copies a specific event's pre-check-in link from its row (QRL-07)", () => {
    login()

    cy.intercept('GET', '/api/v1/events').as('getEvents')
    cy.intercept('GET', '/api/v1/events/types').as('getEventTypes')
    cy.get('a[href="/events"]').click()
    cy.wait('@getEvents')
    cy.wait('@getEventTypes')

    const eventTitle = `Evento Copiar Link ${Date.now()}`

    cy.contains('Novo Evento').click()
    cy.get('input[type="text"]').first().type(eventTitle)
    cy.get('select').first().select(0)
    cy.get('input[type="datetime-local"]').first().type('2030-12-01T10:00')

    cy.intercept('POST', '/api/v1/events').as('createEvent')
    cy.contains('button', 'Criar').click()
    cy.wait('@createEvent').then((interception) => {
      const eventId = interception.response?.body?.id

      cy.window().then((win) => {
        cy.stub(win.navigator.clipboard, 'writeText').resolves().as('copyStub')
      })

      cy.contains('tr', eventTitle).within(() => {
        cy.get('[title="Copiar link de pré-check-in"]').click()
      })

      cy.window().then((win) => {
        cy.get('@copyStub').should(
          'have.been.calledWith',
          `${win.location.origin}/precheckin?event_id=${eventId}`
        )
      })
    })
  })

  it('QR modal on the Events page remains fully visible with no horizontal overflow at mobile width (QRL-10)', () => {
    cy.viewport(375, 667)
    login()

    cy.intercept('GET', '/api/v1/events').as('getEvents')
    cy.intercept('GET', '/api/v1/events/types').as('getEventTypes')
    cy.get('a[href="/events"]').click()
    cy.wait('@getEvents')
    cy.wait('@getEventTypes')

    const eventTitle = `Evento Mobile ${Date.now()}`

    cy.contains('Novo Evento').click()
    cy.get('input[type="text"]').first().type(eventTitle)
    cy.get('select').first().select(0)
    cy.get('input[type="datetime-local"]').first().type('2030-12-01T10:00')

    cy.intercept('POST', '/api/v1/events').as('createEvent')
    cy.contains('button', 'Criar').click()
    cy.wait('@createEvent')

    cy.contains('tr', eventTitle).within(() => {
      cy.get('[title="Ver QR code de check-in"]').click()
    })

    cy.contains('h3', eventTitle).should('be.visible')
    cy.get('[role="img"][aria-label^="QR code de check-in"]').should('be.visible')
    cy.contains('a', 'Imprimir').should('be.visible')

    cy.document().then((doc) => {
      expect(doc.documentElement.scrollWidth).to.be.at.most(doc.documentElement.clientWidth)
    })
  })

  it('QR modal on the Event Series page remains fully visible with no horizontal overflow at mobile width (QRL-10, series variant)', () => {
    cy.viewport(375, 667)
    login()

    cy.intercept('GET', '/api/v1/event-series').as('getSeries')
    cy.intercept('GET', '/api/v1/events/types').as('getEventTypes')
    cy.get('a[href="/event-series"]').click()
    cy.wait('@getSeries')
    cy.wait('@getEventTypes')

    const seriesTitle = `Serie Mobile ${Date.now()}`

    cy.contains('Nova Série').click()
    cy.contains('Título').parent().find('input[type="text"]').type(seriesTitle)
    cy.contains('Tipo').parent().find('select').select(1)
    cy.contains('label', 'Segunda').find('input[type="checkbox"]').check({ force: true })

    cy.intercept('POST', '/api/v1/event-series').as('createSeries')
    cy.contains('button', 'Criar').click()
    cy.wait('@createSeries')

    cy.contains('tr', seriesTitle).within(() => {
      cy.get('[title="Ver QR code de check-in"]').click()
    })

    cy.contains('h3', seriesTitle).should('be.visible')
    cy.get('[role="img"][aria-label^="QR code de check-in"]').should('be.visible')
    cy.contains('a', 'Imprimir').should('be.visible')

    cy.document().then((doc) => {
      expect(doc.documentElement.scrollWidth).to.be.at.most(doc.documentElement.clientWidth)
    })
  })
})
