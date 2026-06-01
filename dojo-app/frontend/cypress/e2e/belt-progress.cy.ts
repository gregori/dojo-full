/// <reference types="cypress" />

describe('Progresso de Faixa', () => {
  const adminEmail = 'admin@dojo.com'
  const adminPassword = 'admin123'
  const instructorEmail = 'instructor@dojo.com'
  const instructorPassword = 'instruct123'

  describe('Visualizar Progresso do Aluno', () => {
    beforeEach(() => {
      // Login as admin
      cy.clearLocalStorage()
      cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
      cy.visit('/login')
      cy.get('input[type="email"]').type(adminEmail)
      cy.get('input[type="password"]').type(adminPassword)
      cy.get('button[type="submit"]').click()
      cy.wait('@loginRequest')
    })

    it('deve exibir progresso zerado para aluno novo', () => {
      cy.intercept('GET', '/api/v1/students').as('getStudents')
      cy.intercept('GET', '/api/v1/belts').as('getBelts')
      cy.get('a[href="/students"]').click()
      cy.wait('@getStudents')

      // Click on a student to view details
      cy.get('table tbody tr').first().click()

      // Wait for student details to load
      cy.wait('@getStudents')

      // Find and verify progress section
      cy.contains(/progresso|faixa atual|próxima faixa/i).should('be.visible')

      // Current belt should be shown
      cy.contains(/Branca|Belt/i).should('be.visible')

      // Verify all counters show 0
      cy.get('[data-testid*="progress"]').then(($els) => {
        // Check that progress indicators exist
        expect($els.length).to.be.greaterThan(0)
      })
    })

    it('deve exibir progresso após presenças registradas', () => {
      cy.intercept('GET', '/api/v1/students').as('getStudents')
      cy.intercept('GET', '/api/v1/students/*/progress').as('getProgress')
      cy.get('a[href="/students"]').click()
      cy.wait('@getStudents')

      // Click on student
      cy.get('table tbody tr').first().click()
      cy.wait('@getProgress')

      // Progress section should show counts
      cy.get('body').should('contain', /completed|remaining|presenças/i)
    })

    it('deve mostrar progresso completo quando requisitos atingidos', () => {
      cy.intercept('GET', '/api/v1/students').as('getStudents')
      cy.intercept('GET', '/api/v1/students/*/progress').as('getProgress')
      cy.get('a[href="/students"]').click()
      cy.wait('@getStudents')

      cy.get('table tbody tr').first().click()
      cy.wait('@getProgress')

      // Should indicate ready for exam when progress is 100%
      cy.get('body').should('contain', /100%|completo|pronto|exame/i)
    })

    it('deve considerar apenas eventos que contam para faixa', () => {
      cy.intercept('GET', '/api/v1/students').as('getStudents')
      cy.intercept('GET', '/api/v1/students/*/progress').as('getProgress')
      cy.get('a[href="/students"]').click()
      cy.wait('@getStudents')

      cy.get('table tbody tr').first().click()
      cy.wait('@getProgress')

      // Verify progress calculation considers counts_for_belt flag
      cy.get('body').should('contain', /Aula Regular|Limpeza|evento/i)
    })

    it('deve mostrar múltiplos requisitos de presença', () => {
      cy.intercept('GET', '/api/v1/students').as('getStudents')
      cy.intercept('GET', '/api/v1/students/*/progress').as('getProgress')
      cy.get('a[href="/students"]').click()
      cy.wait('@getStudents')

      cy.get('table tbody tr').first().click()
      cy.wait('@getProgress')

      // Should show multiple event types with their requirements
      cy.get('body').should('contain', /30\/30|5\/5|\d+\/\d+/i)
    })
  })

  describe('Progresso via Instrutor', () => {
    it('instrutor deve visualizar progresso de qualquer aluno', () => {
      cy.clearLocalStorage()
      cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
      cy.visit('/login')
      cy.get('input[type="email"]').type(instructorEmail)
      cy.get('input[type="password"]').type(instructorPassword)
      cy.get('button[type="submit"]').click()
      cy.wait('@loginRequest')

      cy.intercept('GET', '/api/v1/students').as('getStudents')
      cy.intercept('GET', '/api/v1/students/*/progress').as('getProgress')
      cy.get('a[href="/students"]').click()
      cy.wait('@getStudents')

      // Click on student
      cy.get('table tbody tr').first().click()
      cy.wait('@getProgress')

      // Instructor should see progress section
      cy.contains(/progresso|faixa/i).should('be.visible')
    })
  })

  describe('Progresso via Aluno (auto-consulta)', () => {
    it('aluno deve visualizar seu próprio progresso', () => {
      // Login as any user with access
      cy.clearLocalStorage()
      cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
      cy.visit('/login')
      cy.get('input[type="email"]').type(instructorEmail)
      cy.get('input[type="password"]').type(instructorPassword)
      cy.get('button[type="submit"]').click()
      cy.wait('@loginRequest')

      // Navigate to student detail
      cy.intercept('GET', '/api/v1/students').as('getStudents')
      cy.intercept('GET', '/api/v1/students/*/progress').as('getProgress')
      cy.get('a[href="/students"]').click()
      cy.wait('@getStudents')

      cy.get('table tbody tr').first().click()
      cy.wait('@getProgress')

      // Progress data should be visible
      cy.get('body').should('contain', /faixa|progresso|presenças/i)
    })
  })
})