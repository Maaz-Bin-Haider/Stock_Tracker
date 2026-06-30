# Software Requirements Specification

## SwissTech Inventory Management System

## 1. Introduction

### 1.1 Purpose

This Software Requirements Specification defines the requirements for the SwissTech Inventory Management System.

The system will replace the existing spreadsheet-based stock tracking process with a professional web-based inventory application. It will manage products, purchases, purchase collection, refunds/cancellations, shipments, sales, stock ledger, GST, reports, users, permissions, and audit activity.

### 1.2 Intended Audience

This document is intended for:

- business owner and decision makers
- system users
- software developers
- UI/UX designers
- QA testers
- deployment/IT support team

### 1.3 Project Scope

The system will support daily inventory operations across multiple business locations, including Australia, New Zealand, Dubai, USA, and Karachi.

The system will allow users to enter each business event once and automatically update stock, pending quantities, in-transit quantities, GST, reports, and audit history.

The system will not include profit distribution or full accounting features in the first version.

### 1.4 Definitions

| Term | Meaning |
| --- | --- |
| Product Master | Standard list of products used for purchases, sales, and stock tracking |
| Purchase Invoice | A purchase record that can contain one or more product lines |
| Purchase Collection | Receiving/collecting purchased stock from a supplier or purchase location |
| Pending Quantity | Purchased quantity not yet collected or cancelled/refunded |
| Shipment | Movement of stock from one location to another |
| In-Transit Stock | Stock shipped but not yet received at destination |
| Stock Ledger | Central transaction history of all stock movements |
| GST | Goods and Services Tax or other configurable tax for purchase locations |
| Reversal Entry | Ledger entry that reverses stock/GST/value impact without deleting original history |
| Audit Activity | Record of user actions such as create, update, delete, login, and settings changes |

### 1.5 Related Documents

The following documents support this SRS:

- `docs/requirements/PROJECT_CONTEXT.md` contains the full requirements gathering log.
- `docs/requirements/SYSTEM_SPEC.md` converts requirements into an implementation-oriented system specification.
- `docs/business-flow/EXECUTION_FLOW_NON_TECHNICAL.md` explains the end-to-end business flow for non-technical users.
- `docs/architecture/SYSTEM_DIAGRAMS.md` contains the use case diagram, activity diagrams, sequence diagrams, class diagram, and ER/database diagram.

The diagrams document should be used together with this SRS during development and QA review.

## 2. Overall Description

### 2.1 Product Perspective

The application will be a web-based inventory management system. It will replace `stock tracker.xlsx`, which currently contains multiple manual sheets for stock, purchases, shipping, GST, sales, and profit calculations.

The new system will centralize the process through controlled forms and automatically generated reports.

### 2.2 Product Functions

The system will provide:

- user login and role-based permissions
- product master management
- supplier/party master management
- customer master management
- location management
- currency and exchange rate management
- GST rate management
- purchase invoice entry with multiple product lines
- purchase collection and pending stock tracking
- purchase refund/cancellation workflow
- shipment creation and receiving
- Dubai to Karachi transfer flow
- sales entry for Dubai and Karachi
- stock adjustment
- stock ledger
- dashboard
- reports and exports
- file uploads
- audit activity

### 2.3 User Classes

| User Role | Description |
| --- | --- |
| Admin | Full access to all system functions |
| Purchase User | Can manage purchases and purchase refunds/cancellations |
| Sale User | Can manage sales |
| Viewer | Can only view data and reports |

### 2.4 Operating Environment

The system will be a web application.

Primary use:

- desktop/laptop browser

Required support:

- responsive layout for mobile phone access

Deployment plan:

- local testing first
- AWS deployment later
- initial AWS deployment can run on a single EC2 instance

### 2.5 Design and Implementation Constraints

- The system must use a database-backed model, not spreadsheet formulas.
- The stock ledger must be the source of truth for stock movement.
- Original stock-affecting records must remain traceable.
- Refunds/cancellations must use reversal entries.
- Reports must be exportable to Excel and PDF.
- PDF reports must use a clean, modern, professional style.
- The system is single-company for now but should be designed so multi-company support can be added later.

### 2.6 Assumptions and Dependencies

- Opening stock will be entered manually.
- Products, suppliers, and customers will be entered manually.
- Bulk import from Excel is not required.
- Barcode/QR scanning is not required.
- Low-stock and reorder alerts are not required.
- Profit calculation is not required.
- Backup details are deferred, but automatic backup is desired later.

