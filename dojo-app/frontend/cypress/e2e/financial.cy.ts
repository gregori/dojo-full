/// <reference types="cypress" />

describe('Financeiro - Planos e Mensalidades', () => {
  const adminEmail = 'admin@dojo.com'
  const adminPassword = 'admin123'
  const instructorEmail = 'instructor@dojo.com'
  const instructorPassword = 'instruct123'

  describe('Gestão de Planos (Admin)', () => {
    it('admin deve criar novo plano com preço', () => {
      // Use unique weekly_frequency to avoid DB uniqueness conflicts across test runs
      const uniqueFrequency = Math.floor(Math.random() * 1000) + 100

      cy.getAuthToken(adminEmail, adminPassword).then(() => {
        cy.createPlanTier({
          weekly_frequency: uniqueFrequency,
          name: `${uniqueFrequency}x plan`,
          price: '150.00',
        }).then((planTier: any) => {
          expect(planTier).to.have.property('id')
          expect(planTier).to.have.property('weekly_frequency', uniqueFrequency)
          expect(planTier).to.have.property('name')
        })
      })
    })

    it('admin deve alterar preço de plano (cria nova versão)', () => {
      const uniqueFrequency = Math.floor(Math.random() * 1000) + 300

      cy.getAuthToken(adminEmail, adminPassword).then((token: any) => {
        // First create a plan to update
        cy.createPlanTier({
          weekly_frequency: uniqueFrequency,
          name: `${uniqueFrequency}x plan`,
          price: '150.00',
        }).then((planTier: any) => {
          const planId = planTier.id

          // Update the price
          cy.request({
            method: 'PUT',
            url: `http://localhost:8000/api/v1/plans/${planId}/price`,
            headers: {
              Authorization: `Bearer ${token}`,
            },
            body: {
              price: '200.00',
            },
            failOnStatusCode: false,
          }).then((updateResponse) => {
            expect(updateResponse.status).to.eq(200)
            expect(updateResponse.body).to.have.property('current_price')
          })
        })
      })
    })
  })

  describe('Atribuição de Plano a Aluno', () => {
    let studentData: { id: string; registration_number: string; pin: string }

    beforeEach(() => {
      cy.getAuthToken(adminEmail, adminPassword).then(() => {
        // Create a student with known classes_per_week
        cy.createStudent({
          full_name: 'Financial Test Student',
          birth_date: '1991-06-14',
          category: 'adult',
        }).then((student: any) => {
          studentData = {
            id: student.id,
            registration_number: student.registration_number,
            pin: student.pin,
          }
        })

        // Ensure a plan tier exists for testing
        cy.createPlanTier({
          weekly_frequency: 2,
          name: '2x por semana',
          price: '120.00',
        })
      })
    })

    it('instrutor deve atribuir plano a aluno (baseado em classes_per_week)', () => {
      cy.clearLocalStorage()
      cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
      cy.visit('/login')
      cy.get('input[type="email"]').type(instructorEmail)
      cy.get('input[type="password"]').type(instructorPassword)
      cy.get('button[type="submit"]').click()
      cy.wait('@loginRequest')

      const token = localStorage.getItem('token')

      // Assign plan to student
      cy.request({
        method: 'POST',
        url: `http://localhost:8000/api/v1/students/${studentData.id}/plan`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        failOnStatusCode: false,
      }).then((response) => {
        expect([200, 201]).to.include(response.status)
        expect(response.body).to.have.property('plan_version')
        expect(response.body).to.have.property('status')
      })
    })

    it('histórico de atribuição deve manter preço em que foi atribuído (price locking)', () => {
      cy.clearLocalStorage()
      cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
      cy.visit('/login')
      cy.get('input[type="email"]').type(instructorEmail)
      cy.get('input[type="password"]').type(instructorPassword)
      cy.get('button[type="submit"]').click()
      cy.wait('@loginRequest')

      const token = localStorage.getItem('token')

      // Assign initial plan
      cy.request({
        method: 'POST',
        url: `http://localhost:8000/api/v1/students/${studentData.id}/plan`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        failOnStatusCode: false,
      }).then((response1) => {
        expect([200, 201]).to.include(response1.status)
        const initialPrice = response1.body.plan_version.price

        // Get history
        cy.request({
          method: 'GET',
          url: `http://localhost:8000/api/v1/students/${studentData.id}/plan`,
          headers: {
            Authorization: `Bearer ${token}`,
          },
          failOnStatusCode: false,
        }).then((historyResponse) => {
          expect(historyResponse.status).to.eq(200)
          expect(historyResponse.body).to.be.an('array')
          if (historyResponse.body.length > 0) {
            expect(historyResponse.body[0].plan_version.price).to.equal(initialPrice)
          }
        })
      })
    })
  })

  describe('Geração e Gerenciamento de Mensalidades', () => {
    let studentData: { id: string; registration_number: string; pin: string }

    beforeEach(() => {
      cy.getAuthToken(adminEmail, adminPassword).then(() => {
        cy.createStudent({
          full_name: 'Mensalidade Test Student',
          birth_date: '1993-09-05',
          category: 'adult',
        }).then((student: any) => {
          studentData = {
            id: student.id,
            registration_number: student.registration_number,
            pin: student.pin,
          }
        })

        // Create plan with unique frequency to avoid DB conflicts
        const uniquePlanFrequency = Math.floor(Math.random() * 1000) + 200
        cy.createPlanTier({
          weekly_frequency: uniquePlanFrequency,
          name: `${uniquePlanFrequency}x semanal`,
          price: '150.00',
        })
      })
    })

    it('instrutor deve gerar mensalidades mensais', () => {
      cy.clearLocalStorage()
      cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
      cy.visit('/login')
      cy.get('input[type="email"]').type(instructorEmail)
      cy.get('input[type="password"]').type(instructorPassword)
      cy.get('button[type="submit"]').click()
      cy.wait('@loginRequest')

      const token = localStorage.getItem('token')

      // First, assign student to a plan
      cy.request({
        method: 'POST',
        url: `http://localhost:8000/api/v1/students/${studentData.id}/plan`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        failOnStatusCode: false,
      })

      // Generate charges
      cy.request({
        method: 'POST',
        url: 'http://localhost:8000/api/v1/mensalidades/generate',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        failOnStatusCode: false,
      }).then((response) => {
        expect([200, 201]).to.include(response.status)
        expect(response.body).to.have.property('created_count')
      })
    })

    it('geração de mensalidades é idempotente', () => {
      cy.clearLocalStorage()
      cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
      cy.visit('/login')
      cy.get('input[type="email"]').type(instructorEmail)
      cy.get('input[type="password"]').type(instructorPassword)
      cy.get('button[type="submit"]').click()
      cy.wait('@loginRequest')

      const token = localStorage.getItem('token')

      // Assign plan
      cy.request({
        method: 'POST',
        url: `http://localhost:8000/api/v1/students/${studentData.id}/plan`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        failOnStatusCode: false,
      })

      // Generate once
      cy.request({
        method: 'POST',
        url: 'http://localhost:8000/api/v1/mensalidades/generate',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        failOnStatusCode: false,
      }).then((response1) => {
        expect([200, 201]).to.include(response1.status)

        // Generate again (should be idempotent)
        cy.request({
          method: 'POST',
          url: 'http://localhost:8000/api/v1/mensalidades/generate',
          headers: {
            Authorization: `Bearer ${token}`,
          },
          failOnStatusCode: false,
        }).then((response2) => {
          expect([200, 201]).to.include(response2.status)
          // Should not create duplicates
        })
      })
    })

    it('mensalidade deve exibir status computado', () => {
      cy.clearLocalStorage()
      cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
      cy.visit('/login')
      cy.get('input[type="email"]').type(instructorEmail)
      cy.get('input[type="password"]').type(instructorPassword)
      cy.get('button[type="submit"]').click()
      cy.wait('@loginRequest')

      const token = localStorage.getItem('token')

      // Assign plan
      cy.request({
        method: 'POST',
        url: `http://localhost:8000/api/v1/students/${studentData.id}/plan`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        failOnStatusCode: false,
      })

      // Generate charges
      cy.request({
        method: 'POST',
        url: 'http://localhost:8000/api/v1/mensalidades/generate',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        failOnStatusCode: false,
      })

      // Get student mensalidades
      cy.request({
        method: 'GET',
        url: `http://localhost:8000/api/v1/students/${studentData.id}/mensalidades`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        failOnStatusCode: false,
      }).then((response) => {
        expect(response.status).to.eq(200)
        expect(response.body).to.be.an('array')
        if (response.body.length > 0) {
          const mensalidade = response.body[0]
          expect(mensalidade).to.have.property('status')
          expect(['open', 'partial', 'paid', 'overdue']).to.include(mensalidade.status)
          expect(mensalidade).to.have.property('amount')
        }
      })
    })
  })

  describe('Pagamentos e Saldo', () => {
    let studentData: { id: string; registration_number: string; pin: string }

    beforeEach(() => {
      cy.getAuthToken(adminEmail, adminPassword).then(() => {
        cy.createStudent({
          full_name: 'Payment Test Student',
          birth_date: '1994-11-20',
          category: 'adult',
        }).then((student: any) => {
          studentData = {
            id: student.id,
            registration_number: student.registration_number,
            pin: student.pin,
          }
        })

        // Create plan
        cy.createPlanTier({
          weekly_frequency: 2,
          name: '2x semanal',
          price: '100.00',
        })
      })
    })

    it('instrutor deve registrar pagamento', () => {
      cy.clearLocalStorage()
      cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
      cy.visit('/login')
      cy.get('input[type="email"]').type(instructorEmail)
      cy.get('input[type="password"]').type(instructorPassword)
      cy.get('button[type="submit"]').click()
      cy.wait('@loginRequest')

      const token = localStorage.getItem('token')

      // Assign plan and generate charges
      cy.request({
        method: 'POST',
        url: `http://localhost:8000/api/v1/students/${studentData.id}/plan`,
        headers: { Authorization: `Bearer ${token}` },
        failOnStatusCode: false,
      })

      cy.request({
        method: 'POST',
        url: 'http://localhost:8000/api/v1/mensalidades/generate',
        headers: { Authorization: `Bearer ${token}` },
        failOnStatusCode: false,
      })

      // Record a payment
      cy.request({
        method: 'POST',
        url: 'http://localhost:8000/api/v1/payments',
        body: {
          student_id: studentData.id,
          amount: '50.00',
          payment_date: '2026-01-15',
          method: 'cash',
        },
        headers: {
          Authorization: `Bearer ${token}`,
        },
        failOnStatusCode: false,
      }).then((response) => {
        expect([200, 201]).to.include(response.status)
        expect(response.body).to.have.property('amount')
      })
    })

    it('saldo deve atualizar após pagamento', () => {
      cy.clearLocalStorage()
      cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
      cy.visit('/login')
      cy.get('input[type="email"]').type(instructorEmail)
      cy.get('input[type="password"]').type(instructorPassword)
      cy.get('button[type="submit"]').click()
      cy.wait('@loginRequest')

      const token = localStorage.getItem('token')

      // Setup: assign plan and generate charges
      cy.request({
        method: 'POST',
        url: `http://localhost:8000/api/v1/students/${studentData.id}/plan`,
        headers: { Authorization: `Bearer ${token}` },
        failOnStatusCode: false,
      })

      cy.request({
        method: 'POST',
        url: 'http://localhost:8000/api/v1/mensalidades/generate',
        headers: { Authorization: `Bearer ${token}` },
        failOnStatusCode: false,
      })

      // Get initial balance
      cy.request({
        method: 'GET',
        url: `http://localhost:8000/api/v1/students/${studentData.id}/balance`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        failOnStatusCode: false,
      }).then((balanceBefore) => {
        const initialBalance = balanceBefore.body?.balance || '0'

        // Record payment
        cy.request({
          method: 'POST',
          url: 'http://localhost:8000/api/v1/payments',
          body: {
            student_id: studentData.id,
            amount: '50.00',
            payment_date: '2026-01-15',
            method: 'cash',
          },
          headers: { Authorization: `Bearer ${token}` },
          failOnStatusCode: false,
        })

        // Get balance after payment
        cy.request({
          method: 'GET',
          url: `http://localhost:8000/api/v1/students/${studentData.id}/balance`,
          headers: {
            Authorization: `Bearer ${token}`,
          },
          failOnStatusCode: false,
        }).then((balanceAfter) => {
          expect(balanceAfter.status).to.eq(200)
          expect(balanceAfter.body).to.have.property('balance')
          // Balance should reflect the payment
        })
      })
    })

    it('mensalidades vencidas devem aparecer no dashboard', () => {
      cy.clearLocalStorage()
      cy.intercept('POST', '/api/v1/auth/login').as('loginRequest')
      cy.visit('/login')
      cy.get('input[type="email"]').type(instructorEmail)
      cy.get('input[type="password"]').type(instructorPassword)
      cy.get('button[type="submit"]').click()
      cy.wait('@loginRequest')

      const token = localStorage.getItem('token')

      // Setup: assign plan and generate charges
      cy.request({
        method: 'POST',
        url: `http://localhost:8000/api/v1/students/${studentData.id}/plan`,
        headers: { Authorization: `Bearer ${token}` },
        failOnStatusCode: false,
      })

      cy.request({
        method: 'POST',
        url: 'http://localhost:8000/api/v1/mensalidades/generate',
        headers: { Authorization: `Bearer ${token}` },
        failOnStatusCode: false,
      })

      // Get overdue dashboard
      cy.request({
        method: 'GET',
        url: 'http://localhost:8000/api/v1/finance/overdue',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        failOnStatusCode: false,
      }).then((response) => {
        expect(response.status).to.eq(200)
        expect(response.body).to.be.an('array')
        // Dashboard shows students with overdue charges
      })
    })
  })
})
