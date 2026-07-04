# SwissTech Stock Tracker Project Context

This root-level context file is maintained so future work can continue from the latest project state without reading every document first.

## Current Repository

- Repository folder: `Stock_Tracker`
- Purpose: plan and build a professional web-based inventory system to replace the current spreadsheet workflow.
- Original workbook reference: `data/source/stock_tracker_original.xlsx`
- Application implementation has not started yet.

## Current Project Structure

```text
Stock_Tracker/
├── README.md
├── PROJECT_CONTEXT.md
├── data/
│   ├── source/
│   │   └── stock_tracker_original.xlsx
│   └── exports/
├── deployment/
├── docs/
│   ├── architecture/
│   │   └── SYSTEM_DIAGRAMS.md
│   │   └── diagrams/pdf/
│   ├── business-flow/
│   │   └── EXECUTION_FLOW_NON_TECHNICAL.md
│   └── requirements/
│       ├── PROJECT_CONTEXT.md
│       ├── SYSTEM_SPEC.md
│       └── SRS.md
├── scripts/
├── src/
└── tests/
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

### 2026-07-04

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

Review `docs/architecture/TECHNICAL_ARCHITECTURE.md`, then begin phase M0: scaffold the Django project and apps, the Next.js app, and the Docker Compose local environment.
