# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased] - PR-1-auth: Authentication & Multi-Org Foundation

### 🔒 Security
- bcrypt password hashing (12 rounds via passlib)
- httpOnly, Secure (production), SameSite=Lax cookie flags
- CSRF protection on Google OAuth via state parameter
- Optimistic locking on refresh token revocation (concurrent detection)
- Session invalidation on role changes (revoke_all_for_user)
- JWT_SECRET startup validation (crashes if insecure)
- Generic error messages prevent user enumeration
- Password hash null check for Google-only users

### 🚀 Features
- Email/password registration and login with JWT tokens
- Google OAuth login (Authorization Code flow, scopes: email + profile)
- JWT token management via httpOnly cookies (access: 15min, refresh: 7 days)
- Refresh token rotation with SHA-256 hashing in database
- Role-based access control (RBAC): student, instructor, super-admin
- User management: list users, assign role, remove instructor role
- Multi-organization foundation: orgs table, org_id foreign key on users
- Default organization seeding via Alembic data migration
- Rate limiting on auth endpoints (5 attempts/min per IP)
- Cookie-based authentication dependency (reads from request.cookies)
- Opportunistic refresh token cleanup on each refresh

### 🔧 Infrastructure
- initContainer for Alembic migrations in K8s backend deployment
- Standalone migration Job (k8s/backend-migration-job.yaml) as fallback
- Updated deploy workflow with migration Job apply step
- Updated docker-compose with auth environment variables
- K8s Secret uses empty strings with validation enforcement

### 📚 Documentation
- Google OAuth setup guide (docs/google-oauth-setup.md)
- Backend README (backend/README.md)
- API documentation (docs/api/auth.md)
- Auth flow architecture (docs/architecture/auth-flow.md)
- Domain models documentation (docs/domain/models.md)
- Local development setup (docs/dev-setup.md)

### 🐛 Fixes
- bcrypt pinned to 4.2.1 (5.x incompatible with passlib)
- Test conftest dependency override corrected (get_db instead of get_async_session)
- Duplicate UserResponse schema deduplicated
- OAuth state cookie cleared on error paths
- Register endpoint catches DuplicateEmailError specifically (not generic Exception)

### 🧪 Tests
- 13/13 security unit tests passed
- Integration tests for auth, users, RBAC (require MySQL, run in CI/CD)
- Test fixtures for async client, DB session, test users

### Dependencies (new)
- **Backend:** fastapi, sqlalchemy[asyncio], aiomysql, alembic, python-jose[cryptography], passlib[bcrypt], bcrypt==4.2.1, google-auth, slowapi, pydantic-settings, httpx (test)
- **Frontend:** react-router-dom
