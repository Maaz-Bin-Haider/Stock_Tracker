# SwissTech Inventory System Execution Flow

This document explains how the inventory system will be used by business users from the beginning. It is written for non-technical users and focuses on the practical daily flow, not programming or database details.

## 1. Starting With a New System

When the new system is first opened, the business will begin with a clean setup.

The first step is to create the basic records that the system needs before purchases, shipments, and sales can be entered.

Initial setup includes:

- users and roles
- locations
- currencies
- exchange rates
- GST rates
- product categories
- products
- suppliers/parties
- customers

After this setup is complete, users can start entering real business activity.

## 2. User Login

Every user logs in with their own account.

The system records who logged in, when they logged in, and what actions they performed.

User roles decide what each user can do:

- Admin can do everything.
- Purchase user can manage purchases and purchase refunds/cancellations.
- Sale user can manage sales.
- Viewer can only view records and reports.

All users except viewer can create, edit, and delete only the records allowed by their role. Every action is saved in the audit activity.

## 3. Settings Setup

Before daily work starts, the Settings page should be prepared.

Settings include:

- locations, such as Dubai, Karachi, Sydney, Melbourne, Perth, New Zealand, and Houston
- currencies, such as AED, AUD, NZD, USD, and PKR
- exchange rates
- GST rates
- product categories

GST rates, exchange rates, and categories can be managed by normal users. Users, roles, locations, and currencies are managed by admin.

## 4. Product Setup

Products are created in the Products page.

Each product should have a proper standard name so users do not type different names for the same item.

Example:

- Product name: iPhone 15 Pro
- Category: iPhone
- Brand: Apple
- Model: 15 Pro
- Storage/specs: 256GB
- Status: Active

The system allows the same product name with different storage/specs, but it should not allow exact duplicate products.

Purchase users can also create a new product while entering a purchase, if the product is not already available.

Sale users cannot create products from the sale entry page. They must select an existing product.

## 5. Supplier and Customer Setup

Supplier/party records are created for purchases.

Customer records are created for sales.

This avoids typing names differently every time and makes party-wise reports possible.

Examples:

- Supplier/party: Apple Distributor Sydney
- Customer: Dubai Walk-in Customer

## 6. Opening Stock

There is no separate opening stock import from Excel.

Opening stock will be entered manually one by one by following the normal system flow.

This means the business can enter the initial available stock carefully and avoid importing old spreadsheet mistakes.

## 7. Purchase Entry Flow

When stock is purchased, the user opens the Purchases page and creates a purchase invoice.

One purchase invoice can contain multiple products.

For each product line, the user enters:

- product
- quantity
- per-unit purchase price
- currency
- GST rate
- collected quantity
- notes if needed

The system automatically calculates:

- pending quantity
- purchase status
- GST amount
- AED value where needed

Example:

An invoice has:

- 100 units of Product A
- 50 units of Product B

If 70 units of Product A are collected now, then 30 units remain pending.

If all 50 units of Product B are collected now, then Product B becomes fully collected.

The user does not manually choose the final status. The system decides it from the quantities.

## 8. Purchase Collection Flow

Purchase collection is separate from purchase entry.

This is important because sometimes stock is purchased but not fully received immediately.

The user opens Purchase Collection/Pending and selects the purchase invoice.

The system shows all pending product lines.

The user can collect:

- full pending quantity
- partial pending quantity
- one product from an invoice
- multiple products from an invoice

When stock is collected, the system increases physical stock at the collection location.

Example:

A purchase has 100 units pending in Sydney.

The user collects 40 units today.

The system updates:

- collected quantity becomes 40
- pending quantity becomes 60
- Sydney stock increases by 40
- stock ledger records the movement

## 9. Purchase Refund/Cancellation Flow

Refunds and cancellations have a separate page.

The user first selects the purchase invoice.

The system then loads the invoice details and product lines.

The user selects the product line and enters the quantity to refund or cancel.

This can happen in different cases:

- a full product line is cancelled
- only pending quantity is cancelled
- received quantity is refunded
- part of the same product quantity was received and the remaining part is cancelled

Example:

A purchase invoice has 100 units of Product A.

70 units were received.

30 units are still pending.

Later, the supplier cancels the remaining 30 units.

The user opens Purchase Refunds/Cancellations, selects the invoice, selects Product A, and cancels 30 units.

The system updates:

- net quantity becomes 70
- pending quantity becomes 0
- cancellation is recorded
- GST is reduced where relevant
- original purchase stays visible
- reversal entry is added to the ledger
- user activity is recorded

If received stock is refunded, the system reverses the stock quantity also.

Original records are not destroyed. The system keeps the original purchase and adds proper reversal records.

## 10. Shipment Flow

Shipment is separate from purchase and collection.

Stock can be purchased and collected in one location, then shipped later.

The user creates a shipment when stock moves from one location to another.

Common shipment examples:

- Sydney to Dubai
- Melbourne to Dubai
- New Zealand to Dubai
- Houston to Dubai
- Dubai to Karachi

One shipment can contain multiple products.

The shipment form includes:

- shipment date
- from location
- to location
- products and quantities
- shipping cost
- notes

When shipment is created and marked shipped:

- stock decreases from the source location
- in-transit stock increases

When shipment is received:

- in-transit stock decreases
- destination stock increases

Partial receiving is allowed for Dubai shipments.

Example:

