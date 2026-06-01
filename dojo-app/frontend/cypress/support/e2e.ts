// Custom Cypress commands for Dojo Admin

// ============================================
// AUTH COMMANDS
// ============================================

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
    win.localStorage.removeItem('user')
  })
  cy.visit('/login')
})

// Check if user is authenticated
Cypress.Commands.add('isAuthenticated', () => {
  cy.window().its('localStorage').invoke('getItem', 'token').should('exist')
})

// ============================================
// SEEDING COMMANDS
// ============================================

// Seed a student via API (returns student data)
Cypress.Commands.add('createStudent', (data: {
  full_name: string
  birth_date?: string
  category?: string
  belt_id?: number
}) => {
  const adminToken = Cypress.env('adminToken') || localStorage.getItem('token')

  cy.request({
    method: 'POST',
    url: `${Cypress.env('VITE_API_URL') || 'http://localhost:8000'}/api/v1/students`,
    body: {
      full_name: data.full_name,
      birth_date: data.birth_date || '1990-01-01',
      category: data.category || 'adult',
      belt_id: data.belt_id || 1,
    },
    headers: { Authorization: `Bearer ${adminToken}` },
    failOnStatusCode: false,
  }).then((response) => {
    if (response.status !== 201) {
      cy.log(`Student creation warning: ${response.status} - ${response.body?.detail}`)
    }
    return cy.wrap(response.body)
  })
})

// Seed an event via API
Cypress.Commands.add('createEvent', (data: {
  title: string
  event_type_id: number
  start_datetime: string
  end_datetime?: string
  description?: string
}) => {
  const adminToken = Cypress.env('adminToken') || localStorage.getItem('token')
  const apiUrl = Cypress.env('VITE_API_URL') || 'http://localhost:8000'

  cy.request({
    method: 'POST',
    url: `${apiUrl}/api/v1/events`,
    body: {
      title: data.title,
      event_type_id: data.event_type_id,
      start_datetime: data.start_datetime,
      end_datetime: data.end_datetime || data.start_datetime,
      description: data.description || '',
    },
    headers: { Authorization: `Bearer ${adminToken}` },
    failOnStatusCode: false,
  }).then((response) => {
    if (response.status !== 201) {
      cy.log(`Event creation warning: ${response.status} - ${JSON.stringify(response.body)}`)
    }
    return cy.wrap(response.body)
  })
})

// Seed a belt via API
Cypress.Commands.add('createBelt', (data: {
  name: string
  category: string
  sort_order: number
}) => {
  const adminToken = Cypress.env('adminToken') || localStorage.getItem('token')
  const apiUrl = Cypress.env('VITE_API_URL') || 'http://localhost:8000'

  cy.request({
    method: 'POST',
    url: `${apiUrl}/api/v1/belts`,
    body: data,
    headers: { Authorization: `Bearer ${adminToken}` },
    failOnStatusCode: false,
  }).then((response) => {
    if (response.status !== 201) {
      cy.log(`Belt creation warning: ${response.status} - ${response.body?.detail}`)
    }
    return cy.wrap(response.body)
  })
})

// Seed a belt requirement via API
Cypress.Commands.add('createRequirement', (data: {
  belt_id: number
  event_type_id: number
  required_count: number
  description?: string
}) => {
  const adminToken = Cypress.env('adminToken') || localStorage.getItem('token')
  const apiUrl = Cypress.env('VITE_API_URL') || 'http://localhost:8000'

  cy.request({
    method: 'POST',
    url: `${apiUrl}/api/v1/belts/${data.belt_id}/requirements`,
    body: {
      belt_id: data.belt_id,
      event_type_id: data.event_type_id,
      required_count: data.required_count,
      description: data.description || '',
    },
    headers: { Authorization: `Bearer ${adminToken}` },
    failOnStatusCode: false,
  }).then((response) => {
    if (response.status !== 201) {
      cy.log(`Requirement creation warning: ${response.status} - ${response.body?.detail}`)
    }
    return cy.wrap(response.body)
  })
})

