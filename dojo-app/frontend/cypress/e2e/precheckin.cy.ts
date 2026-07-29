/// <reference types="cypress" />

describe('Pré-Check-in', () => {
  const adminEmail = 'admin@dojo.com'
  const adminPassword = 'admin123'

  describe('Pré-Check-in - API Tests', () => {
    it('deve confirmar pré-check-in com registro e PIN válidos via API', () => {
      cy.getAuthToken(adminEmail, adminPassword).then((token: any) => {
        cy.createStudent({
          full_name: 'API Test Student',
          birth_date: '1990-01-01',
          category: 'adult',
        }).then((student: any) => {
          const futureDate = new Date(Date.now() + 48 * 60 * 60 * 1000).toISOString()
          cy.createEvent({
            title: 'API Test Event',
            start_datetime: futureDate,
            end_datetime: futureDate,
          }).then((event: any) => {
            // Confirm pre-check-in via API
            cy.request({
              method: 'POST',
              url: 'http://localhost:8000/api/v1/pre-checkins/confirm',
              body: {
                event_id: event.id,
                registration_number: student.registration_number,
                pin: student.pin,
              },
              failOnStatusCode: false,
            }).then((response) => {
              expect(response.status).to.eq(200)
              expect(response.body).to.have.property('status')
            })
          })
        })
      })
    })

    it('deve permitir cancelamento de pré-check-in via API', () => {
      cy.getAuthToken(adminEmail, adminPassword).then((token: any) => {
        cy.createStudent({
          full_name: 'Cancel Test Student',
          birth_date: '1990-03-01',
          category: 'adult',
        }).then((student: any) => {
          const futureDate = new Date(Date.now() + 48 * 60 * 60 * 1000).toISOString()
          cy.createEvent({
            title: 'Cancel Event',
            start_datetime: futureDate,
            end_datetime: futureDate,
          }).then((event: any) => {
            cy.request({
              method: 'POST',
              url: 'http://localhost:8000/api/v1/pre-checkins/confirm',
              body: {
                event_id: event.id,
                registration_number: student.registration_number,
                pin: student.pin,
              },
              failOnStatusCode: false,
            })

            cy.request({
              method: 'POST',
              url: 'http://localhost:8000/api/v1/pre-checkins/cancel',
              body: {
                event_id: event.id,
                registration_number: student.registration_number,
                pin: student.pin,
              },
              failOnStatusCode: false,
            }).then((response) => {
              expect(response.status).to.eq(200)
            })
          })
        })
      })
    })

    it('deve permitir re-confirmação idempotente', () => {
      cy.getAuthToken(adminEmail, adminPassword).then((token: any) => {
        cy.createStudent({
          full_name: 'Idempotent Student',
          birth_date: '1990-04-01',
          category: 'adult',
        }).then((student: any) => {
          const futureDate = new Date(Date.now() + 48 * 60 * 60 * 1000).toISOString()
          cy.createEvent({
            title: 'Idempotent Event',
            start_datetime: futureDate,
            end_datetime: futureDate,
          }).then((event: any) => {
            const confirmPayload = {
              event_id: event.id,
              registration_number: student.registration_number,
              pin: student.pin,
            }

            cy.request({
              method: 'POST',
              url: 'http://localhost:8000/api/v1/pre-checkins/confirm',
              body: confirmPayload,
              failOnStatusCode: false,
            }).then((response1) => {
              expect(response1.status).to.eq(200)

              cy.request({
                method: 'POST',
                url: 'http://localhost:8000/api/v1/pre-checkins/confirm',
                body: confirmPayload,
                failOnStatusCode: false,
              }).then((response2) => {
                expect(response2.status).to.eq(200)
              })
            })
          })
        })
      })
    })
  })

  describe('Pré-Check-in - Instructor Roster', () => {
    it('instrutor deve visualizar count de pré-confirmações', () => {
      cy.getAuthToken(adminEmail, adminPassword).then((token: any) => {
        cy.createStudent({
          full_name: 'Roster Count Student',
          birth_date: '1995-05-15',
          category: 'adult',
        }).then((student: any) => {
          const futureDate = new Date(Date.now() + 48 * 60 * 60 * 1000).toISOString()
          cy.createEvent({
            title: 'Roster Count Event',
            start_datetime: futureDate,
            end_datetime: futureDate,
          }).then((event: any) => {
            cy.request({
              method: 'POST',
              url: 'http://localhost:8000/api/v1/pre-checkins/confirm',
              body: {
                event_id: event.id,
                registration_number: student.registration_number,
                pin: student.pin,
              },
              failOnStatusCode: false,
            })

            cy.request({
              method: 'GET',
              url: `http://localhost:8000/api/v1/pre-checkins/events/${event.id}/count`,
              headers: {
                Authorization: `Bearer ${token}`,
              },
              failOnStatusCode: false,
            }).then((response) => {
              expect(response.status).to.eq(200)
              expect(response.body).to.have.property('confirmed_count')
            })
          })
        })
      })
    })

    it('instrutor deve visualizar roster de pré-confirmações', () => {
      cy.getAuthToken(adminEmail, adminPassword).then((token: any) => {
        cy.createStudent({
          full_name: 'Roster View Student',
          birth_date: '1995-06-20',
          category: 'adult',
        }).then((student: any) => {
          const futureDate = new Date(Date.now() + 48 * 60 * 60 * 1000).toISOString()
          cy.createEvent({
            title: 'Roster View Event',
            start_datetime: futureDate,
            end_datetime: futureDate,
          }).then((event: any) => {
            cy.request({
              method: 'POST',
              url: 'http://localhost:8000/api/v1/pre-checkins/confirm',
              body: {
                event_id: event.id,
                registration_number: student.registration_number,
                pin: student.pin,
              },
              failOnStatusCode: false,
            })

            cy.request({
              method: 'GET',
              url: `http://localhost:8000/api/v1/pre-checkins/events/${event.id}`,
              headers: {
                Authorization: `Bearer ${token}`,
              },
              failOnStatusCode: false,
            }).then((response) => {
              expect(response.status).to.eq(200)
              expect(response.body).to.be.an('array')
            })
          })
        })
      })
    })
  })
})
