# Dojo Manager Backend

Aikido Dojo Management System — Backend API built with FastAPI.

## Setup

### Prerequisites

- Python 3.13+
- MySQL 8.4+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Installation

```bash
cd backend
uv sync
```

### Environment Variables

Copy `.env.example` to `.env` and fill in the values:

```bash
cp .env.example .env
```

Key environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | MySQL connection string | `mysql+aiomysql://root:@localhost:3306/dojo` |
| `JWT_SECRET` | Secret key for JWT signing | Change in production! |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Access token expiry | `15` |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token expiry | `7` |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | Required for OAuth |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret | Required for OAuth |
| `GOOGLE_REDIRECT_URI` | Google OAuth redirect URI | `http://localhost:8000/api/v1/auth/google/callback` |
| `ALLOWED_ORIGINS` | CORS allowed origins (comma-separated) | `http://localhost:5173,http://localhost:80` |
| `RATE_LIMIT_DEFAULT` | Default rate limit | `100/minute` |
| `RATE_LIMIT_AUTH` | Auth endpoints rate limit | `5/minute` |
| `APP_ENV` | Environment | `development` |
| `API_PREFIX` | API route prefix | `/api/v1` |

### Database Migrations

```bash
# Run all migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Create a new migration
alembic revision --autogenerate -m "description"

# Check current migration state
alembic current
```

### Running the Server

```bash
# Development
uvicorn app.main:app --reload --port 8000

# Or with uv
uv run uvicorn app.main:app --reload --port 8000
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_auth.py -v

# Run with coverage
pytest tests/ -v --cov=app
```

**Note:** Tests require a running MySQL instance. Set `DATABASE_URL` in your test environment or `.env` file.

## API Endpoints

### Auth

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/auth/register` | Public | Register new user |
| POST | `/api/v1/auth/login` | Public | Login with email/password |
| GET | `/api/v1/auth/google` | Public | Initiate Google OAuth |
| GET | `/api/v1/auth/google/callback` | Public | Google OAuth callback |
| POST | `/api/v1/auth/refresh` | Refresh cookie | Refresh access token |
| POST | `/api/v1/auth/logout` | Authenticated | Logout |
| GET | `/api/v1/auth/me` | Authenticated | Get current user |

### Users

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/users` | instructor+ | List users |
| POST | `/api/v1/users/{id}/roles` | super-admin | Assign role |
| DELETE | `/api/v1/users/{id}/roles/instructor` | super-admin | Remove instructor role |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check (root) |
| GET | `/api/v1/health` | Health check (API v1) |

## Architecture

```
app/
├── api/                    # API routes (interface layer)
│   ├── dependencies/       # FastAPI dependencies (auth, db)
│   └── routes/            # Endpoint handlers
├── core/                  # Core logic (security, exceptions, middleware)
├── domain/                # Domain models and exceptions
│   └── models/           # SQLAlchemy ORM models
├── repositories/          # Data access layer
├── schemas/               # Pydantic request/response schemas
└── services/              # Business logic (use cases)
```

## Authentication

- **Tokens:** JWT (HS256) stored in httpOnly cookies
- **Access token:** 15 minutes, used for API authentication
- **Refresh token:** 7 days, stored as SHA-256 hash in database
- **Token rotation:** New refresh token issued on each refresh, old one revoked
- **Multi-device:** Supported (one refresh token row per device)

## Google OAuth Setup

See [docs/google-oauth-setup.md](../docs/google-oauth-setup.md) for detailed setup instructions.