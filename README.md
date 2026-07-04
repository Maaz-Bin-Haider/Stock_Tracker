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

Phase M0 scaffolding is in place: Django backend (`src/backend`), Next.js frontend (`src/frontend`), and a Docker Compose environment (`deployment/`).

Run the full stack (requires Docker):

```bash
make up        # docker compose up --build; app served at http://localhost:8080
make down      # stop the stack
make logs      # follow container logs
```

nginx serves everything from one origin: `/` → Next.js, `/api` and `/admin` → Django, `/media` → dev uploads.

Backend development (host tooling):

```bash
make venv      # create .venv and install backend deps
make test      # pytest (tests live under tests/, mirroring src/)
make lint      # ruff (backend) + eslint (frontend)
make typecheck # tsc --noEmit (frontend)
```

CI (`.github/workflows/ci.yml`) runs lint, tests (against Postgres), typecheck, and the frontend build on every push/PR to main.

## Current Status

Requirements and planning documents are complete; phase M0 (repo scaffolding) is done. Next phase is M1: accounts, master data, products, and the audit foundation (see `docs/architecture/TECHNICAL_ARCHITECTURE.md` §15).
