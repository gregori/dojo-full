# Domain Models

This document describes the core domain models introduced in PR-1-auth.

---

## Org

Represents a tenant/organization for multi-org data isolation.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID (string) | PK, default=gen | Organization identifier |
| name | string(255) | NOT NULL | Organization name |
| created_at | datetime | NOT NULL, server_default=now() | Creation timestamp |
| updated_at | datetime | NOT NULL, server_default=now(), onupdate=now() | Last update timestamp |

**Table:** `orgs`

**Seed data:**
- ID: `00000000-0000-0000-0000-000000000001`
- Name: `"Default Dojo"`
- Seeded via Alembic data migration (idempotent `INSERT IGNORE`)

**Relationships:**
- One `Org` → Many `User` (`users.org_id` FK with `ON DELETE CASCADE`)

---

## User

Represents an authenticated user. In the MVP, instructors and students are the same entity with different roles.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID (string) | PK, default=gen | User identifier |
| org_id | UUID (string) | FK → orgs.id, NOT NULL, ON DELETE CASCADE | Organization membership |
| email | string(255) | NOT NULL, UNIQUE | Login email |
| password_hash | string(255)\|null | NULLABLE | bcrypt hash (NULL for Google-only users) |
| name | string(255) | NOT NULL | Display name |
| roles | JSON | NOT NULL, default=`[]` | Array of role strings |
| auth_provider | string(50) | NOT NULL, default=`"email"` | `email` or `google` |
| google_sub | string(255)\|null | NULLABLE, UNIQUE | Google subject identifier |
| created_at | datetime | NOT NULL, server_default=now() | Creation timestamp |
| updated_at | datetime | NOT NULL, server_default=now(), onupdate=now() | Last update timestamp |

**Table:** `users`

**Indexes:**
- Unique on `email`
- Unique on `google_sub` (MySQL allows multiple NULLs)

**Role helpers:**

```python
def has_role(self, role: str) -> bool
# Check if "instructor" in self.roles

def add_role(self, role: str) -> None
# Append role if not present (immutable list update)

def remove_role(self, role: str) -> None
# Filter out role from list
```

**Valid roles:** `student`, `instructor`, `super-admin`

**Relationships:**
- Many `User` → One `Org`
- One `User` → Many `RefreshToken`

---

## RefreshToken

Stores SHA-256 hashed refresh tokens for JWT rotation and multi-device support.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID (string) | PK, default=gen | Token identifier |
| user_id | UUID (string) | FK → users.id, NOT NULL, ON DELETE CASCADE | Owner |
| token_hash | string(255) | NOT NULL, UNIQUE | SHA-256 hex digest of raw token |
| expires_at | datetime | NOT NULL | Token expiry (7 days from creation) |
| created_at | datetime | NOT NULL, server_default=now() | Creation timestamp |
| revoked | bool | NOT NULL, default=False | Revocation flag |
| updated_at | datetime | NOT NULL, server_default=now(), onupdate=now() | Used for optimistic locking |

**Table:** `refresh_tokens`

**Indexes:**
- Unique on `token_hash`
- Index on `(user_id, revoked)` for revocation queries

**Security properties:**
- Raw tokens are **never** stored in the database
- SHA-256 provides deterministic lookup without exposing the token
- Optimistic locking on `updated_at` prevents concurrent replay attacks
- Opportunistic cleanup deletes revoked/expired tokens older than 30 days

**Lifecycle:**
1. Created on login / register / refresh
2. Used once during refresh (then revoked)
3. Revoked on logout
4. Revoked on role change (`revoke_all_for_user`)
5. Deleted by `cleanup_expired()` after 30 days past expiry/revocation

---

## Entity Relationship Diagram

```
+------------+         +------------------+         +------------------+
|    Org     | 1     * |      User        | 1     * |  RefreshToken    |
+------------+---------+------------------+---------+------------------+
| id (PK)    |         | id (PK)          |         | id (PK)          |
| name       |         | org_id (FK)      |         | user_id (FK)     |
| created_at |         | email (UQ)       |         | token_hash (UQ)  |
| updated_at |         | password_hash    |         | expires_at       |
+------------+         | name             |         | revoked          |
                       | roles (JSON)     |         | created_at       |
                       | auth_provider    |         | updated_at       |
                       | google_sub (UQ)  |         +------------------+
                       | created_at       |
                       | updated_at       |
                       +------------------+
```

---

## Multi-Org Isolation

All queries that return user data are scoped to the current user's `org_id` extracted from the JWT payload. In the MVP:
- The UI is single-org (no org switching)
- `org_id` is hardcoded to the default org for all new registrations
- Future epics will add org management UI
