# SwissTech Stock Tracker Project Context

This root-level context file is maintained so future work can continue from the latest project state without reading every document first.

## Current Repository

- Repository folder: `Stock_Tracker`
- Purpose: plan and build a professional web-based inventory system to replace the current spreadsheet workflow.
- Original workbook reference: `data/source/stock_tracker_original.xlsx`
- Implementation status: phases M0–M3 complete (scaffolding; auth/master data/products/audit; stock ledger + purchases + collection; purchase refunds/cancellations). Next: M4 shipments + receiving.

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

- Backup schedule, retention, and restore process are deferred.
- Final report columns can be refined after business review.
- Final AWS architecture will be decided after local testing, with S3-compatible storage expected for uploaded invoices and generated reports.

## Documentation Maintenance Rule

After each project change, update this file with:

- what changed
- which documents/files were updated
- any new open items
- the next recommended step

If a change affects requirements, workflows, permissions, entities, database design, or reports, also update the matching detailed document under `docs/`.

## Change Log

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

**TODO (next session): Phase M4 — shipments + receiving (incl. Dubai→Karachi).** M0–M3 are done and verified. Per `TECHNICAL_ARCHITECTURE.md` §5.2/§15 and SYSTEM_SPEC §11:

- [ ] `Shipment` + `ShipmentLine` + receipt models; header fields per FR-058 (shipment type distinguishes the Dubai→Karachi transfer flow), shipping cost recorded but excluded from stock value (FR-119).
- [ ] Statuses computed, never stored: draft / shipped / partially received / fully received / cancelled (FR-060).
- [ ] Ledger rows: ship → −PHYSICAL @ from-location, +IN_TRANSIT @ to-location; receipt → −IN_TRANSIT/+PHYSICAL @ to-location; cancel → reversal of unreceived quantities. Value moves at the source location's carrying average cost from `stock_balances` (§5.3.1) — the first flow consuming carrying value rather than line-frozen values.
- [ ] Negative-stock confirmation on shipping (FR-083); over-receiving allowed with warning, IN_TRANSIT may go negative for the line, flag `over_received` drives highlighting (§5.2 note, FR-084/FR-085).
- [ ] Endpoints per §6: `/api/v1/shipments/`, `/api/v1/shipments/{id}/receipts/`; admin + purchase users write (Batch 9 decision).
- [ ] Frontend: Shipments page + receiving flow; in-transit visibility.
- [ ] Tests: ship/receive/partial/over-receive/cancel, Dubai→Karachi, valuation-at-carrying-average, reconciliation.

Deferred small items (fold into a later milestone): `app_settings` model/endpoint (SYSTEM_SPEC §24 — no concrete requirement yet), OpenAPI-generated typed frontend client + TanStack Query/shadcn DataTable adoption (TECHNICAL_ARCHITECTURE §6/§9), file attachments app (FR-035/FR-073), pagination controls on the new list pages (they currently show the first API page).
