# SwissTech Inventory System Technical Architecture

This document turns the requirements (`docs/requirements/SRS.md`, `docs/requirements/SYSTEM_SPEC.md`) into a concrete implementation architecture. It is the reference for how the system is built; the SRS remains the reference for what the system must do.

## 1. System Overview

```text
                        ┌─────────────────────────────────────────┐
                        │              Browser (user)             │
                        └────────────────────┬────────────────────┘
                                             │ HTTPS
                        ┌────────────────────▼────────────────────┐
                        │        Reverse proxy (nginx)            │
                        │  /            → Next.js frontend        │
                        │  /api, /admin → Django backend          │
                        │  /media       → uploaded files (dev)    │
                        └───────┬─────────────────────┬───────────┘
                                │                     │
                 ┌──────────────▼──────┐   ┌──────────▼───────────┐
                 │  Next.js (TypeScript)│   │  Django + DRF        │
                 │  UI, forms, tables   │   │  API, domain services│
                 └─────────────────────┘   └───┬────────┬─────────┘
                                               │        │
                                     ┌─────────▼──┐  ┌──▼────────────┐
                                     │ PostgreSQL │  │ Redis         │
                                     │ (all data) │  │ cache + queue │
                                     └────────────┘  └──┬────────────┘
                                                        │
                                              ┌─────────▼──────────┐
                                              │ Celery workers     │
                                              │ exports, rebuilds  │
                                              └────────────────────┘
```

- Single-origin deployment: the proxy serves frontend and API from one domain, which keeps authentication cookies simple and avoids CORS in production.
- One PostgreSQL database owns all business data. Redis is used for Celery and short-lived caching only — never as a source of truth.
- Celery handles report exports (Excel/PDF) and heavy ledger rebuilds so web requests stay fast.

## 2. Repository Layout

Monorepo — backend and frontend live in this repository under `src/`:

```text
src/
├── backend/
│   ├── manage.py
│   ├── config/                  # Django project: settings, urls, celery app
│   │   ├── settings/            # base.py, dev.py, prod.py
│   │   ├── urls.py
│   │   └── celery.py
│   ├── apps/                    # all Django apps (section 3)
│   ├── media/                   # dev uploads (gitignored)
│   └── pyproject.toml
├── frontend/
│   ├── app/                     # Next.js App Router
│   ├── components/
│   ├── lib/                     # API client, utils
│   └── package.json
deployment/
├── docker-compose.yml           # local dev environment
└── nginx/
```

## 3. Backend: Django App Breakdown

One Django project, focused apps with clear ownership. Apps may read each other's models but stock-changing writes go only through the `inventory` services (section 5).

| App | Owns | Notes |
| --- | --- | --- |
| `core` | Base model mixins, shared validators, enums | `TimeStampedModel` (created/updated by/at), `CompanyScopedModel` (nullable `company_id` for future multi-company), soft-delete mixin |
| `accounts` | User, Role, sessions, login/logout | Custom user model from day one; single `role` field per user (ADMIN, PURCHASE, SALE, VIEWER) |
| `masterdata` | Locations, currencies, exchange rates, GST rates, categories, suppliers, customers, app settings | All configurable reference data behind Settings pages |
| `products` | Product master | Case-insensitive uniqueness on (name, storage/specs) via functional unique index |
| `purchases` | Purchases, purchase lines, collections, collection lines, refunds, refund lines | Statuses are computed properties, never stored user input |
| `shipments` | Shipments, shipment lines, receipts, receipt lines | Includes Dubai→Karachi transfer as a shipment type |
| `sales` | Sales, sale lines | Location validated against `is_sales_location` flag |
| `inventory` | **Stock ledger, stock balances, stock adjustments, all stock-posting services** | The only writer of ledger rows; other apps call its services |
| `reports` | Report queries, dashboard aggregates, export jobs | Read-only over other apps' models |
| `audits` | Audit log, request-context middleware | Written in-transaction by services |
| `attachments` | File uploads metadata | Generic FK to owning record; storage backend swappable (local media → S3) |

## 4. Data Model Highlights

Full table list is in SYSTEM_SPEC §24; the decisions that matter:

- **Every business table** inherits `created_by/created_at/updated_by/updated_at` and nullable `company_id`.
- **Soft delete** for stock-affecting records (`deleted_at`, `deleted_by`, `is_deleted`): a delete posts reversal ledger entries and flags the record; rows are never physically removed.
- **Stored quantities vs computed quantities.** Purchase lines store `quantity` only; `collected_qty`, `refunded_qty`, `pending_qty`, and line/invoice status are computed from collection lines, refund lines, and ledger entries (exposed as annotated querysets for list-page performance).
- **Money fields**: `DECIMAL(14,2)` for values, `DECIMAL(12,6)` for exchange rates; each purchase line stores currency, exchange rate (overridable), unit price, computed AED unit price/total, GST rate, GST amount — frozen at entry time so historical values never drift when settings change.
- **Locations** carry behavior flags instead of hardcoded names: `can_purchase`, `is_sales_location` (Dubai, Karachi), `region_group` (for the calculated combined-Australia view), `gst_region` (nullable, drives GST applicability).
- **Indexes** on all filter columns per SRS §7.2: dates, product, location, supplier/customer, status-driving FKs, and ledger `(product, location, bucket)`.

## 5. The Stock Ledger (Core of the System)

### 5.1 Ledger table

Append-only. Rows are never updated or deleted — corrections are new reversal rows.

```text
stock_ledger
├── id, txn_at, txn_type            # txn_type: enum below
├── source_module, source_id, source_line_id   # traceability to the business record
├── reversal_of_id                  # FK to the ledger row being reversed (nullable)
├── product_id, location_id
├── bucket                          # PHYSICAL | PENDING | IN_TRANSIT
├── qty_in, qty_out                 # always >= 0; one of them is 0
├── related_location_id             # e.g. source location on a shipment receipt
├── currency, aed_value, gst_value  # where relevant (purchases/refunds)
├── notes, created_by, created_at
```

### 5.2 Event → ledger entry mapping

This table is the contract every service implements. One business event may write multiple rows, always in one DB transaction.

| Business event | Ledger entries (bucket @ location) |
| --- | --- |
| Purchase line entered | +PENDING @ purchase location |
| Purchase collection | −PENDING @ purchase location, +PHYSICAL @ collection location (they default to the same place; the reduction posts where the pending was created) |
| Refund/cancel of pending qty | −PENDING @ purchase location |
| Refund of received qty | −PHYSICAL @ collection location (with negative AED/GST values) |
| Shipment marked shipped | −PHYSICAL @ from-location, +IN_TRANSIT @ to-location |
| Shipment receipt | −IN_TRANSIT @ to-location, +PHYSICAL @ to-location |
| Shipment cancelled | reversal rows of the unreceived shipped entries |
| Sale | −PHYSICAL @ sale location |
| Stock adjustment | ±PHYSICAL @ location |
| Edit of any stock-affecting record | reversal rows for the old state + fresh rows for the new state |
| Soft delete of stock-affecting record | reversal rows only |

Over-receiving posts the real received quantity (IN_TRANSIT may go negative for that shipment line) and flags the line `over_received` — the warning/highlight is driven from that flag, not from blocking the write.

### 5.3 Balances: derived, but materialized

`stock_balances (product, location, bucket, quantity, value_aed)` is a materialized rollup of the ledger:

- Updated **in the same transaction** as ledger inserts using `SELECT ... FOR UPDATE` on the balance row (row-level locking serializes concurrent movements of the same product+location).
- The ledger remains the source of truth: a `rebuild_stock_balances` management command (also a Celery task) recomputes all balances from the full ledger and reports any drift. Run after bulk edits and on a schedule as a consistency check.
- Dashboards and stock reports read `stock_balances`; the "past cutoff" dashboard (FR-096) aggregates the ledger directly with `txn_at <= cutoff`.

### 5.3.1 Stock valuation: value follows quantity

The admin-only Stock Valuation section (SYSTEM_SPEC §26, FR-115…FR-123) is driven by the same mechanism — no separate costing subsystem:

- Every ledger row that moves purchased stock carries its `aed_value` (frozen at purchase entry). `stock_balances.value_aed` accumulates alongside `quantity` in the same transaction, so **weighted average unit cost is simply `value_aed / quantity`** per product+location+bucket.
- Value moves with quantity through the buckets: purchase entry adds PENDING value; collection moves it to PHYSICAL; shipping moves it to IN_TRANSIT at the source's carrying average and into destination PHYSICAL on receipt; sales and adjustments remove value at the location's carrying average; refunds remove value at the original purchase line rate.
- Shipping costs never enter `value_aed` (decision: purchase rates only).
- Valuation summary/detail endpoints read `stock_balances` directly; `rebuild_stock_balances` reconciles values the same way it reconciles quantities, so valuation correctness is covered by the same drift check.
- Endpoints and exports live in `reports` behind an admin-only permission class; exports reuse the standard Celery Excel/PDF pipeline.

