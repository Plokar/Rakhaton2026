#!/bin/bash
# =============================================================================
# Hackathon OS – Developer Automation Script
# Usage: ./dev.sh [up|down|seed|reset|build|logs|test]
# =============================================================================
set -e

COMPOSE_FILE="docker-compose.dev.yml"
CMD="${1:-up}"

case "$CMD" in
  up)
    echo "🚀 Spouštím Hackathon OS v dev módu (hot-reload)..."
    if [ ! -f ".env" ]; then
      echo "⚠️  .env nenalezen, kopíruji z .env.dev.example..."
      cp .env.dev.example .env
    fi
    docker compose -f $COMPOSE_FILE up --build -d
    echo ""
    echo "✅ Služby nastartovány:"
    echo "   Frontend:          http://localhost:3000"
    echo "   Swagger UI:        http://localhost:8000/api/docs/"
    echo "   Backend API:       http://localhost:8000/api/"
    echo "   Django Admin:      http://localhost:8000/admin/ (admin / admin123456)"
    echo "   Mailhog:           http://localhost:8025"
    echo "   Traefik Dashboard: http://localhost:8080"
    ;;

  down)
    echo "🛑 Zastavuji kontejnery..."
    docker compose -f $COMPOSE_FILE down
    echo "✅ Vše zastaveno."
    ;;

  seed)
    echo "🌱 Spouštím seedování demo dat v backendu..."
    docker compose -f $COMPOSE_FILE exec backend python manage.py seed_demo_data
    ;;

  reset)
    echo "⚠️  Resetuji databázi a provádím nové migrace..."
    docker compose -f $COMPOSE_FILE down -v
    docker compose -f $COMPOSE_FILE up --build -d
    sleep 5
    docker compose -f $COMPOSE_FILE exec backend python manage.py migrate
    docker compose -f $COMPOSE_FILE exec backend python manage.py seed_demo_data
    echo "✅ Databáze resetována a naplněna."
    ;;

  build)
    echo "🔨 Přestavuji kontejnery..."
    docker compose -f $COMPOSE_FILE build --no-cache
    ;;

  logs)
    docker compose -f $COMPOSE_FILE logs -f
    ;;

  test)
    echo "🧪 Spouštím testy..."
    docker compose -f $COMPOSE_FILE exec backend pytest
    ;;

  *)
    echo "Použití: $0 {up|down|seed|reset|build|logs|test}"
    exit 1
    ;;
esac
