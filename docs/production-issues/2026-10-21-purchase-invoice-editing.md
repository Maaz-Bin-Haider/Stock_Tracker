# Purchase invoice editing investigation

Date: 2026-10-21. Investigation only: no application fix or deployment performed.

## Conclusion

Purchase editing has deliberate restrictions and several independently reproducible
defects. The main reason product, unit price, currency, exchange rate, and GST become
uneditable is a business-service lock once a line has collected or refunded quantity.
This applies to Admin as well as Purchase users. Purchase location is locked as soon
as the invoice is created, even if nothing has been collected.

The UI does not consistently communicate or enforce these rules. It also has real
save failures involving inactive master records, and a new line's "Collected now"
value is silently ignored when adding it to an existing invoice. Partial API updates
have two separate unhandled errors.

This investigation establishes reproducible conditions. It does not identify which
particular production invoice prompted the report: no failing production update was
submitted and no production invoice was modified.

## Safety and evidence

- Local repository baseline: `408ee06`.
- SHA-256 hashes of the deployed backend purchase services, serializers, and views,
  and the frontend purchase page, exactly matched the local source.
- Production access was restricted to SSH/source inspection and SQL inside
  `BEGIN TRANSACTION READ ONLY`; `transaction_read_only` returned `on`.
- No production login, POST, PUT, PATCH, DELETE, migration, seed, restore, ledger
  rebuild, application restart, or data repair was performed.
- All editing attempts ran against a new local PostgreSQL 16 container with tmpfs
  storage and explicitly supplied synthetic credentials. No production backup,
  environment secret, or business data was copied into the test environment.
- A separate localhost UI/API/nginx stack was used to reproduce browser behavior.

## Field behavior matrix

"Collected/refunded" below means nonzero quantities on active collection/refund
records. Undoing those records can change the quantities and therefore the lock.

| Field/action | Uncollected, no refund | Collected or refunded | Notes |
| --- | --- | --- | --- |
| Invoice/reference | Editable | Editable | Whole-invoice validation can still block the save. |
| Purchase date | Editable | Editable | Explicit frozen line rates remain unchanged on ordinary UI saves. |
| Supplier | Editable | Editable | Inactive existing supplier disappears from the UI choices. |
| Invoice notes | Editable | Editable | Tested successfully in all five normal stock states. |
| Purchase location | Locked | Locked | UI disables it; backend rejects a different location. |
| Product | Editable | Locked | Refund-only UI incorrectly leaves it enabled. |
| Unit price | Editable | Locked | No Admin override. |
| Currency | Editable | Locked | No Admin override. |
| Exchange rate | Editable | Locked | Frozen rate is not changed by editing Settings. |
| GST percentage/rate reference | Editable through applicable API/UI fields | Locked | Existing UI exposes percentage, not the GST master-record reference. |
| Purchased quantity | Editable | Editable within floor | Must be positive and at least collected + cancelled-pending quantity. |
| Collected quantity | Separate workflow after entry | Separate workflow after entry | Existing-line `collected_qty` in an edit request is discarded. |
| Pending/refunded/net quantities, statuses, AED/GST totals | Calculated | Calculated | Read-only; supplied replacement values are ignored. |
| Line notes | API-editable | API-editable | The purchase editor renders no line-notes input. |
| Remove existing line | Allowed | Rejected | Collection/refund quantities protect the line. |
| Add a new line | Allowed | Allowed | New line remains pending; see the ignored collection defect. |

Example: purchase 10 units, collect 4, cancel 2 still-pending units. Purchased
quantity may be reduced to 6 but not 5. Returning received units does not subtract
them from the historical collected quantity used for this floor.

Rules are applied per line. An untouched collected line does not stop editing an
uncollected line on the same invoice. An invalid change to any one line rejects the
entire request, including otherwise valid header corrections.

Source: `src/backend/apps/purchases/services.py:323` (`update_purchase`), `:387`
(`PRICING_FIELDS`), `:390` (`_reprice_line`), and `:470` (`_remove_line`);
`src/frontend/app/(app)/purchases/page.tsx:468` and `:501`.

## Why those locks exist

Collection moves the original line's frozen AED cost from pending into physical
stock. Shipments and sales can then move or consume that carrying value. The edit
service only reverses and reposts the remaining pending balance; it does not
revalue collected stock and all downstream movements. Changing historical product,
price, currency, or GST through that path would therefore leave inconsistent costs
or tax history. Refund values are likewise frozen and tied to the original line.

The restriction predates the September GST correction. Git blame traces the
location/collected-price locks to M2 (`d1330f4`, 2026-07-06), and the refund-aware
lock/floor to M3 (`0d3598a`, the same date). The user guide explicitly describes
collection-based price locks in its "Editing and deleting" section.

If the business needs historical price correction after collection, that requires
an explicit audited correction/revaluation design. Simply enabling the inputs or
removing the backend guard would not implement that safely. The current error's
suggestion to refund/cancel does not itself correct the original locked price.

## Confirmed defects and limitations

### 1. Refund-only invoices show editable fields that the API rejects

Reproduction: create 10 units, collect none, cancel 2 pending units, open Edit,
change the unit price, and Save.

- UI: Product, unit price, currency, exchange rate, and GST are enabled.
- API: HTTP 400, `unit_price cannot change after stock was collected or refunded`.
- The entire update rolls back; header changes in the same request are not saved.

Cause: the frontend's `locked` condition only checks `collected > 0`. Its form
types and `openEdit` omit the API's `refunded` value. The backend checks collected
**or** refunded quantity. The same mismatch affects line removal.

Source: `purchases/page.tsx:19`, `:187`, `:501`, `:630`;
`purchases/services.py:407` and `:470`.

### 2. Inactive master records block unrelated corrections

