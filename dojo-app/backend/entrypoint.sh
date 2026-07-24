#!/bin/bash
set -e

echo "Dojo Admin - Backend Entrypoint"
echo "================================"

# Wait for database
echo "Waiting for database..."
until python -c "
import sys
sys.path.append('.')
from app.core.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    conn.execute(text('SELECT 1'))
print('Database is ready!')
" 2>/dev/null; do
  echo "Database not ready yet. Retrying in 2s..."
  sleep 2
done

# Run migrations
echo "Running database migrations..."
alembic upgrade head

# Seed database if needed
echo "Checking if seed is needed..."
python scripts/seed_database.py

# Start application
echo "Starting FastAPI application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
