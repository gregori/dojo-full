# Authentication API

API base path: `/api/v1`

All error responses follow the format:

```json
{ "detail": "message" }
```

Common HTTP status codes:

| Code | Meaning | Typical cause |
|------|---------|---------------|
| 400  | Bad Request | Missing query parameters (Google callback), invalid role value |
| 401  | Unauthorized | Missing/invalid/expired token, invalid credentials, refresh token reused |
| 403  | Forbidden | Authenticated but role insufficient |
| 404  | Not Found | User ID does not exist |
| 409  | Conflict | Email already registered |
| 422  | Unprocessable Entity | Pydantic validation error (e.g. email format, password < 8 chars) |
| 429  | Too Many Requests | Rate limit exceeded |

---

## Endpoints

### POST /auth/register

| | |
|---|---|
| **Auth** | Public |
| **Rate limit** | 5 requests / min |

Register a new user with email/password. The user is created with the default organization (`00000000-0000-0000-0000-000000000001`) and the `student` role.

**Request body** (`RegisterRequest`)

| Field | Type | Constraints |
|-------|------|-------------|
| email | string (EmailStr) | RFC format, max 255 chars |
| password | string | min 8, max 255 chars |
| name | string | min 2, max 255 chars |

**Response** `201 Created` — `AuthResponse`

| Field | Type | Description |
|-------|------|-------------|
| access_token | string | Short-lived JWT (15 min) |
| token_type | string | `bearer` |
| user | UserResponse | Full user object |

**Cookies set:** `access_token` (httpOnly), `refresh_token` (httpOnly)

**Error codes:** 409 (email exists), 422 (validation failure), 429 (rate limited)

---

### POST /auth/login

| | |
|---|---|
| **Auth** | Public |
| **Rate limit** | 5 requests / min |

Login with email and password.

**Request body** (`LoginRequest`)

| Field | Type |
|-------|------|
| email | string (EmailStr) |
| password | string |

**Response** `200 OK` — `AuthResponse` (same schema as register)

**Cookies set:** `access_token` (httpOnly), `refresh_token` (httpOnly)

**Error codes:** 401 (invalid credentials), 422, 429

---

### GET /auth/google

| | |
|---|---|
| **Auth** | Public |
| **Rate limit** | None |

Initiates Google OAuth Authorization Code flow.

**Behavior:**
- Generates a CSRF `state` token (32 bytes, URL-safe)
- Stores `state` in an httpOnly cookie named `oauth_state` (10 min TTL)
- Redirects (`302`) to Google OAuth consent screen with scopes `email+profile`

**Response:** `302 Found` → Google OAuth URL

---

### GET /auth/google/callback

| | |
|---|---|
| **Auth** | Public |
| **Rate limit** | None |

Handles the Google OAuth callback.

**Query parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| code | string | yes* | Authorization code from Google |
| state | string | yes* | CSRF state token |
| error | string | no | Error code if user denied consent |

\* Required unless `error` is present.

**Behavior:**
1. Validates `error` param — if present, clears `oauth_state` cookie and redirects to frontend with `success=false`
2. Validates presence of `code` and `state` — 400 if missing
3. Validates `state` against `oauth_state` cookie — 400 if mismatch or missing
4. Exchanges `code` for Google ID token (server-to-server)
5. Verifies ID token (`aud` = `GOOGLE_CLIENT_ID`)
6. Finds existing user by `google_sub` or email; creates new user if not found
7. If email matches existing email/password user, links accounts (sets `google_sub`, updates `auth_provider`)
8. Sets `access_token` and `refresh_token` cookies
9. Clears `oauth_state` cookie
10. Redirects (`302`) to frontend `/auth/callback?success=true`

**Error codes:** 400 (missing params, CSRF mismatch)

---

### POST /auth/refresh

| | |
|---|---|
| **Auth** | Refresh token cookie |
| **Rate limit** | None |

Refresh the access token using the `refresh_token` cookie.

