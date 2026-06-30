# SwissTech Inventory System Context

## Current File

- Workbook: `stock tracker.xlsx`
- Purpose: manual stock, purchases, shipping, GST, sales, and profit tracking.
- Current process is spreadsheet-based with many manual entries and formulas.

## Current Workbook Structure

Important sheets:

- `Product_Master`: main stock summary/dashboard.
- `Stock_Transactions`: main stock movement ledger.
- `Pending_Stock`: pending Australia and New Zealand stock.
- `ShipToDubai`: stock shipped to Dubai and remaining/received quantities.
- `Purchases`: purchase records with currency/exchange calculations.
- `Usa Purchase`: USA purchase and item/IMEI-level tracking.
- `GST`: GST calculations for Australia and New Zealand.
- `Monthly Sales`: sales and profit calculations.
- `Karachi Sale`: Karachi sales/payment ledger.
- `Pending Things`: miscellaneous pending items/tasks.
- `profit distribution`: net income/profit split calculation.

## Problems With Current Process

- Too many manual entries across many sheets.
- High chance of human error.
- Stock movements can be inconsistent because entries are repeated manually.
- Purchase locations are increasing, such as China and future locations.
- Current workbook uses plain ranges and formulas instead of a proper database/table model.
- Locations are embedded into sheet structure, making expansion harder.

## Recommended Direction

Move to a professional inventory tracking system where every business event is entered once through controlled forms, and reports are generated automatically.

Core principle:

> Enter each business event once. Let the system update stock, pending quantity, in-transit quantity, GST, and reports automatically.

## Preferred Long-Term Solution

A web-based inventory app is preferred over a more complex spreadsheet because it can support:

- Multiple purchase locations: USA, Australia, New Zealand, China, etc.
- Multiple stock/sales locations: Dubai, Karachi, and future locations.
- User login and permissions.
- Controlled forms instead of manual cell editing.
- Audit history.
- Direct purchase entry.
- Purchase collection tracking.
- Stock transfers.
- Sales.
- GST tracking with editable rates.
- Excel export when needed.

The user selected this option as the preferred direction.

## Core Modules To Design

1. Product Master
   - SKU/code
   - Product name
   - Brand/model/category
   - Color/storage/specs where needed
   - Standardized product names
   - Active/inactive status

2. Locations
   - Location name
   - Type: purchase, warehouse, sales, transit, supplier/customer if needed
   - Add future locations without changing report formulas

3. Purchases
   - Supplier
   - Purchase location
   - Currency
   - Exchange rate
   - One product per purchase entry
   - Quantity purchased
   - Unit price
   - Collection status
   - Quantity collected
   - Quantity pending

4. Purchase Collection
   - Purchase reference
   - Quantity collected
   - Quantity pending
   - Collection location
   - Automatically increases physical stock for collected quantity

5. Stock Transfers
   - From location
   - To location
   - Product
   - Quantity shipped
   - Quantity received
   - In-transit quantity
   - Status

6. Sales
   - Sale location
   - Customer
   - Product
   - Quantity sold
   - Automatically reduces stock

7. GST
   - GST rates must be configurable.
   - GST calculations must use the active rate for the relevant purchase/location/date.

8. Stock Ledger
   - Central source of truth for all movement.
   - Each stock movement should create a transaction row.
   - Reports should calculate from this ledger.

9. Users and Audit Activity
   - User login is required.
   - Every user action should be recorded.
   - Activity history should be viewable when required.

10. Reports and Exports
   - Operational reports should be generated from the database/ledger.
   - Reports should be exportable.

## Next Steps

- Design the professional workflow in detail.
- Decide whether to build:
  - a professional structured Excel/Google Sheets system, or
  - a web-based inventory app.
- If building a web app, define:
  - database schema,
  - user roles,
  - screens/forms,
  - reports,
  - migration path from `stock tracker.xlsx`.

## Requirements Gathered

### Business Locations

Current operating locations:

- Australia
  - Sydney
  - Melbourne
  - Perth
- New Zealand
  - currently one location
- Dubai, UAE
- USA
  - Texas, Houston
- Pakistan
  - Karachi

### Purchase Locations

All current locations can purchase stock:

- Sydney
- Melbourne
- Perth
- Dubai
- USA/Houston
- Karachi
- New Zealand

### Sales Locations

Only these locations can sell stock:

- Dubai
- Karachi

### Stock Holding Locations

- Australia locations can hold stock if not yet shipped.
- New Zealand can hold stock if not yet shipped.
- USA can hold stock if not yet shipped.
- Dubai holds stock and is the main sales market.
- Karachi holds stock for local sales after transfer from Dubai or local purchase.

### Normal Stock Flow

- Stock can be purchased from any current location.
- Shipments from anywhere generally go first to Dubai.
- Dubai is the main sale market.
- Some products are later shipped from Dubai to Karachi.
- Dubai and Karachi can also purchase stock locally and sell locally; no shipping step is needed for those local purchases.

### Tracking Level

- Stock tracking should be quantity-based.
- IMEI/serial tracking is not required.
- Product variants should be tracked by GB/storage.
- Color-level stock tracking is not required.

### Current Pain Points

- Duplicate entries.
- Forgetting to update received quantity.
- Improper pending stock entries.
- Human error caused by too many manual spreadsheet entries.

### Batch 2 Requirements - Purchase, Shipment, Sales, GST

Purchase entry:

- Formal purchase orders are not required.
- The system should allow direct purchase entry after buying.
- Each purchase entry is for one single product.
- Quantity can be very large, including thousands of units.
- Multiple purchases can happen at one location before being shipped collectively.

Purchase and collection statuses:

- Required purchase/stock statuses:
  - purchased
  - pending
  - fully collected
  - partially received
  - cancelled
  - refunded
- Purchase collection is separate from shipment.
- Sometimes purchased stock is fully collected immediately.
- Sometimes only part of a purchase is collected and the remaining quantity stays pending.
- Pending purchase quantity may be received after a week or even after a month.
- The system must track purchased quantity, collected quantity, and pending quantity.

Local stock behavior:

- Locally bought Dubai stock should immediately increase physical stock in Dubai.
- Locally bought Karachi stock should immediately increase physical stock in Karachi.

Shipment workflow:

- Shipment is a separate process from purchase collection.
- Shipments need their own details and ledger.
- Multiple purchases from one location can be combined into one shipment to Dubai.
- Required shipment fields:
  - shipped date
  - received date
  - shipping cost
  - remaining quantity
- Shipments can be partially received.
- Example: 100 units shipped, 70 received now, 30 received later.
- Partial shipment receiving happens for Dubai shipments, not Karachi shipments.

Negative stock:

- The system should allow negative stock with a warning.
- Reason: sometimes stock is purchased in Australia without complete details, then extra stock is received in Dubai before the Australia team provides the missing purchase details.

Sales:

- Sales require customer tracking.
- Sales do not require payment status.
- Sales are required for stock quantity tracking only.

Profit:

- Profit calculations are not required in the new system.
- Existing workbook profit calculations are manual and should not be treated as required stock tracking functionality.

GST:

- GST calculations should be included.
- GST rates are dynamic.
- The system must provide an option to update GST rates when they change.

### Batch 3 Requirements - Products, Locations, Ledger, Audit

Product master:

- The system should force standardized product names from Product Master.
- New products can be added during purchase entry.
- During sale entry, users cannot create a new product.
- Sales must use products that already exist in Product Master.
- Product categories are required.
- Example categories may include Starlink, iPhone, MacBook, JBL, Camera, Accessories, and other business-specific categories.

Product variants and specifications:

- Every product can have optional storage/specification fields.
- For mobile phones, laptops, iPads, tablets, and MacBooks, GB/storage should be available as a product detail.
- Some products do not have GB storage but may have other details, so the model should support flexible optional specifications.

