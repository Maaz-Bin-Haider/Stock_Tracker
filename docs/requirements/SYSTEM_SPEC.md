# SwissTech Inventory System Specification

## 1. Objective

Build a web-based inventory system to replace the current spreadsheet workflow in `stock tracker.xlsx`.

The system must let users enter each business event once through controlled forms, then automatically update:

- stock by location
- pending purchase quantities
- collected quantities
- in-transit quantities
- GST/tax values
- purchase and sale records
- stock ledger
- audit activity
- reports and exports

Profit distribution and detailed profit calculation are not required in this system.

## 2. Core Principles

- Stock ledger is the source of truth.
- Every stock-changing event creates ledger entries.
- Original records must remain traceable.
- Edits, deletes, refunds, and cancellations must be audited.
- Refunds and cancellations use reversal entries instead of destroying history.
- Reports are calculated from database records and ledger entries, not manual formulas.
- Locations, categories, currencies, GST rates, and exchange rates must be configurable.
- The app is single-company for now, but the database design should allow future multi-company support.

## 2.1 Architecture Diagram Reference

Detailed system diagrams are maintained in `docs/architecture/SYSTEM_DIAGRAMS.md`.

That document includes:

- use case diagram for actors and system actions
- activity diagrams for main business workflows
- sequence diagrams for important system interactions
- class diagram for major business objects
- ER diagram for proposed database design

The diagrams should be updated when workflows, permissions, major entities, or database relationships change.

## 3. Main Navigation

Required main menu pages:

- Dashboard
- Products
- Purchases
- Purchase Collection/Pending
- Purchase Refunds/Cancellations
- Shipments
- Sales
- Party-wise Purchase Records
- Party-wise Sale Records
- Stock Ledger
- Stock Adjustments
- Stock Valuation (admin only)
- Reports
- Users
- Settings
- Audit Activity

## 4. Locations

### Current Locations

- Sydney, Australia
- Melbourne, Australia
- Perth, Australia
- New Zealand
- Dubai, UAE
- Houston, Texas, USA
- Karachi, Pakistan

### Location Rules

- All current locations can purchase stock.
- Only Dubai and Karachi can sell stock.
- Sydney, Melbourne, and Perth must be tracked separately.
- Combined Australia stock is a calculated report/view only.
- Dubai is the main sales market.
- Karachi can receive stock from Dubai and can also buy/sell locally.
- Local Dubai purchases increase Dubai stock immediately when collected.
- Local Karachi purchases increase Karachi stock immediately when collected.
- Shipments from other locations generally go first to Dubai.
- Dubai to Karachi shipment is a separate transfer flow.

## 5. Product Tracking

- Stock is quantity-based.
- IMEI/serial tracking is not required.
- Color-level tracking is not required.
- Product variants must support storage/spec fields.
- Products can have optional flexible specifications.
- Sales must use existing Product Master records.
- Purchase users may create new products during purchase entry.
- Exact duplicate products are not allowed.
- Duplicate checking is case-insensitive.
- Same product name with different storage/specs is allowed.

### Product Fields

- product code/SKU
- product name
- category
- brand
- model
- storage/specs
- active/inactive
- created by
- created at
- updated by
- updated at

## 6. Roles and Permissions

### Roles

- Admin
- Purchase User
- Sale User
- Viewer

### Permission Matrix

| Area | Admin | Purchase User | Sale User | Viewer |
| --- | --- | --- | --- | --- |
| View dashboard | Yes | Yes | Yes | Yes |
| View products | Yes | Yes | Yes | Yes |
| Create/update/delete products | Yes | Yes, during purchase flow | No | No |
| View purchases | Yes | Yes | Yes | Yes |
| Create/update/delete purchases | Yes | Yes | No | No |
| Create/update/delete purchase refunds/cancellations | Yes | Yes | No | No |
| View purchase collection/pending | Yes | Yes | Yes | Yes |
| Manage purchase collection | Yes | Yes | No | No |
| View sales | Yes | Yes | Yes | Yes |
| Create/update/delete sales | Yes | No | Yes | No |
| View shipments | Yes | Yes | Yes | Yes |
| Create/update/delete shipments | Yes | Yes | No | No |
| View stock ledger | Yes | Yes | Yes | Yes |
| Create/update/delete stock adjustments | Yes | No | No | No |
| View stock valuation | Yes | No | No | No |
| Export stock valuation reports | Yes | No | No | No |
| View reports | Yes | Yes | Yes | Yes |
| Export reports | Yes | Yes | Yes | Yes |
| Manage users | Yes | No | No | No |
| Manage roles | Yes | No | No | No |
| Manage locations | Yes | No | No | No |
| Manage currencies | Yes | No | No | No |
| Manage GST rates | Yes | Yes | Yes | No |
| Manage exchange rates | Yes | Yes | Yes | No |
| Manage categories | Yes | Yes | Yes | No |
| View audit activity | Yes | Yes | Yes | Yes |

