#!/usr/bin/env bash
set -e

echo "Starting DailyPlanner on port: $PORT"
echo "Environment: ${FLASK_ENV:-production}"

exec gunicorn "app:create_app()" \
  --bind "0.0.0.0:$PORT" \
  --workers "${GUNICORN_WORKERS:-2}" \
  --threads "${GUNICORN_THREADS:-2}" \
  --timeout 120 \
  --graceful-timeout 30 \
  --keep-alive 5 \
  --access-logfile - \
  --error-logfile - \
  --log-level "${LOG_LEVEL:-info}"
