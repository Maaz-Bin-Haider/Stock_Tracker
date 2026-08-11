# SwissTech Stock Tracker Project Context

This root-level context file is maintained so future work can continue from the latest project state without reading every document first.

## Current Repository

- Repository folder: `Stock_Tracker`
- Purpose: plan and build a professional web-based inventory system to replace the current spreadsheet workflow.
- Original workbook reference: `data/source/stock_tracker_original.xlsx`
- Implementation status: phases M0–M7 complete and manual functional testing passed on the Mac test environment. **M9 will be a fresh three-month installation on a different Windows machine with one Admin operator.** No Mac test database, Docker volumes, media, or backups will be transferred. Windows-native setup, Desktop shortcut, manual backup/restore tooling, and hardened 12-hour automatic database/media backups are included. **M8 server/AWS deployment remains deferred until the Windows trial finishes without a blocking problem and the client chooses to proceed.**

## Current Project Structure

```text
Stock_Tracker/
├── README.md
├── PROJECT_CONTEXT.md
├── Makefile                  # up/down/logs/venv/test/lint/typecheck
├── pytest.ini
├── data/
│   ├── source/
│   │   └── stock_tracker_original.xlsx
│   └── exports/
├── deployment/
│   ├── docker-compose.yml    # postgres, redis, backend, worker, frontend, nginx
│   └── nginx/default.conf
├── docs/
│   ├── architecture/
│   │   ├── TECHNICAL_ARCHITECTURE.md
│   │   ├── SYSTEM_DIAGRAMS.md
│   │   └── diagrams/pdf/
│   ├── business-flow/
│   │   └── EXECUTION_FLOW_NON_TECHNICAL.md
│   └── requirements/
│       ├── PROJECT_CONTEXT.md
│       ├── SYSTEM_SPEC.md
│       └── SRS.md
├── scripts/
├── src/
│   ├── backend/              # Django + DRF (config/, apps/ with 11 apps)
│   └── frontend/             # Next.js + TypeScript + Tailwind
└── tests/
    └── backend/              # pytest tests mirroring src/backend
```

## Key Documents

- `README.md`: repository overview and document map.
- `LOCAL_SETUP_GUIDE.md`: clean-machine clone/setup, Desktop launcher, 12-hour backups, and disaster recovery for the local trial.
- `docs/USER_GUIDE.md`: non-technical end-user guide for client staff — every screen, button, and workflow with worked examples ("if you do X, then Y").
- `docs/requirements/PROJECT_CONTEXT.md`: detailed requirements gathering history.
- `docs/requirements/SYSTEM_SPEC.md`: implementation-oriented system specification.
- `docs/requirements/SRS.md`: formal Software Requirements Specification.
- `docs/business-flow/EXECUTION_FLOW_NON_TECHNICAL.md`: non-technical execution flow from new system setup to daily/monthly use.
- `docs/architecture/SYSTEM_DIAGRAMS.md`: use case, activity, sequence, class, and ER diagrams.
- `docs/architecture/TECHNICAL_ARCHITECTURE.md`: implementation architecture — Django app breakdown, stock ledger design, API/auth, frontend structure, Docker Compose environment, key decisions, and implementation phases.
- `docs/architecture/diagrams/pdf/`: PDF exports of individual diagrams rendered from the Mermaid diagram source.

## Current Requirements Summary

- Web-based inventory system.
- Single company for now, future multi-company design possible.
- Desktop/web first, responsive for mobile.
- AWS deployment later after local testing, initially possible on one EC2 instance.
- Recommended implementation stack: Django backend, Django REST Framework API, PostgreSQL database, Next.js/TypeScript frontend, Tailwind CSS with shadcn/ui or Radix UI, Celery with Redis for background jobs, local Django media storage during development, and S3-compatible object storage during deployment.
- Development file uploads should use the local Django media folder; deployment should move uploaded/generated files to S3-compatible object storage.
- Stock ledger is the source of truth.
- Purchases can contain multiple product lines.
- Purchase collection is separate from purchase entry.
- Purchase refunds/cancellations happen from a separate page by selecting the original invoice and product line.
- Refunds/cancellations use reversal entries and must reverse stock and GST where relevant.
- Sales happen only from Dubai and Karachi.
- Shipments track source stock, in-transit stock, destination receiving, partial receiving, and over-receiving warnings.
- GST report is product-line based and uses net quantity after refund/cancellation.
- All important user actions must be audited.
- Admin-only Stock Valuation section: total worth of current stock at weighted average purchase cost (AED), covering physical + in-transit + pending buckets, shipping costs excluded, with summary and detail views exportable to Excel/PDF.
- UI: light, modern, professional theme by default plus a dedicated professional dark mode (designed palette, not inverted colors), user-switchable and remembered.
- Fully adaptive layouts for large desktops, small-screen laptops, iPads, and small tablets, in addition to mobile phone support.
- Business time zone is Dubai (Asia/Dubai) for all "today" boundaries and daily reports; timestamps stored in UTC.

## Roles

- Admin: full access.
- Purchase user: purchases, purchase collection, purchase refunds/cancellations, shipments (including receiving), and product creation during purchase flow.
- Sale user: sales only for create/update/delete, with view access to system data.
- Viewer: read-only.

## Open Items

- **AWS deployment (M8) is postponed:** the single-Admin local trial runs for approximately three months first; server deployment proceeds only after a successful trial and client approval.
- Local backup policy is confirmed: database + uploaded-media backup pairs every 12 hours while online, 120-day retention, plus regular off-machine copies by the technician. The final server/cloud policy remains open for M8.
- Final report columns can be refined after business review.
- Final AWS architecture will be decided after the offline trial, with S3-compatible storage expected for uploaded invoices and generated reports.

## Documentation Maintenance Rule

After each project change, update this file with:

- what changed
- which documents/files were updated
- any new open items
- the next recommended step

If a change affects requirements, workflows, permissions, entities, database design, or reports, also update the matching detailed document under `docs/`.

## Change Log

### 2026-08-11 (latest) — Windows target and fresh-data requirement

