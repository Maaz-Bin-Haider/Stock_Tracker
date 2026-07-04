COMPOSE = docker compose -f deployment/docker-compose.yml
VENV = .venv/bin

.PHONY: up down logs seed venv test lint typecheck

seed:
	$(COMPOSE) exec backend python manage.py seed

up:
	$(COMPOSE) up --build

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

venv:
	python3 -m venv .venv
	$(VENV)/pip install --upgrade pip
	$(VENV)/pip install -e "src/backend[dev]"

# Compose publishes Postgres on host port 5433 (5432 may be a native install).
test:
	POSTGRES_PORT=5433 $(VENV)/pytest

lint:
	$(VENV)/ruff check src/backend
	cd src/frontend && npm run lint

typecheck:
	cd src/frontend && npm run typecheck
