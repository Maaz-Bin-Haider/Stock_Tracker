# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project State

The SwissTech Stock Tracker is a web-based inventory system replacing a spreadsheet workflow (`data/source/stock_tracker_original.xlsx`). Django backend under `src/backend` (11 apps under `apps/`, settings split in `config/settings/`), Next.js frontend under `src/frontend`, Docker Compose + nginx under `deployment/`. Phases M0–M5 are done: auth + role matrix (`apps/accounts/permissions.py`), audited master-data/product CRUD (`apps/core/viewsets.py`), audit foundation (`apps/audits/`), the inventory core — append-only ledger + materialized `stock_balances` with `post_event` in `apps/inventory/services.py` as the only ledger writer (`rebuild_stock_balances` is the drift check) — the full purchase lifecycle in `apps/purchases/services.py` (entry, collection, refunds/cancellations; reversal values frozen at the original line rate), shipments + receiving in `apps/shipments/services.py` (draft → ship → partial/over-receive → cancel/delete; Dubai→Karachi as a shipment type; value moves at the source's carrying average from `stock_balances` via proportional remainders; `over_received` is computed and IN_TRANSIT may go negative per §5.2), M5: sales in `apps/sales/services.py` (sales locations only, reference-only price, carrying-average value removal via a running `CarryingPool`, location locked after entry) + stock adjustments in `apps/inventory/adjustments.py` (INCREASE at carrying average / DECREASE proportional, mandatory reason, admin-only), and M6: dashboard + reports + exports in `apps/reports/` — a single report registry (`builders.py`) where every SRS §5 report is a `Report` (declared filters + build function) consumed identically by the JSON views and both export renderers (FR-098); dashboard live cards from `stock_balances` with `?cutoff=` ledger snapshots; GST/money figures always from purchase/refund-line frozen values, never ledger `gst_value` sums; admin-only valuation summary/detail enforced server-side; Celery `ExportJob` pipeline rendering openpyxl Excel and ReportLab PDF (ReportLab, not WeasyPrint — no system libraries) into private `EXPORTS_ROOT` outside `MEDIA_ROOT`, downloadable only via the authenticated endpoint. All stock writes and audits go through the domain services, never through viewsets directly. M7 (hardening) is also done: file attachments in `apps/attachments/` (purchases/sales only, magic-byte content sniffing, module-scoped write roles, audited, authenticated download; Upload/File report key `uploads`), theming via semantic tokens in `src/frontend/app/globals.css` (Tailwind v4 `@theme inline`; separately designed dark palette swapped by `.dark` on `<html>`; preference on `User.theme` + localStorage with a no-flash boot script — components must use token classes like `bg-surface`/`text-muted`, never raw Tailwind palette classes), responsive drawer shell, shared pagination component, exports-history panel, and `manage.py seed --demo` (demo business history through the services, idempotent). SRS §12 acceptance criteria verified locally. Plan change (2026-07-23): AWS deployment is postponed — the client will run the system offline/locally first, then deploy to AWS only if satisfied. So the immediate next phase is **M9 (offline/local production use: gunicorn + Next build, persistent local volumes, LAN access, scheduled local `pg_dump` backup + restore, restart-on-reboot, operator make targets)**, and **M8 (AWS deployment: EC2 + S3 + cloud backups) is deferred to future** — undertaken only after a successful offline trial. Phases are tracked in `TECHNICAL_ARCHITECTURE.md` §15. Dev login after `make seed`: admin/admin123 (DEBUG only). Tests run against Dockerized Postgres on host port 5433 (`make test`; pytest uses `config.settings.test` — eager Celery, temp exports/media dirs).

Commands (root `Makefile`): `make up` (full stack via Docker at `http://localhost:8080`), `make venv` (host venv for backend tooling), `make test` (pytest; config in root `pytest.ini`, tests under `tests/` mirroring `src/`), `make lint` (ruff + eslint), `make typecheck` (tsc).

Decided tech stack (see `docs/requirements/SYSTEM_SPEC.md` §23): Django + Django REST Framework, PostgreSQL, Next.js/TypeScript frontend with Tailwind CSS (shadcn/ui or Radix UI), Celery + Redis for background jobs, Docker Compose locally. File uploads use local Django media in development and S3-compatible storage in deployment (DB stores metadata/paths only, never file contents). Target deployment is a single EC2 instance on AWS after local testing.

## Document Map

Read in this order of authority when documents seem to conflict:

- `docs/requirements/SRS.md` — formal requirements (FR-001 … FR-114), acceptance criteria, out-of-scope list
- `docs/requirements/SYSTEM_SPEC.md` — implementation-oriented spec: permission matrix, field lists, report columns, suggested DB tables, implementation notes
- `docs/architecture/TECHNICAL_ARCHITECTURE.md` — how it gets built: monorepo layout, Django app breakdown, ledger posting design (`post_event` service, event→ledger mapping table), API/auth, frontend structure, implementation phases M0–M8
- `docs/architecture/SYSTEM_DIAGRAMS.md` — Mermaid source for use case, activity, sequence, class, and ER diagrams (PDF exports in `docs/architecture/diagrams/pdf/`)
- `docs/business-flow/EXECUTION_FLOW_NON_TECHNICAL.md` — end-to-end business flow in plain language
- `docs/requirements/PROJECT_CONTEXT.md` — requirements gathering history
- `PROJECT_CONTEXT.md` (root) — current state summary, open items, change log

## Core Domain Rules

These invariants drive the whole design; any implementation or doc change must preserve them:

- **The stock ledger is the single source of truth.** Every stock-changing event (purchase collection, refund/cancellation, shipment out/receive/cancel, sale, adjustment, edits/deletes affecting stock) creates ledger entries. Stock balances are derived from the ledger, never stored as independent truth.
- **History is never destroyed.** Refunds, cancellations, edits, and deletes use reversal ledger entries referencing the original invoice/line; originals stay traceable. Prefer soft delete for stock-affecting records. Everything important is audited (before/after values).
- **Stock lives in three buckets per product/location:** physical, pending (purchased but not collected), and in-transit (shipped but not received).
- **Purchase entry, purchase collection, and shipments are three separate workflows.** Collection increases stock at the collection location; shipments move already-collected stock between locations.
- **Location rules:** all seven locations (Sydney, Melbourne, Perth, New Zealand, Dubai, Houston, Karachi) can purchase; only Dubai and Karachi can sell. Australia cities are tracked separately — "combined Australia" is a calculated view only. Dubai→Karachi transfer is its own flow.
- **Money:** base currency is AED; purchase lines carry their own currency, exchange rate (manually overridable), and GST rate. GST applies to Australia/NZ purchases now, must be expandable. Refunds must reverse GST and AED values. Shipments have no currency handling.
- **Statuses are computed, never set manually** (purchase status from line quantities; pending = purchased − collected − cancelled/refunded).
- **Stock valuation is admin-only** (SYSTEM_SPEC §26, FR-115…FR-123): weighted average cost in AED per product/location, value follows quantity through all three buckets, shipping costs excluded, refunds reverse value at the original purchase line rate. Enforced server-side, not just hidden in the UI.
- **Business time zone is Dubai (Asia/Dubai)**: all "today" boundaries, date filters, and daily reports use Dubai time; timestamps stored in UTC (FR-128).
- **UI:** light professional theme by default plus a separately designed dark palette (not inverted colors), user-switchable and remembered (FR-124…FR-127). Layouts must adapt to desktops, small laptops, iPads, and small tablets without horizontal scrolling traps (SRS §7.6).
- **Negative stock and over-receiving are allowed with warnings** (negative requires user confirmation); mismatches get highlighted.
- Single-company for now, but schema should carry `company_id` for future multi-company support.
- Out of scope for v1: profit calculation, payments, accounting, barcode/IMEI/serial tracking, low-stock alerts, Excel bulk import.

## Roles

Admin (full access) · Purchase User (purchases, collection, refunds/cancellations, shipments incl. receiving, product creation during purchase) · Sale User (sales CRUD only) · Viewer (read-only). All users can view all data across all locations. Full matrix in `SYSTEM_SPEC.md` §6. Shipment permissions were confirmed 2026-07-02: Admin + Purchase User; remaining open items are backup strategy and final report columns.

## Documentation Maintenance Rule

After each meaningful change, update root `PROJECT_CONTEXT.md` (what changed, files updated, new open items, next recommended step — with a dated change-log entry). If the change affects requirements, workflows, permissions, entities, database design, or reports, also update the matching document under `docs/`, including the Mermaid diagrams in `SYSTEM_DIAGRAMS.md`.

## Conventions

- Commits: short imperative messages (`Add ER diagram PDF`, `Update SRS report fields`).
- Docs and generated assets use kebab-case names (`main-er-diagram.pdf`).
- Future tests go under `tests/` mirroring `src/`, named after the behavior (`purchase-refund.test.*`); inventory, GST, shipment, refund, and audit-log logic need the deepest coverage.
- When implementation code is added, commit the stack's formatter/lint config and document the dev commands in `README.md`.