The editor fetches active products, locations, suppliers, and currencies only.
`Combobox` displays a selection only if the existing ID is in that option list.

Browser-confirmed examples:

- An invoice's supplier is made inactive. Edit shows an empty required supplier
  control (`validity.valueMissing === true`), so even a notes-only correction
  cannot be submitted without choosing another supplier.
- The same occurs for an inactive product on an uncollected line. Locked fields
  are exempt from browser required validation, so collection state matters.
- An inactive location appears blank and disabled. Save reaches the API but is
  rejected with `not an active purchase location (FR-026)` even when only notes
  changed. The user cannot change that location in the editor either.

The API accepts an unchanged inactive supplier/product when the full invoice
payload is supplied; those cases are UI failures. Location additionally fails
backend validation because create-time eligibility is rechecked on every PUT.
Inactive currency follows the same active-option rendering path; it was inspected
in code, rather than separately exercised in the browser.

Source: `purchases/page.tsx:158`; `components/combobox.tsx:76`, `:247`;
`purchases/serializers.py:123`.

### 3. "Collected now" on a newly added line is silently ignored

Browser reproduction: edit an existing pending invoice, add a new product with
quantity 5 and "Collected now" 3, then Save.

- Save succeeds with no warning.
- The new line shows collected **0**, pending **5**, instead of collected 3 and
  pending 2.

The UI submits `collected_qty` for every new line, including during editing. The
update service removes it before deciding whether the line is new. Immediate
collection is implemented in `create_purchase`, but not for lines added through
`update_purchase`.

Source: `purchases/page.tsx:231`, `:597`; `purchases/services.py:345`.

### 4. Header-only PATCH returns HTTP 500

Synthetic request: `PATCH /api/v1/purchases/<sample-id>/` with
`{"notes": "Correction"}`.

Serializer validation accepts it, but `perform_update` unconditionally calls
`validated_data.pop("lines")`, raising `KeyError('lines')`. The note is not saved.

This is an API defect. The current browser editor uses a full PUT with lines, so
this alone does not explain ordinary browser edit failures.

Source: `purchases/views.py:83`.

### 5. Partial line PATCH also returns HTTP 500

Synthetic request: `PATCH /api/v1/purchases/<sample-id>/` with
`{"lines": [{"id": <sample-line-id>, "quantity": "12"}]}`.

Nested validation accepts the partial fields. The rate resolver then indexes
`line["currency"]` although the existing line's currency was omitted, raising
`KeyError('currency')`.

Related API behavior: omitting frozen exchange/GST values from a full line can
resolve current Settings defaults, rather than retain the existing frozen values.
On a collected line this can make an otherwise valid correction fail the pricing
lock. The ordinary UI preserves the explicit values on locked controls.

Source: `purchases/serializers.py:130`.

### 6. Line notes cannot be edited in the purchase UI

The API permits line-note changes after collection, and this succeeded in the
synthetic test. The form retains line notes internally and submits them, but renders
only the invoice-level Notes textarea. A user cannot update individual line notes
from this screen.

Source: `purchases/page.tsx:206`, `:234`, `:500`, `:651`.

### 7. Empty invoice updates and removed-line responses need validation

An API PUT with `lines: []` on an uncollected invoice succeeds, reverses its pending
stock, and leaves no active lines. The browser normally prevents removing the last
line, but the API does not enforce the same boundary.

The PUT response also includes the line just soft-deleted, while a subsequent GET
correctly shows no active lines. DRF clears the active-only prefetch on update;
the response serializer then follows the unfiltered reverse relation. The normal
UI reloads its list after saving, so that reload masks the response inconsistency.

Source: `purchases/serializers.py:97`; `purchases/views.py:26`, `:83`;
`purchases/services.py:363`.

## Validation performed

- All **227 existing backend tests passed** against the new local PostgreSQL
  cluster.
- **86 diagnostic cases passed** after documenting observed behavior. These are
  investigation assertions, including assertions that known defects return errors;
  passing diagnostics do not mean the defects have been fixed.
- Cases cover pending, partially collected, fully collected, pending-cancelled,
  and received-refunded invoices; header and pricing fields; quantity floors;
  no-op saves; line removal; calculated fields; inactive records; and all four roles.
- Rejected multi-field updates were checked for transaction rollback, with no
  partial header/ledger/audit writes. Successful stock-changing sample edits were
  checked by comparing balances to ledger aggregates without calling a repair.
- Browser reproductions confirmed collection locks, refund-only mismatch, missing
  inactive choices, inactive-location rejection, and ignored added-line collection.

Diagnostic source, synthetic seed, compose configuration, JUnit evidence, and
screenshots are retained locally under
`data/exports/purchase-edit-audit-2026-10-21/` (gitignored generated artifacts).
The original execution workspace is `/private/tmp/stock-tracker-edit-audit-20261021/`.

## Recommended next change

1. Align the UI with backend eligibility, explain each lock, and show the quantity
   floor before Save. Include refunds when deciding whether pricing/removal is locked.
2. Preserve historical selected master records in edit choices. Allow unchanged
   archived references for historical corrections while continuing to reject
   ineligible new selections.
3. Either support immediate collection for new lines added on edit in the same
   transaction, or hide/reject that input and direct users to Collection/Pending.
4. Define PATCH semantics explicitly: omitted lines retain existing lines; partial
   line changes retain omitted frozen fields. Keep intentional PUT replacement
   semantics separate and validate nonempty line lists.
5. Expose line notes if required and ensure update responses filter soft-deleted
   lines.
6. Separately decide whether historical financial corrections after collection
   are a business requirement. Implement an audited correction/revaluation workflow
   if approved; preserve existing stock/GST history and test downstream movements.

No production repair is recommended from this investigation alone. The observed
update restrictions do not establish that existing production values are incorrect.