All non-viewer users can view all data across all locations. There are no location-level access restrictions for now.

Shipment creation, editing, deletion, and receiving are allowed for admin and purchase users. This was confirmed on 2026-07-02: purchase users own the full inbound stock flow (purchase, collection, refund/cancellation), and shipments continue that same flow, so no separate shipment/operator role is needed.

## 7. Master Data

### Supplier/Party Master

Supplier/party master data is required.

Suggested fields:

- supplier code
- supplier/party name
- contact person
- phone
- email
- country
- city
- address
- notes
- active/inactive

### Customer Master

Customer master data is required.

Suggested fields:

- customer code
- customer name
- phone
- email
- country
- city
- address
- notes
- active/inactive

### Settings Master Data

Managed from Settings:

- categories
- locations
- currencies
- GST/tax rates
- exchange rates

Only admins manage users, roles, locations, and currencies. Normal users may manage GST rates, exchange rates, and categories.

## 8. Purchases

### Purchase Structure

- Formal purchase orders are not required.
- Direct purchase entry after buying is required.
- One purchase invoice can contain multiple product lines.
- Each product line has its own quantity, unit cost, currency, exchange rate, GST rate, and collected quantity.
- No purchase discount option is required.
- Invoice-level discount is not required.
- Supplier/party is required.
- Purchase invoice/bill upload is optional.
- Uploads can be image files or PDF files.

### Purchase Header Fields

- purchase invoice/reference number
- purchase date
- purchase location/store
- supplier/party
- notes
- attachments
- created by
- created at
- updated by
- updated at

### Purchase Line Fields

- product
- category
- storage/specs
- quantity purchased
- unit price
- currency
- exchange rate
- unit price AED
- total value AED
- GST rate
- GST amount
- collected quantity
- pending quantity
- refunded/cancelled quantity
- available remaining quantity
- line status
- notes

### Purchase Status Automation

Users should not manually set purchase status.

Statuses should be calculated from line quantities:

- pending
- partially received
- fully collected
- cancelled
- refunded

Pending quantity must be calculated automatically:

`pending quantity = purchased quantity - collected quantity - cancelled/refunded pending quantity`

If collected quantity equals purchased quantity, status becomes fully collected.

If part of the quantity is collected, status becomes partially received.

If uncollected pending quantity is cancelled/refunded, status updates accordingly.

## 9. Purchase Collection/Pending

Purchase collection is separate from shipment.

Users should be able to:

- view pending purchase quantities
- select purchase invoice/reference
- collect product-by-product
- collect partial quantities
- record collection date
- record collection location
- update pending quantity automatically

Collection creates stock ledger entries that increase stock at the collection location.

For local Dubai/Karachi purchases, collection can happen immediately and increase local stock.

## 10. Purchase Refunds/Cancellations

Purchase refunds/cancellations must have a separate page.

Workflow:

1. User selects purchase invoice/reference.
2. System loads purchase header and product lines.
3. User selects product line(s).
4. User enters refund/cancellation quantity.
5. User selects reason and notes.
6. System validates available refundable/cancellable quantity.
7. System creates reversal ledger entries.
8. System recalculates stock, pending quantity, AED purchase value, and GST.

### Refund/Cancellation Rules

- Refund/cancellation must support line-level partial quantities.
- In one invoice, some products may be received and others may remain pending.
- In one product line, some quantity may be received and some may remain pending.
- Pending quantity may later be cancelled/refunded.
- Received quantity may be refunded/cancelled and must reverse stock.
- Refunds/cancellations must reduce/reverse GST where relevant.
- Original purchase records must remain unchanged and traceable.
- Reversal entries must reference the original purchase invoice and line.

## 11. Shipments

Shipments are separate from purchase collection.

### Shipment Rules

- One shipment can contain multiple products.
- Multiple purchases from one location can be combined into one shipment to Dubai.
- Shipments can be partially received.
- Dubai shipments support partial receiving.
- Dubai to Karachi shipment is a separate process and takes stock from current Dubai stock.
- Shipments do not require currency or exchange-rate handling.

### Shipment Header Fields

- shipment/reference number
- shipment date
- from location
- to location
- shipment type
- shipping cost
- notes
- attachments if needed
- status
- created by
- created at

### Shipment Line Fields

- product
- shipped quantity
- received quantity
- remaining quantity
- over-received quantity
- line status
- notes

