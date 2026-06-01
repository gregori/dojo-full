/// <reference types="cypress" />

describe('Autenticação', () => {
  const adminEmail = 'admin@dojo.com'
  const adminPassword = 'admin123'
  const instructorEmail = 'instructor@dojo.com'
  const instructorPassword = 'instruct123'

  describe('Login', () => {
    beforeEach(() => {
      cy.clearLocalStorage()
      cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
      cy.visit('/login')
    })

    it('deve fazer login com credenciais válidas de admin', () => {
      cy.get('input[type="email"]').type(adminEmail)
      cy.get('input[type="password"]').type(adminPassword)
      cy.get('button[type="submit"]').click()

      cy.wait('@loginRequest').then((interception) => {
        expect(interception.response?.statusCode).to.eq(200)
        expect(interception.response?.body).to.have.property('access_token')
      })

      // Verify token is stored and redirects to dashboard
      cy.window().its('localStorage').invoke('getItem', 'token').should('exist')
      cy.url().should('include', '/dashboard')
    })

    it('deve fazer login com credenciais válidas de instrutor', () => {
      cy.get('input[type="email"]').type(instructorEmail)
      cy.get('input[type="password"]').type(instructorPassword)
      cy.get('button[type="submit"]').click()

      cy.wait('@loginRequest').then((interception) => {
        expect(interception.response?.statusCode).to.eq(200)
        expect(interception.response?.body).to.have.property('access_token')
        expect(interception.response?.body).to.have.property('role', 'instructor')
      })

      cy.window().its('localStorage').invoke('getItem', 'token').should('exist')
      cy.url().should('include', '/dashboard')
    })

    it('deve rejeitar login com senha incorreta', () => {
      cy.get('input[type="email"]').type(adminEmail)
      cy.get('input[type="password"]').type('senhaerrada')
      cy.get('button[type="submit"]').click()

      cy.wait('@loginRequest').then((interception) => {
        expect(interception.response?.statusCode).to.eq(401)
      })

      // Verify error message is shown
      cy.contains(/credenciais inválidas|email ou senha/i).should('be.visible')
      // Verify user stays on login page
      cy.url().should('include', '/login')
    })

    it('deve rejeitar login com email inexistente', () => {
      cy.get('input[type="email"]').type('naoexiste@dojo.com')
      cy.get('input[type="password"]').type('qualquer123')
      cy.get('button[type="submit"]').click()

      cy.wait('@loginRequest').then((interception) => {
        expect(interception.response?.statusCode).to.eq(401)
      })

      // Verify generic error message (doesn't reveal if email exists)
      cy.contains(/credenciais inválidas|email ou senha/i).should('be.visible')
      cy.url().should('include', '/login')
    })

    it('deve validar campos obrigatórios do formulário', () => {
      // Try to submit empty form
      cy.get('button[type="submit"]').click()

      // HTML5 validation should prevent submission
      cy.get('input[type="email"]').should('have.attr', 'required')
      cy.get('input[type="password"]').should('have.attr', 'required')

      // Verify no login request was made
      cy.get('@loginRequest.all').should('have.length', 0)
    })
  })

  describe('Controle de Acesso por Papel', () => {
    it('admin deve ver todas as páginas do menu', () => {
      cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
      cy.visit('/login')
      cy.get('input[type="email"]').type(adminEmail)
      cy.get('input[type="password"]').type(adminPassword)
      cy.get('button[type="submit"]').click()
      cy.wait('@loginRequest')

      // Admin should see all navigation links
      cy.get('a[href="/dashboard"]').should('exist')
      cy.get('a[href="/students"]').should('exist')
      cy.get('a[href="/events"]').should('exist')
      cy.get('a[href="/exams"]').should('exist')
      cy.get('a[href="/belts"]').should('exist')
      cy.get('a[href="/event-types"]').should('exist')
      cy.get('a[href="/dojos"]').should('exist')
      cy.get('a[href="/belt-requirements"]').should('exist')
    })

    it('instrutor NÃO deve ver páginas admin-only no menu', () => {
      cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
      cy.visit('/login')
      cy.get('input[type="email"]').type(instructorEmail)
      cy.get('input[type="password"]').type(instructorPassword)
      cy.get('button[type="submit"]').click()
      cy.wait('@loginRequest')

      // Instructor should see these links
      cy.get('a[href="/dashboard"]').should('exist')
      cy.get('a[href="/students"]').should('exist')
      cy.get('a[href="/events"]').should('exist')
      cy.get('a[href="/exams"]').should('exist')

      // Instructor should NOT see admin-only links
      cy.get('a[href="/belts"]').should('not.exist')
      cy.get('a[href="/event-types"]').should('not.exist')
      cy.get('a[href="/dojos"]').should('not.exist')
      cy.get('a[href="/belt-requirements"]').should('not.exist')
    })

    it('instrutor redirecionado ao acessar rota admin diretamente', () => {
      cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
      cy.visit('/login')
      cy.get('input[type="email"]').type(instructorEmail)
      cy.get('input[type="password"]').type(instructorPassword)
      cy.get('button[type="submit"]').click()
      cy.wait('@loginRequest')

      // Try to access admin-only route directly
      cy.visit('/belt-requirements')

      // Should be redirected (to dashboard or show access denied)
      cy.url().should('not.include', '/belt-requirements')
      cy.url().should.match(/(\/dashboard|\/login)/)
    })

    it('usuário não autenticado redirecionado para login', () => {
      // Clear any existing auth
      cy.clearLocalStorage()
      cy.visit('/students')

      // Should redirect to login
      cy.url().should('include', '/login')
    })
  })

  describe('Logout', () => {
    it('deve fazer logout e limpar sessão', () => {
      // Login first
      cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
      cy.visit('/login')
      cy.get('input[type="email"]').type(adminEmail)
      cy.get('input[type="password"]').type(adminPassword)
      cy.get('button[type="submit"]').click()
      cy.wait('@loginRequest')

      // Verify logged in
      cy.window().its('localStorage').invoke('getItem', 'token').should('exist')

      // Click logout button (assuming there's a logout button in the nav)
      cy.contains('Sair').click()

      // Verify token is cleared
      cy.window().its('localStorage').invoke('getItem', 'token').should('not.exist')

      // Verify redirected to login
      cy.url().should('include', '/login')
    })

    it('página de check-in acessível sem login', () => {
      cy.clearLocalStorage()
      cy.visit('/checkin')

      // Check-in page should load without redirect
      cy.url().should('include', '/checkin')
      // Should see check-in form elements
      cy.get('input[placeholder*="matrícula"]').should('exist')
      cy.get('input[placeholder*="PIN"]').should('exist')
    })
  })
})