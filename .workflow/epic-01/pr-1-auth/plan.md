# PR-1-auth: Technical Implementation Plan

## Overview

This PR implements authentication (email/password + Google OAuth), JWT token management with refresh tokens, role-based access control (RBAC), and multi-organization data foundation for the Dojo Manager application.

**Dependencies:** PR-0-infra (Docker, K8s manifests, CI/CD already in place)
**Blocks:** PR-2 through PR-8 (all subsequent PRs depend on auth + org foundation)

---

## 1. Database Migrations

Two Alembic migration files. Both use async MySQL via aiomysql.

### Migration 1: 001_create_orgs_table.py

**Table: orgs**

| Column | Type | Constraints | Default |
|--------|------|-------------|---------|
| id | UUID | PRIMARY KEY, NOT NULL | UUID() |
| name | VARCHAR(255) | NOT NULL | - |
| created_at | DATETIME | NOT NULL | NOW() |
| updated_at | DATETIME | NOT NULL | NOW(), onupdate=func.now() (SQLAlchemy-level) |

**Indexes:** ix_orgs_id on id
**Seed:** id=00000000-0000-0000-0000-000000000001, name="Default Dojo" (INSERT IGNORE for idempotency)

### Migration 2: 002_create_users_and_refresh_tokens.py

**Table: users**

| Column | Type | Constraints | Default |
|--------|------|-------------|---------|
| id | UUID | PRIMARY KEY, NOT NULL | UUID() |
| org_id | UUID | FK orgs.id, NOT NULL, CASCADE | - |
| email | VARCHAR(255) | NOT NULL, UNIQUE | - |
| password_hash | VARCHAR(255) | NULLABLE | NULL |
| name | VARCHAR(255) | NOT NULL | - |
| roles | JSON | NOT NULL | ["student"] |
| auth_provider | VARCHAR(50) | NOT NULL | "email" |
| google_sub | VARCHAR(255) | NULLABLE, UNIQUE | NULL |
| created_at | DATETIME | NOT NULL | NOW() |
| updated_at | DATETIME | NOT NULL | NOW(), onupdate=func.now() (SQLAlchemy-level) |

**Indexes:** ix_users_id, ix_users_org_id, ix_users_email (unique), ix_users_google_sub (unique)

**Table: refresh_tokens**

| Column | Type | Constraints | Default |
|--------|------|-------------|---------|
| id | UUID | PRIMARY KEY, NOT NULL | UUID() |
| user_id | UUID | FK users.id, NOT NULL, CASCADE | - |
| token_hash | VARCHAR(255) | NOT NULL, UNIQUE | - |
| expires_at | DATETIME | NOT NULL | - |
| created_at | DATETIME | NOT NULL | NOW() |
| revoked | BOOLEAN | NOT NULL | FALSE |
| updated_at | DATETIME | NOT NULL | NOW(), onupdate=func.now() (SQLAlchemy-level) |

**Indexes:** ix_refresh_tokens_id, ix_refresh_tokens_user_id, ix_refresh_tokens_token_hash (unique), ix_refresh_tokens_expires_at

**Design:** Refresh tokens stored as SHA-256 hashes. Multi-device: each device gets own row. Rotation: old revoked, new issued on refresh. Logout: revoked=TRUE. The `updated_at` field is used for concurrent refresh detection (MAJ-5 fix).

---

## 2. Backend File Structure

Clean Architecture: api > services > repositories > domain. All under backend/app/.

```
backend/
+-- pyproject.toml                          # CREATE with new dependencies
+-- alembic.ini                             # UPDATE: sqlalchemy.url from env var
+-- .env.example                            # CREATE with new env vars
+-- alembic/
|   +-- env.py                              # UPDATE for async migrations
|   +-- script.py.mako
|   +-- versions/
|       +-- 001_create_orgs_table.py        # NEW
|       +-- 002_create_users_and_refresh_tokens.py  # NEW
+-- app/
|   +-- __init__.py
|   +-- main.py                             # UPDATE: routers, CORS, middleware, lifespan
|   +-- config.py                           # UPDATE: auth-related settings
|   +-- database.py                         # NEW: async engine, session factory
|   +-- api/
|   |   +-- __init__.py
|   |   +-- router.py                       # NEW: aggregate all routers
|   |   +-- routes/
|   |   |   +-- __init__.py
|   |   |   +-- auth.py                     # NEW: /api/auth/* endpoints
|   |   |   +-- users.py                    # NEW: /api/users/* endpoints
|   |   +-- dependencies/
|   |       +-- __init__.py
|   |       +-- get_db.py                   # NEW: async session dependency
|   |       +-- get_current_user.py         # NEW: JWT extraction from cookie + RBAC
|   +-- core/
|   |   +-- __init__.py
|   |   +-- security.py                     # NEW: JWT, password hash/verify, Google token verify
|   |   +-- exceptions.py                   # NEW: custom exception classes
|   |   +-- middleware.py                   # NEW: rate limiter setup
|   +-- domain/
|   |   +-- __init__.py
|   |   +-- models/
|   |   |   +-- __init__.py
|   |   |   +-- org.py                      # NEW: SQLAlchemy ORM model
|   |   |   +-- user.py                     # NEW: SQLAlchemy ORM model
|   |   +-- exceptions.py                   # NEW: domain-level exceptions
|   +-- services/
|   |   +-- __init__.py
|   |   +-- auth_service.py                 # NEW: register, login, OAuth, refresh, logout
|   |   +-- user_service.py                 # NEW: list users, assign/remove roles
|   +-- repositories/
|   |   +-- __init__.py
|   |   +-- user_repo.py                    # NEW: CRUD for users + refresh tokens
|   +-- schemas/
|       +-- __init__.py
|       +-- auth.py                         # NEW: request/response schemas for auth
|       +-- user.py                         # NEW: request/response schemas for users
+-- tests/
    +-- __init__.py
    +-- conftest.py                         # NEW: test fixtures
    +-- test_auth.py                        # NEW
    +-- test_users.py                       # NEW
    +-- test_security.py                    # NEW
    +-- test_rbac.py                        # NEW
```