### Shipment Statuses

- draft
- shipped
- partially received
- fully received
- cancelled

### Shipment Ledger Behavior

When shipped:

- decrease stock from source location
- increase in-transit stock for destination

When received:

- decrease in-transit stock
- increase destination physical stock

When cancelled:

- reverse the shipment entries as appropriate

Over-receiving is allowed with a warning.

## 12. Sales

### Sale Rules

- Only Dubai and Karachi can sell stock.
- Sales require customer tracking.
- Sale price is optional and for reference only.
- Sale price must not be used for profit calculations.
- Payment status is not required.
- Sales reduce stock at the sale location.
- Negative stock is allowed only after user confirmation.
- Sale users cannot create new products from sale entry.

### Sale Fields

- sale number/reference
- sale date
- sale location
- customer
- product
- quantity
- optional sale price
- notes
- optional invoice/file upload
- created by
- created at

## 13. Stock Adjustments

Manual stock adjustment is allowed.

Required fields:

- date
- location
- product
- adjustment type
- quantity
- reason
- notes

Examples:

- stock count correction
- damaged stock
- lost stock
- extra stock found

Every adjustment must create stock ledger and audit entries.

## 14. Stock Ledger

The stock ledger is the central source of truth.

Every stock-changing operation creates ledger entries:

- purchase collection
- purchase refund/cancellation
- shipment out
- shipment received
- shipment cancellation/reversal
- sale
- sale edit/delete reversal
- stock adjustment
- purchase edit/delete reversal where stock is affected

### Ledger Fields

- ledger ID
- transaction date/time
- transaction type
- source module
- source record ID
- source line ID
- product
- location
- quantity in
- quantity out
- net quantity
- stock bucket: physical, pending, in-transit
- related location
- currency
- AED value where relevant
- GST value where relevant
- notes
- created by
- created at

Stock should be recalculated from the full ledger after edits to purchases, sales, shipments, or adjustments.

## 15. Negative, Mismatch, and Warning Handling

- Negative stock is allowed with a warning.
- Negative stock on sale or shipment requires confirmation before saving.
- Over-receiving is allowed with a warning.
- Products with over-received, negative, or mismatch situations should be highlighted with a clear indication color throughout the system.

## 16. GST and Currency

### Currency

Base system currency is AED.

Required currencies:

- AED
- AUD
- NZD
- USD
- PKR

Purchases should convert values to AED.

Exchange rates are maintained in Settings.

Purchase entry allows manual exchange-rate override per purchase line.

Shipments do not require currency handling.

### GST

- GST is currently needed for Australia and New Zealand purchases.
- GST setup should support more locations in the future, including USA.
- GST rates are configurable.
- Purchases must use the relevant active GST rate for the purchase/location/date unless manually selected.
- Refunds/cancellations must reduce/reverse GST.
- GST report must reflect refunds/cancellations.

## 17. Dashboard

Default dashboard should show live/current data.

Summary cards:

- total company stock
- total stock by location
- pending stock
- in-transit stock
- Dubai stock
- Karachi stock
- GST total
- today's sales

Users should also be able to generate past dashboard summaries using a date/time cutoff, such as "up to yesterday at 5:00 PM".

## 18. List Pages

Every list page should include:

- fast search
- advanced filters
- sort
- pagination
- quick totals at top
- export where relevant

Quick totals may include:

- total quantity
- total pending
- total received
- total shipped
- total in-transit
- total AED value
- total GST
- total records

## 19. Reports

Reports must support filters and export only filtered data.

Exports:

- Excel
- PDF

PDF exports should use a clean, modern, light professional theme.

Stock valuation reports (summary and detail) are defined in section 26 and are admin-only.

### Proposed Reports and Columns

#### Current Stock by Location

- location
- product
- category
- brand
- model
- storage/specs
- physical quantity
- in-transit quantity
- pending quantity
- negative/mismatch indicator
- last movement date

#### Total Company Stock

- product
- category
- total physical quantity
- total in-transit quantity
- total pending quantity
- total stock across locations
- AED stock value where available

#### Australia Combined Stock

- product
- Sydney quantity
- Melbourne quantity
- Perth quantity
- total Australia quantity
- pending Australia quantity
- in-transit from Australia quantity

#### Dubai Stock

- product
- category
- quantity available
- quantity in-transit to Dubai
- quantity sold today
- negative/mismatch indicator

#### Karachi Stock

- product
- category
- quantity available
- in-transit from Dubai
- quantity sold today
- negative/mismatch indicator

#### Pending Purchase Stock

