# Dropdown type-ahead incident

## Summary

On 2026-09-05, users reported that every choice control in the system was
effectively unsearchable. Typing a single letter jumped to the first entry
starting with that letter, as expected — but typing a whole word did not find
that word. Typing `starlink` landed on the first entry beginning with **K**,
because the last key pressed was `k`. The only reliable way to pick an entry was
to scroll the whole list by hand.

## Impact

- Selecting a product on a purchase invoice, sale, shipment or stock adjustment
  meant scrolling a list of hundreds of entries.
- The same behaviour affected every location, supplier, customer, currency,
  category, user and report-filter dropdown — 22 controls across nine screens.
- Wrong-entry selections were easy to make and hard to notice: the control
  silently moved to a valid-looking neighbouring product.
- Product dropdowns showed the product name only, so two products that share a
  name and differ by storage/specs (allowed by FR-018/FR-019) appeared as two
  identical rows with nothing to choose between them.

No data was lost or corrupted; incorrect selections that were saved are ordinary
records and can be corrected through the normal edit/refund flows.

## Root cause

Every choice control was a native HTML `<select>`.

Browsers give `<select>` a type-ahead buffer that **expires after roughly one
second of inactivity**. Keystrokes typed within that window accumulate; the
first keystroke after it starts a brand-new search. At normal human typing speed
the buffer expires part-way through a word, so `s-t-a-r-l-i-n-k` was not one
search for "starlink" but a series of single-letter searches ending with `k` —
which selected Kingston SSD.

The behaviour is also prefix-only and invisible: `<select>` matches only from
the start of the option text, never mid-label, and never shows what it thinks
you typed. With more than 200 products, that leaves scrolling as the only
dependable method.

This is browser behaviour, not application code, so no amount of option ordering
or data change could fix it — the control itself had to change.

## Resolution

- Added `components/combobox.tsx`, one searchable single-select used by every
  choice control in the app. It uses the entire query, matches anywhere in the
  label, narrows the list as you type, and never expires.
- Added `lib/options.ts` with the labelling and ranking rules, kept free of
  React so they are unit-testable. Ranking is: exact label, then labels starting
  with the query, then labels with a word starting with it, then labels
  containing it — so a lone `s` still lands on the first S entry (the behaviour
  users relied on) while `starlink` lands on Starlink. Whitespace-separated
  tokens may be typed in any order, so `iphone 256` finds "iPhone 15 Pro 256GB".
- Product labels now include storage/specs everywhere, matching what the report
  filters already did, so same-named products are distinguishable and findable.
- Lists render in a portal with fixed positioning, so the modals'
  `overflow-y-auto` containers can no longer clip them, and they flip above the
  field when there is no room below (SRS §7.6).
- Keyboard behaviour is preserved and extended: arrows move, Enter selects, Esc
  reverts, Home/End jump, and lists of eight or fewer entries stay read-only
  (no tablet keyboard for a two-choice field) while still supporting the
  first-letter jump users know from `<select>`.
- Required fields keep the browser's own "please fill this in" check: the text
  field carries `required`, and a query that does not resolve to an option is
  reverted when the field loses focus, so the box can never show text that is
  not a real selection.

## Regression coverage

`src/frontend/tests/options.test.mjs` covers the reported symptom directly: it
asserts that `rankOptions(catalogue, "starlink")` returns the Starlink entries
and specifically **not** Kingston SSD, and walks every prefix of the word
(`s`, `st`, `sta`, …) asserting the list never wanders to another product. It
also covers single-letter jumps, case-insensitivity, mid-label matches,
multi-token queries, exact-match ranking, empty queries and no-match queries.

## Related fix found while verifying

Browser-driven verification was initially impossible because **every
authenticated write through the dev stack failed CSRF**: `deployment/nginx/
default.conf` forwards `Host: $host`, which nginx supplies without the port, so
Django compared the browser's `Origin: http://localhost:8080` against
`http://localhost` and rejected it. Requests made without an `Origin` header
(curl, the Django test client) were unaffected, which is why the automated suite
never caught it. `config/settings/dev.py` now sets `CSRF_TRUSTED_ORIGINS` for
the local dev origins. Development only — `local_prod` and `prod` already take
this from `DJANGO_CSRF_TRUSTED_ORIGINS`.

## Rollout check

Deploy the rebuilt frontend, then open a new purchase invoice and type a word
that appears in the middle of a product's name (for example `link` for
Starlink). The list should narrow to matching products only. Repeat on a sale,
shipment, stock adjustment and a product-filtered report. No database migration
or data repair is required.