### 5.4 Posting service

All writes flow through one narrow API in `inventory/services.py`:

```python
post_event(
    txn_type=...,            # enum from 5.2
    source=record,           # business record (purchase line, shipment receipt, ...)
    movements=[Movement(product, location, bucket, qty_in|qty_out, aed=..., gst=...)],
)  # inside transaction.atomic(); writes ledger rows, locks+updates balances, writes audit
```

Rules enforced here, nowhere else:

- Runs inside `transaction.atomic()` together with the business-record write — partial updates are impossible (SRS §7.3).
- Validates refundable/collectable/receivable quantities against current state before posting.
- Negative PHYSICAL stock on sale/shipment is allowed only when the API call carries an explicit `confirm_negative=true` flag (the UI shows the confirmation dialog; the API enforces it).
- Every post writes the matching audit entry in the same transaction.

## 6. API Design (Django REST Framework)

- URL shape: `/api/v1/<module>/...` — e.g. `/api/v1/purchases/`, `/api/v1/purchases/{id}/refunds/`, `/api/v1/shipments/{id}/receipts/`, `/api/v1/stock/balances/`, `/api/v1/stock/ledger/`.
- Business actions that post ledger entries are **explicit sub-resources or actions**, not bare PATCHes: collections, refunds, receipts, and status transitions each have their own endpoint so validation and audit are unambiguous.
- **Authentication**: Django session cookies + CSRF (DRF `SessionAuthentication`). Same-origin via the proxy makes this the simplest secure option; login/logout events feed the audit log directly. Token/JWT can be added later if a mobile app appears — nothing in the design depends on session auth.
- **Permissions**: one DRF permission class per module driven by a static `ROLE_MATRIX` mirroring SYSTEM_SPEC §6 (admin: all; purchase: purchases/collections/refunds/shipments/receiving + product create; sale: sales CRUD; viewer: read-only). Object-level checks are unnecessary in v1 (all users see all data).
- **Filtering/search/pagination**: `django-filter` filtersets + search on every list endpoint; cursor-free page-number pagination; list endpoints return a `totals` object alongside `results` for the quick-totals bars (FR-103).
- **OpenAPI schema** via `drf-spectacular`; the frontend generates its typed client from it, so backend and frontend cannot silently drift.

## 7. Audit Implementation