// Seed a check-in via API (for attendance list tests)
Cypress.Commands.add('seedCheckIn', (data: {
  event_id: number
  student_id: number
  registration_number?: string
  pin?: string
  method?: 'tablet' | 'qrcode' | 'manual'
}) => {
  const apiUrl = Cypress.env('VITE_API_URL') || 'http://localhost:8000'

  cy.request({
    method: 'POST',
    url: `${apiUrl}/api/v1/checkin/tablet/${data.event_id}`,
    body: {
      event_id: data.event_id,
      student_id: data.student_id,
      registration_number: data.registration_number,
      pin: data.pin,
      check_in_method: data.method || 'tablet',
    },
    failOnStatusCode: false,
  }).then((response) => {
    if (response.status !== 200) {
      cy.log(`Check-in warning: ${response.status} - ${response.body?.detail}`)
    }
    return cy.wrap(response.body)
  })
})

// Seed a full exam setup (exam + board + participants)
Cypress.Commands.add('seedExam', (data: {
  event_id: number
  belt_id: number
  exam_date: string
  notes?: string
  board_members?: { user_id: number; role: string }[]
  participants?: { student_id: number; role: string }[]
}) => {
  const adminToken = Cypress.env('adminToken') || localStorage.getItem('token')
  const apiUrl = Cypress.env('VITE_API_URL') || 'http://localhost:8000'

  // Create exam
  cy.request({
    method: 'POST',
    url: `${apiUrl}/api/v1/exams`,
    body: {
      event_id: data.event_id,
      belt_id: data.belt_id,
      exam_date: data.exam_date,
      notes: data.notes || '',
    },
    headers: { Authorization: `Bearer ${adminToken}` },
    failOnStatusCode: false,
  }).then((examResp) => {
    if (examResp.status !== 201) {
      cy.log(`Exam creation warning: ${examResp.status} - ${examResp.body?.detail}`)
      return cy.wrap(examResp.body)
    }

    const examId = examResp.body.id

    // Add board members
    if (data.board_members) {
      data.board_members.forEach((member) => {
        cy.request({
          method: 'POST',
          url: `${apiUrl}/api/v1/exams/${examId}/board-members`,
          body: { user_id: member.user_id, role_in_board: member.role },
          headers: { Authorization: `Bearer ${adminToken}` },
          failOnStatusCode: false,
        })
      })
    }

    // Add participants
    if (data.participants) {
      data.participants.forEach((participant) => {
        cy.request({
          method: 'POST',
          url: `${apiUrl}/api/v1/exams/${examId}/participants`,
          body: { student_id: participant.student_id, role: participant.role },
          headers: { Authorization: `Bearer ${adminToken}` },
          failOnStatusCode: false,
        })
      })
    }

    return cy.wrap(examResp.body)
  })
})

// Create exam participant via API
Cypress.Commands.add('createExamParticipant', (examId: number, data: {
  student_id: number
  role: 'candidate' | 'uke'
}) => {
  const adminToken = Cypress.env('adminToken') || localStorage.getItem('token')
  const apiUrl = Cypress.env('VITE_API_URL') || 'http://localhost:8000'

  cy.request({
    method: 'POST',
    url: `${apiUrl}/api/v1/exams/${examId}/participants`,
    body: data,
    headers: { Authorization: `Bearer ${adminToken}` },
    failOnStatusCode: false,
  }).then((response) => {
    return cy.wrap(response.body)
  })
})

// Get auth token for API calls
Cypress.Commands.add('getAuthToken', (email: string, password: string) => {
  const apiUrl = Cypress.env('VITE_API_URL') || 'http://localhost:8000'

  cy.request({
    method: 'POST',
    url: `${apiUrl}/api/v1/auth/login`,
    body: {
      username: email,
      password: password,
    },
    failOnStatusCode: false,
  }).then((response) => {
    if (response.status === 200) {
      const token = response.body.access_token
      Cypress.env('adminToken', token)
      localStorage.setItem('token', token)
      return cy.wrap(token)
    }
    return cy.wrap(null)
  })
})

// ============================================
// HELPTER COMMANDS
// ============================================

// Wait for API to settle
Cypress.Commands.add('waitForApi', (alias: string, timeout = 10000) => {
  cy.wait(alias, { requestTimeout: timeout })
})

// Clear and seed database (for admin tests)
Cypress.Commands.add('clearDatabase', () => {
  // This would typically call a test utilities endpoint
  // For now, we rely on test isolation via unique data
  cy.log('Database clear requested - using test isolation pattern')
})