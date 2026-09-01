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
- [Local Trial Setup and Recovery Guide](LOCAL_SETUP_GUIDE.md)
- [AWS EC2 Deployment Guide](deployment/AWS_EC2_GUIDE.md)

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

Frontend regression tests can also be run directly:

```bash
cd src/frontend
npm test
```

CI (`.github/workflows/ci.yml`) runs backend lint/tests (against Postgres), frontend
lint/tests/typecheck, and the frontend production build on every push/PR to main.

### Offline / local production (Phase M9)

To run the app in **production mode on a single machine or office LAN** (gunicorn + a
Next.js production build behind nginx, persistent volumes, automatic local backups) —
the retained Windows/local deployment used for manual testing — see the runbook in
[`deployment/README.md`](deployment/README.md). In short:

```powershell
# On the fresh Windows trial machine; private secrets are generated automatically:
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\setup-windows.ps1
```

This is separate from `make up` (the dev stack) and uses `config.settings.local_prod`.
The authoritative [local setup guide](LOCAL_SETUP_GUIDE.md) creates a fresh Windows
installation with no Mac testing data, installs a one-click Windows Desktop shortcut,
and configures database/uploaded-file backups every 12 hours with 120-day retention.

## Current Status

Phases M0–M7 are done: scaffolding; auth + role matrix, master data, products, and the
audit foundation; the stock ledger core with purchases and collection; purchase
refunds/cancellations; shipments + receiving (including the Dubai→Karachi transfer);
sales + stock adjustments; dashboard, reports, Excel/PDF exports, and admin stock
valuation; and hardening (attachments, theming/dark mode, responsive shell, demo seed).
The **M9 offline/local production stack** is implemented, and manual functional testing
passed on Windows. **M8 (AWS deployment) is now approved and its EC2 deployment path
is implemented in the repository:** a fresh Ubuntu 24.04 ARM64 `t4g.medium` in
`ap-south-1`, manually associated Elastic IP, trusted automatically renewed IP-address
TLS certificate, and the original role-aware application stack. Production starts with
new users and no Windows/Mac testing data. Backup pairs remain local to encrypted EBS
and are copied manually to the Mac for now; private S3 backup is the planned next
durability upgrade. The frontend is locked to the patched Next.js 15.5.24 release;
rerun the security/build gate documented in the runbook before public go-live. See
[`deployment/AWS_EC2_GUIDE.md`](deployment/AWS_EC2_GUIDE.md).