- supplier/party
- purchase invoice
- purchase date
- location
- product
- purchased quantity
- collected quantity
- pending quantity
- cancelled/refunded pending quantity
- AED value pending
- GST pending
- status

#### Pending Purchase Stock by Location

- location
- product
- total purchased
- total collected
- total pending
- total cancelled/refunded
- supplier/party
- oldest pending date

#### In-Transit Stock

- shipment reference
- shipment date
- from location
- to location
- product
- shipped quantity
- received quantity
- remaining quantity
- over-received quantity
- status

#### Purchase Report

- purchase invoice
- purchase date
- supplier/party
- location
- product
- category
- quantity
- collected quantity
- pending quantity
- refunded/cancelled quantity
- unit price
- currency
- exchange rate
- AED unit price
- AED total
- GST rate
- GST amount
- status
- created by

#### Party-wise Purchase Records

- supplier/party
- purchase invoice
- purchase date
- location
- product
- quantity
- collected quantity
- pending quantity
- refunded/cancelled quantity
- AED total
- GST amount
- invoice/file link
- status

#### Sales Report

- sale reference
- sale date
- sale location
- customer
- product
- quantity
- optional sale price
- notes
- created by

#### Party-wise Sale Records

- customer
- sale reference
- sale date
- sale location
- product
- quantity
- optional sale price
- invoice/file link
- created by

#### GST Report

The GST report should show purchase invoice details at product-line level, not only invoice totals. Quantity should be shown as net quantity after any cancellation/refund instead of separate purchased, collected, pending, and refunded quantity columns.

- purchase invoice
- purchase date
- invoice/reference status
- location
- GST country/region
- product
- storage/specs
- net quantity after refund/cancellation
- per-unit purchase price
- currency
- gross purchase value in original currency
- GST rate
- GST amount in original currency where applicable
- refund/cancellation GST reversal
- refund/cancellation reference
- refund/cancellation date
- net GST amount
- line status
- created by
- created at
- last updated by
- last updated at
- notes

#### Refund/Cancellation Report

- refund/cancellation reference
- date
- purchase invoice
- supplier/party
- product
- quantity refunded/cancelled
- original quantity
- received quantity affected
- pending quantity affected
- AED value reversed
- GST reversed
- reason
- created by

#### Stock Ledger Report

- date/time
- transaction type
- source module
- reference
- product
- location
- quantity in
- quantity out
- net quantity
- stock bucket
- AED value
- GST value
- created by

#### Stock Adjustment Report

- adjustment reference
- date
- location
- product
- adjustment type
- quantity
- reason
- notes
- created by

#### User Activity Report

- date/time
- user
- action
- module
- record reference
- before value summary
- after value summary
- IP/device where available
- login/logout activity where available

#### Upload/File Report

- file name
- file type
- linked module
- linked record
- uploaded by
- uploaded at
- downloadable link

## 20. Audit Activity

Audit must record:

- create
- update
- delete
- login
- logout where available
- product creation
- supplier/customer creation
- refund/cancellation
- settings changes
- GST/exchange-rate/category changes

Audit fields:

- audit ID
- user
- action
- module
- record ID/reference
- before values for updates/deletes
- after values for creates/updates
- date/time
- IP/device/session where available
- notes

Audit Activity page should be visible to all users, but viewer remains read-only.

## 21. File Uploads

Supported uploads:

- purchase invoice/bill images
- purchase invoice/bill PDFs
- sale invoice/file images
- sale invoice/file PDFs

Files should be:

- stored inside the system
- stored in the local Django media folder during development
- moved to S3-compatible object storage during deployment
- linked to the source record
- downloadable from reports where relevant
- included in audit trail for upload activity

Development file storage should use Django `MEDIA_ROOT`, for example `media/uploads/`. The database should store file metadata and paths/keys, not the binary file contents, so storage can move from local media files to S3-compatible object storage later without redesigning the business records.

## 22. Data Entry and Migration

- No Excel migration is required.
- Bulk import is not required.
- Opening stock will be entered manually one by one through the normal system flow.
- Products will be entered manually one by one.
- Suppliers/parties will be entered manually one by one.
- Customers will be entered manually one by one.

## 23. Technical Direction

### Application

- Web-based app.
- Desktop/web is primary.
- Must be fully responsive for mobile phone use.
- Manual product selection is enough.
- Barcode/QR code support is not required.

### Recommended Tech Stack

- Backend: Django.
- API: Django REST Framework.
- Database: PostgreSQL.
- Frontend: Next.js with TypeScript.
- UI: Tailwind CSS with shadcn/ui or Radix UI components.
- Background jobs: Celery for report exports, scheduled tasks, and heavier recalculation jobs.
- Queue/cache: Redis.
- Development file storage: local Django media folder.
- Deployment file storage: S3-compatible object storage.
- Local environment: Docker Compose.

