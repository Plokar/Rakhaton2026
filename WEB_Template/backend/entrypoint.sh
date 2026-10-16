#!/bin/bash
# =============================================================================
# Backend Entrypoint – Hackathon Web Template
# Supports: development (Django dev server) & production (Daphne ASGI)
# =============================================================================
set -e

echo "============================================"
echo "  Hackathon Backend Starting..."
echo "  Settings: ${DJANGO_SETTINGS_MODULE}"
echo "  Debug: ${DJANGO_DEBUG}"
echo "============================================"

# ── Wait for PostgreSQL ───────────────────────────────────────────────────────
echo "⏳ Waiting for PostgreSQL at ${POSTGRES_HOST}:${POSTGRES_PORT}..."
max_retries=30
retry=0
until nc -z "${POSTGRES_HOST:-db}" "${POSTGRES_PORT:-5432}"; do
  retry=$((retry + 1))
  if [ $retry -ge $max_retries ]; then
    echo "❌ PostgreSQL not available after ${max_retries} retries. Exiting."
    exit 1
  fi
  echo "   PostgreSQL not ready (attempt ${retry}/${max_retries}), waiting..."
  sleep 2
done
echo "✅ PostgreSQL ready"

# ── Wait for Redis ────────────────────────────────────────────────────────────
REDIS_HOST=$(echo "${REDIS_URL:-redis://redis:6379}" | sed 's|redis://[^@]*@\([^:]*\).*|\1|' | sed 's|redis://\([^:]*\).*|\1|')
echo "⏳ Waiting for Redis at ${REDIS_HOST}:6379..."
retry=0
until nc -z "${REDIS_HOST:-redis}" 6379; do
  retry=$((retry + 1))
  if [ $retry -ge $max_retries ]; then
    echo "⚠️  Redis not available, continuing without Redis..."
    break
  fi
  sleep 1
done
echo "✅ Redis ready (or skipped)"

# ── Database migrations ───────────────────────────────────────────────────────
echo "🔄 Running database migrations..."
python manage.py migrate --noinput
echo "✅ Migrations complete"

# ── Static files (only in production) ────────────────────────────────────────
if [ "${DJANGO_DEBUG}" != "True" ]; then
  echo "📁 Collecting static files..."
  python manage.py collectstatic --noinput --clear
  echo "✅ Static files collected"
fi

# ── Create superuser (only in dev if env vars set) ───────────────────────────
if [ "${DJANGO_DEBUG}" = "True" ] && [ -n "${DJANGO_SUPERUSER_USERNAME}" ]; then
  echo "👤 Creating superuser '${DJANGO_SUPERUSER_USERNAME}'..."
  python manage.py createsuperuser \
    --noinput \
    --username "${DJANGO_SUPERUSER_USERNAME}" \
    --email "${DJANGO_SUPERUSER_EMAIL:-admin@hackathon.local}" 2>/dev/null || \
    echo "   (superuser already exists, skipping)"
fi

# ── Seed Demo Data (dev only) ───────────────────────────────────────────────
if [ "${DJANGO_DEBUG}" = "True" ]; then
  echo "🌱 Seeding demo data for Hackathon OS..."
  python manage.py seed_demo_data || echo "   (seed data skipped or already present)"
fi


# ── Start Server ──────────────────────────────────────────────────────────────
if [ $# -gt 0 ]; then
  echo ""
  echo "🚀 Executing command: $@"
  echo ""
  exec "$@"
elif [ "${DJANGO_DEBUG}" = "True" ]; then
  echo ""
  echo "🚀 Starting Daphne ASGI development server..."
  echo "   API:        http://0.0.0.0:8000/api/"
  echo "   Swagger UI: http://0.0.0.0:8000/api/docs/"
  echo "   WebSocket:  ws://0.0.0.0:8000/ws/"
  echo "   Admin:      http://0.0.0.0:8000/admin/"
  echo ""
  exec daphne -b 0.0.0.0 -p 8000 \
    --verbosity 2 \
    config.asgi:application
else
  echo ""
  echo "🚀 Starting Daphne ASGI production server..."
  echo "   Workers:    ${DAPHNE_WORKERS:-4}"
  echo ""
  exec daphne -b 0.0.0.0 -p 8000 \
    --verbosity 1 \
    --access-log - \
    --proxy-headers \
    config.asgi:application
fi