## 3. System Modules

The system must include the following main navigation pages:

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

## 4. Functional Requirements

### 4.1 Authentication and Users

#### FR-001 User Login

The system shall require every user to log in using their own account.

#### FR-002 User Roles

The system shall support these roles:

- admin
- purchase user
- sale user
- viewer

#### FR-003 User Activity Tracking

The system shall record login activity and user actions in audit activity.

#### FR-004 Admin User Management

Admin users shall be able to create, update, disable, and manage users.

#### FR-005 Role Management

Only admin users shall manage user roles.

### 4.2 Permissions

#### FR-006 Admin Permissions

Admin users shall be able to perform all actions in the system.

#### FR-007 Purchase User Permissions

Purchase users shall be able to create, update, and delete:

- purchases
- purchase collections
- purchase refunds/cancellations

Purchase users shall also be able to create products during purchase entry.

#### FR-008 Sale User Permissions

Sale users shall be able to create, update, and delete sales only.

#### FR-009 Viewer Permissions

Viewer users shall be read-only for all system data.

#### FR-010 View Access

All non-viewer users shall be able to view all system data across all locations.

#### FR-011 Location Access

The system shall not restrict users by assigned location in the first version. Role permissions shall control access.

#### FR-012 Settings Permissions

Only admins shall manage:

- users
- roles
- locations
- currencies

Normal users may manage:

- GST rates
- exchange rates
- categories

### 4.3 Product Management

#### FR-013 Product Master

The system shall maintain a Product Master.

#### FR-014 Product Fields

Each product shall support:

- product code/SKU
- product name
- category
- brand
- model
- storage/specs
- active/inactive status

#### FR-015 Product Selection

Purchases and sales shall use products from Product Master.

#### FR-016 Product Creation During Purchase

Purchase users shall be able to add a new product during purchase entry.

#### FR-017 Product Creation Restriction During Sale

Sale users shall not be able to create products during sale entry.

#### FR-018 Duplicate Product Prevention

The system shall prevent exact duplicate products using case-insensitive matching.

#### FR-019 Product Variants

The system shall allow the same product name with different storage/specs.

### 4.4 Supplier and Customer Management

#### FR-020 Supplier Master

The system shall maintain supplier/party master data.

#### FR-021 Customer Master

The system shall maintain customer master data.

#### FR-022 Party-wise Records

The system shall provide party-wise purchase and sale record pages.

#### FR-023 Date Range for Party Records

Party-wise purchase and sale record pages shall support selected date ranges.

### 4.5 Location Management

#### FR-024 Location Master

The system shall maintain configurable locations.

#### FR-025 Current Locations

The system shall support:

- Sydney
- Melbourne
- Perth
- New Zealand
- Dubai
- Houston, Texas
- Karachi

#### FR-026 Purchase Locations

All current locations shall be allowed as purchase locations.

#### FR-027 Sales Locations

Only Dubai and Karachi shall be allowed as sales locations.

#### FR-028 Australia Location Tracking

Sydney, Melbourne, and Perth shall be tracked as separate stock locations.

#### FR-029 Australia Combined View

The system shall provide combined Australia stock as a calculated report/view.

### 4.6 Purchase Management

#### FR-030 Direct Purchase Entry

The system shall allow users to enter purchases directly after buying. Formal purchase orders are not required.

#### FR-031 Multi-line Purchase Invoice

One purchase invoice shall be able to contain multiple product lines.

#### FR-032 Purchase Header Fields

The purchase invoice header shall include:

- invoice/reference number
- purchase date
- purchase location/store
- supplier/party
- notes
- attachments

#### FR-033 Purchase Line Fields

Each purchase line shall include:

- product
- quantity
- per-unit price
- currency
- GST rate
- collected quantity
- pending quantity
- status
- notes

#### FR-034 No Discount Requirement

The system shall not require invoice-level or product-level discount fields.

#### FR-035 Purchase Invoice Upload

The system shall support optional upload of purchase invoice images or PDF files.

#### FR-036 Purchase Status Automation

The system shall automatically calculate purchase status from quantities.

#### FR-037 Pending Quantity Automation

The system shall automatically calculate pending quantity.

#### FR-038 Large Quantity Support

Purchase quantities shall support large quantities, including thousands of units.

### 4.7 Purchase Collection and Pending Stock

#### FR-039 Separate Collection Workflow