- Clarified that the real three-month trial will run on a different Windows machine, not the Mac used for manual testing.
- The Windows installation must be a fresh Git clone with new `.env.prod` secrets and new Docker volumes. Mac test database, media, backups, and Docker state must not be copied; only required master settings are seeded.
- Reworked root `LOCAL_SETUP_GUIDE.md` as the authoritative Windows guide with explicit clean-data safeguards, PowerShell clone/configuration commands, fresh-data verification, daily operation, updates, and replacement-machine recovery.
- Added `scripts/setup-windows.ps1` to build the new stack, wait for migrations/health, seed master settings only, create the Admin interactively, install the Desktop shortcut, and create the first post-setup backup pair.
- Added `scripts/open-stock-tracker-windows.cmd` and `scripts/install-desktop-launcher-windows.ps1`. The resulting **SwissTech Stock Tracker** Windows shortcut starts Docker Desktop/the Compose stack, waits for health, and opens `http://localhost:8080`.
- Added Windows-native `scripts/backup-windows.ps1` and paired `scripts/restore-windows.ps1` so a technician does not need Bash or Make on the target machine.
- Made the Windows initializer generate `deployment/.env.prod` automatically with random machine-specific Django/database secrets when it is missing. The private repository contains only the template; the real environment remains gitignored. The existing Mac environment remains a development/test configuration, and a future server deployment will use separate production secrets.
- Updated README, deployment docs, SRS, system specification, requirements history, architecture, and project guidance from the earlier Mac trial assumption to the confirmed fresh Windows target.
- The current Mac test data was not deleted or altered; it remains isolated from the future Windows trial.
- Next recommended step: commit/push these setup changes, then clone on the new Windows machine, run the one setup command, and verify all business pages are empty before live trial entries begin.

### 2026-08-11 (later) — three-month local trial operations

- Confirmed the immediate operating model: one Admin uses the system on one local Mac for approximately three months; server/AWS deployment is considered only after a stable trial.
- Hardened the automatic backup sidecar: it waits for a healthy migrated backend, uses a temporary uncompressed dump so `pg_dump` failure cannot be hidden by a pipeline, validates the compressed result, and removes failed output.
- Changed automatic backups to every 12 hours (`43200` seconds) with 120-day retention. Each cycle now creates a timestamp-matched PostgreSQL dump and uploaded-media archive under `data/backups/`; generated report exports remain reproducible and are not backed up.
- Extended the guarded manual backup/restore tooling with media archive backup and `restore-media`; the manual backup script now reads retention from `.env.prod`.
- Added `scripts/open-stock-tracker.command`, which starts Docker Desktop/the Compose stack if necessary, waits for the health endpoint, and opens the browser. Added `scripts/install-desktop-launcher.sh` and `make desktop-launcher` for one-time installation of a Desktop icon for the non-technical operator.
- Added root `LOCAL_SETUP_GUIDE.md` covering prerequisites, Git clone/update, private configuration, initialization, Desktop launcher installation, automatic/manual backup, integrity checks, and recovery on a replacement Mac.
- Updated requirements, architecture, business flow, deployment documentation, README, Makefile, and project guidance to reflect the confirmed trial model.
- Open operational item: copy `data/backups/` to encrypted USB or another trusted machine at least weekly and monitor the trial. Final report columns and future server/cloud architecture remain business decisions.
- Live verification completed: the recreated sidecar logged the 43,200-second schedule and produced a valid 28 KB database dump plus 4 KB media archive; the Desktop launcher was installed at `/Users/apple/Desktop/SwissTech Stock Tracker.command` and passed an end-to-end start/health/browser-open test.
- Next recommended step: begin the three-month trial, review logs if the launcher reports an error, and copy `data/backups/` off the Mac at least weekly.

### 2026-08-11 — manual testing passed

- The client confirmed that manual functional testing of the local production application passed.
- The production-mode Docker stack remains the accepted local trial build; automated verification remains at 196 passing backend tests with Ruff, ESLint, TypeScript, and the Next.js production build clean.
- A live audit confirmed all seven production services, applied migrations, seeded master data, working authentication, and successful frontend/API/static-file health checks through nginx.
- Operational follow-up: configure the actual office LAN address and test from a second machine. The backup sidecar's startup pipeline also needs failure propagation fixed; `make backup` remains the verified manual backup path.
- Files updated: `PROJECT_CONTEXT.md`, `README.md`, and `CLAUDE.md`.
- Next recommended step: fix the backup-sidecar failure handling, then complete the office-LAN rollout. AWS deployment (M8) remains deferred unless the client chooses to proceed.

### 2026-07-23 (later — M9 offline stack implemented)

