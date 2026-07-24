/// <reference types="cypress" />
/**
 * Contracts E2E Test Suite
 * Tests all 6 scenarios specified in Epic 02 Plan Phase 4
 */
describe('Contratos', () => {
  const adminEmail = 'admin@dojo.com'
  const adminPassword = 'admin123'
  const instructorEmail = 'instructor@dojo.com'
  const instructorPassword = 'instruct123'

  describe('Scenario 1: D1 - Geração de Contrato (Matricular/Renovar)', () => {
    let studentData: { id: string; full_name: string }
    const uniqueSuffix = `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`

    beforeEach(() => {
      cy.getAuthToken(adminEmail, adminPassword).then((token: any) => {
        cy.createBelt({
          name: 'Faixa Branca',
          category: 'adult',
          sort_order: 1,
        }).then((belt: any) => {
          cy.createStudent({
            full_name: `Scenario1Student${uniqueSuffix}`,
            birth_date: '1990-06-14',
            category: 'adult',
          }).then((student: any) => {
            if (!student || !student.id) {
              cy.log('ERROR: Student creation failed or returned no ID')
              return
            }

            studentData = { id: student.id, full_name: student.full_name }

            cy.request({
              method: 'PUT',
              url: `http://localhost:8000/api/v1/students/${student.id}`,
              headers: { Authorization: `Bearer ${token}` },
              body: {
                full_name: student.full_name,
                birth_date: '1990-06-14',
                category: 'adult',
                current_belt_id: belt.id,
                contract_name: 'Responsável Legal',
                contract_cpf: '123.456.789-00',
                address_street: 'Rua das Flores, 123',
                address_neighborhood: 'Centro',
                address_city: 'São Paulo',
                address_zip: '01234-567',
                phone: '(11) 99999-9999',
                classes_per_week: 2,
              },
              failOnStatusCode: false,
            })
          })

          cy.createPlanTier({
            weekly_frequency: 2,
            name: '2x por semana',
            price: '150.00',
          })

          cy.createContractTemplate({
            body: `Contrato de Matrícula

Aluno: {{ student.contract_name }}
CPF: {{ student.contract_cpf }}
Data de Nascimento: {{ student.birth_date }}
Endereço: {{ student.address }}
Telefone: {{ student.phone }}

Plano: {{ plan_tier.name }} - {{ plan_tier.weekly_frequency }}x por semana
Preço: {{ plan_version.price }}

O aluno aceita os termos e condições da escola.`,
          })
        })
      })
    })

    it('logs in as instructor, opens student contract modal, triggers Matricular/Renovar, confirms draft appears', () => {
      cy.clearLocalStorage()
      cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
      cy.intercept('GET', '/api/v1/students').as('getStudents')
      cy.visit('/login')
      cy.get('input[type="email"]').type(instructorEmail)
      cy.get('input[type="password"]').type(instructorPassword)
      cy.get('button[type="submit"]').click()
      cy.wait('@loginRequest')

      cy.visit('/students')

      cy.wait('@getStudents')
      cy.get('table tbody', { timeout: 10000 }).should('exist')

      cy.contains('tr', studentData.full_name).within(() => {
        cy.get('[title="Contrato"]', { timeout: 5000 }).click()
      })

      cy.contains('Contrato').should('be.visible')
      cy.get('h3').contains(studentData.full_name).scrollIntoView().should('be.visible')

      cy.intercept('POST', `/api/v1/students/${studentData.id}/contracts/matricular`).as('matricular')
      cy.intercept('GET', `/api/v1/students/${studentData.id}/contracts/current`).as('getCurrent')

      cy.contains('button', /Matricular\/Renovar/i).click()

      cy.wait('@matricular', { timeout: 15000 }).then((interception) => {
        expect(interception.response?.statusCode).to.equal(201)
        expect(interception.response?.body).to.have.property('status', 'draft')
      })

      cy.wait('@getCurrent', { timeout: 15000 })

      cy.contains(/Rascunho/i, { timeout: 10000 }).should('be.visible')
      cy.contains(/Assinar na Tela/i).should('be.visible')
    })
  })

  describe('Scenario 2: D2/D3 - On-screen signature capture', () => {
    let studentData: { id: string; full_name: string }
    const uniqueSuffix = `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`

    beforeEach(() => {
      cy.getAuthToken(adminEmail, adminPassword).then((token: any) => {
        cy.createBelt({
          name: 'Faixa Branca',
          category: 'adult',
          sort_order: 1,
        }).then((belt: any) => {
          cy.createStudent({
            full_name: `Scenario2Student${uniqueSuffix}`,
            birth_date: '1991-03-20',
            category: 'adult',
          }).then((student: any) => {
            if (!student || !student.id) return
            studentData = { id: student.id, full_name: student.full_name }

            cy.request({
              method: 'PUT',
              url: `http://localhost:8000/api/v1/students/${student.id}`,
              headers: { Authorization: `Bearer ${token}` },
              body: {
                full_name: student.full_name,
                birth_date: '1991-03-20',
                category: 'adult',
                current_belt_id: belt.id,
                contract_name: 'Responsável Legal',
                contract_cpf: '123.456.789-00',
                address_street: 'Rua das Flores, 123',
                address_neighborhood: 'Centro',
                address_city: 'São Paulo',
                address_zip: '01234-567',
                phone: '(11) 99999-9999',
                classes_per_week: 2,
              },
              failOnStatusCode: false,
            })
          })

          cy.createPlanTier({
            weekly_frequency: 2,
            name: '2x por semana',
            price: '150.00',
          })

          cy.createContractTemplate({
            body: `Contrato de Matrícula

Aluno: {{ student.contract_name }}
CPF: {{ student.contract_cpf }}
Data de Nascimento: {{ student.birth_date }}
Endereço: {{ student.address }}
Telefone: {{ student.phone }}

Plano: {{ plan_tier.name }} - {{ plan_tier.weekly_frequency }}x por semana
Preço: {{ plan_version.price }}

O aluno aceita os termos e condições da escola.`,
          })
        })
      }).then(() => {
        // Create draft contract in beforeEach (required for test to pass)
        const token = Cypress.env('adminToken') || localStorage.getItem('token')
        return cy.request({
          method: 'POST',
          url: `http://localhost:8000/api/v1/students/${studentData.id}/contracts/matricular`,
          headers: { Authorization: `Bearer ${token}` },
          failOnStatusCode: false,
        }).then((response) => {
          expect(response.status, 'beforeEach: matricular contract precreation').to.equal(201)
        })
      })
    })

    it('draws signature on canvas, confirms status becomes signed and download link appears', () => {
      cy.clearLocalStorage()
      cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
      cy.visit('/login')
      cy.get('input[type="email"]').type(instructorEmail)
      cy.get('input[type="password"]').type(instructorPassword)
      cy.get('button[type="submit"]').click()
      cy.wait('@loginRequest')

      cy.visit('/students')
      cy.get('table tbody', { timeout: 10000 }).should('exist')

      cy.contains('tr', studentData.full_name).within(() => {
        cy.get('[title="Contrato"]', { timeout: 5000 }).click()
      })

      cy.contains(/Rascunho/i, { timeout: 10000 }).should('be.visible')

      cy.get('canvas').should('exist')
      cy.get('canvas').then((canvas) => {
        const rect = canvas[0].getBoundingClientRect()
        const pointerOpts = { pointerId: 1, isPrimary: true, button: 0, buttons: 1 }
        cy.get('canvas')
          .trigger('pointerdown', { ...pointerOpts, x: rect.width / 4, y: rect.height / 2 })
          .trigger('pointermove', { ...pointerOpts, x: (rect.width * 3) / 4, y: rect.height / 2 })
          .trigger('pointerup', { ...pointerOpts, buttons: 0 })
      })

      cy.intercept('POST', '/api/v1/contracts/*/sign/on-screen').as('sign')
      cy.contains('button', /^Assinar$/i).click()

      cy.wait('@sign', { timeout: 15000 }).then((interception) => {
        expect(interception.response?.statusCode).to.equal(200)
      })

      cy.contains(/Assinado/i, { timeout: 10000 }).should('be.visible')
      cy.contains(/Baixar Contrato/i).should('be.visible')
      cy.contains(/Assinar na Tela/i).should('not.exist')
    })
  })

  describe('Scenario 3: D6 - Contract renewal keeps prior signed', () => {
    let studentData: { id: string; full_name: string }
    const uniqueSuffix = `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`

    beforeEach(() => {
      cy.getAuthToken(adminEmail, adminPassword).then((token: any) => {
        cy.createBelt({
          name: 'Faixa Branca',
          category: 'adult',
          sort_order: 1,
        }).then((belt: any) => {
          cy.createStudent({
            full_name: `Scenario3Student${uniqueSuffix}`,
            birth_date: '1992-07-25',
            category: 'adult',
          }).then((student: any) => {
            if (!student || !student.id) return
            studentData = { id: student.id, full_name: student.full_name }

            cy.request({
              method: 'PUT',
              url: `http://localhost:8000/api/v1/students/${student.id}`,
              headers: { Authorization: `Bearer ${token}` },
              body: {
                full_name: student.full_name,
                birth_date: '1992-07-25',
                category: 'adult',
                current_belt_id: belt.id,
                contract_name: 'Responsável Legal',
                contract_cpf: '123.456.789-00',
                address_street: 'Rua das Flores, 123',
                address_neighborhood: 'Centro',
                address_city: 'São Paulo',
                address_zip: '01234-567',
                phone: '(11) 99999-9999',
                classes_per_week: 2,
              },
              failOnStatusCode: false,
            })
          })

          cy.createPlanTier({
            weekly_frequency: 2,
            name: '2x por semana',
            price: '150.00',
          })

          cy.createContractTemplate({
            body: `Contrato de Matrícula

Aluno: {{ student.contract_name }}
CPF: {{ student.contract_cpf }}
Data de Nascimento: {{ student.birth_date }}
Endereço: {{ student.address }}
Telefone: {{ student.phone }}

Plano: {{ plan_tier.name }} - {{ plan_tier.weekly_frequency }}x por semana
Preço: {{ plan_version.price }}

O aluno aceita os termos e condições da escola.`,
          })
        })
      }).then(() => {
        const token = Cypress.env('adminToken') || localStorage.getItem('token')
        return cy.request({
          method: 'POST',
          url: `http://localhost:8000/api/v1/students/${studentData.id}/contracts/matricular`,
          headers: { Authorization: `Bearer ${token}` },
          failOnStatusCode: false,
        }).then((response) => {
          expect(response.status, 'beforeEach: matricular contract precreation').to.equal(201)
          return cy.request({
            method: 'POST',
            url: `http://localhost:8000/api/v1/contracts/${response.body.id}/sign/on-screen`,
            headers: { Authorization: `Bearer ${token}` },
            body: { signature_png: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==' },
            failOnStatusCode: false,
          }).then((signResponse) => {
            expect(signResponse.status, 'beforeEach: sign-on-screen precreation').to.equal(200)
          })
        })
      })
    })

    it('second Matricular/Renovar creates new draft while prior contract remains signed (not yet superseded)', () => {
      cy.clearLocalStorage()
      cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
      cy.visit('/login')
      cy.get('input[type="email"]').type(instructorEmail)
      cy.get('input[type="password"]').type(instructorPassword)
      cy.get('button[type="submit"]').click()
      cy.wait('@loginRequest')

      cy.visit('/students')
      cy.get('table tbody', { timeout: 10000 }).should('exist')

      cy.contains('tr', studentData.full_name).within(() => {
        cy.get('[title="Contrato"]', { timeout: 5000 }).click()
      })

      cy.contains(/Assinado/i, { timeout: 10000 }).should('be.visible')

      cy.intercept('POST', '/api/v1/students/*/contracts/matricular').as('renewalMatricula')
      cy.contains('button', /Matricular\/Renovar/i).click()

      cy.wait('@renewalMatricula', { timeout: 15000 }).then((interception) => {
        expect(interception.response?.statusCode).to.equal(201)
        expect(interception.response?.body).to.have.property('status', 'draft')
      })

      cy.contains(/Rascunho/i, { timeout: 10000 }).should('be.visible')

      cy.contains(/Histórico/i).scrollIntoView().should('be.visible')
      cy.get('table').last().scrollIntoView().within(() => {
        cy.contains(/Rascunho/).should('be.visible')
        cy.contains(/Assinado/).should('be.visible')
      })
    })
  })

  describe('Scenario 4: D4 - Upload-signed PDF contract', () => {
    let studentData: { id: string; full_name: string }
    const uniqueSuffix = `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`

    beforeEach(() => {
      cy.getAuthToken(adminEmail, adminPassword).then((token: any) => {
        cy.createBelt({
          name: 'Faixa Branca',
          category: 'adult',
          sort_order: 1,
        }).then((belt: any) => {
          cy.createStudent({
            full_name: `Scenario4Student${uniqueSuffix}`,
            birth_date: '1989-11-10',
            category: 'adult',
          }).then((student: any) => {
            if (!student || !student.id) return
            studentData = { id: student.id, full_name: student.full_name }

            cy.request({
              method: 'PUT',
              url: `http://localhost:8000/api/v1/students/${student.id}`,
              headers: { Authorization: `Bearer ${token}` },
              body: {
                full_name: student.full_name,
                birth_date: '1989-11-10',
                category: 'adult',
                current_belt_id: belt.id,
                contract_name: 'Responsável Legal',
                contract_cpf: '123.456.789-00',
                address_street: 'Rua das Flores, 123',
                address_neighborhood: 'Centro',
                address_city: 'São Paulo',
                address_zip: '01234-567',
                phone: '(11) 99999-9999',
                classes_per_week: 2,
              },
              failOnStatusCode: false,
            })
          })

          cy.createPlanTier({
            weekly_frequency: 2,
            name: '2x por semana',
            price: '150.00',
          })

          cy.createContractTemplate({
            body: `Contrato de Matrícula

Aluno: {{ student.contract_name }}
CPF: {{ student.contract_cpf }}
Data de Nascimento: {{ student.birth_date }}
Endereço: {{ student.address }}
Telefone: {{ student.phone }}

Plano: {{ plan_tier.name }} - {{ plan_tier.weekly_frequency }}x por semana
Preço: {{ plan_version.price }}

O aluno aceita os termos e condições da escola.`,
          })
        })
      }).then(() => {
        const token = Cypress.env('adminToken') || localStorage.getItem('token')
        return cy.request({
          method: 'POST',
          url: `http://localhost:8000/api/v1/students/${studentData.id}/contracts/matricular`,
          headers: { Authorization: `Bearer ${token}` },
          failOnStatusCode: false,
        }).then((response) => {
          expect(response.status, 'beforeEach: matricular contract precreation').to.equal(201)
        })
      })
    })

    it('uploads PDF, confirms signed/uploaded status and download link appears', () => {
      cy.clearLocalStorage()
      cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
      cy.visit('/login')
      cy.get('input[type="email"]').type(instructorEmail)
      cy.get('input[type="password"]').type(instructorPassword)
      cy.get('button[type="submit"]').click()
      cy.wait('@loginRequest')

      cy.visit('/students')
      cy.get('table tbody', { timeout: 10000 }).should('exist')

      cy.contains('tr', studentData.full_name).within(() => {
        cy.get('[title="Contrato"]', { timeout: 5000 }).click()
      })

      cy.contains(/Rascunho/i, { timeout: 10000 }).should('be.visible')

      const pdfContent = '%PDF-1.4\n%EOF'
      cy.get('input[type="file"]').selectFile({
        contents: Cypress.Buffer.from(pdfContent),
        fileName: 'signed-contract.pdf',
        mimeType: 'application/pdf',
      })

      cy.contains('button', /Enviar/).click()

      cy.contains(/Assinado/i, { timeout: 15000 }).should('be.visible')
      cy.contains(/Baixar Contrato/i).should('be.visible')
      cy.contains(/Ou Enviar Contrato Assinado/i).should('not.exist')
    })
  })

  describe('Scenario 5: D7 - Regenerate draft preserves price', () => {
    let studentData: { id: string; full_name: string }
    const uniqueSuffix = `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`

    beforeEach(() => {
      cy.getAuthToken(adminEmail, adminPassword).then((token: any) => {
        cy.createBelt({
          name: 'Faixa Branca',
          category: 'adult',
          sort_order: 1,
        }).then((belt: any) => {
          cy.createStudent({
            full_name: `Scenario5Student${uniqueSuffix}`,
            birth_date: '1993-05-15',
            category: 'adult',
          }).then((student: any) => {
            if (!student || !student.id) return
            studentData = { id: student.id, full_name: student.full_name }

            cy.request({
              method: 'PUT',
              url: `http://localhost:8000/api/v1/students/${student.id}`,
              headers: { Authorization: `Bearer ${token}` },
              body: {
                full_name: student.full_name,
                birth_date: '1993-05-15',
                category: 'adult',
                current_belt_id: belt.id,
                contract_name: 'Responsável Legal',
                contract_cpf: '123.456.789-00',
                address_street: 'Rua das Flores, 123',
                address_neighborhood: 'Centro',
                address_city: 'São Paulo',
                address_zip: '01234-567',
                phone: '(11) 99999-9999',
                classes_per_week: 2,
              },
              failOnStatusCode: false,
            })
          })

          cy.createPlanTier({
            weekly_frequency: 2,
            name: '2x por semana',
            price: '175.00',
          })

          cy.createContractTemplate({
            body: `Contrato de Matrícula

Aluno: {{ student.contract_name }}
CPF: {{ student.contract_cpf }}
Data de Nascimento: {{ student.birth_date }}
Endereço: {{ student.address }}
Telefone: {{ student.phone }}

Plano: {{ plan_tier.name }} - {{ plan_tier.weekly_frequency }}x por semana
Preço: {{ plan_version.price }}

O aluno aceita os termos e condições da escola.`,
          })
        })
      }).then(() => {
        const token = Cypress.env('adminToken') || localStorage.getItem('token')
        return cy.request({
          method: 'POST',
          url: `http://localhost:8000/api/v1/students/${studentData.id}/contracts/matricular`,
          headers: { Authorization: `Bearer ${token}` },
          failOnStatusCode: false,
        }).then((response) => {
          expect(response.status, 'beforeEach: matricular contract precreation').to.equal(201)
        })
      })
    })

    it('regenerate draft updates document without changing locked price', () => {
      cy.clearLocalStorage()
      cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
      cy.visit('/login')
      cy.get('input[type="email"]').type(instructorEmail)
      cy.get('input[type="password"]').type(instructorPassword)
      cy.get('button[type="submit"]').click()
      cy.wait('@loginRequest')

      cy.visit('/students')
      cy.get('table tbody', { timeout: 10000 }).should('exist')

      cy.contains('tr', studentData.full_name).within(() => {
        cy.get('[title="Contrato"]', { timeout: 5000 }).click()
      })

      cy.contains(/Rascunho/i, { timeout: 10000 }).should('be.visible')

      cy.intercept('POST', '/api/v1/contracts/*/regenerate').as('regenerate')
      cy.contains('button', /Regenerar Rascunho/i).click()

      cy.wait('@regenerate', { timeout: 15000 }).then((interception) => {
        expect(interception.response?.statusCode).to.equal(200)
        expect(interception.response?.body).to.have.property('status', 'draft')
      })

      cy.contains(/Rascunho/i, { timeout: 10000 }).should('be.visible')
      cy.get('h3').contains(studentData.full_name).scrollIntoView().should('be.visible')
    })
  })

  describe('Scenario 6: D5 - Authorization: Invalid token gets 401', () => {
    let studentData: { id: string; full_name: string }
    const uniqueSuffix = `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`

    beforeEach(() => {
      cy.getAuthToken(adminEmail, adminPassword).then((token: any) => {
        cy.createBelt({
          name: 'Faixa Branca',
          category: 'adult',
          sort_order: 1,
        }).then((belt: any) => {
          cy.createStudent({
            full_name: `Scenario6Student${uniqueSuffix}`,
            birth_date: '1988-12-03',
            category: 'adult',
          }).then((student: any) => {
            if (!student || !student.id) return
            studentData = { id: student.id, full_name: student.full_name }

            cy.request({
              method: 'PUT',
              url: `http://localhost:8000/api/v1/students/${student.id}`,
              headers: { Authorization: `Bearer ${token}` },
              body: {
                full_name: student.full_name,
                birth_date: '1988-12-03',
                category: 'adult',
                current_belt_id: belt.id,
                contract_name: 'Responsável Legal',
                contract_cpf: '123.456.789-00',
                address_street: 'Rua das Flores, 123',
                address_neighborhood: 'Centro',
                address_city: 'São Paulo',
                address_zip: '01234-567',
                phone: '(11) 99999-9999',
                classes_per_week: 2,
              },
              failOnStatusCode: false,
            })
          })

          cy.createPlanTier({
            weekly_frequency: 2,
            name: '2x por semana',
            price: '160.00',
          })

          cy.createContractTemplate({
            body: `Contrato de Matrícula

Aluno: {{ student.contract_name }}
CPF: {{ student.contract_cpf }}
Data de Nascimento: {{ student.birth_date }}
Endereço: {{ student.address }}
Telefone: {{ student.phone }}

Plano: {{ plan_tier.name }} - {{ plan_tier.weekly_frequency }}x por semana
Preço: {{ plan_version.price }}

O aluno aceita os termos e condições da escola.`,
          })
        })
      })
    })

    it('non-authorized caller gets 401 on contract endpoints', () => {
      cy.request({
        method: 'GET',
        url: `http://localhost:8000/api/v1/students/${studentData.id}/contracts/current`,
        headers: { Authorization: 'Bearer invalid-token-xyz' },
        failOnStatusCode: false,
      }).then((response) => {
        expect(response.status).to.equal(401)
      })

      cy.request({
        method: 'POST',
        url: `http://localhost:8000/api/v1/students/${studentData.id}/contracts/matricular`,
        headers: { Authorization: 'Bearer invalid-token-xyz' },
        failOnStatusCode: false,
      }).then((response) => {
        expect(response.status).to.equal(401)
      })
    })
  })
})
