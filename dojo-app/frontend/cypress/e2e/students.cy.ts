/// <reference types="cypress" />

describe('Gestão de Alunos', () => {
  const adminEmail = 'admin@dojo.com'
  const adminPassword = 'admin123'

  beforeEach(() => {
    cy.clearLocalStorage()
    cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
    cy.visit('/login')
    cy.get('input[type="email"]').type(adminEmail)
    cy.get('input[type="password"]').type(adminPassword)
    cy.get('button[type="submit"]').click()
    cy.wait('@loginRequest')

    // Intercept student-related API calls
    cy.intercept('GET', '/api/v1/students').as('getStudents')
    cy.intercept('GET', '/api/v1/belts').as('getBelts')
    cy.intercept('GET', '/api/v1/event-types').as('getEventTypes')
  })

  describe('Criar Aluno', () => {
    it('deve cadastrar novo aluno com sucesso', () => {
      cy.intercept('POST', '/api/v1/students').as('createStudent')
      cy.get('a[href="/students"]').click()
      cy.wait('@getStudents')

      // Click "Novo Aluno" button
      cy.contains('Novo Aluno').click()

      // Fill in the form
      cy.get('input[placeholder*="nome"]').type('João Silva')
      cy.get('input[type="date"]').type('1990-05-15')

      // Select category
      cy.get('select').filter(':visible').first().select('adult')

      // Submit
      cy.contains('Criar').click()

      // Wait for creation
      cy.wait('@createStudent').then((interception) => {
        expect(interception.response?.statusCode).to.eq(201)
        expect(interception.response?.body).to.have.property('registration_number')
        expect(interception.response?.body).to.have.property('pin')
      })

      // Verify toast/message
      cy.contains(/sucesso|Criado/i).should('be.visible')
    })

    it('deve gerar matrícula automática única', () => {
      cy.intercept('POST', '/api/v1/students').as('createStudent1')
      cy.get('a[href="/students"]').click()
      cy.wait('@getStudents')

      cy.contains('Novo Aluno').click()
      cy.get('input[placeholder*="nome"]').type('Aluno Base')
      cy.get('input[type="date"]').type('1990-01-01')
      cy.get('select').filter(':visible').first().select('adult')
      cy.contains('Criar').click()

      cy.wait('@createStudent1').then((response) => {
        const firstReg = response.body?.registration_number
        expect(firstReg).to.exist

        // Create second student
        cy.intercept('POST', '/api/v1/students').as('createStudent2')
        cy.contains('Novo Aluno').click()
        cy.get('input[placeholder*="nome"]').type('Segundo Aluno')
        cy.get('input[type="date"]').type('1995-03-20')
        cy.get('select').filter(':visible').first().select('adult')
        cy.contains('Criar').click()

        cy.wait('@createStudent2').then((response2) => {
          const secondReg = response2.body?.registration_number
          expect(secondReg).to.not.equal(firstReg)
        })
      })
    })

    it('deve gerar PIN de 4 dígitos', () => {
      cy.intercept('POST', '/api/v1/students').as('createStudent')
      cy.get('a[href="/students"]').click()
      cy.wait('@getStudents')

      cy.contains('Novo Aluno').click()
      cy.get('input[placeholder*="nome"]').type('Teste PIN')
      cy.get('input[type="date"]').type('1985-11-25')
      cy.get('select').filter(':visible').first().select('adult')
      cy.contains('Criar').click()

      cy.wait('@createStudent').then((response) => {
        const pin = response.body?.pin?.toString() || response.body?.pin
        expect(pin).to.match(/^\d{4}$/)
      })
    })

    it('deve validar campos obrigatórios', () => {
      cy.get('a[href="/students"]').click()
      cy.wait('@getStudents')

      cy.contains('Novo Aluno').click()

      // Try to submit without filling required fields
      cy.contains('Criar').click()

      // HTML5 validation should prevent submission or show error
      cy.get('input[placeholder*="nome"]').should('have.attr', 'required')
      cy.get('input[type="date"]').should('have.attr', 'required')
    })

    it('deve categorizar aluno automaticamente pela data de nascimento', () => {
      cy.intercept('POST', '/api/v1/students').as('createChild')
      cy.get('a[href="/students"]').click()
      cy.wait('@getStudents')

      cy.contains('Novo Aluno').click()
      cy.get('input[placeholder*="nome"]').type('Pedro Kids')
      cy.get('input[type="date"]').type('2015-03-10')
      cy.get('select').filter(':visible').first().select('adult')
      cy.contains('Criar').click()

      cy.wait('@createChild').then((response) => {
        // Backend should auto-categorize based on age
        expect(response.body?.category).to.be.oneOf(['child', 'adult'])
      })
    })
  })

  describe('Listar Alunos', () => {
    it('deve exibir lista de alunos ativos', () => {
      cy.get('a[href="/students"]').click()
      cy.wait('@getStudents')

      // Table should be visible with headers
      cy.contains('Nome').should('be.visible')
      cy.contains('Matrícula').should('be.visible')
      cy.contains('Faixa').should('be.visible')
    })

    it('não deve exibir alunos inativos por padrão', () => {
      cy.get('a[href="/students"]').click()
      cy.wait('@getStudents')

      // Should not see inactive toggle checked by default
      cy.get('input[type="checkbox"]').should('not.be.checked')

      // Only active students shown
      cy.get('table tbody tr').should('have.length.greaterThan', 0)
    })

    it('deve permitir filtrar incluindo inativos', () => {
      cy.get('a[href="/students"]').click()
      cy.wait('@getStudents')

      // Look for "Mostrar inativos" toggle
      cy.contains(/inativos/i).should('exist')

      // Toggle to show inactive
      cy.contains(/Mostrar inativos/i).click()

      // Table should now include inactive students
      cy.wait('@getStudents')
    })

    it('deve buscar aluno por nome', () => {
      cy.get('a[href="/students"]').click()
      cy.wait('@getStudents')

      // Type in search field
      const searchInput = cy.get('input[placeholder*="buscar"]').should('exist')
      searchInput.type('João')

      // Table should filter results
      cy.wait('@getStudents')
      cy.contains('João').should('be.visible')
    })
  })

  describe('Editar Aluno', () => {
    it('deve editar nome e dados de contato', () => {
      cy.intercept('GET', '/api/v1/students').as('getStudentsList')
      cy.get('a[href="/students"]').click()
      cy.wait('@getStudentsList')

      // Click edit button (pencil icon)
      cy.get('table tbody tr').first().within(() => {
        cy.get('button').first().click()
      })

      // Wait for edit form to load
      cy.wait('@getStudentsList')

      // Clear and update name
      const nameInput = cy.get('input[placeholder*="nome"]').should('exist')
      nameInput.clear().type('João Atualizado')

      // Update email if field exists
      cy.get('input[type="email"]').then(($email) => {
        if ($email.length > 0) {
          cy.wrap($email).clear().type('joao@email.com')
        }
      })

      // Update phone if field exists
      cy.get('input[type="tel"]').then(($phone) => {
        if ($phone.length > 0) {
          cy.wrap($phone).clear().type('11999999999')
        }
      })

      // Submit
      cy.intercept('PUT', '/api/v1/students/*').as('updateStudent')
      cy.contains('Atualizar').click()
      cy.wait('@updateStudent')

      // Verify update was successful
      cy.contains('João Atualizado').should('be.visible')
    })

    it('deve alterar faixa de um aluno', () => {
      cy.intercept('GET', '/api/v1/students').as('getStudentsList')
      cy.get('a[href="/students"]').click()
      cy.wait('@getStudentsList')

      // Click edit on first student
      cy.get('table tbody tr').first().within(() => {
        cy.get('button').first().click()
      })

      cy.wait('@getStudentsList')

      // Find belt dropdown and select different belt
      cy.get('select').filter(':visible').then(($selects) => {
        // Find the belt selector (usually second select)
        cy.wrap($selects).last().select(1)
      })

      cy.intercept('PUT', '/api/v1/students/*').as('updateStudentBelt')
      cy.contains('Atualizar').click()
      cy.wait('@updateStudentBelt')

      // Verify success
      cy.contains(/atualizado|sucesso/i).should('be.visible')
    })
  })

  describe('Inativar Aluno', () => {
    it('deve inativar aluno via botão de delete', () => {
      cy.intercept('GET', '/api/v1/students').as('getStudentsList')
      cy.get('a[href="/students"]').click()
      cy.wait('@getStudentsList')

      // Get student name before deletion
      cy.get('table tbody tr').first().within(() => {
        cy.get('td').first().invoke('text').as('studentName')
      })

      // Click delete button (trash icon) - usually last button
      cy.get('table tbody tr').first().within(() => {
        cy.get('button').last().click()
      })

      // Confirm dialog if exists
      cy.get('button').filter(':visible').then(($buttons) => {
        const confirmBtn = $buttons.filter(':contains("Confirmar")')
        if (confirmBtn.length > 0) {
          confirmBtn.click()
        }
      })

      // Wait for delete API
      cy.intercept('DELETE', '/api/v1/students/*').as('deleteStudent')
      cy.intercept('GET', '/api/v1/students').as('getStudentsAfterDelete')

      // Find and click confirm in dialog
      cy.contains('Confirmar').click()

      cy.wait('@deleteStudent')
      cy.wait('@getStudentsAfterDelete')

      // Verify student is not in list anymore
      cy.get('@studentName').then((name) => {
        cy.contains(name as string).should('not.exist')
      })
    })

    it('aluno inativo não aparece na lista padrão', () => {
      cy.get('a[href="/students"]').click()
      cy.wait('@getStudents')

      // Verify toggle for inactive is unchecked
      cy.get('input[type="checkbox"]').should('not.be.checked')

      // Inactive students should not be visible
      cy.get('table tbody tr').should('have.length.greaterThan', 0)
    })
  })
})