### Deployment

- Local testing comes first.
- AWS deployment comes after local confirmation.
- Initial AWS deployment can run on a single EC2 instance.
- Development file storage should use the local Django media folder.
- Deployment file storage should use S3-compatible object storage for uploaded invoices and generated reports.
- Deployment should include app server, database, file storage, users, and backup setup as needed.

### Backup

- Automatic backup is desired.
- Exact backup schedule, retention, and restore process are deferred.

## 24. Suggested Database Tables

Core tables:

- users
- roles
- permissions
- user_sessions
- categories
- products
- locations
- currencies
- exchange_rates
- gst_rates
- suppliers
- customers
- purchases
- purchase_lines
- purchase_collections
- purchase_collection_lines
- purchase_refunds
- purchase_refund_lines
- shipments
- shipment_lines
- shipment_receipts
- shipment_receipt_lines
- sales
- sale_lines
- stock_adjustments
- stock_ledger
- file_attachments
- audit_logs
- app_settings

Future-ready fields:

- company_id on business tables, nullable/defaulted for now
- created_by
- created_at
- updated_by
- updated_at
- deleted_by
- deleted_at
- is_deleted or status where soft delete is needed

## 25. Implementation Notes

- Prefer soft delete plus reversal records for business records that affect stock.
- Do not physically delete stock-affecting records without audit history.
- Use database transactions for every stock-changing operation.
- Validate stock state before saving sales, shipments, refunds, and adjustments.
- Keep calculated stock as a report/view derived from stock ledger, or maintain a stock balance table that is always reconciled from ledger.
- Any edit to historical stock-affecting records should create adjustment/reversal ledger entries and then recalculate stock.
- Use indexes on dates, product IDs, location IDs, supplier/customer IDs, status fields, and source references for fast search/filter.

## 26. Stock Valuation (Admin Only)

A completely separate Stock Valuation section, visible and exportable by admin users only. It shows the total worth of all products currently in stock, valued at actual purchase rates.

### Valuation Rules (confirmed 2026-07-02)

- Costing method: **weighted average cost** in AED, maintained per product per location.
- Value follows quantity through the stock buckets: purchase entry adds pending value, collection moves value from pending to physical, shipments move value from physical to in-transit to destination physical at carrying average cost.
- Valuation scope: **physical + in-transit + pending** all count toward total worth, shown separately per bucket with a combined total.
- Shipping costs are **excluded** from product worth; they remain visible on shipment records only.
- Refunds/cancellations remove value based on the original purchase line AED rate.
- The AED value uses the exchange rate frozen at purchase entry time.
- Negative stock lines show negative value and carry the standard mismatch highlight.

### Valuation Views

Summary view:

- total company stock worth (AED)
- worth by location
- worth by bucket: physical, in-transit, pending
- worth by category
- top products by value

Detail view (per product per location):

- product, category, brand, model, storage/specs
- location
- physical quantity, in-transit quantity, pending quantity
- weighted average unit cost (AED)
- physical value, in-transit value, pending value (AED)
- total value (AED)
- last movement date
- mismatch/negative indicator

Both views support the standard filters (location, product, category, date cutoff) and export to Excel and PDF with only the filtered data. Exports follow the same clean, professional PDF theme as other reports.

## 27. UI Theme and Responsiveness

### Theme

- Default theme: light, modern, professional.
- Dark mode: a dedicated professional dark palette designed for readability and hierarchy — not an automatic inversion of the light colors.
- Users can switch theme manually; the preference is remembered per user. System preference is respected on first visit.
- All components, charts, status colors, and warning/mismatch highlights must have designed values in both themes.

### Responsiveness

The system must adapt cleanly across:

- large desktop monitors
- small-screen laptops
- iPads and similar tablets
- small tablets

Layouts, tables, forms, and dashboards must adapt to both large and small screens without broken layouts or horizontal scrolling traps. Mobile phone support remains required as previously specified.

## 28. Business Time Zone

- All timestamps are stored in UTC.
- The business time zone is **Dubai time (Asia/Dubai)** (confirmed 2026-07-02).
- "Today" boundaries for dashboard cards, date filters, daily reports, and past-cutoff snapshots are calculated in Dubai time for all users and locations.

## 29. Resolved Confirmation Items

- Shipment permissions (confirmed 2026-07-02): admin and purchase users can create, update, and delete shipments and record shipment receiving. Sale users and viewers have view-only access to shipments. No separate shipment/operator role is introduced.