Opening stock and migration:

- No Excel migration is required for opening inventory.
- Opening stock will be entered manually by the business.

Australia location tracking:

- Sydney, Melbourne, and Perth must be tracked as separate stock locations.
- The system should also show combined Australia stock for reporting/detail.
- Combined Australia stock is a calculated view only; it should not replace separate branch/location stock tracking.

Shipment entries:

- One shipment can contain multiple products.

Ledger behavior:

- Every purchase, collection, shipment, shipment receiving, and sale should automatically create stock ledger entries.

Editing and deletion:

- Users need the ability to edit and delete old entries.
- Because edits/deletes affect stock history, the system must record which user edited or deleted an entry and when.

GST locations:

- GST is currently needed for Australia and New Zealand purchases.
- The system should support GST/tax setup for more locations in the future, including USA.

User-oriented audit tracking:

- The system must record which user made each entry.
- Every activity performed by a user should be tracked by the system.
- User activity should be viewable when required.

### Batch 4 Requirements - Adjustments, Roles, Reports, Currency

Manual stock adjustment:

- Manual stock adjustment should be allowed.
- A reason field is required for every manual stock adjustment.
- Manual adjustment examples include stock count corrections, damaged/lost stock, or extra stock found.
- Manual adjustments must create stock ledger entries and user activity audit entries.

User roles:

- Required roles:
  - admin
  - purchase user
  - sale user
  - viewer
- Users should not be restricted to their own location.
- Users can access locations according to their role, not by assigned branch/location.

Edit/delete permissions:

- All users can edit and delete old entries.
- Audit history is enough; approval is not required before edit/delete.
- Deleted entries should still be traceable in audit history because every user activity is recorded.

Required reports:

- Current stock by location.
- Pending purchase stock total.
- Pending purchase stock by location.
- In-transit stock.
- Dubai stock.
- Karachi stock.
- Australia combined stock.
- GST report.
- Sales report.
- User activity report.

Report exports:

- All reports must be exportable to PDF and Excel.
- PDF exports should be lightweight, professional, and modern-looking.

Currency:

- Base system currency is AED.
- All purchases should convert to AED.
- Required currencies:
  - AED
  - AUD
  - NZD
  - USD
  - PKR
- Exchange rates should be maintained in a currency-rate settings screen.
- Purchase entry should also allow a manual exchange rate override per purchase.
- Shipments do not require currency or exchange-rate handling.

### Batch 5 Requirements - Forms, Uploads, Dashboard

Purchase entry form:

- Required purchase fields:
  - date
  - location/store name
  - supplier/party
  - product
  - category
  - storage/specs
  - quantity
  - unit price
  - currency
  - exchange rate
  - GST rate
  - collected quantity
  - pending quantity
  - status
  - notes
- Supplier/party is required.
- Purchase invoice/bill image upload should be supported.
- Purchase records and attached invoice/bill details should be exportable where relevant.

Sale entry form:

- Required sale fields:
  - date
  - sale location
  - customer name
  - product
  - quantity
  - notes
- Sale price should be optional and recorded only for reference.
- Sale price should not be used in calculations.

Shipment form:

- Required shipment fields:
  - shipment date
  - from location
  - to location
  - products with quantities
  - shipping cost
  - received date
  - received quantities
  - remaining quantities
  - status
  - notes
- Shipments can go from purchase/stock locations to Dubai.
- Dubai to Karachi shipment is a separate shipment type/process.
- Dubai to Karachi shipment takes stock from current Dubai stock and ships it to Karachi.

Opening stock:

- A separate opening stock form is not required.
- Opening stock will be entered manually by following the normal system flow.

Product master form:

- Required product master fields:
  - product name
  - category
  - brand
  - model
  - storage/specs
  - active/inactive

Dashboard:

- Dashboard should show summary cards for:
  - total company stock
  - total stock by location
  - pending stock
  - in-transit stock
  - Dubai stock
  - Karachi stock
  - GST total
  - today's sales

