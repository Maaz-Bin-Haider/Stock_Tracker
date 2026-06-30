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
- `docs/architecture/diagrams/pdf/`: PDF exports of individual diagrams rendered from the Mermaid diagram source.

## Current Requirements Summary

- Web-based inventory system.
- Single company for now, future multi-company design possible.
- Desktop/web first, responsive for mobile.
- AWS deployment later after local testing, initially possible on one EC2 instance.
- Stock ledger is the source of truth.
- Purchases can contain multiple product lines.
- Purchase collection is separate from purchase entry.
- Purchase refunds/cancellations happen from a separate page by selecting the original invoice and product line.
- Refunds/cancellations use reversal entries and must reverse stock and GST where relevant.
- Sales happen only from Dubai and Karachi.
- Shipments track source stock, in-transit stock, destination receiving, partial receiving, and over-receiving warnings.
- GST report is product-line based and uses net quantity after refund/cancellation.
- All important user actions must be audited.

## Roles

- Admin: full access.
- Purchase user: purchases, purchase collection, purchase refunds/cancellations, and product creation during purchase flow.
- Sale user: sales only for create/update/delete, with view access to system data.
- Viewer: read-only.

## Open Items

- Confirm who can create, update, and delete shipments. Current safe default is admin-only.
- Backup schedule, retention, and restore process are deferred.
- Final report columns can be refined after business review.
- Final AWS architecture will be decided after local testing.

## Documentation Maintenance Rule

After each project change, update this file with:

- what changed
- which documents/files were updated
- any new open items
- the next recommended step

If a change affects requirements, workflows, permissions, entities, database design, or reports, also update the matching detailed document under `docs/`.

## Change Log

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

## Next Recommended Step

Review and confirm shipment permissions, then proceed to implementation planning and technology stack selection.