Purchase collection shall be separate from purchase entry.

#### FR-040 Partial Collection

The system shall allow partial collection of a purchase line.

#### FR-041 Product-wise Collection

The system shall allow collection product-by-product from a purchase invoice.

#### FR-042 Collection Stock Increase

When purchase stock is collected, the system shall increase physical stock at the collection location.

#### FR-043 Pending Purchase Tracking

The system shall track pending purchase quantities by purchase, product, and location.

### 4.8 Purchase Refunds and Cancellations

#### FR-044 Separate Refund/Cancellation Page

The system shall provide a separate Purchase Refunds/Cancellations page.

#### FR-045 Invoice Selection for Refund

The user shall select a purchase invoice/reference before performing a refund/cancellation.

#### FR-046 Load Invoice Details

After selecting a purchase invoice, the system shall display the invoice product lines and related quantities.

#### FR-047 Line-level Refund/Cancellation

The system shall allow refund/cancellation at product-line level.

#### FR-048 Partial Quantity Refund/Cancellation

The system shall allow partial quantity refund/cancellation from a product line.

#### FR-049 Pending Quantity Cancellation

The system shall allow pending quantity to be cancelled/refunded.

#### FR-050 Received Quantity Refund

The system shall allow received quantity to be refunded/cancelled and shall reverse stock where needed.

#### FR-051 Refund/Cancellation Reversal Entries

Refunds/cancellations shall create reversal ledger entries.

#### FR-052 Preserve Original Purchase

Refunds/cancellations shall not delete or overwrite original purchase history.

#### FR-053 GST Reversal

Refunds/cancellations shall reduce/reverse GST where relevant.

#### FR-054 AED Value Recalculation

Refunds/cancellations shall recalculate purchase value where relevant.

### 4.9 Shipments

#### FR-055 Shipment Module

The system shall provide a shipment module.

#### FR-056 Multi-product Shipment

One shipment shall be able to contain multiple products.

#### FR-057 Combined Shipment

Multiple purchases from one location may be combined into one shipment.

#### FR-058 Shipment Header Fields

Shipment header shall include:

- shipment/reference number
- shipment date
- from location
- to location
- shipment type
- shipping cost
- status
- notes

#### FR-059 Shipment Line Fields

Shipment lines shall include:

- product
- shipped quantity
- received quantity
- remaining quantity
- line status

#### FR-060 Shipment Statuses

The system shall support shipment statuses:

- draft
- shipped
- partially received
- fully received
- cancelled

#### FR-061 Partial Shipment Receiving

The system shall allow product-wise partial shipment receiving.

#### FR-062 Dubai Partial Receiving

Partial shipment receiving shall be supported for Dubai shipments.

#### FR-063 Shipment Stock Movement

When a shipment is shipped, the system shall reduce source stock and increase in-transit stock.

#### FR-064 Shipment Receiving Movement

When shipment stock is received, the system shall reduce in-transit stock and increase destination stock.

#### FR-065 Dubai to Karachi Shipment

The system shall support Dubai to Karachi shipment as a separate transfer flow.

#### FR-066 Shipment Currency

Shipments shall not require currency or exchange-rate handling.

### 4.10 Sales

#### FR-067 Sales Module

The system shall provide a sales module.

#### FR-068 Sales Locations

Sales shall be allowed only from Dubai and Karachi.

#### FR-069 Sale Fields

Sale entry shall include:

- sale date
- sale location
- customer
- product
- quantity
- optional sale price
- notes
- optional upload

#### FR-070 Sale Price Reference

Sale price shall be optional and recorded only for reference.

#### FR-071 No Payment Status

Payment status is not required for sales.

#### FR-072 Sale Stock Reduction

Sales shall reduce stock at the sale location.

#### FR-073 Sale Upload

The system shall allow optional upload of sale invoice image or PDF file.

### 4.11 Stock Adjustments

#### FR-074 Manual Stock Adjustment

The system shall allow manual stock adjustments.

#### FR-075 Adjustment Reason

Every stock adjustment shall require a reason.

#### FR-076 Adjustment Ledger Entry

Every stock adjustment shall create a stock ledger entry.

#### FR-077 Adjustment Audit Entry

Every stock adjustment shall create an audit activity entry.

### 4.12 Stock Ledger

#### FR-078 Central Stock Ledger

The stock ledger shall be the central source of truth for all stock movement.