Design/export style:

- PDF and Excel exports are required where relevant.
- PDF output should use a beautiful, modern, light professional theme.

### Batch 6 Requirements - Status Automation, Validation, Upload Rules

Purchase automation:

- Purchase status should be calculated automatically from total quantity, collected quantity, and pending quantity.
- Users should not manually change purchase status.
- Pending quantity should be calculated automatically.
- Example: if quantity is 100 and collected quantity is 70, pending quantity should automatically become 30.
- If collected quantity equals total quantity, status should automatically become fully collected.
- If only part of the purchased quantity is collected, status should automatically become partially received/pending according to the quantity state.
- For cancelled or refunded purchases, stock should be reversed automatically if any quantity was already collected.

Shipment status:

- Required shipment statuses:
  - draft
  - shipped
  - partially received
  - fully received
  - cancelled

Shipment receiving:

- Users should receive shipments product-by-product.
- Each shipment product line should have its own received quantity.
- Each shipment product line should have its own remaining quantity.

Over-receiving and negative indicators:

- If Dubai receives more quantity than originally shipped, the system should allow it with a warning.
- Products with over-received/negative/mismatch situations should be highlighted throughout the system with a specific indication color.
- Negative stock on sale or shipment should require user confirmation before saving.

Product duplicate validation:

- The system should allow the same product name with different storage/specs.
- The system should prevent exact duplicate products.
- Product name matching should be case-insensitive.
- Example: `IPHONE 12` and `Iphone 12` should be treated as the same product name for duplicate checking.

Invoice and document uploads:

- Purchase entry should allow optional upload of invoice screenshots/images or PDF files.
- Sale entry should allow optional upload of invoice screenshots/images or PDF files.

### Batch 7 Requirements - Navigation, Permissions, Settings, and System Behavior

Main navigation:

- Required main menu pages:
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
  - Reports
  - Users
  - Settings
  - Audit Activity

Party-wise records:

- The system must provide party-wise purchase and sale record pages.
- Party-wise purchase records should show supplier/party purchase history.
- Party-wise sale records should show customer sale history.
- These pages must support selected date ranges.
- Date filtering should support precise ranges where needed.

Purchase refund and cancellation workflow:

- Purchase refunds/cancellations must have a separate page.
- The user should select a purchase invoice/reference first.
- The system should load the invoice details and product lines from that selected purchase.
- The user should perform the refund/cancellation against that specific purchase invoice.
- Refund/cancellation must support line-level and partial-quantity handling.
- In a single purchase invoice, some products may be received and some may remain pending.
- Pending products from the same invoice may later be cancelled or refunded.
- For the same product line in a purchase invoice, some quantity may be received and some quantity may remain pending.
- The pending quantity for that same product line may later be cancelled or refunded.
- Cancelled/refunded quantities must create reversal ledger entries.
- The original purchase and original stock movements must remain traceable.
- Refund/cancellation should not destroy or overwrite original purchase history.

Permissions:

- Purchase users are allowed to create products during purchase entry.
- No user should be restricted from viewing stock and products unless their role is viewer-only/read-only.
- Sale users can create sales and can also view stock and products.
- Viewer users should be read-only for everything.
- Only admins should manage:
  - users
  - roles
  - locations
  - currencies
- GST rates, exchange rates, and categories can also be managed by normal users.
- Role permissions should control access across all locations.
- Users should not have location-level access restrictions for now.

Master data and settings:

- Supplier/party master data is required.
- Customer master data is required.
- Categories, locations, currencies, GST rates, and exchange rates should all be managed from Settings.
- The system should support only one company for now.
- The design should allow multiple companies/businesses to be added in the future.

List pages and reports:

- Every list page should support advanced, fast search and filters.
- List pages should show quick totals at the top.
- Quick totals may include total quantity, total pending, total AED value, and other relevant totals for the page.
- Reports should allow date filters, location filters, product/category filters, and other relevant filters.
- Report exports should export only the filtered data.
- Dashboard should show live/current data by default.
- Users should be able to generate past dashboard summaries.
- Past dashboard summaries should support date and time cutoffs.
- Example: user can generate dashboard data up to yesterday at 5:00 PM.

Stock and alerts:

- Low-stock alerts and reorder level alerts are not required.

Files and exports:

- Invoice/file uploads should be stored inside the system.
- Invoice/file uploads should also be downloadable from reports where relevant.

Future features and operations:

- Barcode/QR code support is not required.
- Manual product selection is enough.
- The app is primarily desktop/web based for now.
- The app must be fully responsive so it can open and work on mobile phones.
- Automatic daily/monthly backups are required.
- The app will be deployed to AWS for cloud access by users in different countries.

Stock history behavior:

- Purchase refunds/cancellations should keep the original record and create reversal entries instead of deleting/changing old stock movement history.
- When users edit old purchases, sales, shipments, or adjustments, the system should recalculate stock from the full ledger automatically.

### Batch 8 Requirements - Final Permissions, Invoice Structure, Audit, Reports, and Deployment Notes

Exact role permissions:

- Admin can do everything in the system.
- Purchase user can create, update, and delete purchases.
- Purchase user can create, update, and delete purchase refunds/cancellations.
- Sale user can create, update, and delete sales only.
- All non-viewer users can view all system data.
- Viewer can only view data and cannot create, update, or delete records.
- All create, update, and delete actions must be recorded in user activity/audit history.
- Every permissioned action performed by a user must be traceable.

Purchase invoice structure:

- One purchase invoice can contain multiple products.
- Purchase cost should be recorded per product line.
- No purchase discount option is required.
- Invoice-level discount is not required.
- Product line values should drive AED purchase value, GST calculations, and stock value reporting where relevant.

Refund/cancellation financial and stock behavior:

- Refunds/cancellations must recalculate total stock properly.
- Refunds/cancellations must reduce/reverse GST where relevant.
- Refund/cancellation impact should be reflected in GST reports.
- Refund/cancellation impact should be reflected in AED purchase value calculations where relevant.
- Refund/cancellation should use reversal entries and preserve original invoice history.

Audit and activity rules:

- The system must audit create, update, and delete actions.
- Audit records should include before/after details for updates.
- Audit records should include the user, action, date/time, affected record, and important changed values.
- Product creation must be audited.
- Party/supplier/customer creation must be audited.
- Refund/cancellation activity must be audited.
- Login activity must be audited.
- User online/activity details should be visible to other users where required.
- User activity should be visible in the Audit Activity page.

Backups:

- Backup details are deferred for now.
- Automatic backup is still desired, but restore process, retention period, and exact backup schedule can be finalized later.

Deployment and infrastructure:

- The app will first be tested locally.
- After local testing and confirmation, deployment will be handled later.
- Target deployment is AWS.
- Initial AWS deployment can run all required services on a single EC2 instance.
- The deployment phase should include web app, database, file storage, users, and backup setup as needed.

Reports:

- The reports module should initially include as many useful report details and columns as practical.
- The user will later filter which reports/columns to keep or discard.
- Reports should be designed broadly first, then narrowed during review.
- Reports should support filtering and export as already defined.

Data import:

- Bulk import from Excel is not required for opening stock, suppliers, customers, or products.
- Products, suppliers/parties, customers, and opening stock will be entered manually one by one.

### Documentation and Architecture Update

- A root-level project context file is maintained at `PROJECT_CONTEXT.md` for future continuation.
- Detailed architecture diagrams are maintained at `docs/architecture/SYSTEM_DIAGRAMS.md`.
- The diagrams document includes:
  - Use Case Diagram
  - Activity Diagrams
  - Sequence Diagrams
  - Class Diagram
  - ER Diagram / Database Design
- After each future change, the root-level `PROJECT_CONTEXT.md` should be updated with the change summary, affected files, open items, and next recommended step.
