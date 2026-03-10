#!/bin/bash
set -e

echo "Running database migrations..."
python -m src.db.run_migrations

echo "Starting TheStudio..."
exec uvicorn src.app:app \
  --host 0.0.0.0 \
  --port 8000 \
  --log-level info \
  --timeout-graceful-shutdown 30