#### FR-079 Automatic Ledger Entries

The system shall automatically create stock ledger entries for:

- purchase collection
- purchase refund/cancellation
- shipment out
- shipment receiving
- shipment cancellation/reversal
- sale
- stock adjustment
- edits/deletes affecting stock

#### FR-080 Ledger Fields

The stock ledger shall include:

- date/time
- transaction type
- source module
- source reference
- product
- location
- quantity in
- quantity out
- net quantity
- stock bucket
- related location
- AED value where relevant
- GST value where relevant
- created by

#### FR-081 Stock Recalculation

When users edit old purchases, sales, shipments, or adjustments, the system shall recalculate stock from the full ledger automatically.

### 4.13 Negative Stock and Warning Handling

#### FR-082 Negative Stock Allowed With Warning

The system shall allow negative stock with a warning.

#### FR-083 Confirmation for Negative Stock

Negative stock on sale or shipment shall require user confirmation before saving.

#### FR-084 Over-receiving

The system shall allow over-receiving with a warning.

#### FR-085 Mismatch Highlighting

Products with negative, over-received, or mismatch situations shall be highlighted with a clear indication color.

### 4.14 GST and Currency

#### FR-086 Base Currency

The system base currency shall be AED.

#### FR-087 Supported Currencies

The system shall support:

- AED
- AUD
- NZD
- USD
- PKR

#### FR-088 Exchange Rates

Exchange rates shall be maintained in Settings.

#### FR-089 Manual Exchange Rate Override

Purchase entry shall allow manual exchange rate override.

#### FR-090 GST Rates

GST rates shall be configurable in Settings.

#### FR-091 GST Locations

GST shall support Australia and New Zealand purchases and be expandable to other locations in the future.

#### FR-092 GST Calculation

GST shall be calculated from the purchase line GST rate and purchase value.

#### FR-093 GST Refund Reversal

GST shall reduce/reverse when a purchase refund/cancellation is recorded.

### 4.15 Dashboard

#### FR-094 Live Dashboard

The dashboard shall show live/current data by default.

#### FR-095 Dashboard Cards

The dashboard shall show:

- total company stock
- total stock by location
- pending stock
- in-transit stock
- Dubai stock
- Karachi stock
- GST total
- today's sales

#### FR-096 Past Dashboard Snapshot

Users shall be able to generate dashboard summaries for a past date and time cutoff.

### 4.16 Reports and Exports

#### FR-097 Report Filters

Reports shall support filters such as:

- date range
- time range where needed
- location
- product
- category
- supplier/party
- customer
- status

#### FR-098 Filtered Export

Exports shall include only filtered report data.

#### FR-099 Excel Export

Reports shall be exportable to Excel.

#### FR-100 PDF Export

Reports shall be exportable to PDF.

#### FR-101 PDF Design

PDF reports shall use a lightweight, modern, professional theme.

### 4.17 List Pages

#### FR-102 Search and Filter

Every list page shall support advanced, fast search and filters.

#### FR-103 Quick Totals

List pages shall show quick totals at the top where relevant.

Quick totals may include:

- total quantity
- total pending
- total received
- total shipped
- total AED value
- total GST
- total records

### 4.18 File Uploads

#### FR-104 Upload Types

The system shall support upload of images and PDF files for purchases and sales.

#### FR-105 File Storage

Files shall be stored inside the system.

#### FR-106 File Download

Uploaded files shall be downloadable from reports where relevant.

#### FR-107 File Audit

File upload activity shall be recorded in audit activity.

### 4.19 Audit Activity

#### FR-108 Audit Create Actions

The system shall audit create actions.

#### FR-109 Audit Update Actions

The system shall audit update actions and store before/after details.

#### FR-110 Audit Delete Actions

The system shall audit delete actions and preserve traceability.

#### FR-111 Audit Login Activity

The system shall audit login activity.

#### FR-112 Audit Settings Changes

The system shall audit settings changes.

#### FR-113 Audit Page

The system shall provide an Audit Activity page visible to all users.

#### FR-114 Audit Fields

Audit records shall include:

- user
- action
- module
- record reference
- before values where applicable
- after values where applicable
- date/time
- IP/device/session where available

## 5. Report Requirements

The system shall provide at least the following reports:

- Current Stock by Location
- Total Company Stock
- Australia Combined Stock
- Dubai Stock
- Karachi Stock
- Pending Purchase Stock
- Pending Purchase Stock by Location
- In-Transit Stock
- Purchase Report
- Party-wise Purchase Records
- Sales Report
- Party-wise Sale Records
- GST Report
- Refund/Cancellation Report
- Stock Ledger Report
- Stock Adjustment Report
- User Activity Report
- Upload/File Report

### 5.1 GST Report Requirements

The GST report shall show purchase invoice details at product-line level.

The GST report shall include:

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

## 6. Data Requirements

### 6.1 Suggested Database Tables

The system should include these core data tables:

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

### 6.2 Future-ready Fields

Business tables should support:

- company_id for future multi-company support
- created_by
- created_at
- updated_by
- updated_at
- deleted_by
- deleted_at
- status

## 7. Non-Functional Requirements

### 7.1 Usability

The system shall be easy for business users to operate without technical knowledge.

Forms shall use dropdowns, validations, warnings, and clear labels to reduce manual errors.

### 7.2 Performance

Search and filtering shall be fast on list pages and reports.

The system should use indexes on commonly filtered fields such as:

- date
- product
- location
- supplier/customer
- status
- source reference

### 7.3 Reliability

Stock-changing operations shall be processed reliably using database transactions.

If any part of a stock-changing operation fails, the full operation should fail and no partial stock update should be saved.

### 7.4 Security

The system shall require authenticated user access.

Users shall only perform actions allowed by their role.

Sensitive admin functions shall be restricted to admins.

### 7.5 Auditability

All important user actions shall be traceable.

The system shall preserve history for stock-affecting actions.

### 7.6 Responsiveness

The system shall be primarily designed for desktop/laptop use but must be responsive enough to open and operate on mobile phones.

### 7.7 Maintainability

The system should be modular so future locations, currencies, GST rules, companies, and reports can be added without major redesign.

### 7.8 Backup

Automatic backup is desired.

Backup schedule, retention, and restore process are deferred and shall be finalized later.

## 8. Business Rules

### 8.1 Stock Source of Truth

Stock quantities shall be calculated from stock ledger entries.

### 8.2 Original Record Preservation

Stock-affecting original records shall remain traceable even after edit, delete, refund, or cancellation.

### 8.3 Refund/Cancellation Reversal

Refunds and cancellations shall use reversal entries.

### 8.4 No Profit Calculation

Profit calculation and profit distribution are out of scope.

### 8.5 Sales Stock Locations

Only Dubai and Karachi can sell stock.

### 8.6 Purchase Locations

All configured business locations can purchase stock.

### 8.7 No Barcode Requirement

Barcode and QR code support are not required.

### 8.8 No Low Stock Alerts

Low-stock and reorder-level alerts are not required.

## 9. External Interface Requirements

### 9.1 User Interface

The system shall provide a modern web interface with main navigation, forms, searchable lists, reports, and dashboards.

### 9.2 File Interface

The system shall allow upload and download of invoice images and PDF files.

### 9.3 Export Interface

The system shall export reports to Excel and PDF.

### 9.4 Hosting Interface

The system shall be deployable on AWS after local testing.

Initial deployment may use one EC2 instance.

## 10. Out of Scope

The following are out of scope for the first version:

- profit distribution
- full accounting system
- payment status tracking
- barcode/QR scanning
- IMEI/serial tracking
- color-level product tracking
- low-stock alerts
- reorder alerts
- Excel bulk import
- multi-company active operation
- detailed backup/restore design

## 11. Open Items

The following items need final confirmation before development:

- Who can create, update, and delete shipments. Current safe default is admin-only.
- Final backup schedule, retention, and restore process.
- Final report columns after business review.
- Final AWS deployment architecture after local testing.

## 12. Acceptance Criteria

The system will be considered acceptable when:

- users can log in with role-based permissions
- products, suppliers, customers, locations, currencies, GST rates, and exchange rates can be managed
- purchases with multiple product lines can be entered
- purchase collection can handle partial quantities
- refunds/cancellations can be done against selected purchase invoices and product lines
- GST reverses correctly after refunds/cancellations
- shipments can move stock between locations and track in-transit quantities
- sales reduce stock from Dubai or Karachi
- stock ledger records all stock movements
- reports can be filtered and exported
- dashboard shows live and past cutoff summaries
- audit activity records create, update, delete, login, and important settings changes
- uploaded invoice files can be stored and downloaded
- negative stock and over-receiving warnings work correctly
- stock can be recalculated from the ledger after edits
