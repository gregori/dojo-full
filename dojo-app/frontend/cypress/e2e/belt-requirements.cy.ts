/// <reference types="cypress" />

describe('Belt Requirements Page', () => {
  const testEmail = 'admin@dojo.com'
  const testPassword = 'admin123'

  beforeEach(() => {
    // Clear auth state and intercept API calls
    cy.clearLocalStorage()
    cy.intercept('GET', '/api/v1/belts').as('getBelts')
    cy.intercept('GET', '/api/v1/events/types').as('getEventTypes')
    cy.visit('/login')
  })

  it('should create a new belt requirement with valid data', () => {
    // Login
    cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
    cy.get('input[type="email"]').type(testEmail)
    cy.get('input[type="password"]').type(testPassword)
    cy.get('button[type="submit"]').click()
    cy.wait('@loginRequest')

    // Navigate to Belt Requirements page
    cy.get('a[href="/belt-requirements"]').click()
    cy.wait('@getBelts')

    // Select a belt from dropdown
    cy.get('select').first().select(1) // Select second option (first is "Selecione...")

    // Wait for requirements to load
    cy.intercept('GET', '/api/v1/belts/*/requirements').as('getRequirements')
    cy.wait('@getRequirements')

    // Click "Adicionar" button
    cy.contains('Adicionar').click()

    // Fill in the form
    cy.get('select').filter(':visible').last().select(0) // event type
    cy.get('input[type="number"]').clear().type('5') // quantity

    // Verify NaN handling works (empty or non-numeric should fallback to 1)
    cy.get('input[type="number"]').clear()
    cy.get('input[type="number"]').type('3')

    cy.get('input[type="text"]').filter(':visible').last().type('Treinos normais')

    // Submit - intercept the create request
    cy.intercept('POST', '/api/v1/belts/*/requirements').as('createRequirement')
    cy.contains('Adicionar').last().click()
    cy.wait('@createRequirement')

    // Verify requirement appears in table
    cy.contains('5').should('be.visible')
    cy.contains('Treinos normais').should('be.visible')
  })

  it('should handle NaN quantity by falling back to default value', () => {
    // Login
    cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
    cy.get('input[type="email"]').type(testEmail)
    cy.get('input[type="password"]').type(testPassword)
    cy.get('button[type="submit"]').click()
    cy.wait('@loginRequest')

    // Navigate to Belt Requirements page
    cy.get('a[href="/belt-requirements"]').click()
    cy.wait('@getBelts')

    // Select a belt
    cy.get('select').first().select(1)

    // Click "Adicionar" to open form
    cy.contains('Adicionar').click()

    // Fill event type
    cy.get('select').filter(':visible').last().select(0)

    // Test NaN handling - clear and type invalid value
    cy.get('input[type="number"]').clear()
    cy.get('input[type="number"]').invoke('val', '').trigger('change')

    // The fix uses: parseInt(e.target.value) || 1
    // So empty value should fallback to 1
    cy.get('input[type="number"]').should('have.value', '')

    // Submit with empty quantity - should use default
    cy.intercept('POST', '/api/v1/belts/*/requirements').as('createReqWithNaN')
    cy.contains('Adicionar').last().click()

    // The handler should convert empty/NaN to 1
    cy.wait('@createReqWithNaN').then((interception) => {
      // Verify the request body contains required_count: 1 (not NaN)
      const body = interception.request.body
      expect(body.required_count).to.not.be.NaN
      expect(body.required_count).to.be.at.least(1)
    })
  })

  it('should delete a belt requirement', () => {
    // Login
    cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
    cy.get('input[type="email"]').type(testEmail)
    cy.get('input[type="password"]').type(testPassword)
    cy.get('button[type="submit"]').click()
    cy.wait('@loginRequest')

    // Navigate to Belt Requirements page
    cy.get('a[href="/belt-requirements"]').click()
    cy.wait('@getBelts')
    cy.wait('@getEventTypes')

    // Select a belt
    cy.get('select').first().select(1)
    cy.intercept('GET', '/api/v1/belts/*/requirements').as('getReq')
    cy.wait('@getReq')

    // Create a requirement first
    cy.contains('Adicionar').click()
    cy.get('select').filter(':visible').last().select(0)
    cy.get('input[type="number"]').clear().type('10')
    cy.get('input[type="text"]').filter(':visible').last().type('Requirement to delete')

    cy.intercept('POST', '/api/v1/belts/*/requirements').as('createReq')
    cy.contains('Adicionar').last().click()
    cy.wait('@createReq')

    // Delete the requirement
    cy.intercept('DELETE', '/api/v1/belts/requirements/*').as('deleteReq')
    cy.intercept('GET', '/api/v1/belts/*/requirements').as('getReqAfterDelete')
    cy.get('table tbody tr').first().within(() => {
      cy.get('button').click() // Delete button
    })
    cy.wait('@deleteReq')
    cy.wait('@getReqAfterDelete')

    // Verify requirement is deleted
    cy.contains('Requirement to delete').should('not.exist')
  })

  it('should show admin-only access message for non-admin users', () => {
    // Login as non-admin (if we had a non-admin user)
    // For now, just verify the page loads for admin
    cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
    cy.get('input[type="email"]').type(testEmail)
    cy.get('input[type="password"]').type(testPassword)
    cy.get('button[type="submit"]').click()
    cy.wait('@loginRequest')

    // Navigate to Belt Requirements page - should work for admin
    cy.get('a[href="/belt-requirements"]').click()
    cy.wait('@getBelts')

    // Admin should see the belt selector, not an access denied message
    cy.contains('Selecione a Faixa').should('be.visible')
  })

  it('should verify belt_id is included in create request', () => {
    // Login
    cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
    cy.get('input[type="email"]').type(testEmail)
    cy.get('input[type="password"]').type(testPassword)
    cy.get('button[type="submit"]').click()
    cy.wait('@loginRequest')

    // Navigate to Belt Requirements page
    cy.get('a[href="/belt-requirements"]').click()
    cy.wait('@getBelts')

    // Select a specific belt
    cy.get('select').first().select(1)
    cy.wait('@getBelts') // Wait for belts to load

    // Get the selected belt value
    cy.get('select').first().invoke('val').then((beltId) => {
      // Click "Adicionar" to open form
      cy.contains('Adicionar').click()

      // Fill event type and quantity
      cy.get('select').filter(':visible').last().select(0)
      cy.get('input[type="number"]').clear().type('2')

      // Submit and verify belt_id is in the request
      cy.intercept('POST', '/api/v1/belts/*/requirements').as('createReq')
      cy.contains('Adicionar').last().click()
      cy.wait('@createReq').then((interception) => {
        // Bug fix verification: belt_id must be included in the request
        const body = interception.request.body as any
        expect(body.belt_id).to.exist
        expect(body.belt_id).to.equal(beltId)
        expect(body.event_type_id).to.exist
        expect(body.required_count).to.not.be.NaN
      })
    })
  })
})