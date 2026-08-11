COMPOSE = docker compose -f deployment/docker-compose.yml
# Offline/local production stack (Phase M9): prod compose + operator env file.
PROD_COMPOSE = docker compose -f deployment/docker-compose.prod.yml --env-file deployment/.env.prod
VENV = .venv/bin

.PHONY: up down logs seed venv test lint typecheck \
	prod-up prod-down prod-logs prod-seed prod-superuser local-open \
	desktop-launcher backup restore restore-media

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

# --- Offline / local production (Phase M9) ---
# Requires deployment/.env.prod (copy from deployment/env.prod.example first).

prod-up:
	$(PROD_COMPOSE) up -d --build

prod-down:
	$(PROD_COMPOSE) down

prod-logs:
	$(PROD_COMPOSE) logs -f

# Master data only — never --demo in production.
prod-seed:
	$(PROD_COMPOSE) exec backend python manage.py seed

# Creates an ADMIN-role superuser (plain createsuperuser leaves role=VIEWER,
# which is read-only in the app). Prompts for username/password.
prod-superuser:
	$(PROD_COMPOSE) exec backend python manage.py create_admin

# Start the local production stack if needed and open it in the browser (macOS).
local-open:
	scripts/open-stock-tracker.command

# One-time installer: add a clickable launcher to the current user's Desktop (macOS).
desktop-launcher:
	scripts/install-desktop-launcher.sh

backup:
	scripts/backup.sh

# Usage: make restore FILE=data/backups/stock_tracker-YYYYmmdd-HHMMSS.sql.gz
restore:
	scripts/restore.sh $(FILE)

# Usage: make restore-media FILE=data/backups/stock_tracker-media-YYYYmmdd-HHMMSS.tar.gz
restore-media:
	scripts/restore-media.sh $(FILE)
