# Authentication Flows

This document describes the step-by-step flows for registration, login, Google OAuth, token refresh, logout, and RBAC middleware.

---

## 1. Registration Flow

```
Client                                  Backend
  |                                       |
  |-- POST /api/v1/auth/register ------->|
  |   {email, password, name}             |
  |                                       |
  |                              [Validate input (Pydantic)]
  |                              [Check email uniqueness]
  |                              [Hash password with bcrypt]
  |                              [Insert user with default org_id]
  |                              [Generate JWT access + refresh tokens]
  |                              [Hash refresh token with SHA-256]
  |                              [Store refresh token hash in DB]
  |<-- 201 Created + Set-Cookie ---------|
  |   access_token (15 min, httpOnly)     |
  |   refresh_token (7 days, httpOnly)    |
```

**Notes:**
- Default `org_id`: `00000000-0000-0000-0000-000000000001` (seeded via Alembic migration)
- Default role: `student`
- Rate limit: 5 requests / min per IP

---

## 2. Login Flow

```
Client                                  Backend
  |                                       |
  |-- POST /api/v1/auth/login ----------->|
  |   {email, password}                   |
  |                                       |
  |                              [Find user by email]
  |                              [Verify password_hash is not None]
  |                              [bcrypt verify password]
  |                              [Generate JWT access + refresh tokens]
  |                              [Hash refresh token with SHA-256]
  |                              [Store refresh token hash in DB]
  |<-- 200 OK + Set-Cookie --------------|
  |   access_token, refresh_token         |
```

**Notes:**
- Generic error message on failure: `"Invalid email or password"` (prevents user enumeration)
- Google OAuth users (password_hash = None) cannot log in with email/password
- Rate limit: 5 requests / min per IP

---

## 3. Google OAuth Flow

### 3.1 Initiation

```
Client                                  Backend
  |                                       |
  |-- GET /api/v1/auth/google ----------->|
  |                                       |
  |                              [Generate CSRF state: secrets.token_urlsafe(32)]
  |                              [Set oauth_state cookie (10 min, httpOnly)]
  |<-- 302 Found ------------------------|
  |   Location: https://accounts.google.com/o/oauth2/v2/auth?...
```

### 3.2 Callback

```
Google                                  Backend
  |                                       |
  |-- GET /api/v1/auth/google/callback -->|
  |   ?code=...&state=...                 |
  |                                       |
  |                              [Check for ?error= param]
  |                              [Validate code + state presence]
  |                              [Validate state against oauth_state cookie]
  |                              [Exchange code for tokens (server-to-server)]
  |                              [Verify Google ID token (aud = client_id)]
  |                              [Find or create user by google_sub / email]
  |                              [Account linking: if email exists, set google_sub]
  |                              [Generate JWT access + refresh tokens]
  |                              [Store refresh token hash in DB]
  |<-- 302 Found + Set-Cookie -----------|
  |   access_token, refresh_token         |
  |   Clear oauth_state cookie            |
  |   Location: /auth/callback?success=true
```

**Error path (user denies consent):**
- Backend clears `oauth_state` cookie and redirects to `/auth/callback?success=false&error=...`

**Security:**
- CSRF state is httpOnly cookie (XSS-proof)
- Client secret never reaches browser
- ID token verified server-side with `google-auth` library

---

## 4. Refresh Flow

```
Client                                  Backend
  |                                       |
  |-- POST /api/v1/auth/refresh --------->|
  |   Cookie: refresh_token=...           |
  |                                       |
  |                              [Read refresh_token from cookie]
  |                              [Compute SHA-256 hash]
  |                              [Find token in DB (with updated_at)]
  |                              [Check not revoked and not expired]
  |                              [Optimistic locking: revoke WHERE updated_at = ?]
  |                              [If rowcount == 0 → token already used → 401]
  |                              [Generate new access + refresh tokens]
  |                              [Store new refresh token hash in DB]
  |                              [cleanup_expired(): delete revoked/expired >30d]
  |<-- 200 OK + Set-Cookie --------------|
  |   New access_token, refresh_token     |
```

**Optimistic locking:**
- Prevents concurrent refresh token reuse (race condition / replay attack)
- Only one concurrent request succeeds; others receive 401

**Frontend refresh lock:**
- `api.ts` uses a module-level `refreshPromise` to prevent multiple simultaneous refresh requests

---

## 5. Logout Flow

```
Client                                  Backend
  |                                       |
  |-- POST /api/v1/auth/logout ---------->|
  |   Cookie: access_token, refresh_token |
  |                                       |
  |                              [Validate access_token (get_current_user)]
  |                              [Read refresh_token from cookie]
  |                              [Find token in DB (with updated_at)]
  |                              [Revoke with optimistic locking]
  |                              [Clear access_token cookie (max_age=0)]
  |                              [Clear refresh_token cookie (max_age=0)]
  |<-- 204 No Content -------------------|
```

**Notes:**
- If refresh token is not found, logout still succeeds (idempotent)
- Clears both cookies unconditionally

---

## 6. RBAC Middleware Flow

### 6.1 Authentication (`get_current_user`)

```
Request → [Extract access_token from cookie]
        → [Verify JWT signature and expiry (HS256)]
        → [Extract user_id from "sub" claim]
        → [Load User from DB]
        → [Attach User to request scope]
```

**Failures:**
- Missing cookie → 401 `"Not authenticated"`
- Expired token → 401 `"Token has expired"`
- Invalid signature → 401 `"Invalid token"`
- User not found → 401 `"User not found"`

### 6.2 Authorization (`require_role`)

```
Request → [Run get_current_user]
        → [Check user.has_role(required_role)]
        → [If none match → 403]
        → [If match → proceed to handler]
```

**Usage in routes:**

```python
@router.get("/users", ...)
async def list_users(
    current_user: User = Depends(require_role("instructor", "super-admin")),
    ...
):
    ...
```

**Role hierarchy:**

| Role | Permissions |
|------|-------------|
| `student` | Self-service attendance (future), view own profile |
| `instructor` | List users, manage classes/attendance (future) |
| `super-admin` | Assign/remove roles, full access |

**Important:** Role changes invalidate all refresh tokens immediately, forcing re-authentication with updated role claims.
