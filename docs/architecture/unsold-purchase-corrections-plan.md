# Unsold purchase corrections implementation plan

Date: 2026-10-22. Local implementation only; production deployment requires the
user's explicit authorization.

## Agreed scope

- Permit changing the selected product, changing unit price, and removing a line
  on an invoice whose collected stock has no downstream dependencies.
- Include collection at entry, partial collection, multiple collection locations,
  and collection recorded later.
- Block a dependent line with a clear reason when shipments, refunds,
  adjustments, or sales affect it. Other eligible lines remain editable.
- Retain existing currency/exchange/GST restrictions on collected lines in this
  first change. Keep at least one product line on an invoice.
- No production SSH, update, migration, data repair, or restart during this work.

## Design

1. Expose correction eligibility and its explanation per purchase line. Enforce
   the same decision in the transaction that performs the correction.
2. Reverse each affected collection's current net ledger contribution, then the
   purchase line's pending basis. Repost the corrected line and replay existing
   collections with their original quantities/locations. Retain original ledger
   and audit history; no schema migration is planned.
3. For removal, reverse those contributions and soft-delete only that invoice
   line. Later collection undo must not resurrect removed stock.
4. Record collection correction postings against the collection's source identity.
   Collection undo reverses its current net contribution, including corrections,
   rather than replaying all historical original/reversal rows individually.
5. Serialize stock-writing domain transactions with a transaction-scoped PostgreSQL
   advisory lock before eligibility checks and costing. Existing balance row locks
   remain. This single-company initial implementation trades parallel stock writes
   for straightforward correctness across correction/sale/dispatch races.
6. Use conservative product/location dependency checks because sales/shipments
   have no purchase-lot allocation. Surface the actual blocking activity.
7. Enable product/price/removal in the editor only when eligible. Preserve selected
   historical references in option lists and return active lines after updates.

## Work checklist

- [x] Add behavior tests for eligible corrections and dependency blocks.
- [x] Implement stock serialization, contribution reversal/replay, and safe undo.
- [x] Add eligibility to the API and update the purchase editor.
- [x] Verify money/GST/stock, repeat edits, multi-location collection, removal,
      collection undo, refunds, parent deletion, role rules, and concurrency.
- [x] Run the backend suite, frontend tests/lint/types/build, and local browser checks.
- [x] Update requirements, user guide, technical notes, and project context with
      the verified result and production boundary.

## Production boundary

Completing this plan produces a locally verified change for review. It does not
authorize deployment or any change to production data.

## Subsequent authorized deployment

The user subsequently explicitly authorized EC2 connection, backup, and production
deployment. The fix was deployed on 2026-10-22 after a new 287-case full suite on
the exact ARM64 image and a final backup. Read-only before/after table hashes
matched. See [deployment record](../production-issues/2026-10-22-purchase-corrections-deployment.md).
