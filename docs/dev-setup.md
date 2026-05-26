# Local Development Setup

This guide covers setting up the Dojo Manager project for local development.

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.13+ | Backend runtime |
| Node.js | 22+ | Frontend runtime |
| Docker + Docker Compose | Latest | Local services (MySQL) |
| uv | Latest | Python package manager (recommended) |
| npm | Bundled with Node | Frontend package manager |

---

## 1. Clone and Setup

```bash
git clone <repo-url>
cd dojo-full
```

---

## 2. Backend Setup

```bash
cd backend

# Install dependencies (using uv)
uv sync

# Or with pip
pip install -e ".[dev]"
```

### Environment variables

Copy the example file and edit as needed:

```bash
cp .env.example .env
```

Key variables in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `mysql+aiomysql://root:@localhost:3306/dojo` | MySQL connection string |
| `JWT_SECRET` | `dev-secret-change-me-in-production` | JWT signing secret (min 32 chars) |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access token TTL |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token TTL |
| `GOOGLE_CLIENT_ID` | `your-client-id-here` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | `your-client-secret-here` | Google OAuth client secret |
| `GOOGLE_REDIRECT_URI` | `http://localhost:8000/api/v1/auth/google/callback` | OAuth callback URL |
| `ALLOWED_ORIGINS` | `http://localhost:5173,http://localhost:80` | CORS origins |

> **Security note:** `JWT_SECRET` must be at least 32 characters. The app crashes at startup with a clear error if the secret is insecure or a placeholder.

---

## 3. Frontend Setup

```bash
cd frontend
npm install
```

### Environment variables

Copy the example file:

```bash
cp .env.example .env
```

Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE` | `""` | Empty for dev (uses Vite proxy to `/api/v1`) |

> In development, the frontend uses relative paths (`/api/v1/...`) and the Vite dev server proxies `/api` to `localhost:8000`.

---

## 4. Docker Compose

Start all services (MySQL, backend, frontend) with a single command:

```bash
# From project root
docker-compose up --build
```

Services:

| Service | URL | Description |
|---------|-----|-------------|
| MySQL | `localhost:3306` | Database with healthcheck |
| Backend | `http://localhost:8000` | FastAPI API + auto-generated docs at `/docs` |
| Frontend | `http://localhost:80` | Nginx serving built SPA |

The backend container mounts `./backend` for hot-reload during development.

### Running MySQL only

```bash
docker-compose up mysql
```

Then run the backend locally:

```bash
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 5. Database Migrations

Migrations are run automatically via an initContainer in Kubernetes. For local development:

```bash
cd backend

# Run all pending migrations
uv run alembic upgrade head

# Create a new migration
uv run alembic revision --autogenerate -m "description"

# Downgrade one step
uv run alembic downgrade -1
```

Migrations included in PR-1-auth:

| File | Description |
|------|-------------|
| `001_create_orgs_table.py` | Creates `orgs` table + seeds default org |
| `002_create_users_and_refresh_tokens.py` | Creates `users` and `refresh_tokens` tables |

---

## 6. Google OAuth Setup

See [`docs/google-oauth-setup.md`](./google-oauth-setup.md) for detailed instructions.

Quick checklist:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create an OAuth 2.0 Client ID (Web application)
3. Add authorized redirect URI: `http://localhost:8000/api/v1/auth/google/callback`
4. Copy **Client ID** and **Client Secret** into `backend/.env`
5. Add test users if the app is in testing mode

---

## 7. Running Tests

### Backend

```bash
cd backend

# Unit tests (no DB required)
uv run pytest tests/test_security.py -v

# Integration tests (requires MySQL)
uv run pytest tests/test_auth.py tests/test_users.py tests/test_rbac.py -v

# All tests
uv run pytest tests/ -v
```

Test files:

| File | Coverage |
|------|----------|
| `test_security.py` | Password hashing, JWT creation/verification, token hashing |
| `test_auth.py` | Register, login, refresh, logout endpoints |
| `test_users.py` | List users, assign/remove roles |
| `test_rbac.py` | Role-based access control (401/403) |

### Frontend

```bash
cd frontend
npm test
```

> Frontend tests are configured (Jest + React Testing Library) but not yet implemented.

---

## 8. Linting and Formatting

### Backend (Ruff)

```bash
cd backend

# Check
uv run ruff check .

# Auto-fix
uv run ruff check --fix .

# Format
uv run ruff format .
```

### Frontend (ESLint + Prettier)

```bash
cd frontend

# Lint
npm run lint

# Format
npx prettier --write src/
```

---

## 9. API Documentation

FastAPI auto-generates interactive documentation:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

The docs include all auth endpoints with request/response schemas and cookie-based authentication support.

---

## 10. Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `Access denied for user 'root'@'...'` | MySQL not running or wrong credentials | Check `docker-compose up mysql` and `DATABASE_URL` |
| `JWT_SECRET must be at least 32 characters` | Insecure JWT secret set | Use `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| CORS errors in browser | `ALLOWED_ORIGINS` mismatch | Ensure frontend origin is in the list |
| Google OAuth redirect fails | Wrong `GOOGLE_REDIRECT_URI` | Must match exactly in Google Console |
| `Module 'bcrypt' has no attribute '__about__'` | bcrypt 5.x incompatible with passlib | Already pinned to `bcrypt==4.2.1` in pyproject.toml |
