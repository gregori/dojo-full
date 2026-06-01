// Custom Cypress commands for Dojo Admin

// Login command - fills the login form and submits
Cypress.Commands.add('login', (email: string, password: string) => {
  cy.visit('/login')
  cy.get('input[type="email"]').type(email)
  cy.get('input[type="password"]').type(password)
  cy.get('button[type="submit"]').click()

  // Wait for navigation or token to be set
  cy.wait('@loginRequest', { requestTimeout: 10000 }).then((interception) => {
    if (interception.response?.statusCode === 200) {
      // Verify token is stored
      cy.window().its('localStorage').invoke('getItem', 'token').should('exist')
    }
  })
})

// Clear auth state
Cypress.Commands.add('logout', () => {
  cy.window().then((win) => {
    win.localStorage.removeItem('token')
  })
  cy.visit('/login')
})

// Check if user is authenticated
Cypress.Commands.add('isAuthenticated', () => {
  cy.window().its('localStorage').invoke('getItem', 'token').should('exist')
})