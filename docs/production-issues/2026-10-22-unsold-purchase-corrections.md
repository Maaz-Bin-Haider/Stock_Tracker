# Corrections to saved purchase invoices before sale

Date: 2026-10-22. Historical focused investigation of the original behavior.
The subsequent [local fix and verification](2026-10-22-purchase-corrections-local-fix.md)
implements the prioritized corrections. Production behavior is unchanged.

## User clarification and first priority

The first requested fix is to allow these corrections on a saved purchase invoice
whose products have not been sold:

1. Select the correct product when the wrong product was entered.
2. Correct a product line's unit price.
3. Remove a mistakenly entered product line while keeping the rest of the invoice.

Collection alone should not prevent those corrections. This request includes goods
entered as already collected when the invoice is first saved.

"Product name" is interpreted here as the selected product on one invoice line.
Changing a name in Product Master is a different operation: all invoices referencing
that shared product then display the renamed product.

This narrows the broader 2026-10-21 investigation. The other editing defects remain
documented, but these three unsold-stock corrections take priority. No application
fix or production deployment was performed in this follow-up.

## Confirmed cause

The existing lock is based on collected/refunded quantity. It never checks whether
the purchased product has been sold.

- Frontend `purchases/page.tsx:501` sets `locked` whenever an existing line has
  `collected > 0`; product selection and unit price are disabled.
- Frontend `purchases/page.tsx:630` hides Remove for locked lines, and also for
  the last remaining line in an invoice.
- Backend `purchases/services.py:407` rejects product/pricing changes when a line
  has collected or refunded quantity. The same restriction applies to Admin.
- Backend `purchases/services.py:472` rejects removing such a line.
- `create_purchase` records "Collected now" through the ordinary collection
  service before returning. The invoice can therefore be locked on its first save.
- Quantity changes take another path, retaining a minimum of collected quantity
  plus cancelled pending quantity. This accounts for the observed editable Qty.

The basic case is therefore confirmed: even without sales, shipments, refunds, or
adjustments, received stock makes these three corrections unavailable.

## Focused local reproduction

All scenarios used a new local PostgreSQL 16 cluster, synthetic accounts/products,
and a two-line invoice. The second line remained present during removal tests,
so failure was not caused by the editor's last-line restriction.

Each ordinary scenario explicitly asserted:

- no Sale records;
- no SaleLine records;
- no SALE stock-ledger entries;
- no shipments, refunds, or stock adjustments.

| Synthetic state of the first line | Change selected product | Change unit price | Remove line | Increase quantity |
| --- | --- | --- | --- | --- |
| 10 purchased, none collected | Succeeds | Succeeds | Succeeds | Succeeds |
| 10 purchased, 4 collected at initial save | Rejected | Rejected | Rejected | Succeeds |
| 10 purchased, all 10 collected at initial save | Rejected | Rejected | Rejected | Succeeds |
| 10 purchased, 4 collected later | Rejected | Rejected | Rejected | Succeeds |
| 10 purchased, all 10 collected later | Rejected | Rejected | Rejected | Succeeds |

API rejection was HTTP 400. Failed corrections left the invoice, ledger, and
audit-record count unchanged. The tests ran as Admin; insufficient permissions
were not the cause. A separate case confirmed the same lock at a location where
sales are not enabled.

Three additional tests shipped 3 units without creating a sale. All three
corrections were still rejected. This confirms that the current lock does not
distinguish unsold goods at the purchase location from unsold goods in transit.

## What the correction must update

The current edit service can reverse/repost pending stock. It has no equivalent
edit path for the already-collected part of a line. Enabling the controls alone
still reaches the backend rejection; removing only the backend guard allows
invoice/stock inconsistencies.

Two controlled experiments temporarily bypassed the pricing guard inside local
tests only, without changing application source:

- Ten fully collected units at AUD 100 with an exchange rate of 2.4 had AED 2,400
  of physical stock. Changing the line to AUD 120 updated its invoice total to
  AED 2,880, but physical stock value stayed AED 2,400.
- Changing the selected product on a fully collected line updated the invoice's
  product ID, but all ten physical units remained under the original product.

