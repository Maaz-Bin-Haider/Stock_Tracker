# Repository Guidelines

## Project Structure & Module Organization

This repository is the planning and documentation base for the SwissTech Stock Tracker, a web-based inventory system intended to replace the current spreadsheet workflow. Key paths:

- `README.md` and `PROJECT_CONTEXT.md`: top-level overview, current status, open items, and change log.
- `docs/requirements/`: formal requirements, SRS, and implementation-oriented system specification.
- `docs/business-flow/`: non-technical workflow documentation.
- `docs/architecture/`: system diagrams and architecture notes; PDF diagram exports live in `docs/architecture/diagrams/pdf/`.
- `data/source/`: original workbook reference, currently `stock_tracker_original.xlsx`.
- `data/exports/`: generated exports during development or testing.
- `src/`, `tests/`, `scripts/`, and `deployment/`: reserved for implementation, automated tests, utilities, and deployment assets.

## Build, Test, and Development Commands

No application stack is committed yet, so there are currently no build or test commands. When adding implementation code, also add the matching manifest and document commands in `README.md`, for example:

- `npm run dev`: start a local web app.
- `npm test`: run automated tests.
- `npm run build`: produce a production build.

Until then, validate documentation changes by checking links, headings, and paths manually.

## Coding Style & Naming Conventions

Keep Markdown concise and structured with sentence-case headings where possible. Use fenced code blocks for directory trees and commands. Prefer descriptive, kebab-case names for documentation files and generated assets, matching existing names such as `main-er-diagram.pdf`. When source code is introduced, follow the formatter and lint rules defined by that stack and commit the relevant configuration files.

## Testing Guidelines

Place future automated tests under `tests/`, mirroring the structure of `src/`. Name tests after the behavior being verified, such as `purchase-refund.test.*` or `shipment-receiving.test.*`. Inventory, GST, shipment, refund, and audit-log behavior should receive focused coverage because they define core business correctness.

## Commit & Pull Request Guidelines

Recent commits use short imperative messages, for example `Add ER diagram PDF`. Continue that style: `Add shipment tests`, `Update SRS report fields`, or `Fix purchase refund workflow`. Pull requests should include a clear summary, affected documents or modules, linked issue or requirement when available, and screenshots or generated PDFs for visual diagram changes.

## Documentation Maintenance

After each meaningful change, update `PROJECT_CONTEXT.md` with what changed, files updated, new open items, and the next recommended step. If requirements, workflows, permissions, entities, database design, or reports change, update the matching file under `docs/`.
