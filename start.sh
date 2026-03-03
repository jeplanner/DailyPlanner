#!/usr/bin/env bash
echo "Starting on port: $PORT"
exec gunicorn "app:create_app()" --bind 0.0.0.0:$PORT --workers 1 --threads 1 --timeout 120 --log-level debug