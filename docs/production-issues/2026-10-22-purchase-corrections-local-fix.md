# Saved purchase corrections: local fix and verification

Date: 2026-10-22. Implemented and verified locally with synthetic data only.
Production has not been accessed or modified during implementation. Deployment
requires the user's explicit authorization.

Subsequent status: explicitly authorized production deployment completed on
2026-10-22. See the [deployment record](2026-10-22-purchase-corrections-deployment.md).
The local results below document the implementation phase.

## Result and agreed boundary

Admin and Purchase users can change an invoice line's selected product and unit
price, or remove an erroneous line, after partial/full collection when that stock
has not moved further. Collection at entry and later collection are both supported.
At least one invoice line must remain. This changes the invoice's product selection;
it does not rename the shared Product Master.

The user chose: block a dependent line with a clear reason for now; allow corrections
to received stock that has not moved further. The API and editor enforce this for
sales, shipments/receipts, open draft shipments, refunds/cancellations, and stock
adjustments. Other eligible lines on the invoice remain editable. Currency,
exchange rate, and GST remain fixed after collection in this first change.

Stock is pooled without purchase-lot allocation. Later movement of the same SKU at
any collection location is conservatively treated as a dependency, including
historical reversed activity and activity attributable to another invoice. Missing
history or unavailable physical quantity/value also blocks correction for review.

## Implementation

- `purchases/corrections.py` exposes eligibility and performs correction postings.
  Reverse affected collections' current net contribution, reverse purchase basis,
  repost corrected basis, and replay the original collection quantities/locations.
  Original ledger rows and collection identities remain unchanged.
- Removal reverses only the removed line's contributions and soft-deletes that
  line. Collection undo uses current net contributions, so it cannot revive removed
  or superseded stock. Further collection and refunds use corrected costs.
- Domain stock writes acquire one transaction-scoped PostgreSQL advisory lock
  before validation/costing. This prevents eligibility checks racing a sale or
  dispatch. It serializes stock writes for the current single-company system,
  trading throughput for correctness. Existing balance row locks remain.
- The API returns per-line `can_correct` and `correction_block_reason`, rechecks
  eligibility under the write lock, rejects empty/duplicate line submissions, and
  returns active lines after updates. The editor enables eligible controls, shows
  collected/minimum quantities, and preserves historical selected dropdown values.
- Requirements, user guide, business flow, technical architecture, project context,
  and the [implementation plan](../architecture/unsold-purchase-corrections-plan.md)
  are updated. No database migration is required.

## Verification

All data is synthetic. PostgreSQL 16 runs in a dedicated tmpfs container with its
port bound to loopback; pytest uses its separate test database. The local browser
stack runs at `http://127.0.0.1:18080` using the source checkout and a seeded sample
database, without production environment files or credentials.

| Check | Result |
| --- | --- |
| Full backend regression suite | 285 passed, including 58 correction cases |
| Final correction suite after reversal-link refinement and report tests | 60 passed |
| Frontend tests | 27 passed |
| Frontend TypeScript, ESLint, production build | Passed; Next.js 15.5.24, 19 routes |
| Backend Ruff | Passed |
| Migration dry run against synthetic DB | No changes detected |
| Browser: partial collection product + price correction | Saved; 4 collected / 6 pending preserved |
| Browser: fully collected line price correction | Saved; 10 collected / 0 pending preserved |
| Browser: remove received line | Saved; other line retained, removed stock reversed |
| Browser: shipped line | Product/price/removal blocked with shipment reason; other line editable |

The full suite preceded a small `reversal_of` traceability refinement; the final
60-case suite verifies that final code and adds current report checks. Tests cover
Admin/Purchase roles, collection at entry/later, partial/full receipt, immutable
history, repeated corrections with linear ledger growth, collection undo,
multi-location rounding, refunds/undo after correction, parent deletion, dependent
line rejection/rollback, role denial, empty/duplicate lines, and frozen rates.
Two real PostgreSQL multi-connection race tests prove sale-first blocks correction
and correction-first makes the waiting sale use the corrected carrying cost.
Reconciliation compares balances to ledger sums without repairing them.

Current purchase, pending, GST, and valuation report tests verify the corrected SKU,
price, physical/pending value, and removed-line exclusion. For 10 units at AUD 120
and FX 2.4, AED value is 2,880 and inclusive GST is AED 261.82; four collected units
carry AED 1,152 and six pending units AED 1,728.

Evidence is gitignored under `data/exports/unsold-purchase-audit-2026-10-22/`:
`implementation-backend-results.xml`, `implementation-corrections-final.xml`,
`local-corrected-invoice.png`, `local-removed-line.png`, and
`local-dependent-line-blocked.png`. `local-preview/` retains Compose and seed
sources. Earlier 27-case diagnostics describe the old restrictions and are not
regression expectations for the fix.

## Remaining work

Review the local change, then obtain explicit production authorization before any
transfer, rebuild, migration, restart, or production data operation. Before an
authorized deployment, follow the existing backup/release runbook and its current
ARM64 build/security checks. Deploy backend and frontend together; after corrected
events exist, an old backend does not understand the new collection undo behavior,
so do not roll back application code alone without reviewing those events.

Other findings from the broader 2026-10-21 investigation remain deferred, including
header-only PATCH handling and collected-now quantities on newly added edit lines.
This local preview is focused on purchase corrections; workers, uploaded files,
exports, and a full deployment/recovery drill were not exercised here.
