#!/bin/sh
set -e

echo "[entrypoint] Running database migrations..."
python manage.py migrate --noinput

echo "[entrypoint] Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "[entrypoint] Seeding initial admin account..."
python manage.py seed_admin

echo "[entrypoint] Starting gunicorn..."
exec gunicorn scd_reporting.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --worker-tmp-dir /dev/shm \
    --log-level "${GUNICORN_LOG_LEVEL:-info}" \
    --access-logfile -