- Built the offline/local production stack (Phase M9) alongside the untouched dev stack — the app now runs in production mode on a single machine / office LAN with no cloud dependency:
  - **Local production settings** `config/settings/local_prod.py`: `DEBUG=False`, `SECRET_KEY` required from env (raises a helpful `ImproperlyConfigured` if missing), `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` from env, and secure cookies/HSTS **off by default** for plain HTTP on a trusted LAN (opt-in via `DJANGO_SECURE_COOKIES=1` when TLS is added). Kept separate from `prod.py` (the AWS/TLS profile) on purpose — secure cookies over plain HTTP would break login.
  - **Production process managers:** `deployment/docker-compose.prod.yml` runs the backend under **gunicorn** (`migrate` + `collectstatic` then `gunicorn config.wsgi`) and the frontend from a new `src/frontend/Dockerfile.prod` that bakes `next build` into the image and serves with `next start`. Added `gunicorn>=23` to backend deps.
  - **Persistence & survivability:** named volumes `postgres_data`/`media_files`/`exports_data`/`static_files`; every service `restart: unless-stopped` so the stack returns after a reboot. DB port is **not** published (internal only).
  - **nginx prod config** `deployment/nginx/prod.conf`: serves collected Django static + uploaded media from the shared volumes (gunicorn doesn't serve static), proxies `/api` `/admin` to gunicorn and `/` to `next start`; host port via `${HTTP_PORT:-8080}`.
  - **Local backups:** a `backup` sidecar runs `pg_dump` on a schedule into host `data/backups/` with retention pruning; plus `scripts/backup.sh` (one-shot / cron) and `scripts/restore.sh` (guarded, destructive restore with a `yes` prompt that stops app services, loads the dump, restarts).
  - **Operator ergonomics:** `make prod-up/prod-down/prod-logs/prod-seed/prod-superuser/backup/restore`, a committed `deployment/env.prod.example` template (real `.env.prod` gitignored), and a full runbook `deployment/README.md`.
  - **Admin bootstrap fix (`apps/accounts/management/commands/create_admin.py`):** found during verification that permissions key off `user.role`, not `is_superuser`, so a plain `createsuperuser` leaves the account at the VIEWER default — read-only in the app, no admin nav. Added an idempotent `create_admin` command (creates/promotes to `role=ADMIN` + staff + superuser, non-interactive via `--username/--email/--password` or `DJANGO_ADMIN_*` env, interactive prompt otherwise); `make prod-superuser` now calls it.
- **Verified end-to-end on a live Docker run** (`docker compose ... up -d --build`, all 7 services healthy): health `200`, Next.js prod homepage/login `200`, Django admin static `200` (proves collectstatic → shared static volume → nginx), `migrate` created 36 tables, `seed` loaded master data, `create_admin` produced a working admin, full CSRF→login flow returns `role":"ADMIN"`, named volumes present, the backup sidecar + `scripts/backup.sh` produced a valid 36-table dump, and the **restore drill** (`scripts/restore.sh`) restored cleanly with the admin login working `200` afterward. Also confirmed earlier: `manage.py check` under `local_prod`, refusal to boot without `DJANGO_SECRET_KEY`, secure-cookie toggle, ruff clean, gitignore rules.
  - Minor observed wart (not blocking): the backup sidecar's very first dump races the backend's `migrate` and can capture an empty DB (368 bytes); it self-corrects on the next scheduled cycle. Manual/cron backups after startup are full.
- **Still needs the actual office machine/LAN:** real `.env.prod` with the machine's LAN IP in `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`, browse from a second machine over the LAN, and walk the SRS §12 daily flow with real users. The verification above ran against `localhost` on the dev host.
- Files: `src/backend/config/settings/local_prod.py`, `src/backend/apps/accounts/management/commands/{__init__.py,create_admin.py}` (+ `management/__init__.py`), `src/backend/pyproject.toml`, `src/frontend/Dockerfile.prod`, `src/frontend/.dockerignore`, `deployment/docker-compose.prod.yml`, `deployment/nginx/prod.conf`, `deployment/env.prod.example`, `deployment/README.md`, `scripts/backup.sh`, `scripts/restore.sh`, `Makefile`, `.gitignore`, `README.md`, `data/backups/.gitkeep`.
- Next recommended step: deploy the offline stack on the actual target machine (real `.env.prod` + LAN test + daily-flow walkthrough); once the trial is signed off, proceed to the deferred **M8 — AWS deployment**.

### 2026-07-23 (plan change — AWS postponed, new M9 offline phase)

- **Plan change:** AWS deployment (M8) is postponed. The client will run the system **offline/locally** for a trial period first and deploy to AWS **only if satisfied**. Introduced a new phase **M9 — offline/local production use** as the immediate next phase; **M8 (AWS deployment) is marked deferred to future**. (Numbering note: M8 keeps its lower number but M9 is executed first; most M9 work — prod settings, gunicorn/Next build, persistent volumes, backup/restore — carries directly into M8, where local disk/`pg_dump` is swapped for S3 + EC2.)
- **M9 scope:** run the existing Docker Compose stack in production mode on a single local machine / office LAN with no cloud dependency — local production settings (`DEBUG=False`, secrets from local `.env`, LAN `ALLOWED_HOSTS`), gunicorn + Next.js production build (replacing `runserver`/`next dev`), persistent named Docker volumes for DB/media/exports, `restart: unless-stopped` to survive reboots, LAN reachability via nginx, scheduled **local** `pg_dump` backups with a documented + tested restore, simple start/stop/backup make targets for non-technical operators, and an offline smoke run of the full daily flow. No code changes yet — this entry records the re-plan only.
- **Files updated (docs only):** `docs/architecture/TECHNICAL_ARCHITECTURE.md` §15 (M8 relabeled deferred, added M9 row + execution-order note), `CLAUDE.md` (project-state "next phase" line), root `PROJECT_CONTEXT.md` (status line, Open Items, this entry, Next Recommended Step).
- **Next recommended step:** **Phase M9 — offline/local production use** (see the detailed checklist under "Next Recommended Step" below).

### 2026-07-16 (later — M7)

- Completed phase M7 (hardening), verified end-to-end through nginx with the SRS §12 acceptance walkthrough:
  - **File attachments** (`apps/attachments`, FR-035/FR-073/FR-104…FR-107): `FileAttachment` (module + record_id link to purchases/sales, metadata in DB, bytes in default storage → local media dev / S3 later), upload validation with **magic-byte content sniffing** (PDF/JPEG/PNG/WebP only, 10 MB cap — a renamed executable is rejected), module-scoped write permissions (sale users can't attach to purchases), audited uploads/deletes, authenticated download. The deferred **Upload/File report** is now in the registry (`uploads` key) with download links. Frontend: `components/attachments-panel.tsx` inside the expanded purchase/sale rows.
  - **Theming** (FR-124…FR-127): full semantic token sets in `globals.css` (Tailwind v4 `@theme inline` over CSS vars) with a **separately designed dark palette** (elevated navy surfaces, desaturated text, brighter accents — not an inversion); every page/component swept off raw Tailwind palette classes onto tokens (`bg-surface`, `border-edge`, `text-muted`, `text-danger`, `bg-warning-soft`, …); `color-scheme` set per theme so native controls follow. Preference lives on the user profile (`User.theme` LIGHT/DARK/'' = system, migration 0002; `PATCH /api/v1/auth/me/`) **and** localStorage, with an inline no-flash boot script in the root layout; toggle in the sidebar. System preference respected on first visit.
  - **Responsive shell** (SRS §7.6): static sidebar ≥lg, hamburger top bar + overlay drawer below; `min-w-0` main column so tables scroll inside their containers, never the page.
  - **Pagination**: shared `components/pagination.tsx` wired into `resource-crud.tsx` and all custom list pages (purchases, sales, shipments, adjustments, ledger, collection, audit), with page reset on search/filter/tab changes.
  - **Exports history**: "Recent exports" panel on /reports (per-user job list + re-download). Fixed an export bug the acceptance run caught: Excel forbids `/ \ ? * : [ ]` in sheet names, so "Upload/File Report" failed — sheet titles are now sanitized (regression test added).
  - **Demo seed**: `manage.py seed --demo` builds a small business history **through the domain services** (Sydney AUD purchase w/ GST + partial collection + pending cancellation, Dubai purchase, Sydney→Dubai partial shipment, Dubai→Karachi transfer, sales incl. today, admin adjustment) in one transaction, idempotent via the DEMO-0001 guard; dashboards/reports/valuation have data on a fresh env, zero ledger drift.
  - **Dev-DB repair**: the local Docker Postgres had drifted from the checked-in shipments 0001 migration (edited in place during M4: missing `cancel_reason`, narrow `shipment_type`, legacy `unit_value_aed`/`total_value_aed`/`receipt_no` columns). Patched the dev DB to match the models (verified with an all-tables introspection diff — clean), soft-deleted the partial demo rows via the services, reconciled with zero drift. Fresh databases were never affected.
  - **Acceptance run (SRS §12)**: exercised live — login/roles, dashboard live + past cutoff (Dubai-time conversion verified), GST report netting demo refund (3000 − 300 = 2700 AUD), in-transit report (partial + over-received rows), valuation summary, upload → download → uploads report → uploads export via the real Celery worker, theme PATCH persistence, all pages 200 in both themes. Negative-stock/over-receive warnings, recalculation-from-ledger, and permission-matrix items covered by the 196-test suite.
- Tests: 196 passing (16 new: attachments upload/sniffing/permissions/report + theme preference + sheet-title regression). ruff/eslint/tsc clean.
- Files: `src/backend/apps/attachments/{models,serializers,views}.py` + migration 0001, `apps/accounts/{models,serializers,views}.py` + migration 0002, `apps/reports/{builders,rendering}.py`, `apps/masterdata/management/commands/seed.py`, `config/{urls.py,settings/test.py}`, `src/frontend/app/globals.css`, `app/layout.tsx`, `app/(app)/layout.tsx` (drawer + theme toggle), `lib/{theme.ts,auth.tsx,api.ts}`, `components/{pagination,attachments-panel}.tsx`, all pages (token sweep + pagination), `tests/backend/{test_attachments,test_report_exports}.py`, docs (ER users.theme, PROJECT_CONTEXT, CLAUDE.md).
- Open items: dedicated per-breakpoint DataTable column priorities and Playwright viewport/theme screenshot flows (TECHNICAL_ARCHITECTURE §9.2) remain nice-to-haves; `app_settings` and the OpenAPI-generated typed client stay deferred.
- Next recommended step: **Phase M8 — AWS deployment** per TECHNICAL_ARCHITECTURE §12/§15: single EC2 with the Compose stack under prod settings (gunicorn, TLS, Next.js production build), S3 for media + private exports (django-storages), backups (`pg_dump` to S3 — schedule/retention still an open item), production hardening of `config/settings/prod.py`.

### 2026-07-16 (M6)

- Completed phase M6 (dashboard + reports + Excel/PDF exports + admin stock valuation), verified end-to-end through nginx with the real Celery worker:
  - `apps/reports` report registry (`builders.py`): every SRS §5 report as a `Report` (declared filters + build function returning `Section`s of plain rows) consumed identically by the JSON endpoint and both export renderers, so exports always contain exactly the filtered dataset (FR-098). Reports: current stock by location, total company stock (AED value column admin-only, stripped server-side), Australia combined (dynamic per-AU-city columns over `region_group`), Dubai/Karachi stock (sold-today in Dubai business time), pending purchase stock (+ by-location rollup), in-transit stock, purchase + party-wise purchase, sales + party-wise sales, GST report (SRS §5.1: net qty/net GST from purchase/refund-line frozen values — never ledger `gst_value` sums), refund/cancellation, stock ledger, stock adjustments, user activity, and admin-only valuation summary (multi-section: by bucket/location/category/top products) + detail (weighted average `value_aed / quantity` per product/location per bucket). The Upload/File report is deferred with the attachments feature (FR-104…FR-107) — nothing to report yet.
  - Dashboard endpoint (`/api/v1/reports/dashboard/`, FR-094…FR-096): live cards read `stock_balances`; `?cutoff=` rebuilds the same figures from the ledger with `txn_at <= cutoff` (naive cutoffs interpreted as Dubai time); GST total = purchase-line GST minus refund reversals with soft-delete windows honoured at the cutoff; today's sales bounded by the Dubai business day (FR-128 via `apps/core/time.py`).
  - Export pipeline: `ExportJob` model (report key + params + format + status + file) + Celery task that replays the stored params; Excel via openpyxl (sheet per section, styled headers, number formats, frozen panes), PDF via **ReportLab** (landscape A4, light professional theme, content-aware column widths) — ReportLab replaces the originally planned WeasyPrint because it needs no pango/cairo system libraries (host venv tests + slim Docker image both work). Files live in `EXPORTS_ROOT` **outside** MEDIA_ROOT (nginx serves /media publicly) and download only through the authenticated endpoint; users see their own jobs, admins all; valuation data/exports are admin-only server-side at every step (FR-115…FR-123). Endpoints: `GET /api/v1/reports/`, `GET /api/v1/reports/{key}/`, `POST /api/v1/reports/{key}/export/`, `GET /api/v1/reports/exports/{id}[/download/]`.
  - Frontend: live Dashboard page (cards: total/pending/in-transit/GST/today's sales + per-sales-location, stock-by-location table, past-cutoff datetime picker with snapshot banner); `/reports` page (report picker + per-report filter controls + section tables + totals bar + Excel/PDF export buttons with job polling and auto-download); `/valuation` admin page (summary/detail tabs on the same machinery); shared `components/report-view.tsx`; nav entries (Stock Valuation admin-only).
  - Tests: 180 passing (45 new across `test_dashboard.py`, `test_reports.py`, `test_report_exports.py`) — dashboard live vs cutoff snapshot vs ledger, GST netting after pending-cancel + received-refund, valuation totals surviving `rebuild_stock_balances`, admin-only enforcement on valuation data + exports + value columns (JSON and generated files), export job lifecycle incl. failure capture and cross-user isolation. `config/settings/test.py` (eager Celery + temp exports dir) now drives pytest.
- Files: `src/backend/apps/reports/{definitions,filters,builders,dashboard,models,rendering,serializers,tasks,views}.py` + migration 0001, `config/{urls.py,settings/{base,test}.py}`, `pyproject.toml` (+openpyxl, +reportlab), root `pytest.ini`/`.gitignore`, `src/frontend/components/report-view.tsx`, `src/frontend/app/(app)/{page,reports/page,valuation/page}.tsx`, `src/frontend/app/(app)/layout.tsx`, `tests/backend/{conftest,test_dashboard,test_reports,test_report_exports}.py`, docs (`TECHNICAL_ARCHITECTURE.md` §8, `SYSTEM_SPEC.md` §24, `SYSTEM_DIAGRAMS.md` ER + table notes).
- New open item: the frontend polls exports inline; an exports-history page (list of past export jobs with re-download) can ride along with M7 hardening if wanted.
- Next recommended step: **Phase M7 — hardening** per TECHNICAL_ARCHITECTURE §15: audit review, mismatch highlighting pass, responsive/theming pass (FR-124…FR-127, SRS §7.6 — the dedicated dark palette and viewport testing are still outstanding), richer seed data, purchase/sale file attachments (FR-035/FR-073, unlocks the Upload/File report), pagination controls on list pages, and the SRS §12 acceptance run.

### 2026-07-15 (later — M5)

- Completed phase M5 (sales + stock adjustments), verified end-to-end through nginx with zero ledger drift:
  - `apps/sales`: `Sale` (auto `sale_no` "SL-000001"-style, location validated against `is_sales_location` — Dubai/Karachi only per FR-068 — customer tracked, no payment status per FR-071) + `SaleLine` with an optional reference-only `unit_price` (FR-070) that never touches stock value.
  - Ledger mapping (§5.2): sale → −PHYSICAL @ sale location at the location's carrying average from `stock_balances` (§5.3.1), via a running per-product `CarryingPool` so multi-line sales share value proportionally and empty the pool to exactly zero; line edits post a reversal of the line's net posted state (restoring the *old* product when the product changed, and crediting the pool before fresh rows draw from it) + fresh rows at the current average; soft delete posts reversal rows only. Sale location is locked after entry (stock already left it). Negative stock requires `confirm_negative` (FR-083).
  - `StockAdjustment` lives in `apps/inventory` per TECHNICAL_ARCHITECTURE §3 (model + `adjustments.py` services): direction via `adjustment_type` INCREASE|DECREASE with a mandatory reason (FR-075); decreases take a proportional share of the physical pool (exact when emptied), increases add at the current carrying average so unit cost is undisturbed; edits reverse the net posted state + fresh rows; deletes reverse only. Admin-only writes per the §6 matrix.
  - API: `/api/v1/sales/` CRUD with quick totals (total quantity + reference-only sale value, FR-103); `/api/v1/stock-adjustments/` CRUD; `?confirm_negative=true` retry contract on both. Sale users get their first write module (admin + sale write sales; product creation stays closed to them, FR-017).
  - Frontend: Sales page (sales-location-filtered dropdown, customer, per-line optional price, expandable lines, negative-stock retry on create/edit) and Stock Adjustments page (single-record form with type/reason, negative retry on create/edit/delete); nav + permissions mirror updated.
  - Tests: 135 passing (19 new — carrying-average value removal incl. exact emptying, optional price, non-sales-location rejection, negative confirmations (sale + adjustment), edit reversal + fresh rows (sale + adjustment), price-only edit posts nothing, location change rejected, delete restores stock (sale + adjustment), increase-at-average, reason required, role matrices incl. sale-user-cannot-create-products, quick totals; reconciliation asserted in every scenario). `conftest.make_user` now reuses an existing user of the same username so fixtures and tests can request the same role twice.
- Files: `src/backend/apps/sales/{models,services,serializers,views}.py` + migration 0001, `src/backend/apps/inventory/{models,adjustments,serializers,views}.py` + migration 0002, `src/backend/config/urls.py`, `src/frontend/app/(app)/{sales,stock-adjustments}/page.tsx`, `src/frontend/app/(app)/layout.tsx`, `src/frontend/lib/permissions.ts`, `tests/backend/{conftest,test_sales,test_stock_adjustments}.py`.
- Next recommended step: **Phase M6 — dashboard + reports + Excel/PDF exports (Celery) + admin stock valuation** per TECHNICAL_ARCHITECTURE §15/§8 and SRS §5: dashboard cards (FR-094…FR-095) + past-cutoff snapshot aggregating the ledger with `txn_at <= cutoff` (FR-096), the SRS §5 report list over annotated querysets (GST report per §5.1 from purchase/refund lines — never ledger gst sums), Celery Excel (openpyxl)/PDF (WeasyPrint) export pipeline with filtered-data-only exports (FR-097…FR-101), admin-only valuation summary/detail endpoints reading `stock_balances` (FR-115…FR-123) in `apps/reports`, and the `attachments` app for export storage (FR-104…FR-107). Use `apps/core/time.py` business-day helpers for every "today" boundary (FR-128).

### 2026-07-15 (M4)

- Completed phase M4 (shipments + receiving, incl. Dubai→Karachi), verified end-to-end through nginx with zero ledger drift:
  - `apps/shipments`: `Shipment` (auto `shipment_no` "SH-000001"-style, `shipment_type` STANDARD | DUBAI_KARACHI per FR-065, shipping cost recorded but excluded from stock value per FR-119, no currency per FR-066) + `ShipmentLine`, `ShipmentReceipt` + `ShipmentReceiptLine`. `shipped_at`/`cancelled_at` record events set only by the ship/cancel services; statuses (draft/shipped/partially received/fully received/cancelled, FR-060) and received/remaining/`over_received` are always computed, never stored.
  - Ledger mapping (§5.2): ship → −PHYSICAL @ from-location / +IN_TRANSIT @ to-location; receipt → −IN_TRANSIT/+PHYSICAL @ to-location; cancel → reversal of each line's unreceived in-transit remainder back to source physical (received stock stays); receipt undo and shipment soft delete reverse the shipment's own ledger rows exactly. All postings via `post_event`, audited in-transaction (modules `shipments`, `shipment_receipts`).
  - Valuation: value moves at the source location's carrying average cost read from `stock_balances` (§5.3.1) — the first flow consuming carrying value rather than line-frozen values. Proportional-remainder sharing (with a running per-product pool for multi-line shipments) empties buckets to exactly zero value; receipts draw value from the line's in-transit ledger remainder, so over-received quantity beyond the remainder carries no extra value (value is conserved end to end).
  - Warnings: negative source stock on ship requires `confirm_negative` (FR-083, same retry contract as purchases); over-receiving is allowed — IN_TRANSIT goes negative for the line and the computed `over_received` flag drives highlighting (FR-084/FR-085).
  - Lifecycle rules: drafts post nothing and are freely editable; once shipped, lines are locked (cancel and re-enter to change them) and only header fields may change; cancelling a fully received shipment is rejected; delete reverses every row the shipment ever posted and soft-deletes receipts/lines with it.
  - API: `/api/v1/shipments/` CRUD with quick totals (shipped/received/remaining, FR-103), `POST /shipments/{id}/ship/`, `POST /shipments/{id}/cancel/`, `POST/GET /shipments/{id}/receipts/`, `DELETE /shipments/{id}/receipts/{rid}/`; `ship: true` on create ships immediately. Admin + purchase users write, all roles read (Batch 9 decision).
  - Frontend: Shipments page — list with quick totals and over-received badges, expandable lines + receipt history with Undo, draft/ship/receive/cancel/delete actions, create/edit modal with Save Draft vs Save & Ship, receive dialog with per-line quantities, over-receive confirmation, and negative-stock retry. Nav + permissions mirror updated.
  - Tests: 116 passing (19 new — draft posts nothing, draft editable vs shipped locked, carrying-average ship, exact pool emptying incl. multi-line same product, negative-stock confirmation, Dubai→Karachi type, partial/full/over receive, receive-before-ship rejected, receipt undo, cancel draft/partial/fully-received, delete restores everything, role matrix, quick totals; reconciliation asserted in every scenario).
- Files: `src/backend/apps/shipments/{models,services,serializers,views}.py` + migration 0001, `src/backend/config/urls.py`, `src/frontend/app/(app)/shipments/page.tsx`, `src/frontend/app/(app)/layout.tsx`, `src/frontend/lib/permissions.ts`, `tests/backend/test_shipments.py`.
- Next recommended step: **Phase M5 — sales + stock adjustments** per TECHNICAL_ARCHITECTURE §15: `Sale` + `SaleLine` (location validated against `is_sales_location`, customer tracking, optional reference-only sale price, FR-067…FR-072), `StockAdjustment` (required reason, ±PHYSICAL, admin-only per §6 matrix, FR-074…FR-077), ledger rows −PHYSICAL @ sale location at carrying average, negative-stock confirmation on sale (FR-083), edit/delete reversals, sale-user role coverage, Sales + Adjustments pages.

### 2026-07-06 (later — M3)

- Completed phase M3 (purchase refunds/cancellations), verified end-to-end through nginx with zero ledger drift:
  - `PurchaseRefund` (auto `refund_no` "RF-000001"-style, required reason, soft delete) + `PurchaseRefundLine` with an explicit `source` per line: `PENDING` cancels undelivered quantity (FR-049, −PENDING @ purchase location), `RECEIVED` returns delivered stock (FR-050, −PHYSICAL @ the location holding it, defaulting to the purchase location). Reversal values (original currency + AED + GST both) are frozen on the refund line at the original purchase line rate (FR-053/FR-054/FR-093/FR-122) for the M6 GST/refund reports.
  - Ledger postings reuse the proportional-remainder allocators so buckets land on exactly zero when emptied; received refunds validate against the line's per-location physical remainder computed from the ledger. `confirm_negative` passes through for refunds that would drive physical stock negative.
  - `PurchaseLine` quantity model finalized: `pending = quantity − collected − cancelled_pending` (SYSTEM_SPEC §8), `net = quantity − refunded_total` (the GST-report quantity), statuses now include CANCELLED/REFUNDED (REFUNDED when any delivered stock was returned). List annotations moved to subqueries to avoid multi-join fan-out.
  - Edit/delete flows updated for refund history: pricing locks once a line has collections *or* refunds; quantity floor is collected + cancelled; purchase soft delete reverses per-location physical remainders (no over-reversal after received refunds) and soft-deletes refunds along with lines/collections. Refund deletion ("undo") reverses the refund's own ledger entries, preserving the full chain.
  - API: `POST/GET /api/v1/purchases/{id}/refunds/`, `DELETE /api/v1/purchases/{id}/refunds/{rid}/` (admin + purchase users; read for all). Audited as module `purchase_refunds` in-transaction.
  - Frontend: Purchase Refunds/Cancellations page per the FR-044 workflow — search/select invoice → line table with collected/pending/refunded/net → per-line quantity + source (cancel pending vs return received) + required reason → refund history with per-refund AED/GST reversal totals and Undo; negative-stock confirmation retry built in. Nav updated.
  - Tests: 97 passing (17 new — pending cancellation with GST reversal, received refund at line rate, whole-line REFUNDED/CANCELLED statuses, mixed received+pending lines in one invoice, over-refund rejections, refund undo, collect-after-partial-cancel, edit floor with cancellations, purchase delete after received refund, reason required, role matrix; reconciliation asserted in every scenario).
- Files: `src/backend/apps/purchases/{models,services,serializers,views}.py` + migration 0002, `src/frontend/app/(app)/purchase-refunds/page.tsx`, `src/frontend/app/(app)/layout.tsx`, `tests/backend/test_purchase_refunds.py`.
- Next recommended step: **Phase M4 — shipments + receiving (incl. Dubai→Karachi)** per TECHNICAL_ARCHITECTURE §15: shipment/receipt models with computed statuses (draft/shipped/partially received/fully received/cancelled), ledger rows −PHYSICAL @ from-location / +IN_TRANSIT @ to-location on ship, −IN_TRANSIT/+PHYSICAL on receipt, cancellation reversals of unreceived quantities, partial + over-receiving with warnings (IN_TRANSIT may go negative per §5.2, flag `over_received`), negative-stock confirmation on shipping, value moved at the source's carrying average cost (§5.3.1) — first flow that consumes `stock_balances` value rather than line-frozen values.

### 2026-07-06

- Completed phase M2 (inventory core + purchases + collection), verified end-to-end through nginx and by the ledger drift check:
  - `apps/inventory`: append-only `StockLedgerEntry` (txn types for all §5.2 events, `reversal_of` FK so corrections reference originals) and materialized `StockBalance` (product × location × bucket, `quantity` + `value_aed`; weighted average unit cost = `value_aed / quantity` per TECHNICAL_ARCHITECTURE §5.3.1).
  - `post_event` in `apps/inventory/services.py` is the only ledger writer: runs in `transaction.atomic()`, locks balance rows with `SELECT ... FOR UPDATE`, enforces the `confirm_negative` flag for PHYSICAL stock going negative (FR-082/FR-083), and validates movement shape. `reversal_movements()` builds exact undo movements.
  - `rebuild_stock_balances` management command + Celery task recomputes balances from the full ledger and reports drift (consistency check, TECHNICAL_ARCHITECTURE §5.3).
  - Read-only `/api/v1/stock/ledger/` and `/api/v1/stock/balances/` for all roles; `value_aed` on balances is stripped server-side for non-admins (stock valuation is admin-only, FR-116).
  - `apps/purchases`: `Purchase` + `PurchaseLine` (currency, exchange rate, AED unit/total, GST rate/amount all frozen at entry; defaults resolved from Settings, manual override wins per FR-089), `PurchaseCollection` + lines. Statuses and collected/pending quantities always computed (properties + annotated querysets), never stored.
  - Ledger mapping implemented in `apps/purchases/services.py`: entry → +PENDING; collection → −PENDING @ purchase location, +PHYSICAL @ collection location; line edits → reversal of remaining pending + fresh rows (pricing immutable once a line has collected stock; quantity cannot drop below collected); soft delete → reversal rows only (pending backed out, collected physical reversed). Proportional value allocation from the ledger keeps pending value exactly zero when a line is fully collected.
  - Business rule note: GST on −PENDING collection rows is bucket bookkeeping (keeps remaining-pending GST exact for M3 cancellations); GST liability lives on PURCHASE_ENTRY rows and purchase lines — never sum `gst_value` across all ledger rows.
  - API: `/api/v1/purchases/` CRUD with nested lines and quick totals (FR-103); explicit sub-resources `POST/GET /purchases/{id}/collections/`, `DELETE /purchases/{id}/collections/{cid}/`; `GET /purchases/pending-lines/` feeds the Collection/Pending page; `?confirm_negative=true` passes the negative-stock confirmation on deletes. All writes audited in-transaction via the purchase services.
  - Frontend: Purchases page (multi-line invoice form with auto/override exchange rate, collected-now quantities, expandable line detail, quick-totals cards), Collection/Pending page (per-line partial collection), Stock Ledger page (balances + movement history tabs, Dubai-time display, admin-only value column); nav + permissions mirror updated.
  - Tests: 80 passing (34 new — post_event validation/negative-confirmation/reversals/rebuild drift, every implemented §5.2 mapping row incl. partials, edit/delete reversals, frozen-value assertions, role matrix for purchases/collections/stock endpoints, reconciliation after every scenario).
- Files: `src/backend/apps/inventory/*`, `src/backend/apps/purchases/*`, `src/backend/config/urls.py`, `src/frontend/app/(app)/{purchases,purchase-collection,stock-ledger}/page.tsx`, `src/frontend/app/(app)/layout.tsx`, `src/frontend/lib/permissions.ts`, `tests/backend/{conftest,test_inventory,test_purchases,test_stock_api}.py`.
- Design decision recorded: collection posts −PENDING at the *purchase* location and +PHYSICAL at the *collection* location (they default to the same place); §5.2's "−PENDING @ collection location" wording assumes they match — posting the reduction where the pending was created keeps balances consistent when they differ.
- New open item: purchase/sale file attachments (FR-035/FR-073) still pending the `attachments` app — fold into M5/M6.
- Next recommended step: **Phase M3 — purchase refunds/cancellations** (separate page/endpoint, line-level partial refunds, reversal entries referencing original invoice/lines, GST + AED reversal at original line rate, `refunded_qty` wired into the pending formula and statuses CANCELLED/REFUNDED).

### 2026-07-04

- Completed phase M1 (accounts, master data, products, audit foundation), all verified end-to-end through nginx:
  - Auth: session login/logout/me endpoints (`/api/v1/auth/…`); login, logout, and failed-login attempts are audited via Django auth signals; `me` guarantees the CSRF cookie for the SPA.
  - Role matrix: `apps/accounts/permissions.py` holds the static `ROLE_MATRIX` mirroring SYSTEM_SPEC §6; a shared `ModulePermission` class enforces read-for-all / writes-per-role; users endpoint is admin-only, users are disabled rather than deleted. Interpretation recorded: suppliers are writable by admin + purchase users, customers by admin + sale users (per the use-case diagram; the §6 matrix doesn't list them explicitly).
  - Master data: models + audited CRUD APIs for categories, locations (behavior flags: `can_purchase`, `is_sales_location`, `region_group`, `gst_region`), currencies, exchange rates, GST rates, suppliers, customers.
  - Products: product master with case-insensitive uniqueness on (name, storage/specs) via functional unique constraint plus a friendly serializer validation (FR-018/FR-019).
  - Audit foundation: append-only `AuditLog`, request-context middleware (contextvar), explicit `record_audit` service, `AuditedModelViewSet` base that snapshots before/after on every write; read-only audit API visible to all roles (FR-113).
  - Seed command (`manage.py seed`, `make seed`): 7 locations, 5 currencies, AU/NZ GST rates, sample exchange rates, categories, and a DEBUG-only dev admin (admin/admin123).
  - Frontend: login page, authenticated app shell with role-aware sidebar, generic CRUD component, pages for products/suppliers/customers/users/audit and settings pages (categories, locations, currencies, exchange rates, GST rates) driven by one dynamic route.
  - Tests: 46 passing (role matrix per endpoint per role, product uniqueness, audit snapshots, auth flow). Compose Postgres now publishes on host port 5433 to avoid colliding with a natively installed Postgres; `make test` sets `POSTGRES_PORT=5433`.
- Deleted the recovered terminal transcript (`Terminal Saved Output.txt`) after reconciling its contents.
- Completed phase M0 scaffolding per `TECHNICAL_ARCHITECTURE.md` §15: Django backend (`src/backend`) with the 11 planned apps, split settings (base/dev/prod), custom `accounts.User` with role field, core model mixins (timestamps, company scope, soft delete), business-time helpers (`apps/core/time.py`), Celery wiring, DRF + OpenAPI schema endpoints, and a health endpoint; Next.js/TypeScript/Tailwind frontend (`src/frontend`); Docker Compose environment (`deployment/docker-compose.yml`) with postgres, redis, backend, celery worker, frontend, and nginx single-origin proxy on `http://localhost:8080`; root `Makefile`, pytest config, first test (`tests/backend/test_health.py`), and GitHub Actions CI (ruff + pytest with Postgres, eslint + tsc + next build).
- Updated `README.md` (development commands, current status), `CLAUDE.md` (project state and commands), and `.gitignore` for the new stack.
- Completed the finishing touches left over from the interrupted 2026-07-02 session (the session was cut off by a connection loss; its state was recovered from a saved terminal transcript): fixed the `9.3 Time Handling` heading level in `docs/architecture/TECHNICAL_ARCHITECTURE.md` so it sits under section 9 (Frontend), and corrected the section 9.2 responsiveness cross-reference from "FR-122" (which is Valuation Refund Reversal) to plain "SRS §7.6".
- Updated `CLAUDE.md` core domain rules with the Batch 10 requirements (admin-only stock valuation at weighted average cost, Dubai business time zone, light/dark themes, and tablet/laptop responsiveness), which the interrupted session had not reached.
- Verified all Batch 9/10 changes landed consistently across `docs/requirements/SRS.md`, `docs/requirements/SYSTEM_SPEC.md`, `docs/requirements/PROJECT_CONTEXT.md`, `docs/architecture/SYSTEM_DIAGRAMS.md`, `docs/business-flow/EXECUTION_FLOW_NON_TECHNICAL.md`, and root `PROJECT_CONTEXT.md`; no duplicated or truncated content was found.

### 2026-07-02

- Added three new client requirements (Batch 10 in `docs/requirements/PROJECT_CONTEXT.md`): admin-only Stock Valuation section with exportable summary/detail reports, professional light + dark themes, and full responsiveness for iPads/small laptops/small tablets.
- Confirmed valuation decisions with the client: weighted average costing in AED per product per location; physical + in-transit + pending all count toward total worth; shipping costs excluded; business time zone is Dubai (raised as a requirements gap, now resolved).
- Updated for the new requirements: `docs/requirements/SRS.md` (FR-115…FR-128, modules, reports list, §7.6, acceptance criteria), `docs/requirements/SYSTEM_SPEC.md` (navigation, permission matrix, new §26 Stock Valuation, §27 UI Theme and Responsiveness, §28 Business Time Zone; Resolved Confirmation Items renumbered to §29), `docs/architecture/SYSTEM_DIAGRAMS.md` (use case diagram), `docs/business-flow/EXECUTION_FLOW_NON_TECHNICAL.md` (new §25 Admin Stock Valuation Flow), and `docs/architecture/TECHNICAL_ARCHITECTURE.md` (valuation design, theming, responsive strategy, time zone).
- Created `docs/architecture/TECHNICAL_ARCHITECTURE.md`: monorepo layout (`src/backend`, `src/frontend`), 11 Django apps with `inventory` owning the append-only stock ledger and a materialized `stock_balances` table, a single `post_event` posting service as the only ledger writer, session-cookie auth behind a single nginx origin, DRF API with OpenAPI-generated frontend client, Celery-based Excel/PDF exports, Docker Compose local environment, testing strategy keyed to the event→ledger mapping table, and implementation phases M0–M8.
- Resolved the shipment permission open item: admin and purchase users can create, update, and delete shipments and record shipment receiving; sale users and viewers are view-only. No separate shipment/operator role is added.
- Updated for the shipment permission decision: `docs/requirements/SYSTEM_SPEC.md` (permission matrix, section 6 note, section 26), `docs/requirements/SRS.md` (user classes, FR-007, open items), `docs/requirements/PROJECT_CONTEXT.md` (Batch 8 permissions, new Batch 9), `docs/architecture/SYSTEM_DIAGRAMS.md` (use case diagram arrows, shipment sequence actor), `docs/business-flow/EXECUTION_FLOW_NON_TECHNICAL.md` (roles, shipment flow, daily flow), and root `PROJECT_CONTEXT.md`.
- Note: PDF exports `01-main-use-cases.pdf` and `12-shipment-and-receiving-sequence.pdf` are now stale and should be re-rendered from the updated Mermaid source.
- Added `CLAUDE.md` with repository guidance for Claude Code.
- Confirmed file storage direction: use Django local media storage during development and move uploads/generated reports to S3-compatible object storage during deployment.
- Documented the recommended full tech stack: Django, Django REST Framework, PostgreSQL, Next.js/TypeScript, Tailwind CSS with shadcn/ui or Radix UI, Celery, Redis, local Django media storage, and S3-compatible deployment storage.
- Updated root and detailed requirement documents with the development/deployment storage decision.

### 2026-06-30

- Created professional repository structure.
- Moved original workbook to `data/source/stock_tracker_original.xlsx`.
- Moved requirement documents under `docs/requirements/`.
- Moved non-technical execution flow under `docs/business-flow/`.
- Created `docs/architecture/SYSTEM_DIAGRAMS.md` with detailed use case, activity, sequence, class, and ER diagrams.
- Updated README, SRS, system specification, and execution flow to reference the architecture diagrams.
- Added `docs/architecture/diagrams/pdf/01-main-use-cases.pdf` as the PDF export for the main use case diagram.
- Added `docs/architecture/diagrams/pdf/02-new-system-setup-activity.pdf` as the PDF export for the new system setup activity diagram.
- Added `docs/architecture/diagrams/pdf/03-purchase-entry-activity.pdf` as the PDF export for the purchase entry activity diagram.
- Added `docs/architecture/diagrams/pdf/04-purchase-collection-activity.pdf` as the PDF export for the purchase collection activity diagram.
- Added `docs/architecture/diagrams/pdf/05-purchase-refund-cancellation-activity.pdf` as the PDF export for the purchase refund/cancellation activity diagram.
- Added `docs/architecture/diagrams/pdf/06-shipment-activity.pdf` as the PDF export for the shipment activity diagram.
- Added `docs/architecture/diagrams/pdf/07-shipment-receiving-activity.pdf` as the PDF export for the shipment receiving activity diagram.
- Added `docs/architecture/diagrams/pdf/08-sales-activity.pdf` as the PDF export for the sales activity diagram.
- Added `docs/architecture/diagrams/pdf/09-report-export-activity.pdf` as the PDF export for the report export activity diagram.
- Added `docs/architecture/diagrams/pdf/10-purchase-invoice-creation-sequence.pdf` as the PDF export for the purchase invoice creation sequence diagram.
- Added `docs/architecture/diagrams/pdf/11-purchase-refund-cancellation-sequence.pdf` as the PDF export for the purchase refund/cancellation sequence diagram.
- Added `docs/architecture/diagrams/pdf/12-shipment-and-receiving-sequence.pdf` as the PDF export for the shipment and receiving sequence diagram.
- Added `docs/architecture/diagrams/pdf/13-sale-entry-sequence.pdf` as the PDF export for the sale entry sequence diagram.
- Added `docs/architecture/diagrams/pdf/14-class-diagram.pdf` as the PDF export for the class diagram.
- Added `docs/architecture/diagrams/pdf/15-main-er-diagram.pdf` as the PDF export for the main ER/database design diagram.

## Next Recommended Step

**Current plan (2026-08-11): install M9 fresh on a separate Windows machine for one Admin to use for approximately three months.** The Mac remains a test environment and none of its runtime data transfers. Server/AWS deployment (M8) proceeds only after a stable Windows trial and explicit client approval.

**Phase M9 — offline/local production use: code-complete; manual functional testing passed on 2026-08-11.** M0–M7 remain done and verified (196 backend tests, ruff/eslint/tsc clean, SRS §12 acceptance walkthrough). The offline stack is built alongside the untouched dev stack:

- [x] Local production settings — `config/settings/local_prod.py`: `DEBUG=False`, secret required from env, LAN `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` from env, secure cookies/HSTS off by default for plain-HTTP LAN (opt-in `DJANGO_SECURE_COOKIES=1`).
- [x] Production process managers — `deployment/docker-compose.prod.yml` runs gunicorn (after `migrate`+`collectstatic`); `src/frontend/Dockerfile.prod` bakes `next build` and serves via `next start`. `gunicorn>=23` added to deps.
- [x] Persistent local storage — named volumes `postgres_data`/`media_files`/`exports_data`/`static_files`; nginx serves static + media from the shared volumes (`deployment/nginx/prod.conf`).
- [x] Survivability — `restart: unless-stopped` on every service.
- [x] Local-only access — nginx serves `http://localhost:8080` on the Windows host; the DB stays internal and unpublished.
- [x] Local backups — hardened backup sidecar + guarded manual tools create database and uploaded-media pairs every 12 hours with 120-day retention and documented restore.
- [x] Operator ergonomics — Windows `.cmd` launcher + `.lnk` installer, one-time PowerShell setup, Windows-native manual backup/restore, and the root setup/recovery guide. The macOS launcher remains only for the test machine.
- [x] **Smoke run verified on a live Docker stack** (localhost, all 7 services healthy): health/homepage/login/admin-static all `200`, migrate (36 tables) + seed + `create_admin` (role ADMIN), full CSRF→login flow, backup sidecar + `scripts/backup.sh` dump, and a passing restore drill.
- [x] **Manual functional testing passed** — confirmed by the client on 2026-08-11.
- [x] **Backup sidecar hardened** — dump failure propagation and compressed archive validation are explicit.
- [ ] **Remaining — fresh Windows rollout:** commit/push the setup changes, clone them on the new Windows machine, initialize new volumes, verify business pages contain no test data, and begin the trial. Copy backup pairs off the Windows machine at least weekly.

Local backup policy is confirmed at **12-hour intervals / 120-day retention**. The final server/cloud backup policy remains a future M8 decision.

**Deferred — Phase M8 — AWS deployment (future, only if the offline trial succeeds).** Most M9 work carries over; the deltas are: swap local storage for an S3-compatible bucket via django-storages (public-ish media for uploads, **private** prefix + authenticated download for exports — `EXPORTS_ROOT` swap is configuration only), run the Compose stack on a single EC2 instance with a domain + TLS certificates, and move backups from local disk to `pg_dump` → S3 on a schedule.

Deferred small items (unchanged): `app_settings` model/endpoint (SYSTEM_SPEC §24 — no concrete requirement yet), OpenAPI-generated typed frontend client + TanStack Query/shadcn DataTable adoption (TECHNICAL_ARCHITECTURE §6/§9), per-breakpoint DataTable column priorities + Playwright viewport/theme screenshot flows (§9.2).
