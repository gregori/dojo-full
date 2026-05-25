# Story 02-01: Authentication and Multi-Org Foundation

**Parent Epic:** [Epic 1: MVP](../epics/epic-01-mvp.md)  
**PR:** PR-1-auth

## User Story

As a **user**, I want to securely log in to the Dojo Manager using email/password or Google OAuth, so that I can access features appropriate to my role (super-admin, instructor, or student).

As a **system architect**, I want all data to be scoped by `org_id`, so that multi-tenancy is supported in the data model even though the MVP UI uses a single hardcoded organization.

## Acceptance Criteria

### AC-1: Email/Password Registration

**Given** a new user visits the registration page  
**When** they provide email, password, and name  
**Then**:
- A user account is created with `org_id` set to the default organization
- Password is hashed using bcrypt
- A JWT access token is returned
- The user is assigned the `student` role by default

### AC-2: Email/Password Login

**Given** a registered user visits the login page  
**When** they provide valid email and password  
**Then**:
- A JWT access token is returned
- The token contains user ID, email, roles, and `org_id`
- The user is redirected to the dashboard

### AC-3: Google OAuth Login

**Given** a user clicks "Sign in with Google"  
**When** they complete the Google OAuth flow  
**Then**:
- If the email matches an existing user, they are logged in
- If the email is new, an account is created with `student` role
- A JWT access token is returned

### AC-4: Role-Based Access Control

**Given** a user is authenticated  
**When** they attempt to access a protected resource  
**Then**:
- `student` role: can view own data, mark own attendance
- `instructor` role: can manage students, classes, exams, cleaning groups (within their org)
- `super-admin` role: can manage organizations and all data globally
- Requests without valid token or insufficient role return 401/403

### AC-5: Multi-Org Data Isolation

**Given** the database schema  
**When** tables are created  
**Then**:
- `orgs` table exists with id, name, created_at
- `users` table has `org_id` foreign key
- All domain tables (students, classes, exams, etc.) have `org_id` column
- Queries are scoped by `org_id` from the authenticated user's token

### AC-6: Instructor Role Assignment

**Given** a super-admin or existing instructor  
**When** they assign the `instructor` role to a student  
**Then**:
- The student gains instructor permissions
- The student remains a student (instructor is an additional role, not a separate entity)
- The change is reflected immediately in subsequent requests

### AC-7: Token Expiration and Refresh

**Given** a user is logged in  
**When** their access token expires (15 minutes)  
**Then**:
- API requests return 401
- The frontend can request a new token using a refresh token (7-day expiry)
- If refresh token is also expired, the user must re-authenticate

## Domain Model References

### Organization
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| name | VARCHAR(255) | Organization name |
| created_at | TIMESTAMP | Creation timestamp |

### User
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| org_id | UUID | FK to orgs |
| email | VARCHAR(255) | Unique email |
| password_hash | VARCHAR(255) | Bcrypt hash (null for OAuth-only users) |
| name | VARCHAR(255) | Display name |
| roles | JSON | Array of roles: ["student"], ["instructor", "student"], ["super-admin"] |
| auth_provider | VARCHAR(50) | "email" or "google" |
| created_at | TIMESTAMP | Creation timestamp |

## UI Requirements

- Login page with email/password form and "Sign in with Google" button
- Registration page with email, password, name fields
- Protected routes redirect unauthenticated users to login
- Dashboard shows role-appropriate navigation

## API Requirements

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/auth/register` | Register new user | Public |
| POST | `/api/auth/login` | Login with email/password | Public |
| POST | `/api/auth/google` | Exchange Google OAuth code for JWT | Public |
| POST | `/api/auth/refresh` | Refresh access token | Refresh token |
| POST | `/api/auth/logout` | Invalidate refresh token | Authenticated |
| GET | `/api/auth/me` | Get current user profile | Authenticated |
| POST | `/api/users/{id}/roles` | Assign role to user | Super-admin/Instructor |

## Dependencies

| Dependency | Type | Details |
|------------|------|---------|
| PR-0-infra | Internal | Requires deployed infrastructure |
| Google OAuth | External | Google Cloud project with OAuth credentials |

## Technical Notes

- JWT tokens signed with HS256 using a secret from environment
- `org_id` is extracted from JWT and used to scope all queries
- MVP uses a single hardcoded org; the org management UI is deferred to Epic 4
- Instructors are students with an additional role — not a separate entity
