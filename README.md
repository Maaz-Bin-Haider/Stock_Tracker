# SwissTech Stock Tracker

Professional inventory management system project for SwissTech.

This repository contains the planning documents, original workbook reference, and project structure for building a web-based stock tracking system to replace the current spreadsheet workflow.

## Repository Structure

```text
.
├── data/
│   ├── source/          Original source files and workbook references
│   └── exports/         Generated exports during development/testing
├── deployment/          Deployment notes and infrastructure files
├── docs/
│   ├── architecture/    Use case, activity, sequence, class, and ER diagrams
│   ├── business-flow/   Non-technical workflow explanations
│   └── requirements/    Requirements, SRS, and system specification
├── scripts/             Utility scripts
├── src/                 Application source code
└── tests/               Automated tests
```

## Key Documents

- [Project Context](PROJECT_CONTEXT.md)
- [Requirements Context Log](docs/requirements/PROJECT_CONTEXT.md)
- [System Specification](docs/requirements/SYSTEM_SPEC.md)
- [Software Requirements Specification](docs/requirements/SRS.md)
- [Non-Technical Execution Flow](docs/business-flow/EXECUTION_FLOW_NON_TECHNICAL.md)
- [System Diagrams](docs/architecture/SYSTEM_DIAGRAMS.md)
- [Technical Architecture](docs/architecture/TECHNICAL_ARCHITECTURE.md)

Diagram PDF exports are stored in:

- `docs/architecture/diagrams/pdf/`

## Source Workbook

The original workbook reference is stored at:

- `data/source/stock_tracker_original.xlsx`

## Development

Django backend (`src/backend`), Next.js frontend (`src/frontend`), and a Docker Compose environment (`deployment/`).

Run the full stack (requires Docker):

```bash
make up        # docker compose up --build; app served at http://localhost:8080
make seed      # load demo master data + dev admin user (admin/admin123, DEBUG only)
make down      # stop the stack
make logs      # follow container logs
```

Compose publishes Postgres on host port **5433** (avoiding any natively installed Postgres on 5432); `make test` points pytest at it automatically.

nginx serves everything from one origin: `/` → Next.js, `/api` and `/admin` → Django, `/media` → dev uploads.

Backend development (host tooling):

```bash
make venv      # create .venv and install backend deps
make test      # pytest (tests live under tests/, mirroring src/)
make lint      # ruff (backend) + eslint (frontend)
make typecheck # tsc --noEmit (frontend)
```

CI (`.github/workflows/ci.yml`) runs lint, tests (against Postgres), typecheck, and the frontend build on every push/PR to main.

### Offline / local production (Phase M9)

To run the app in **production mode on a single machine or office LAN** (gunicorn + a
Next.js production build behind nginx, persistent volumes, automatic local backups) —
the trial deployment used before any AWS move — see the runbook in
[`deployment/README.md`](deployment/README.md). In short:

```bash
cp deployment/env.prod.example deployment/.env.prod   # then edit secrets + LAN IP
make prod-up            # build + start the production stack (detached)
make prod-seed          # master data only (no demo data)
make prod-superuser     # create the admin login
make backup             # on-demand DB backup -> data/backups/
```

This is separate from `make up` (the dev stack) and uses `config.settings.local_prod`.

## Current Status

Phases M0–M7 are done: scaffolding; auth + role matrix, master data, products, and the
audit foundation; the stock ledger core with purchases and collection; purchase
refunds/cancellations; shipments + receiving (including the Dubai→Karachi transfer);
sales + stock adjustments; dashboard, reports, Excel/PDF exports, and admin stock
valuation; and hardening (attachments, theming/dark mode, responsive shell, demo seed).
The **M9 offline/local production stack** is implemented (see above), pending a first run
on the target machine. **M8 (AWS deployment) is deferred** until after the offline trial
(see `docs/architecture/TECHNICAL_ARCHITECTURE.md` §15).