### Key File Responsibilities

| File | Responsibility |
|------|---------------|
| database.py | create_async_engine, async_sessionmaker, get_async_session generator, Base class |
| config.py | Settings class with all env vars (JWT, OAuth, CORS, DB, rate limits) |
| main.py | FastAPI app, CORS middleware, router inclusion, rate limiter, lifespan |
| core/security.py | create_access_token(), verify_token(), hash_password(), verify_password(), verify_google_id_token() |
| core/exceptions.py | AuthenticationError, AuthorizationError, TokenExpiredError |
| core/middleware.py | SlowAPI limiter setup, custom 429 handler |
| api/dependencies/get_db.py | get_db() async generator yielding AsyncSession |
| api/dependencies/get_current_user.py | get_current_user() reads from cookie (NOT OAuth2PasswordBearer), require_role() |
| api/routes/auth.py | All /api/auth/* endpoint handlers |
| api/routes/users.py | All /api/users/* endpoint handlers |
| services/auth_service.py | Business logic: register, login, OAuth callback, token refresh, logout |
| services/user_service.py | Business logic: list users, assign role, remove role |
| repositories/user_repo.py | Data access: find_by_email, find_by_google_sub, create, save, refresh token CRUD |
| domain/models/ | SQLAlchemy ORM models (Org, User, RefreshToken) |
| schemas/ | Pydantic v2 schemas for request validation and response serialization |

---

## 3. Frontend File Structure

All under frontend/src/.

```
frontend/src/
+-- main.tsx                                # UPDATE: wrap with BrowserRouter
+-- App.tsx                                 # UPDATE: define routes
+-- pages/
|   +-- LoginPage.tsx                       # NEW: email/password + Google login
|   +-- RegisterPage.tsx                    # NEW: email/password/name registration
|   +-- CallbackPage.tsx                    # NEW: handles OAuth redirect from backend
|   +-- DashboardPage.tsx                   # NEW: placeholder dashboard
+-- components/
|   +-- ProtectedRoute.tsx                  # NEW: route guard
+-- hooks/
|   +-- useAuth.tsx                         # NEW: auth context + hook
+-- services/
|   +-- auth.ts                             # NEW: API calls for auth endpoints
+-- types/
|   +-- auth.ts                             # NEW: TypeScript interfaces
+-- utils/
    +-- api.ts                              # NEW: base fetch wrapper with cookie support
```

### Key File Responsibilities

| File | Responsibility |
|------|---------------|
| App.tsx | Route definitions: /login, /register, /auth/callback, /dashboard, protected routes |
| pages/LoginPage.tsx | Email/password form, Google button, error display, redirect on success |
| pages/RegisterPage.tsx | Email/password/name form, validation, error display, auto-login on success |
| pages/CallbackPage.tsx | Reads ?success=true/false, calls getMe(), redirects to /dashboard |
| pages/DashboardPage.tsx | Shows user info, role-based nav stubs, logout button |
| components/ProtectedRoute.tsx | Checks auth state, redirects to /login if unauthenticated |
| hooks/useAuth.tsx | AuthContext provider + useAuth() hook: user, login(), register(), logout(), isAuthenticated |
| services/auth.ts | login(), register(), logout(), getMe(), initiateGoogleLogin() |
| types/auth.ts | User, LoginRequest, RegisterRequest, AuthResponse, Role types |
| utils/api.ts | apiFetch() wrapper with credentials: 'include', relative API paths, promise-based refresh lock |

---

## 4. Dependencies

### Backend (backend/pyproject.toml)

```toml
[project]
name = "dojo-backend"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
    "fastapi>=0.128.0",
    "uvicorn[standard]>=0.34.0",
    "sqlalchemy[asyncio]>=2.0.44",
    "aiomysql>=0.2.0",
    "alembic>=1.14.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.7.0",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "google-auth>=2.37.0",
    "slowapi>=0.1.9",
    "httpx>=0.27.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "ruff>=0.8.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"

[tool.ruff]
target-version = "py313"
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "SIM"]
```

**Rationale:**
- python-jose[cryptography] - JWT HS256 with secure key handling
- passlib[bcrypt] - bcrypt password hashing, constant-time comparison
- google-auth - Official Google library for OAuth2 ID token verification (handles cert rotation)
- slowapi - Rate limiting for FastAPI, in-memory backend (no Redis for MVP)
- aiomysql - Pure Python async MySQL driver, ARM64 compatible, no C extensions

### Frontend (package.json additions)

```json
{
  "dependencies": {
    "react-router-dom": "^7.1.0"
  },
  "devDependencies": {
    "@types/jest": "^29.5.0",
    "ts-jest": "^29.2.0",
    "identity-obj-proxy": "^3.0.0"
  }
}
```

**Rationale:**
- react-router-dom v7 - Latest stable, React 19 compatible
- ts-jest - TypeScript preprocessor for Jest
- identity-obj-proxy - Mock CSS modules in Jest

---

## 5. Environment Variables

### Backend (backend/.env.example)

```env
# Database
DATABASE_URL=mysql+aiomysql://root:@localhost:3306/dojo

# JWT
JWT_SECRET=change-me-to-a-random-256-bit-string
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Google OAuth
GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret-here
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback

# CORS
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:80

# Rate Limiting
RATE_LIMIT_DEFAULT=100/minute
RATE_LIMIT_AUTH=5/minute

# App
APP_ENV=development
API_PREFIX=/api/v1
```

**Note:** Real Google OAuth credentials must be set via Kubernetes Secrets or CI/CD secrets. Never commit real credentials. The local `backend/.env` file is gitignored and may contain real values for local development only.

### Frontend (frontend/.env.example - update existing)

```env
# Dev: empty string — Vite proxy handles /api -> localhost:8000
# Prod: full URL — set via CI/CD or deployment config
VITE_API_BASE=
```

**Note:** Removed `VITE_GOOGLE_CLIENT_ID` — Google OAuth is entirely backend-driven (302 redirect chain). The frontend never needs the Google client ID directly.

---

## 6. Endpoint Specifications

### Auth Endpoints

| Method | Endpoint | Auth | Rate Limit | Description |
|--------|----------|------|------------|-------------|
| POST | /api/v1/auth/register | Public | 5/min | Register with email/password |
| POST | /api/v1/auth/login | Public | 5/min | Login with email/password |
| GET | /api/v1/auth/google | Public | - | Redirect to Google OAuth |
| GET | /api/v1/auth/google/callback | Public | - | OAuth callback, sets cookies, redirects to frontend |
| POST | /api/v1/auth/refresh | Refresh cookie | - | Rotate refresh token, issue new access token |
| POST | /api/v1/auth/logout | Access token | - | Revoke refresh token, clear cookie |
| GET | /api/v1/auth/me | Access token | - | Get current user profile |

### User Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | /api/v1/users | instructor+ / super-admin | List users (paginated) |
| POST | /api/v1/users/{id}/roles | super-admin only | Assign role to user |
| DELETE | /api/v1/users/{id}/roles/instructor | super-admin only | Remove instructor role |

### Error Response Format

All errors: {detail: "human-readable message"} with standard HTTP codes:

| Code | Meaning | Example |
|------|---------|---------|
| 400 | Bad request | {"detail": "User does not have instructor role"} |
| 401 | Not authenticated | {"detail": "Invalid email or password"} |
| 403 | Insufficient permissions | {"detail": "Insufficient permissions"} |
| 404 | Not found | {"detail": "User not found"} |
| 409 | Conflict | {"detail": "Email already registered"} |
| 422 | Validation error | Pydantic default format |
| 429 | Rate limited | {"detail": "Too many requests. Try again later."} |

### Cookie Configuration

Both tokens as httpOnly cookies:
- access_token: HttpOnly; Secure (prod only); SameSite=Lax; Path=/; Max-Age=900 (15 min)
- refresh_token: HttpOnly; Secure (prod only); SameSite=Lax; Path=/; Max-Age=604800 (7 days)

Backend reads tokens from cookies, not Authorization header.

### Google OAuth Flow

1. Frontend redirects to GET /api/v1/auth/google
2. Backend generates CSRF state token, stores in httpOnly cookie
3. Backend 302 redirects to Google (scope=email profile, response_type=code)
4. User consents on Google
5. Google redirects to /api/v1/auth/google/callback?code=...&state=...
6. Backend validates state against cookie (CSRF protection)
7. Backend exchanges code with Google for ID token
8. Backend verifies ID token with google-auth (validates aud = client ID)
9. Backend finds or creates user by google_sub / email
10. Backend issues JWT + refresh tokens, sets cookies
11. Backend 302 redirects to frontend: /auth/callback?success=true
12. Frontend CallbackPage calls GET /api/v1/auth/me, redirects to /dashboard

---

## 7. Task Breakdown

Effort: small (<0.5 day), medium (0.5-1 day), large (1-2 days).

### Task 1: Backend Dependencies & Configuration (small)
**Dependencies:** none
**Files:** backend/pyproject.toml, backend/.env.example, backend/alembic.ini, backend/app/config.py
- Add all dependencies to pyproject.toml, run uv sync
- Update .env.example with all new env vars (use placeholder values for secrets)
- Update alembic.ini to read sqlalchemy.url from env var
- Extend config.py Settings class with: JWT settings (JWT_SECRET, JWT_ALGORITHM, JWT_ACCESS_TOKEN_EXPIRE_MINUTES, JWT_REFRESH_TOKEN_EXPIRE_DAYS), Google OAuth settings, CORS origins (comma-separated to list), rate limit settings

### Task 2: Database Layer Setup (small)
**Dependencies:** Task 1
**Files:** backend/app/database.py, backend/alembic/env.py
- Create database.py: create_async_engine with mysql+aiomysql://, async_sessionmaker(expire_on_commit=False), get_async_session() async generator, Base class (AsyncAttrs, DeclarativeBase)
- Update alembic/env.py: import Base, configure async_engine_from_config, set target_metadata = Base.metadata

### Task 3: Database Migrations (medium)
**Dependencies:** Task 2
**Files:** backend/alembic/versions/001_create_orgs_table.py, backend/alembic/versions/002_create_users_and_refresh_tokens.py
- Create migration 001: orgs table + default org seed (INSERT IGNORE with UUID 00000000-0000-0000-0000-000000000001, name "Default Dojo")
- Create migration 002: users + refresh_tokens tables with all columns, constraints, indexes. Include `updated_at` column on refresh_tokens for concurrent refresh detection.
- Verify: alembic upgrade head, then alembic downgrade base && alembic upgrade head

### Task 4: Domain Models (small)
**Dependencies:** Task 3
**Files:** backend/app/domain/models/__init__.py, backend/app/domain/models/org.py, backend/app/domain/models/user.py, backend/app/domain/exceptions.py
- Create Org ORM model (maps to orgs table)
- Create User ORM model with: roles as JSON column, helper methods has_role(role), add_role(role), remove_role(role)
- Create RefreshToken ORM model with updated_at field
- Create domain exceptions: UserNotFoundError, DuplicateEmailError, InvalidRoleError

### Task 5: Security Core (small)
**Dependencies:** Task 1 (moved from Task 4 — security functions don't need ORM models)
**Files:** backend/app/core/security.py, backend/app/core/exceptions.py
- hash_password(password) -> str using passlib bcrypt
- verify_password(password, hash) -> bool
- create_access_token(data, expires_delta) -> str using python-jose HS256
- create_refresh_token_raw() -> str (secrets.token_urlsafe)
- hash_token(token) -> str (SHA-256)
- verify_token(token) -> dict (decode JWT, validate expiry)
- verify_google_id_token(id_token, client_id) -> dict using google-auth id_token.verify_oauth2_token()
- Exception classes: AuthenticationError, AuthorizationError, TokenExpiredError

### Task 6: Repository Layer (medium)
**Dependencies:** Task 3, Task 4
**Files:** backend/app/repositories/__init__.py, backend/app/repositories/user_repo.py
- UserRepository: create(), find_by_email(), find_by_google_sub(), find_by_id(), list_users(org_id, offset, limit) -> (list[User], total), save()
- RefreshTokenRepository: create(), find_by_hash(), find_by_hash_with_updated_at(), revoke(), revoke_all_for_user(), cleanup_expired()
  - `cleanup_expired()`: deletes tokens where revoked=TRUE OR expires_at < NOW() - 30 days. Called opportunistically on each refresh (MAJ-4 fix).
  - `find_by_hash_with_updated_at()`: returns token row including updated_at for concurrent refresh detection (MAJ-5 fix).

### Task 7: Service Layer (large)
**Dependencies:** Task 5, Task 6
**Files:** backend/app/services/__init__.py, backend/app/services/auth_service.py, backend/app/services/user_service.py

AuthService:
- register(email, password, name, org_id) - check uniqueness, hash password, create user with roles=["student"], create tokens, store refresh token hash, return tokens + user
- login(email, password) - find user, verify password_hash is not None (reject Google-only users), create tokens, store refresh token hash, return tokens + user
- google_oauth_login(code, state) - validate state (CSRF), exchange code for ID token, verify ID token, find/create user (if email matches existing email-only user, link by setting google_sub), create tokens, return tokens + user
- refresh_access_token(refresh_token) - hash + lookup, check not expired/revoked, **concurrent refresh detection**: compare updated_at — if token was already used (updated_at changed since lookup), return 401 (force re-auth). Otherwise: revoke old, create new tokens, store new refresh token, return new tokens.
- logout(refresh_token) - hash + lookup, mark revoked

UserService:
- list_users(org_id, offset, limit) - paginated list
- assign_role(user_id, role) - add role to JSON array (super-admin only)
- remove_role(user_id, role) - remove role from JSON array (super-admin only)

### Task 8: API Dependencies (small)
**Dependencies:** Task 5
**Files:** backend/app/api/dependencies/__init__.py, backend/app/api/dependencies/get_db.py, backend/app/api/dependencies/get_current_user.py
- get_db() - async generator yielding AsyncSession
- get_current_user(request: Request) — **Cookie-based auth (NOT OAuth2PasswordBearer)**. Extracts access_token from `request.cookies.get("access_token")`. If missing or invalid, raises HTTPException(401). Verifies JWT via `verify_token()`. Returns User object. For OpenAPI docs only: create a separate `oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)` purely for the security schema — do NOT use it for actual token extraction.
- require_role(*roles) - factory returning dependency that checks user has at least one required role, raises 403 if not

### Task 9: API Routes (large)
**Dependencies:** Task 7, Task 8
**Files:** backend/app/api/__init__.py, backend/app/api/router.py, backend/app/api/routes/__init__.py, backend/app/api/routes/auth.py, backend/app/api/routes/users.py

auth.py:
- POST /register - @limiter.limit("5/minute"), calls AuthService.register, sets refresh token cookie
- POST /login - @limiter.limit("5/minute"), calls AuthService.login, sets cookie
- GET /google - generates CSRF state, stores in cookie, 302 redirects to Google OAuth URL
- GET /google/callback - validates state, calls AuthService.google_oauth_login, sets cookies, 302 redirects to frontend
- POST /refresh - reads refresh token from cookie, calls AuthService.refresh_access_token, sets new cookie
- POST /logout - reads refresh token from cookie, calls AuthService.logout, clears cookie (Max-Age=0)
- GET /me - uses get_current_user (cookie-based), returns user profile

users.py:
- GET / - require_role("instructor", "super-admin"), calls UserService.list_users
- POST /{user_id}/roles - require_role("super-admin"), calls UserService.assign_role
- DELETE /{user_id}/roles/instructor - require_role("super-admin"), calls UserService.remove_role

router.py: Create APIRouter instances, include all under /api/v1 prefix

### Task 10: Middleware & App Setup (medium)
**Dependencies:** Task 9
**Files:** backend/app/main.py, backend/app/core/middleware.py
- CORS middleware with **allow_credentials=True** and allowed_origins from env (parsed from comma-separated string). **Critical:** `allow_origins` cannot be `["*"]` when credentials are enabled — must be explicit list.
- SlowAPI rate limiter: default 100/minute, custom 429 handler returning {"detail": "Too many requests. Try again later."}
- Lifespan: log startup message
- Include all routers
- Health endpoint at /health (existing) and /api/v1/health

### Task 11: Frontend Dependencies & Setup (small)
**Dependencies:** none (parallel with backend)
**Files:** frontend/package.json, frontend/.env.example, frontend/src/main.tsx
- npm install react-router-dom
- Update .env.example with VITE_API_BASE (empty string for dev, full URL for prod)
- Wrap App in BrowserRouter in main.tsx

### Task 12: Frontend Types & Services (small)
**Dependencies:** Task 11
**Files:** frontend/src/types/auth.ts, frontend/src/services/auth.ts, frontend/src/utils/api.ts

types/auth.ts:
- Role = 'student' | 'instructor' | 'super-admin'
- User: id, email, name, roles, org_id, auth_provider, created_at
- LoginRequest: email, password
- RegisterRequest: email, password, name
- AuthResponse: access_token, token_type, user

utils/api.ts:
- **API URL strategy:** Use relative paths (`/api/v1/...`) in development. Vite dev server proxies `/api` to `localhost:8000` (already configured in vite.config.ts). Set `VITE_API_BASE=""` for dev. For production, set `VITE_API_BASE` to the full backend URL via CI/CD or deployment config.
- apiFetch(url, options) - credentials: 'include', base URL from VITE_API_BASE
- **Promise-based refresh lock (MAJ-5 fix):** Module-level `refreshPromise: Promise<void> | null`. On 401: if refresh already in progress, await it instead of starting a new one. If refresh fails, clear promise and redirect to login. After successful refresh, retry original request.

services/auth.ts: login(), register(), logout(), getMe(), initiateGoogleLogin() (redirects to /api/v1/auth/google)

### Task 13: Frontend Auth Hook & Context (medium)
**Dependencies:** Task 12
**Files:** frontend/src/hooks/useAuth.tsx
- AuthContext with: user, isAuthenticated, isLoading, login(), register(), logout()
- AuthProvider: on mount call getMe() to check existing session (cookies persist), provide context
- useAuth() hook for consuming context

### Task 14: Frontend Pages (medium)
**Dependencies:** Task 13
**Files:** frontend/src/pages/LoginPage.tsx, frontend/src/pages/RegisterPage.tsx, frontend/src/pages/CallbackPage.tsx, frontend/src/pages/DashboardPage.tsx
- LoginPage: email + password form, Google button, error display, redirect to /dashboard on success, link to /register
- RegisterPage: email + password + name form, client-side validation, error display, redirect to /dashboard on success, link to /login
- CallbackPage: read ?success=true/false, if success call getMe() and redirect to /dashboard, if failure show error + link to /login
- DashboardPage: display user name/email/roles, role-based nav stubs, logout button

### Task 15: Frontend Route Protection & App Routes (small)
**Dependencies:** Task 14
**Files:** frontend/src/components/ProtectedRoute.tsx, frontend/src/App.tsx
- ProtectedRoute: check isAuthenticated, if loading show spinner, if not authenticated redirect to /login, else render children
- App.tsx routes: /login, /register, /auth/callback, /dashboard (protected), / -> redirect to /dashboard

### Task 16: Backend Tests (large)
**Dependencies:** Task 10
**Files:** backend/tests/conftest.py, backend/tests/test_auth.py, backend/tests/test_users.py, backend/tests/test_security.py, backend/tests/test_rbac.py
- conftest.py: async_client fixture (FastAPI AsyncClient), db_session fixture (rollback after each test), test_user fixture, admin_user fixture, mock Google OAuth responses
- test_security.py: password hash/verify, JWT create/verify, JWT expiry, Google ID token verification (mocked)
- test_auth.py: register (success, duplicate email, validation), login (success, invalid creds, rate limit), refresh (success, expired, revoked, concurrent refresh race), logout, Google OAuth (success, new user, existing user, CSRF mismatch)
- test_users.py: list users (success, forbidden, pagination), assign role (success, forbidden, invalid role), remove role (success, no role)
- test_rbac.py: no token -> 401, wrong role -> 403, correct role -> 200, expired token -> 401

### Task 17: Frontend Tests (medium)
**Dependencies:** Task 15
**Files:** frontend/jest.config.js, frontend/tests/LoginPage.test.tsx, frontend/tests/RegisterPage.test.tsx, frontend/tests/ProtectedRoute.test.tsx, frontend/tests/useAuth.test.tsx
- Configure jest.config.js with ts-jest, jsdom environment
- LoginPage.test.tsx: renders form, validation errors, API call on submit, redirect on success, Google button
- RegisterPage.test.tsx: renders form, validation, API call, redirect
- ProtectedRoute.test.tsx: redirects when unauthenticated, renders children when authenticated
- useAuth.test.tsx: loads user on mount, clears on logout, handles 401

### Task 18: Docker, K8s & Migration Execution (medium)
**Dependencies:** Task 10
**Files:** k8s/backend-deployment.yaml, k8s/backend-migration-job.yaml, docker-compose.yml

**K8s backend-deployment.yaml updates:**
- Add env vars for **JWT_SECRET** (standardized key name), GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI, ALLOWED_ORIGINS as Kubernetes Secrets
- **Add initContainer** that runs `alembic upgrade head` before the main backend container starts. This ensures migrations are applied before the app serves traffic. The initContainer uses the same image as the backend, shares the same env vars, and runs the command `alembic upgrade head`. The backend Deployment will not start until the initContainer completes successfully.

**New file: k8s/backend-migration-job.yaml:**
- Standalone Kubernetes Job as a fallback/alternative to initContainer. Runs `alembic upgrade head` as a one-shot. Can be triggered manually or via CI/CD pre-deploy step.

**docker-compose.yml updates:**
- Add auth-related env vars to backend service

**Migration execution strategy (CRIT-2 fix):**
- **Primary:** initContainer in backend-deployment.yaml (most reliable — migrations run before app starts)
- **Fallback:** backend-migration-job.yaml for manual execution
- **CI/CD:** Add pre-deploy step in deploy.yml that runs the migration Job before rolling out the backend Deployment

### Task 19: Documentation (small)
**Dependencies:** Task 10
**Files:** docs/google-oauth-setup.md, backend/README.md
- Create docs/google-oauth-setup.md: Google Cloud project setup, OAuth credentials, redirect URIs, env vars
- Update backend/README.md: setup instructions, migration commands, test commands, env vars reference

### Task 20: Refresh Token Cleanup (small)
**Dependencies:** Task 6
**Files:** backend/app/services/auth_service.py (update), backend/app/repositories/user_repo.py (update)
- Implement opportunistic cleanup: call `cleanup_expired()` on each refresh token creation (deletes tokens where revoked=TRUE OR expires_at < NOW() - 30 days)
- This is a lightweight approach that doesn't require a separate cron job or scheduled task
- Document that for high-traffic deployments, a separate periodic cleanup (cron job or scheduled endpoint) should be added

### Task Dependency Graph

```
Task 1 (Config) --> Task 2 (DB Layer) --> Task 3 (Migrations) --> Task 4 (Models) --+
                    |                                                               |
                    +---------------------------------------------------------------+
                                                                                    +--> Task 5 (Security) -->+
                                                                                    |                       |
                                                                                    +--> Task 6 (Repo) -----+
                                                                                                            +--> Task 7 (Services) --> Task 8 (Deps) --> Task 9 (Routes) --> Task 10 (App) --> Task 16 (Backend Tests)
                                                                                                                                                                                                   |
Task 11 (FE Deps) --> Task 12 (FE Types/Svc) --> Task 13 (FE Hook) --> Task 14 (FE Pages) --> Task 15 (FE Routes) --> Task 17 (FE Tests)
                                                                                                                                                                                                   |
                                                                                                                                                                                                   +--> Task 18 (Docker/K8s)
                                                                                                                                                                                                   |
                                                                                                                                                                                                   +--> Task 19 (Docs)

Task 6 (Repo) --> Task 20 (Token Cleanup)
```

**Parallel tracks:**
- Backend: 1->2->3->4->5->6->7->8->9->10->16
- Frontend: 11->12->13->14->15->17 (can start after Task 1)
- Infra: Task 18 (after Task 10)
- Docs: Task 19 (after Task 10)
- Cleanup: Task 20 (after Task 6, parallel with 7-10)

---

## 8. Testing Strategy

### Backend (pytest + httpx AsyncClient)

| Category | What to test |
|----------|-------------|
| Unit | Security functions (hash, verify, JWT create/verify), service logic with mocked repos |
| Integration | Full API endpoint tests with test database (rollback per test) |
| RBAC | Role enforcement at endpoint level (401/403/200) |
| Rate limiting | 429 responses after exceeding 5/min limit |
| Cookie auth | Token extraction from cookies (not Authorization header) |
| Concurrent refresh | Race condition: simultaneous refresh attempts with same token -> 401 on second |

**Test database:** Use same MySQL with test schema, rollback after each test via conftest.py fixture.

**Key scenarios:**
1. Register -> verify user in DB with bcrypt hash, student role, tokens returned
2. Login -> JWT contains user ID, email, roles, org_id
3. Refresh -> new access token, old refresh token revoked
4. Google OAuth -> mock Google, verify user created/found, tokens returned
5. RBAC -> student accessing instructor endpoint -> 403
6. Rate limit -> 6 login requests in 1 min -> 429 on 6th
7. Concurrent refresh -> two simultaneous refreshes with same token -> first succeeds, second gets 401
8. Cookie auth -> request without cookie -> 401; request with valid cookie -> 200

### Frontend (Jest + React Testing Library)

| Category | What to test |
|----------|-------------|
| Unit | useAuth hook logic, apiFetch wrapper |
| Component | Page rendering, form validation, button clicks |
| Integration | Full login flow with mocked API (use MSW or jest.mock) |

**Key scenarios:**
1. Login page: fill form -> submit -> API called -> redirect on success
2. Register page: fill form -> submit -> API called -> redirect on success
3. Protected route: unauthenticated -> redirect to login; authenticated -> render children
4. Auth hook: mount -> API call -> user set; logout -> user cleared

---

## 9. Security Considerations

| # | Concern | Implementation |
|---|---------|---------------|
| S1 | Password storage | bcrypt with default rounds (12) |
| S2 | Refresh token storage | SHA-256 hash in DB, never raw tokens |
| S3 | Token transmission | httpOnly cookies for both tokens (XSS-proof) |
| S4 | CSRF protection | OAuth state parameter in httpOnly cookie, validated on callback |
| S5 | Rate limiting | 5 attempts/min on login/register via SlowAPI |
| S6 | Generic error messages | "Invalid email or password" - don't reveal which field |
| S7 | CORS | Env-based ALLOWED_ORIGINS, no wildcards, **allow_credentials=True** |
| S8 | JWT signing | HS256 with 256-bit+ secret from env |
| S9 | Token expiry | Access: 15 min, Refresh: 7 days |
| S10 | Refresh token rotation | New token on each use, old revoked |
| S11 | Multi-device | Separate refresh token row per device |
| S12 | SQL injection | SQLAlchemy parameterized queries only |
| S13 | Input validation | Pydantic schemas enforce type, length, format |
| S14 | HTTPS in production | Secure flag on cookies |
| S15 | SameSite cookies | SameSite=Lax |
| S16 | Google OAuth audience | Verify aud claim matches client ID |
| S17 | Role enforcement | Server-side via require_role() dependency |
| S18 | Org isolation | All queries scoped by org_id from JWT |
| S19 | Refresh token reuse detection | updated_at field comparison — if token was already used, return 401 |
| S20 | Token cleanup | Opportunistic cleanup of expired/revoked tokens older than 30 days |

---

## 10. Acceptance Criteria Mapping

| AC | Tasks | Verification |
|----|-------|-------------|
| AC-1: Email/password registration | 7, 9, 16 | Test: register -> user in DB with bcrypt hash, student role, tokens returned |
| AC-2: Email/password login | 7, 9, 16 | Test: login -> JWT with user ID, email, roles, org_id |
| AC-3: Google OAuth login | 7, 9, 16 | Test: OAuth flow -> new user created or existing found, tokens returned |
| AC-4: RBAC enforced | 8, 9, 16 | Test: no token -> 401, wrong role -> 403, correct role -> 200 |
| AC-5: Multi-org isolation | 3, 4, 7 | Test: orgs table exists, users.org_id FK, queries scoped by org_id from JWT |
| AC-6: Super-admin assigns instructor | 7, 9, 16 | Test: super-admin POST /users/{id}/roles -> user gains instructor role immediately |
| AC-7: Token expiration + refresh | 5, 7, 9, 16 | Test: expired access -> 401, refresh -> new tokens, expired refresh -> re-auth required |

---

## 11. Estimated Total Effort

| Track | Tasks | Effort |
|-------|-------|--------|
| Backend (config + DB + models + security + repo + services + routes + app) | 1-10 | ~3-4 days |
| Backend tests | 16 | ~1-2 days |
| Frontend (deps + types + services + hook + pages + routes) | 11-15 | ~2-3 days |
| Frontend tests | 17 | ~1 day |
| Infra + Docs + Cleanup | 18-20 | ~0.5 day |
| **Total** | | **~7-10 days** |

This aligns with the epic timeline estimate of 1 week for PR-1.

---

## 12. Implementation Notes

1. **Migration execution (CRIT-2 fix):** Migrations run via initContainer in backend-deployment.yaml. The initContainer uses the same backend image and runs `alembic upgrade head` before the main container starts. This is the most reliable approach — migrations complete before the app serves traffic. A standalone K8s Job (backend-migration-job.yaml) is also provided as a fallback for manual execution.

2. **Token storage:** Both access and refresh tokens in httpOnly cookies. Backend reads from cookies via custom `get_current_user(request: Request)` dependency — **NOT OAuth2PasswordBearer**. XSS-proof, sufficient for SPA with SameSite=Lax.

3. **Google OAuth redirect:** Backend handles full redirect chain (302 to Google, 302 back to frontend). Frontend reads ?success=true from URL.

4. **First super-admin:** Create via separate seed migration or CLI command. Documented but not implemented in this PR (ops setup task).

5. **Token cleanup (MAJ-4 fix):** Opportunistic cleanup of expired/revoked refresh tokens older than 30 days, called on each refresh token creation. Lightweight — no separate cron needed for MVP.

6. **Password reset:** DEFERRED per resolved clarifications. Manual workaround via DB intervention.

7. **Email verification:** DEFERRED per resolved clarifications.

8. **Account lockout:** DEFERRED per resolved clarifications. Rate limiting (5/min) provides basic brute-force protection.

9. **CORS credentials (MAJ-3 fix):** `allow_credentials=True` is required in CORSMiddleware. `ALLOWED_ORIGINS` must be an explicit list — no wildcards when credentials are enabled.

10. **Frontend API URL strategy (MAJ-2 fix):** Use relative paths (`/api/v1/...`) in development. Vite dev server already proxies `/api` to `localhost:8000`. Set `VITE_API_BASE=""` for dev. For production, set via CI/CD or deployment config.

11. **Refresh token race condition (MAJ-5 fix):** The `updated_at` field on refresh_tokens is used for concurrent refresh detection. When a refresh is processed, the token's `updated_at` is checked against the value at lookup time. If it changed (meaning another refresh already used this token), return 401 to force re-authentication.

12. **Config key consistency (MAJ-1 fix):** `JWT_SECRET` is used everywhere — config.py, K8s manifests, .env.example. The k8s/backend-deployment.yaml Secret key is updated from `SECRET_KEY` to `JWT_SECRET`.

13. **Google OAuth account linking (MIN-8):** If a user registered with email/password later signs in with Google using the same email, the system links the accounts by setting `google_sub` and updating `auth_provider` to "google".

14. **Login password_hash check (MIN-7):** `auth_service.login()` checks that `user.password_hash is not None` before verifying password. Google-only users attempting email/password login get a clear error message.