These are consequences of an incomplete hypothetical fix, not corruptions caused
by the current guarded application. The present guards prevent those edits.

For the requested unsold-stock behavior, the corrected service needs these effects:

| Correction | Required inventory and document effects |
| --- | --- |
| Wrong product selection | Reverse affected pending/physical quantities and values under the old product; post them under the correct product; retain collection quantities/locations and an audit trail of the original selection. |
| Wrong unit price | Recalculate the line's frozen AED/GST figures and correct pending/physical values for the affected unsold stock; quantities stay the same. |
| Remove a line | Reverse that line's applicable pending/physical stock and tax/value contribution, soft-delete the line, preserve the original records and audit history, and leave other invoice lines intact. |

Example, before any downstream movement: 10 units at AUD 100, exchange rate 2.4,
with 4 collected and 6 pending, have AED 960 physical and AED 1,440 pending value.
Correcting the price to AUD 120 should produce AED 1,152 physical and AED 1,728
pending value. Correcting the product should move both buckets' quantities to the
correct product. Removing the erroneous line should reverse both buckets for that
line rather than requiring a fabricated supplier refund.

GST remains inclusive and inventory retains the full price paid. Original ledger
rows must remain traceable; corrections use new ledger entries in the same
transaction as the invoice change and audit record.

## Dependencies the implementation must account for

### Collection history

Collections point to purchase lines and original collection ledger postings. A
correction must preserve valid later operations, including partial collection,
undoing a collection, refunds, subsequent edits, and whole-invoice deletion.

In particular, `delete_collection` currently reverses its collection ledger entries.
A new price/product correction must not leave that later undo restoring the old
product or old cost incorrectly. Changing only the current balance would not cover
this lifecycle.

### Unsold goods may already have moved

No sale does not prove the goods are still at the purchase/collection location.
Shipments, receiving, refunds, and adjustments can change quantities or carrying
values before sale. The implementation needs dependency-aware correction handling,
or an explicit, specific rejection for a dependency it cannot yet reconcile.

The clean collected-but-unmoved case is unambiguous and already fails today. It
must be included in the first fix rather than left locked solely by collection.

### Sales currently use pooled stock

`SaleLine` stores sale, product, location through the sale header, and quantity.
It has no purchase-line, invoice, or lot allocation. Shipments likewise select
products from the location's pooled stock rather than allocating purchase lines.

Consequently, a future "this invoice has no sold units" rule cannot be implemented
by following a direct invoice-to-sale relationship. When several invoices share
the same product and some pooled stock has sold, exact invoice-level attribution
is unavailable. Eligibility must use a documented conservative dependency rule or
explicit allocation; it must not guess that the invoice is unsold simply because
there is no direct sale foreign key.

Source: `apps/sales/models.py:33`, `apps/sales/services.py:57`,
`apps/shipments/models.py:86`, `apps/purchases/services.py:579`.

## First-fix acceptance cases

- Correct a selected product on a saved, partially and fully collected invoice
  with no sales/downstream consumption; both stock buckets and reports agree.
- Correct unit price in those states; pending and physical quantities remain
  unchanged while AED cost, GST, valuation, and invoice totals agree.
- Remove one erroneous collected line while retaining the invoice and other lines;
  its stock is reversed and its original history remains traceable.
- Support collection at initial save and collection recorded later identically.
- Preserve normal subsequent collection, collection undo, refunds, repeated edits,
  and invoice deletion after a correction.
- Validate dependencies on the server, including concurrent sale/dispatch activity;
  disabling/enabling fields in the browser is not the enforcement boundary.
- Keep sale-dependent/downstream cases explicit and tested; do not rewrite old
  ledger rows or globally rename products to correct a single invoice selection.

## Validation and artifacts

All **27 focused diagnostic cases passed** against the unchanged application.
These assert current restrictions and the two isolated guard-bypass demonstrations;
they are evidence for the fix design, not passing tests for a completed fix.

Files are retained in gitignored
`data/exports/unsold-purchase-audit-2026-10-22/`: synthetic fixtures, diagnostic
source, JUnit results, and rerun instructions. No production connection or production
data was used in this follow-up. No application source file was changed.
