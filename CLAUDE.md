# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project State

This is the planning/documentation phase of the SwissTech Stock Tracker — a web-based inventory system replacing a spreadsheet workflow (`data/source/stock_tracker_original.xlsx`). **No application code exists yet**; `src/`, `tests/`, `scripts/`, and `deployment/` are empty placeholders. There are no build, lint, or test commands until implementation starts.

Decided tech stack (see `docs/requirements/SYSTEM_SPEC.md` §23): Django + Django REST Framework, PostgreSQL, Next.js/TypeScript frontend with Tailwind CSS (shadcn/ui or Radix UI), Celery + Redis for background jobs, Docker Compose locally. File uploads use local Django media in development and S3-compatible storage in deployment (DB stores metadata/paths only, never file contents). Target deployment is a single EC2 instance on AWS after local testing.

## Document Map

Read in this order of authority when documents seem to conflict:

- `docs/requirements/SRS.md` — formal requirements (FR-001 … FR-114), acceptance criteria, out-of-scope list
- `docs/requirements/SYSTEM_SPEC.md` — implementation-oriented spec: permission matrix, field lists, report columns, suggested DB tables, implementation notes
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