- `audits` middleware stores request context (user, IP, user agent, session key) in a contextvar.
- Services write audit rows explicitly, in-transaction, with `before`/`after` JSON snapshots for updates/deletes (signals alone are not used — they miss bulk operations and can't capture business intent like "refund" vs generic "update").
- Login/logout hook into Django's auth signals.
- Audit rows are append-only; no API mutates them.

## 8. Reports and Exports

- Every SRS §5 report is one `Report` in a single registry (`apps/reports/builders.py`): a declared filter vocabulary plus a build function returning sections of plain-value rows. The JSON endpoint, the Excel renderer, and the PDF renderer all consume the same result, so exports always match the on-screen dataset (FR-098).
- The GST report queries purchase lines joined to their refund lines, computing net quantity and net GST per line from the values frozen at entry/refund time (SRS §5.1) — never by summing `gst_value` across ledger rows (bucket-movement rows carry GST for bookkeeping only).
- **Exports run in Celery**: the export endpoint validates filters, records an `ExportJob` (report key + params + format), enqueues a task, and returns the job; the task replays the report build and renders Excel (`openpyxl`) or PDF (ReportLab, clean light theme per FR-101), and the UI polls/downloads. ReportLab replaced the originally planned WeasyPrint because it is pure Python — no pango/cairo system libraries, so the slim Docker image and the host test venv both work unchanged.
- Export files are stored **outside** `MEDIA_ROOT` (`EXPORTS_ROOT`, swapped to a private S3 prefix in deployment): nginx serves `/media` publicly, but exports — including admin-only valuation files (FR-116/FR-123) — must only be reachable through the authenticated download endpoint. Users see their own jobs; admins see all.

## 9. Frontend (Next.js + TypeScript)

- **App Router** with route groups per module mirroring the main navigation (SYSTEM_SPEC §3): `app/(dashboard)`, `app/purchases`, `app/purchase-collection`, `app/purchase-refunds`, `app/shipments`, `app/sales`, `app/stock-ledger`, `app/reports`, `app/settings`, `app/audit`, …
- **Data layer**: TanStack Query against the generated OpenAPI client; server components for initial loads, client components for interactive forms/tables.
- **UI kit**: Tailwind CSS + shadcn/ui. Shared building blocks: `DataTable` (search, filters, sort, pagination, quick-totals header — every list page reuses it), `EntityForm` (react-hook-form + zod schemas derived from API types), `WarningDialog` (negative stock / over-receiving confirmations), status and mismatch-highlight badges.
- **Auth**: session cookie; a lightweight `/api/v1/auth/me` call gates routes and drives role-based menu/action visibility (server remains the enforcement point).

### 9.1 Theming (FR-124…FR-127)

- All colors are **semantic design tokens** (CSS variables: `--background`, `--surface`, `--primary`, `--warning`, `--mismatch`, chart series, …) following the shadcn/ui theming model. Components never reference raw colors, only tokens.
- Light theme is the default: clean, modern, professional.
- Dark mode is a **separately designed token set** — elevated surfaces, adjusted saturation, and contrast-checked status/warning/mismatch colors — not an inversion. Charts and badges get their own dark values.
- `next-themes` manages switching: system preference on first visit, manual toggle, preference persisted per user (profile field, so it follows the user across devices).
- Both themes are enforced in review: every new page/component ships with both token sets exercised (Playwright screenshots run in both themes).

### 9.2 Responsiveness (SRS §7.6)

- Target viewports, tested explicitly: large desktop (≥1440), small laptop (~1280×800), iPad landscape/portrait (1024/768), small tablets (~600), mobile phones (≥360).
- The app shell adapts: full sidebar on desktop, collapsible rail on tablets, drawer on small screens.
- `DataTable` degrades by priority: column sets per breakpoint (declared per page), horizontal scroll only as a last resort inside the table container — never page-level horizontal scroll.
- Forms use a responsive grid (multi-column on desktop, single column on tablets/phones); dashboards reflow card grids.
- Playwright smoke flows run against the desktop, iPad, and small-tablet viewports.

### 9.3 Time Handling (FR-128)

- Postgres and Django store all timestamps in UTC (`USE_TZ = True`).
- A single `BUSINESS_TZ = Asia/Dubai` constant drives every "today" boundary: dashboard cards, default date-filter ranges, daily report grouping, and past-cutoff snapshots. Helpers `business_today()` / `business_day_bounds(date)` are the only way services and reports compute day windows — no ad-hoc `date.today()` calls.
- The frontend displays dates in Dubai time via the generated client's serializers; user-entered dates (purchase date, sale date) are calendar dates, stored as `DATE` and unaffected by time zones.

## 10. Files and Storage

- `attachments.FileAttachment` stores metadata + storage key, generic-linked to purchases/sales/exports.
- Django storage backend abstraction: `FileSystemStorage` (`MEDIA_ROOT=media/uploads/`) in dev, `django-storages` S3 backend in deployment. Business code never touches paths directly, so the swap is configuration only (FR-105).
- Upload validation: images + PDF only, size cap, content-type sniffing.

## 11. Local Environment (Docker Compose)

`deployment/docker-compose.yml` runs: `postgres`, `redis`, `backend` (Django dev server), `worker` (Celery), `frontend` (Next.js dev), `nginx` (single origin at `http://localhost:8080`). Hot reload mounts for both apps. A `make seed` target loads demo master data (locations, currencies, GST rates) for development.

## 12. Deployment Sketch (post-local-testing)

Single EC2 instance: the same Compose stack with prod settings — gunicorn behind nginx, TLS, Next.js production build, S3 bucket for media/exports, RDS optional later (Postgres can start on the instance). Backups: `pg_dump` to S3 on a schedule (details deferred per open item). Finalized after local acceptance, per SRS §9.4.

## 13. Testing Strategy

- **The ledger mapping table (5.2) is the test spec**: every row gets service-level tests, including partials (partial collection, partial refund, partial receipt), reversals, edits, and over/negative flows.
- pytest + pytest-django; factory_boy for fixtures. Business-flow tests named per AGENTS.md (`purchase-refund`, `shipment-receiving`, …).
- A reconciliation test asserts `rebuild_stock_balances` produces identical balances after every scenario — this catches any service that forgets a ledger row.
- API tests cover the permission matrix per role per endpoint.
- Frontend: Playwright smoke flows for the critical paths (purchase → collect → ship → receive → sell) once the UI stabilizes.

## 14. Key Decisions (ADR summary)

| # | Decision | Rationale |
| --- | --- | --- |
| 1 | Monorepo (`src/backend`, `src/frontend`) | One deployable product, one PR per feature, matches existing repo structure |
| 2 | Append-only ledger + materialized `stock_balances` updated in-transaction | Ledger stays the source of truth (SRS §8.1) while list pages/dashboard stay fast; drift is detectable and repairable via rebuild |
| 3 | Single `post_event` service as the only ledger writer | One place enforces transactions, validation, locking, and audit — impossible to forget in a new feature |
| 4 | Session-cookie auth behind a single origin | Simplest correct option for a first-party web app; avoids token storage pitfalls; login audit for free |
| 5 | Statuses always computed, never stored as user input | Matches SYSTEM_SPEC §8; eliminates status-drift bugs by construction |
| 6 | Explicit in-transaction audit writes (not signals) | Captures business intent and before/after reliably, including bulk paths |
| 7 | Values frozen at entry (AED conversion, GST) | Historical records must not change when rates change; refunds reverse the frozen values |
| 8 | OpenAPI-generated typed frontend client | Backend/frontend contracts enforced at build time |
| 9 | Valuation via `value_aed` on `stock_balances` (value follows quantity) | Weighted average cost falls out of the existing ledger/balance mechanism — no separate costing subsystem to drift; reconciled by the same rebuild check |
| 10 | Stock valuation admin-only at the permission layer | Client requirement; enforced server-side, not just hidden in the UI |
| 11 | Semantic color tokens with separately designed light/dark palettes | Professional dark mode (not inversion) becomes a token-set swap; both themes testable by screenshot |
| 12 | Single business time zone (Asia/Dubai), UTC storage | Locations span five time zones; one authoritative "today" keeps dashboards and daily reports unambiguous |

## 15. Implementation Phases

Each phase ends with working, tested software; stock correctness is built and verified before anything depends on it.

| Phase | Scope | Exit criteria |
| --- | --- | --- |
| M0 | Repo scaffolding: Django project + apps, Next.js app, Docker Compose, CI (lint + tests) | `docker compose up` serves both apps through nginx |
| M1 | `accounts` + `masterdata` + `products`: auth, roles, settings pages, product master, audit foundation | Login, role matrix enforced, master data CRUD audited |
| M2 | `inventory` core + purchases + collection | Purchase → pending → collect flows post correct ledger entries; balances reconcile |
| M3 | Purchase refunds/cancellations | Partial line refunds reverse stock/AED/GST; originals traceable |
| M4 | Shipments + receiving (incl. Dubai→Karachi) | Partial/over-receiving, cancellation reversals, in-transit tracking |
| M5 | Sales + stock adjustments | Negative-stock confirmation flow; adjustments audited |
| M6 | Dashboard + reports + Excel/PDF exports (Celery) + admin stock valuation | All SRS §5 reports filterable and exportable; past-cutoff dashboard; valuation reconciles with ledger |
| M7 | Hardening: audit review, mismatch highlighting, responsive pass, seed data, acceptance test run | SRS §12 acceptance criteria pass locally |
| M8 | AWS deployment (EC2 + S3), cloud backups — **deferred/future** (undertaken only if the client is satisfied after the M9 offline trial) | Production instance live; backup job running |
| M9 | Offline/local production use: fresh installation on a separate Windows machine for a three-month, single-Admin trial — no Mac test data and no cloud dependency. Production process managers (gunicorn + `next build`/`next start`), persistent local storage for DB/media/exports, `restart: unless-stopped`, a Windows Desktop shortcut, and verified PostgreSQL + uploaded-media backups every 12 hours with 120-day retention and documented Windows restore | Fresh database contains seeded settings but no business transactions; stack runs with `DEBUG=False`, the Admin completes the daily flow from a Desktop shortcut, uploads persist, and timestamp-matched database/media backup pairs can be restored |

> **Execution order note (2026-07-23):** AWS deployment (M8) is postponed. The client will run the system **offline/locally (M9) first** for a trial period; AWS deployment (M8) proceeds only if that trial is satisfactory. So although M8 carries the lower number, **M9 is the immediate next phase** and M8 follows it (much of M9 — prod settings, gunicorn/Next build, persistent volumes, backup/restore procedure — carries directly into M8, where local disk/`pg_dump` is swapped for S3 and a cloud instance).
