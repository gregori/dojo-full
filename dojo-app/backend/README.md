# Dojo Admin - Backend

FastAPI backend for Dojo Admin - Aikido Dojo Management System.

## Features

- **Multi-tenant Architecture**: Supports multiple organizations and dojos
- **JWT Authentication**: Secure login with role-based access control
- **Student Management**: CRUD operations with automatic registration number generation
- **Event Management**: Dynamic event types (classes, cleaning, exams, etc.)
- **Check-in System**: Tablet and QR Code check-in with PIN validation
- **Belt Progress Tracking**: Automatic calculation of attendance requirements
- **Exam Management**: Complete exam workflow with board members, candidates, and ukes
- **Data Import**: Excel/CSV import for existing student databases
- **Comprehensive Testing**: Unit tests, integration tests, and BDD functional tests

## Quick Start

### Prerequisites

- Python 3.13+
- Poetry
- MySQL 8.0 (or Docker for local development)

### Installation

```bash
cd backend
poetry install
```

### Configuration

```bash
cp .env.example .env
# Edit .env with your database credentials
```

### Run Development Server

```bash
poetry run uvicorn app.main:app --reload
```

API docs available at: http://localhost:8000/docs

### Run Tests

```bash
# Unit and integration tests
poetry run pytest

# BDD functional tests
poetry run behave tests/bdd/features

# With coverage
poetry run pytest --cov=app --cov-report=html
```

## Database Migrations

```bash
# Create migration
poetry run alembic revision --autogenerate -m "description"

# Apply migrations
poetry run alembic upgrade head

# Rollback
poetry run alembic downgrade -1
```

## Data Import

Import existing students from Excel or CSV:

```bash
# Create default belts first
poetry run python scripts/import_students.py students.xlsx --create-belts

# Import with specific organization/dojo
poetry run python scripts/import_students.py students.csv --org-id <id> --dojo-id <id>
```

Expected columns:
- `Nome` (required)
- `Email` (optional)
- `Telefone` (optional)
- `Data_Nascimento` (optional, format: DD/MM/YYYY)
- `Categoria` (optional: 'adult' or 'child')
- `Faixa` (optional)
- `PIN` (optional, default: 1234)

## Project Structure

```
backend/
├── app/
│   ├── api/              # API routes (FastAPI routers)
│   ├── core/             # Config, database, security
│   ├── dependencies/     # Auth dependencies
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas
│   └── services/         # Business logic
├── tests/
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── bdd/              # Functional/BDD tests
├── alembic/              # Database migrations
├── scripts/              # Utility scripts
└── pyproject.toml        # Poetry configuration
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/login` - Login with email/password

### Users (Admin only)
- `GET /api/v1/users` - List users
- `POST /api/v1/users` - Create user
- `PUT /api/v1/users/{id}` - Update user
- `DELETE /api/v1/users/{id}` - Deactivate user

### Students
- `GET /api/v1/students` - List students
- `POST /api/v1/students` - Create student (Admin)
- `PUT /api/v1/students/{id}` - Update student (Admin)
- `GET /api/v1/students/{id}/progress` - Get belt progress

### Events
- `GET /api/v1/events` - List events
- `POST /api/v1/events` - Create event
- `GET /api/v1/events/types` - List event types

### Check-in
- `POST /api/v1/checkin/tablet/{event_id}` - Tablet check-in
- `POST /api/v1/checkin/qr` - QR Code check-in
- `POST /api/v1/checkin/manual` - Manual check-in

### Exams
- `GET /api/v1/exams` - List exams
- `POST /api/v1/exams` - Create exam
- `POST /api/v1/exams/{id}/participants` - Add participant
- `PUT /api/v1/exams/participants/{id}` - Update participant status

## Security

- Passwords hashed with bcrypt
- JWT tokens with 7-day expiration
- Role-based access control (Admin, Instructor)
- PIN validation for student check-in
- Rate limiting on check-in endpoints (recommended for production)

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | MySQL connection string | `mysql+pymysql://dojo_user:dojo_pass@localhost:3306/dojo_db` |
| `SECRET_KEY` | JWT secret key | `your-super-secret-key` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiration | `10080` (7 days) |
| `DEBUG` | Debug mode | `false` |

## Testing Strategy

### Pyramid
- **Unit Tests**: Business logic, validations (pytest)
- **Integration Tests**: API endpoints with test database (pytest + TestClient)
- **Functional Tests**: BDD scenarios validating acceptance criteria (Behave)
- **E2E Tests**: Frontend flows (Cypress)

### Coverage Target
- Backend: >80% unit test coverage
- All acceptance criteria validated by BDD tests

## License

MIT