100 units are shipped to Dubai.

Only 70 units are received today.

The system shows:

- 70 received
- 30 remaining in transit

Later, when 30 more units arrive, the user receives the remaining quantity.

## 11. Dubai to Karachi Shipment Flow

Dubai to Karachi shipment is handled as a separate transfer process.

This shipment uses current Dubai stock.

When stock is shipped from Dubai to Karachi:

- Dubai stock decreases
- in-transit stock to Karachi increases

When Karachi receives it:

- in-transit stock decreases
- Karachi stock increases

## 12. Sales Flow

Sales can happen only from Dubai and Karachi.

The sale user opens the Sales page and creates a sale.

Sale fields include:

- sale date
- sale location
- customer
- product
- quantity
- optional sale price
- notes
- optional invoice/file upload

When a sale is saved:

- stock decreases from the sale location
- sale record is created
- stock ledger entry is created
- user activity is recorded

Sale price is only for reference. It is not used for profit calculation.

Payment status is not required.

If the sale creates negative stock, the system shows a warning and asks for confirmation before saving.

## 13. Stock Adjustment Flow

Stock adjustment is used when stock must be corrected manually.

Examples:

- stock count correction
- damaged stock
- lost stock
- extra stock found

Every adjustment requires a reason.

When adjustment is saved:

- stock increases or decreases
- stock ledger entry is created
- audit activity is recorded

Stock adjustment should only be used when normal purchase, shipment, sale, or refund flow does not explain the difference.

## 14. Stock Ledger Flow

The stock ledger records every stock movement.

Users do not manually maintain the ledger. The system creates ledger entries automatically.

Ledger entries are created for:

- purchase collection
- purchase refund/cancellation
- shipment out
- shipment receiving
- sale
- stock adjustment
- edits/deletes that affect stock

The ledger is the main history of stock.

If old records are edited, the system recalculates stock from the ledger.

## 15. Dashboard Flow

The Dashboard shows live business status by default.

It should show:

- total company stock
- stock by location
- pending stock
- in-transit stock
- Dubai stock
- Karachi stock
- GST total
- today's sales

Users can also generate dashboard data for a past date and time.

Example:

The user can check what the dashboard looked like up to yesterday at 5:00 PM.

## 16. Reports Flow

Reports are generated from system data.

Users can filter reports by:

- date range
- time range where needed
- location
- product
- category
- supplier/party
- customer
- status

Reports can be exported to:

- Excel
- PDF

Only filtered data should be exported.

PDF reports should look clean, modern, and professional.

## 17. GST Report Flow

The GST report should show purchase invoice details product line by product line.

It should include:

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

The important point is that GST should reduce properly when a purchase is refunded or cancelled.

## 18. Party-wise Records Flow

Party-wise purchase records show purchase history by supplier/party.

Party-wise sale records show sale history by customer.

These pages should support selected date ranges.

Example:

A user selects one supplier and a date range, then sees all purchases from that supplier during that period.

## 19. File Upload Flow

Users can upload files where needed.

Supported examples:

- purchase invoice image
- purchase invoice PDF
- sale invoice image
- sale invoice PDF

Files are stored inside the system and linked to the related record.

Where relevant, files should be downloadable from reports.

## 20. Audit Activity Flow

The system records user activity automatically.

Audit activity includes:

- login
- product creation
- supplier/customer creation
- purchase creation
- purchase edit
- purchase delete
- refund/cancellation
- sale creation
- sale edit
- sale delete
- shipment activity
- stock adjustment
- settings changes

For updates, the system should show before and after details.

Audit activity helps answer:

- who did this?
- when did they do it?
- what changed?
- which record was affected?

All users can view audit activity. Viewer users can only view and cannot make changes.

## 21. Search and Filter Flow

Every list page should have fast search and advanced filters.

Examples:

- search product by name
- filter purchases by supplier
- filter sales by customer
- filter stock by location
- filter refund records by invoice
- filter reports by date range

List pages should also show quick totals at the top.

Examples:

- total quantity
- total pending
- total received
- total in-transit
- total AED value where relevant
- total GST where relevant

## 22. Warning Flow

The system should warn users before saving risky entries.

Warnings include:

- negative stock
- shipping more than available stock
- selling more than available stock
- receiving more than shipped quantity
- product mismatch

The user can continue only after confirming the warning.

These warning cases should be highlighted clearly in the system.

## 23. Daily Business Flow Summary

A normal daily flow may look like this:

1. User logs in.
2. User checks Dashboard.
3. Purchase user enters new purchase invoices.
4. Purchase user collects received stock against pending purchases.
5. Purchase user records refunds/cancellations if supplier cancels or refunds anything.
6. User creates shipments when stock moves between locations.
7. User receives shipments when stock reaches destination.
8. Sale user enters Dubai or Karachi sales.
9. User checks reports and party-wise records.
10. Admin or users review audit activity if needed.

## 24. Month-End or Review Flow

At month-end or review time, users can:

- check current stock by location
- check pending purchase stock
- check in-transit stock
- review Dubai and Karachi stock
- review party-wise purchase and sale records
- review GST report
- export reports to Excel or PDF
- check audit activity

## 25. Future Deployment Flow

The system will first be tested locally.

After local testing and business confirmation, it can be deployed to AWS.

The first AWS deployment can run on a single EC2 instance.

Backup details are deferred, but automatic backup is desired for the future.

