# Product dropdown pagination incident

## Summary

On 2026-09-01, production users reported that more than 200 products were
present and searchable on the Products page, but product dropdowns stopped at
names beginning around the letter D. This prevented later products from being
selected on purchase invoices.

## Impact

- Purchase invoices could not select products outside the first alphabetic API
  page.
- The same loading pattern also affected product choices in Sales, Shipments,
  Stock Adjustments, and report filters.
- Other foreign-key dropdowns could show the same behavior after their data grew
  beyond one API page.
- Product records and stock data were not lost or corrupted. The issue was
  limited to frontend choice loading.

## Root cause

Django REST Framework uses page-number pagination with a page size of 50
(`config/settings/base.py`). Products are ordered by name
(`apps/products/models.py`).

The affected frontend pages used a local helper named `fetchAll`, but it returned
only `response.results` from the first request and ignored DRF's `response.next`
link. The first 50 alphabetically ordered products therefore appeared in the
dropdown, while every later page was silently omitted. With the production
product names, the first page ended around D.

## Resolution

- Added shared `apiAll()`/`collectPaginated()` frontend helpers that follow every
  DRF `next` link until it is null.
- Converted absolute DRF next links back to same-origin paths. This preserves the
  browser's active port in local deployments and prevents following another
  origin.
- Replaced first-page-only choice loading in Purchases, Sales, Shipments, Stock
  Adjustments, Purchase Collection, Stock Ledger, report filters, and generic
  master-data forms.
- Kept normal paginated list pages unchanged; only choice controls load the full
  filtered option set.

## Regression coverage

`src/frontend/tests/pagination.test.mjs` simulates 205 products across five
50-item API pages and verifies that all 205, including the final product, are
returned. It also verifies that repeated next links are rejected rather than
causing an infinite loop.

`tests/backend/test_products.py` creates 205 products against the real DRF
endpoint and verifies its first and fifth pages, including products 201–205.

The frontend CI job now runs `npm test` before type checking and the production
build.

## Production rollout check

After deploying the rebuilt frontend, open a new purchase invoice and verify a
product from the final alphabetic group can be selected. Repeat the check on a
sale, shipment, stock adjustment, and product-filtered report. No database
migration or data repair is required.
