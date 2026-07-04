COMPOSE = docker compose -f deployment/docker-compose.yml
VENV = .venv/bin

.PHONY: up down logs venv test lint typecheck

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

test:
	$(VENV)/pytest

lint:
	$(VENV)/ruff check src/backend
	cd src/frontend && npm run lint

typecheck:
	cd src/frontend && npm run typecheck