**Behavior:**
1. Reads `refresh_token` from cookie
2. Looks up SHA-256 hash in `refresh_tokens` table
3. Validates token is not revoked and not expired
4. Uses optimistic locking (`updated_at`) to prevent concurrent reuse
5. Revokes the old token and creates a new one (rotation)
6. Opportunistically cleans up expired/revoked tokens older than 30 days
7. Sets new `access_token` and `refresh_token` cookies

**Response** `200 OK` — `AuthResponse`

**Error codes:** 401 (missing/invalid/expired/reused token)

---

### POST /auth/logout

| | |
|---|---|
| **Auth** | Authenticated (access_token cookie) |
| **Rate limit** | None |

Logout the current user.

**Behavior:**
- Reads `refresh_token` from cookie and revokes it (with optimistic locking)
- Clears `access_token` and `refresh_token` cookies (Max-Age = 0)

**Response:** `204 No Content`

---

### GET /auth/me

| | |
|---|---|
| **Auth** | Authenticated (access_token cookie) |
| **Rate limit** | None |

Return the current authenticated user's profile.

**Response** `200 OK` — `UserResponse`

| Field | Type | Description |
|-------|------|-------------|
| id | string (UUID) | User ID |
| org_id | string (UUID) | Organization ID |
| email | string | User email |
| name | string | User name |
| roles | list[string] | Active roles (e.g. `["student"]`) |
| auth_provider | string | `email` or `google` |
| google_sub | string\|null | Google subject ID (if linked) |
| created_at | datetime | Account creation time |
| updated_at | datetime | Last update time |

**Error codes:** 401 (not authenticated)

---

### GET /users

| | |
|---|---|
| **Auth** | `instructor` or `super-admin` |
| **Rate limit** | None |

List users in the current user's organization.

**Query parameters:**

| Param | Type | Default | Constraints |
|-------|------|---------|-------------|
| offset | int | 0 | >= 0 |
| limit | int | 50 | 1–100 |

**Response** `200 OK` — `UserListResponse`

| Field | Type | Description |
|-------|------|-------------|
| users | list[UserResponse] | User list |
| total | int | Total count |
| offset | int | Current offset |
| limit | int | Current limit |

**Error codes:** 401, 403

---

### POST /users/{user_id}/roles

| | |
|---|---|
| **Auth** | `super-admin` only |
| **Rate limit** | None |

Assign a role to a user. All existing refresh tokens for that user are revoked immediately so the new role takes effect on next login.

**Path parameters:**

| Param | Type | Description |
|-------|------|-------------|
| user_id | string (UUID) | Target user ID |

**Request body** (`RoleAssignmentRequest`)

| Field | Type | Constraints |
|-------|------|-------------|
| role | string | `student`, `instructor`, or `super-admin` |

**Response** `200 OK` — `UserResponse`

**Error codes:** 400 (invalid role), 401, 403, 404 (user not found)

---

### DELETE /users/{user_id}/roles/instructor

| | |
|---|---|
| **Auth** | `super-admin` only |
| **Rate limit** | None |

Remove the `instructor` role from a user. All existing refresh tokens for that user are revoked immediately.

**Path parameters:**

| Param | Type | Description |
|-------|------|-------------|
| user_id | string (UUID) | Target user ID |

**Response** `200 OK` — `UserResponse`

**Error codes:** 400 (user does not have role), 401, 403, 404 (user not found)

---

## Cookie Reference

| Cookie name | Purpose | TTL | Flags |
|-------------|---------|-----|-------|
| `access_token` | JWT access token | 15 min | httpOnly, Secure (prod), SameSite=Lax |
| `refresh_token` | JWT refresh token | 7 days | httpOnly, Secure (prod), SameSite=Lax |
| `oauth_state` | CSRF state for Google OAuth | 10 min | httpOnly, Secure (prod), SameSite=Lax |

---

## Rate Limits

| Endpoint | Limit | Scope |
|----------|-------|-------|
| `POST /auth/register` | 5/min | Per IP |
| `POST /auth/login` | 5/min | Per IP |
| All other endpoints | 100/min | Per IP (default) |
