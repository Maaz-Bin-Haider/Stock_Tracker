# Purchase search and filters

Date: 2026-10-22. Implemented locally, then deployed after explicit authorization
and validated backups. Development/regression tests use synthetic data; production
acceptance uses SELECT-only snapshots. See the
[deployment record](../production-issues/2026-10-22-purchase-search-deployment.md).

## User experience

The Purchases page has a full-width search panel with search scope, clear action,
status buttons, collapsible filters, active filter chips, reset, sorting, a result
range/count, and loading/error/empty states. Supplier, location, and product pickers
use the existing searchable combobox. Inactive references are labelled and retained
for historical searches; the invoice editor still offers active choices plus its
existing selected references.

Purchase dates have inclusive limits and Today/Last 7 days/This month shortcuts.
Shortcuts use Asia/Dubai regardless of browser timezone. Controls wrap at small
screen breakpoints and use existing light/dark semantic tokens.

Filter changes are debounced 300 ms and reset page/expanded detail together.
Sequence/query checks prevent older responses from replacing newer results;
returning to the original query before debounce explicitly refreshes cancelled
loads. Pending requests hide old rows and totals. Filters remain in page state;
saved searches and URL persistence are outside this change.

## API contract

`GET /api/v1/purchases/` accepts these combined read-only parameters:

| Parameter | Values/behavior |
| --- | --- |
| `search` | Existing DRF multiword text search |
| `search_in` | `all` (default), `invoice`, `product`, `supplier`, `location`, `notes` |
| `status` | Existing computed purchase status enum |
| `supplier`, `location`, `product` | Reference IDs; inactive historical references supported |
| `date_from`, `date_to` | Inclusive ISO purchase-date bounds; invalid/reversed dates return 400 |
| `purchase_date` | Existing exact-date filter remains supported |
| `ordering` | UI: `-purchase_date`, `purchase_date`, `invoice_no`, `supplier__name`; existing `created_at` remains supported |
| `page` | Existing page-number pagination, 50 invoices per page |

Invoice IDs break ordering ties, keeping equal-date/reference pagination stable.
Text product search covers name, storage/specs, SKU, brand, and model. A filtered
line relation excludes removed lines and keeps product words on the same line.
Explicit distinct handling deduplicates invoices when multiple lines match.
The quick-total aggregation reuses the full filtered invoice query and includes
every active line on matching invoices, not just the matching product or page.

`purchases/filters.py` mirrors the existing Python line/invoice status rules using
correlated quantity subqueries and status-specific Exists predicates. It handles mixed
cancelled/refunded/fully collected lines and legacy empty invoices without storing
status or multiplying collection/refund quantities through joins. No migration,
stock posting, balance repair, or permission change is required.

Deploy backend and frontend together: the old backend does not implement the new
status/date/product/search-scope parameters. The current deployed source baseline
is `data/exports/purchase-search-release-2026-10-22/release-manifest.json` and its
private EC2 release copy. The repository publication includes the deployed
application source; retain the manifest as evidence of the exact release contents.
Release preparation used the previous correction-release manifest for comparison,
because the application changes had not yet been committed at deployment time.

## Verification

- Full backend suite: **308 passed** against isolated local PostgreSQL 16, including
  21 new search cases. Covers combined filters/totals, all scopes/specs/SKU,
  removed/duplicate lines, words on one product line, all computed statuses with
  mixed refunds/cancellations, invalid filters, stable page boundaries, and all roles.
- Frontend tests: **30 passed**, including query encoding/defaults and Dubai-date
  boundary/date-shortcut behavior. TypeScript, ESLint, Ruff, and production build
  passed (Next.js 15.5.28; 19 routes).
- Browser: combined search/scope/location/date, pending-only totals, rapid query
  changes, empty results/reset, sorting, and light/dark layouts on synthetic samples.
  Desktop page has no horizontal overflow. Small-screen CSS is implemented;
  phone/tablet viewport layouts were subsequently checked at 375/768 px during
  release preparation; see the deployment record.
- The exact optimized ARM64 backend release subsequently passed all **308 tests**
  in 349.12 seconds. The production-sized read-only check reduced fully-collected
  request time from 5.919 to 2.656 seconds with matching counts/totals.
- Evidence: gitignored `data/exports/purchase-search-2026-10-22/`, with backend
  JUnit and local light/dark screenshots. Local preview: loopback port 18080,
  existing synthetic sample users/database. Deployment verification reads production
  data through guarded SELECT-only checks; no production invoice was edited.

Files: frontend purchase search component/helper and Purchases page; backend
purchase filters/viewset; backend/frontend search tests; user guide, SRS,
system specification, and root project context.
