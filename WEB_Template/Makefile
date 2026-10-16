.PHONY: help dev up down restart seed reset logs test build

COMPOSE_DEV = docker compose -f docker-compose.dev.yml

help: ## Zobrazí nápovědu pro dostupné příkazy
	@echo "=========================================================="
	@echo "  Hackathon OS – Rychlé příkazy"
	@echo "=========================================================="
	@echo "  make dev      - Spustí kompletní stack v dev módu s logy"
	@echo "  make up       - Spustí stack na pozadí (-d)"
	@echo "  make down     - Zastaví všechny běžící kontejnery"
	@echo "  make restart  - Restartuje kontejnery"
	@echo "  make seed     - Naplní databázi ukázkovými demo daty"
	@echo "  make reset    - Kompletní reset DB + nové migrace + seed"
	@echo "  make logs     - Zobrazí živý výpis logů ze všech služeb"
	@echo "  make test     - Spustí backendové testy (pytest)"
	@echo "  make build    - Přestaví Docker obrazy bez cache"
	@echo "=========================================================="

dev: ## Spustí kompletní dev stack
	@if [ ! -f .env ]; then cp .env.dev.example .env; echo "Vytvořen .env"; fi
	$(COMPOSE_DEV) up --build

up: ## Spustí dev stack na pozadí
	@if [ ! -f .env ]; then cp .env.dev.example .env; echo "Vytvořen .env"; fi
	$(COMPOSE_DEV) up --build -d
	@echo "✅ Služby běží na pozadí:"
	@echo "   Frontend: http://localhost:3000"
	@echo "   Backend:  http://localhost:8000/api/"
	@echo "   Mailhog:  http://localhost:8025"

down: ## Zastaví dev stack
	$(COMPOSE_DEV) down

restart: down up ## Restartuje stack

seed: ## Naplní DB ukázkovými daty (admin, alice, projekty, úkoly)
	$(COMPOSE_DEV) exec backend python manage.py seed_demo_data

reset: ## Resetuje DB volume, provede migrace a naseeduje demo data
	$(COMPOSE_DEV) down -v
	$(COMPOSE_DEV) up --build -d
	@echo "⏳ Čekám na start databáze..."
	@sleep 5
	$(COMPOSE_DEV) exec backend python manage.py migrate
	$(COMPOSE_DEV) exec backend python manage.py seed_demo_data
	@echo "✅ Databáze resetována a naseedována!"

logs: ## Sleduje logy
	$(COMPOSE_DEV) logs -f

test: ## Spustí backend testy
	$(COMPOSE_DEV) exec backend pytest

build: ## Přestaví kontejnery bez cache
	$(COMPOSE_DEV) build --no-cache
