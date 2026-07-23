# SwissTech Stock Tracker — User Guide

A plain-language guide to using the Stock Tracker for your daily work. It explains
every screen, every button, and what happens when you use them, with worked
examples. No technical knowledge needed — if you can use a website, you can use this.

> **Golden rule:** nothing you do is ever truly lost. Refunds, cancellations,
> edits, and deletes are always recorded and reversible. Every change is stamped
> with your name and the time. So don't be afraid to make an entry — mistakes can
> be corrected, and the history stays intact.

---

## Table of contents

1. [First things first](#1-first-things-first)
2. [Signing in and finding your way around](#2-signing-in-and-finding-your-way-around)
3. [What your role lets you do](#3-what-your-role-lets-you-do)
4. [Key ideas in two minutes](#4-key-ideas-in-two-minutes)
5. [The Dashboard](#5-the-dashboard)
6. [Products](#6-products)
7. [Purchases](#7-purchases)
8. [Collection / Pending](#8-collection--pending)
9. [Refunds / Cancellations](#9-refunds--cancellations)
10. [Shipments](#10-shipments)
11. [Sales](#11-sales)
12. [Stock Adjustments](#12-stock-adjustments)
13. [Invoice files (attachments)](#13-invoice-files-attachments)
14. [Stock Ledger](#14-stock-ledger)
15. [Reports and exports](#15-reports-and-exports)
16. [Stock Valuation (admin only)](#16-stock-valuation-admin-only)
17. [Settings / master data](#17-settings--master-data)
18. [Users (admin only)](#18-users-admin-only)
19. [Audit Activity](#19-audit-activity)
20. [Common questions and problems](#20-common-questions-and-problems)
21. [Quick cheat-sheet](#21-quick-cheat-sheet)

---

## 1. First things first

The Stock Tracker keeps track of your inventory across **seven locations** —
Sydney, Melbourne, Perth, New Zealand, Dubai, Houston, and Karachi — replacing the
old spreadsheet. It records everything you buy, collect, ship between locations,
sell, and adjust, and it always knows exactly how much stock you have and where.

You'll spend most of your time on a handful of screens: **Purchases**,
**Collection**, **Shipments**, **Sales**, and **Reports**. This guide covers those
in detail, plus everything else.

**A few things to know before you start:**

- A `*` (red star) next to a field means it is **required** — you can't save
  without it.
- All dates and "today" in the system use **Dubai time**, no matter which country
  you or the stock are in.
- The base currency is **AED**. You can enter purchases in other currencies (AUD,
  USD, etc.) and the system converts them to AED for you.

---

## 2. Signing in and finding your way around

### Signing in

1. Open your web browser and go to the address your administrator gives you (for
   example `http://192.168.1.50:8080`).
2. Type your **Username** and **Password**.
3. Click **Sign in**.

If the username or password is wrong, you'll see *"Invalid username or password."*
in red — check them and try again. If you're locked out, ask your administrator to
reset your password.

### The screen layout

- **Left sidebar** — the menu. Click any item to go to that screen. The menu only
  shows the screens your role is allowed to see.
- **Main area** — the screen you're working on.
- On a **phone or small tablet**, the sidebar is hidden. Tap the **☰** (menu)
  button at the top-left to slide it open.

### The bottom of the sidebar

- Your **username** and **role** are shown.
- **Dark mode / Light mode** button — switches the colour theme. Your choice is
  remembered and follows you to any device you log in from. Use whichever is easier
  on your eyes.
- **Sign out** — logs you out. Always sign out on a shared computer.

---

## 3. What your role lets you do

Everyone can **view all data** for all locations. What differs is what you can
**create, edit, or delete**. There are four roles:

| Role | What you can change |
| --- | --- |
| **Admin** | Everything, including settings, users, adjustments, and stock valuation. |
| **Purchase User** | Products, Purchases, Collection, Refunds/Cancellations, Shipments (including receiving), Suppliers. |
| **Sale User** | Sales and Customers. |
| **Viewer** | Nothing — view and read reports only. |

**If a button like "New" or "Edit" is missing**, it's because your role can't make
that kind of change. That's normal — ask an Admin or the right role-holder to do
it, or to change your role if you need the access.

Some screens are **Admin only** and won't appear in your menu at all unless you're
an Admin: **Stock Valuation** and **Users**. **Stock Adjustments**, **Locations**,
and **Currencies** can only be *changed* by an Admin.

---

## 4. Key ideas in two minutes

Understanding these five ideas makes everything else obvious.

**1. Stock lives in three "buckets" at each location:**

- **Physical** — stock you actually have in hand right now.
- **Pending** — stock you've *purchased* but not yet *collected* from the supplier.
- **In-transit** — stock you've *shipped* from one location but the destination
  hasn't *received* yet.

**2. Buying and collecting are two separate steps.** Creating a purchase puts stock
into **Pending**. Collecting it moves it from Pending into **Physical**. This mirrors
real life: you order goods, then later pick them up.

**3. Moving stock between locations is a Shipment.** Shipping takes stock out of
**Physical** at the source into **In-transit**, and receiving moves it into
**Physical** at the destination.

**4. Sales only happen from Dubai and Karachi.** Those are the only two selling
locations. All seven locations can buy.

**5. The system never destroys history.** When you refund, cancel, edit, or delete
something, the system adds a *reversing* record rather than erasing the original.
You can always trace what happened.

**One more thing — negative stock warnings.** If an action would take stock below
zero (for example, selling more than you have on hand), the system stops and asks
you to confirm. Click **OK** to proceed anyway (the figure will show in **red** as a
warning) or **Cancel** to stop and check.

---

## 5. The Dashboard

This is your home screen (menu: **Dashboard**). It gives you the big picture at a
glance.

**The cards along the top show:**

- **Total company stock** — all physical units across every location.
- **Pending stock** — purchased but not yet collected.
- **In-transit stock** — shipped but not yet received.
- **GST total** — total GST in AED, already net of any refunds.
- **Dubai stock** and **Karachi stock** — physical units at each selling location
  (plus how much is on its way in).
- **Today's sales** — units sold today (Dubai time).

**Stock by location** (the table below) breaks physical / pending / in-transit down
for every location. A **red** physical number means that location has gone negative
— worth investigating.

### Looking at the past

Want to know what stock looked like at a past moment (say, end of last month)?

1. In **Past snapshot (Dubai time)**, pick a date and time.
2. Click **View snapshot**.

The whole dashboard rewinds to show exactly how things stood at that moment. A
yellow banner reminds you you're looking at the past. Click **Back to live** to
return to now.

---

## 6. Products

Menu: **Products**. A "product" is any item you buy, ship, or sell (for example,
*iPhone 15 128GB*). You must create a product once before you can use it in a
purchase or sale.

*(Changeable by: Admin, Purchase User.)*

### Creating a product

1. Click **New**.
2. Fill in the form:
   - **Product name** `*` — e.g. `iPhone 15`.
   - **Storage/Specs** — e.g. `128GB Black`. This helps tell similar products apart.
   - **Category** `*` — pick from the list (e.g. *Phones*). Categories are managed
     under Settings.
   - **Brand**, **Model**, **SKU** — optional extra identifiers.
   - **Active** — leave ticked. Untick to hide a product you no longer use (it stops
     appearing in the purchase/sale dropdowns but its history stays).
3. Click **Save**.

**Example:** create `iPhone 15` / `128GB Black` / category *Phones*. It now appears
in the product dropdown everywhere else.

**Heads-up:** the system won't let you create two products with the same name *and*
the same storage/specs — that prevents accidental duplicates. If you get an error
about uniqueness, the product likely already exists.

- **Edit** — change any detail. **Search** — find a product by name.

---

## 7. Purchases

Menu: **Purchases**. This is where you record buying stock. One purchase is one
**invoice**, and an invoice can have several **product lines**.

*(Changeable by: Admin, Purchase User.)*

**What a purchase does:** it puts the purchased quantity into the **Pending** bucket
at the purchase location. It does *not* add physical stock yet — that happens at
**Collection** (Section 8), unless you use the "Collected now" shortcut below.

### The summary cards

At the top you'll see running totals for the invoices currently listed: **Total
quantity**, **Collected**, **Pending**, **Value (AED)**, and **GST (AED)**.

### Creating a purchase

1. Click **New Purchase**.
2. Fill in the invoice header:
   - **Invoice/reference** `*` — the supplier's invoice number or your own reference.
   - **Purchase date** `*` — defaults to today.
   - **Location** `*` — where you're buying (any of the seven).
   - **Supplier/party** `*` — pick the supplier.
3. Add **product lines** (click **+ Add line** for more than one):
   - **Product** `*` — the item.
   - **Qty** `*` — how many.
   - **Unit price** `*` — price per unit in the chosen currency.
   - **Currency** `*` — e.g. AUD, USD, AED.
   - **Rate→AED** — the exchange rate to AED. **Leave it blank** and the system
     fills in the current rate automatically. Type a number only if you want to
     override it.
   - **Collected now** — optional shortcut. If you already have some or all of these
     units in hand, type that quantity here and the system collects them
     immediately (so they go straight into Physical). Leave blank if you'll collect
     later.
4. Add **Notes** if needed.
5. Click **Save**.

**Worked example:** You buy 10 × *iPhone 15* from *Tech Supplies AU* in **Sydney** at
**900 AUD** each, GST region Australia. Leave Rate→AED blank so it auto-fills.

- **What happens:** 10 units go into **Pending** at Sydney. The invoice shows status
  **PENDING**. The value and GST are calculated in AED and shown on the cards.
- If you'd typed `10` in **Collected now**, the 10 units would instead land in
  **Physical** at Sydney right away, and the status would be **FULLY COLLECTED**.

### Viewing invoice details

Click any invoice row to expand it. You'll see every line with its quantity, unit
price, exchange rate, value in AED, GST, how much is collected, how much is still
pending, and the line status. You can also **upload invoice files** here (Section 13).

### Statuses you'll see

- **PENDING** — nothing collected yet.
- **PARTIALLY RECEIVED** — some collected, some still pending.
- **FULLY COLLECTED** — everything collected.
- **CANCELLED / REFUNDED** — the invoice was cancelled or had stock returned.

### Editing and deleting

- **Edit** — change the invoice. Once a line has *collected* stock, its product,
  price, currency, and rate are **locked** (you can't rewrite the price of goods
  you've already received) — but you can still change quantity upward or edit
  uncollected lines. On an existing line you'll also see a **GST %** field to set the
  GST rate.
- **Delete** — removes the invoice. **What happens:** any pending and collected
  stock is reversed out, but the record stays visible in the ledger and audit
  history. You'll be asked to confirm first.

---

## 8. Collection / Pending

Menu: **Collection / Pending**. This screen lists every purchase line that still has
stock waiting to be collected. Collecting is how pending stock becomes real,
physical stock.

*(Changeable by: Admin, Purchase User.)*

### How to collect

1. (Optional) Set the **Collection date** at the top-right (defaults to today), and
   filter by **location** if you have a lot of pending lines.
2. Find the line you're collecting.
3. In the **Collect** box, type the quantity you're collecting now. The grey
   placeholder shows the full pending amount — **leave it blank to collect all of
   it.**
4. Click **Collect**.

**What happens:** the quantity moves from **Pending** into **Physical** at the
collection location. A green message confirms it, and the pending figure drops.

**Worked example:** From the Sydney iPhone purchase, 6 of the 10 have arrived.
Type `6` and click **Collect**.

- **Result:** 6 units are now **Physical** in Sydney; 4 remain **Pending**. The
  invoice status becomes **PARTIALLY RECEIVED**. Come back later and collect the
  remaining 4 (leave the box blank to grab all 4 at once).

When nothing is left to collect, the screen says *"Nothing pending — all purchased
stock has been collected."*

---

## 9. Refunds / Cancellations

Menu: **Refunds / Cancellations**. Use this when a supplier cancels part of an order,
or when you send collected goods back.

*(Changeable by: Admin, Purchase User.)*

There are two kinds, and you choose per line:

- **Pending (cancel)** — cancels units you ordered but haven't collected. Removes
  them from **Pending**.
- **Received (return stock)** — returns units you already collected. Removes them
  from **Physical**.

### How to record one

1. In the **Find purchase invoice…** box, type the invoice number, product, or
   supplier. Click the matching invoice from the dropdown.
2. The invoice's lines appear, showing **Qty**, **Collected**, **Pending**,
   **Refunded**, and **Net** (what's left after refunds).
3. On each line you want to refund/cancel:
   - Type the **Refund qty**.
   - Choose **From**: *Pending (cancel)* or *Received (return stock)*.
4. Enter a **Reason** `*` (required) — e.g. `supplier cancelled remaining units`.
   Set the **Refund date** if it isn't today.
5. Click **Record Refund/Cancellation**.

**What happens:** the stock is reversed from the right bucket, and the money and GST
are reversed too — always at the **original purchase price**, so your figures stay
correct. A green message confirms it and the original invoice history is preserved.

**Worked example:** The supplier cancels the last 4 pending iPhones. Select the
invoice, enter `4` on the line, choose *Pending (cancel)*, reason
`supplier out of stock`, and record it.

- **Result:** those 4 leave **Pending**. The invoice line's *Net* drops to 6, and
  its status becomes **CANCELLED** (or **REFUNDED** if you'd returned collected
  stock). The value and GST for those 4 are reversed.

### Refund history and undo

Below the lines, **Refund history for this invoice** lists every refund with the
value and GST reversed in AED. Made a mistake? Click **Undo** on that row to reverse
the refund itself (the stock comes back). Everything stays traceable.

**Note:** returning already-collected stock could take physical stock negative — if
so, the system asks you to confirm before continuing.

---

## 10. Shipments

Menu: **Shipments**. Use this to move stock **between locations** — for example,
Sydney → Dubai, or the special **Dubai → Karachi** transfer.

*(Changeable by: Admin, Purchase User.)*

A shipment has a lifecycle: **Draft → Shipped → Received**. Shipping removes stock
from the source; receiving adds it at the destination.

### Summary cards

**Total shipped**, **Received**, and **In transit / remaining** for the listed
shipments.

### Creating a shipment

1. Click **New Shipment**.
2. Fill in the header:
   - **Shipment date** `*`.
   - **From location** `*` and **To location** `*`.
   - **Type** — *Standard*, or *Dubai → Karachi transfer* for that specific route.
   - **Shipping cost** — optional. This is recorded but **excluded from stock
     value** (it doesn't change what your inventory is worth).
3. Add **product lines**: **Product** `*` and **Qty** `*`.
4. Choose how to save:
   - **Save Draft** — saves it without moving any stock yet. You can edit a draft
     freely.
   - **Save & Ship** — saves *and* ships immediately.

**What happens when you ship:** the quantity leaves **Physical** at the source and
enters **In-transit** toward the destination. If shipping would take the source
negative, you'll be asked to confirm.

**Worked example:** Ship 6 × *iPhone 15* from **Sydney** to **Dubai**. Click
**Save & Ship**.

- **Result:** Sydney's physical stock drops by 6; those 6 show as **In-transit** to
  Dubai. The shipment status is **SHIPPED**.

### Shipping a draft later

A draft shows **Ship** and **Edit** buttons. Click **Ship** when it actually leaves.

### Receiving

When goods arrive at the destination:

1. Click **Receive** on the shipment.
2. In the dialog, type the **Receive now** quantity for each line (the **Remaining**
   column shows what's still expected). Partial receiving is fine — receive what
   arrived.
3. Set the **Receipt date** and click **Record Receipt**.

**What happens:** received units move from **In-transit** into **Physical** at the
destination.

- **Received less than shipped?** No problem — the rest stays in-transit; receive it
  later.
- **Received more than shipped?** Allowed, but the system asks you to confirm, and
  the line is flagged **over-received** (a yellow badge) so mismatches stand out.

**Worked example:** Dubai receives all 6 iPhones. Click **Receive**, enter `6`,
record it.

- **Result:** Dubai's physical stock rises by 6; the shipment becomes **FULLY
  RECEIVED**. Those iPhones can now be sold from Dubai.

### Undo, Cancel, and Delete

Expand a shipment (click the row) to see its **Receipts**. Each receipt has an
**Undo** button (sends that received stock back to in-transit).

- **Cancel** — for a shipment that's still shipped/partly received. Unreceived stock
  returns to the source location. You'll be asked for a reason.
- **Delete** — reverses *all* of the shipment's movements. The record stays
  traceable.

---

## 11. Sales

Menu: **Sales**. Record goods sold to a customer. **Only Dubai and Karachi** can
sell, so those are the only locations in the dropdown.

*(Changeable by: Admin, Sale User.)*

### Summary cards

**Total quantity** and **Sale value (reference)** for the listed sales.

### Recording a sale

1. Click **New Sale**.
2. Header:
   - **Sale date** `*` — defaults to today.
   - **Location** `*` — Dubai or Karachi.
   - **Customer** `*`.
3. Add product lines: **Product** `*`, **Qty** `*`, and **Sale price (optional)**.
   - The sale price is **reference-only** — it's stored for your records but is not
     used to value your stock. You can leave it blank.
4. Click **Save**.

**What happens:** the quantity leaves **Physical** at that selling location.

**Worked example:** Sell 2 × *iPhone 15* to *Al Habtoor Retail* from **Dubai** at a
reference price of `3600 AED` each.

- **Result:** Dubai's physical stock drops by 2. The sale shows on today's dashboard.
- **Selling more than you have?** If Dubai only had 1 in stock, the system warns
  *"This sale takes stock negative. Record it anyway?"* — click **OK** to proceed
  (the stock shows red) or **Cancel** to stop.

### Editing and deleting

- **Edit** — change the sale (the location is locked once saved).
- **Delete** — the sold stock returns to the location, and the record stays
  traceable.

You can attach the customer invoice file to a sale — expand the row (Section 13).

---

## 12. Stock Adjustments

Menu: **Stock Adjustments**. Use this to correct physical stock that doesn't match
reality — breakage, loss, or a counting difference. **Admin only.**

### Making an adjustment

1. Click **New Adjustment**.
2. Fill in:
   - **Date** `*`.
   - **Location** `*` and **Product** `*`.
   - **Type** `*`:
     - **Decrease** — damaged, lost, or counted fewer than recorded.
     - **Increase** — extra found, or counted more than recorded.
   - **Quantity** `*`.
   - **Reason** `*` (required) — e.g. `damaged during stock count`.
   - **Notes** — optional.
3. Click **Save**.

**What happens:** physical stock at that location goes up or down by the quantity.

**Worked example:** Two iPhones in Dubai were found damaged. New Adjustment →
**Decrease**, qty `2`, reason `water damage, written off`.

- **Result:** Dubai physical stock drops by 2. If that would take it negative, the
  system asks you to confirm first.

Adjustments can be edited or deleted (the effect is reversed and stays traceable).
Every adjustment shows **who** made it and **why**.

---

## 13. Invoice files (attachments)

You can attach scanned invoices or bills to **Purchases** and **Sales**.

1. On the Purchases or Sales screen, **click a row to expand it**.
2. At the bottom you'll see **Invoice files**.
3. Click **Upload file**, choose a **PDF or image** (max **10 MB**).
4. The file appears in the list. Click its name to **download** it; click **Delete**
   to remove it.

**Heads-up:** only genuine PDF or image files are accepted — a file renamed to look
like a PDF will be rejected. Purchase files can be added by Purchase Users/Admins;
sale files by Sale Users/Admins.

---

## 14. Stock Ledger

Menu: **Stock Ledger**. This is the system's "book of record" — the ultimate source
of truth for stock. Two tabs:

### Current Balances

Shows the live quantity for every product, location, and bucket
(Physical / Pending / In-transit). Negative quantities appear in **red**. Admins
also see a **Value (AED)** column.

### Movement History

Every single stock movement ever made, newest first: the date/time (Dubai), the type
of movement (purchase, collection, sale, shipment, adjustment, reversal…), which
record it came from, the product and location, the quantity **In** or **Out**, the
AED value, and **who** did it.

**Filters** (top-right): search by product, or filter by location and bucket. Use
this screen to answer "where did this stock go?" — every change is here.

---

## 15. Reports and exports

Menu: **Reports**. Pick a report from the dropdown; each one has its own filters and
can be exported to Excel or PDF.

*(Everyone can view and export reports.)*

### Using a report

1. Choose a report from the dropdown at the top.
2. Set the **filters** shown (dates, location, product, category, supplier,
   customer, status, etc.). Numbers and totals update automatically.
3. **Clear filters** resets them.

### Exporting

- Click **Export Excel** or **Export PDF**. The file is prepared in the background;
  when it's ready it downloads automatically.
- Click **Show recent exports** at the bottom to see your last exports and download
  them again.

### The reports available

**Stock levels**

- **Current Stock by Location** — physical/in-transit/pending per product per
  location. (Can show a past snapshot via the "As of" filter.)
- **Total Company Stock** — company-wide totals per product.
- **Australia Combined Stock** — the Australian cities added together.
- **Dubai Stock** / **Karachi Stock** — available, inbound, and sold-today at each
  selling location.

**Purchasing & pending**

- **Pending Purchase Stock** — purchased-but-not-collected, per purchase line.
- **Pending Purchase Stock by Location** — the same, totalled per location.
- **Purchase Report** — purchase lines with quantities, money, and GST.
- **Party-wise Purchase Records** — purchases grouped by supplier.

**Shipping**

- **In-Transit Stock** — shipped-but-not-received, per shipment line.

**Sales**

- **Sales Report** — sale lines (with reference prices).
- **Party-wise Sale Records** — sales grouped by customer.

**Money & corrections**

- **GST Report** — GST per product line, net of reversals.
- **Refund/Cancellation Report** — refunds/cancellations with reversed AED/GST.
- **Stock Adjustment Report** — manual corrections with reasons.

**Records**

- **Stock Ledger Report** — every movement, straight from the ledger.
- **User Activity Report** — who did what, when.
- **Upload/File Report** — uploaded invoice files with download links.

---

## 16. Stock Valuation (admin only)

Menu: **Stock Valuation**. **Admins only** — it won't appear for other roles.

This shows what your stock is **worth** in AED, using weighted-average cost per
product per location. Value follows the stock through all three buckets (physical,
in-transit, pending). Shipping costs are excluded. Two tabs:

- **Summary** — total worth by bucket, location, and category.
- **Detail** — the average cost and value for each product at each location.

Both can be filtered and exported to Excel/PDF like any other report.

---

## 17. Settings / master data

These screens hold the reference lists everything else uses. Usually an
administrator sets them up once, and you rarely touch them. Each works the same way:
**New** to add, **Edit** to change, **Delete** to remove, **Search** to find.

| Screen | What it holds | Who can change it |
| --- | --- | --- |
| **Categories** | Product groupings (Phones, Laptops…). | Admin, Purchase, Sale |
| **Locations** | The seven locations and their rules (can purchase? can sell?). | Admin |
| **Currencies** | Currency codes (AED, AUD, USD…). | Admin |
| **Exchange Rates** | Rate of each currency to AED, with an effective date. | Admin, Purchase, Sale |
| **GST Rates** | GST percentage per location, with date ranges. | Admin, Purchase, Sale |
| **Suppliers** | Who you buy from. | Admin, Purchase |
| **Customers** | Who you sell to. | Admin, Sale |

**Exchange Rates example:** add `AUD`, rate to AED `2.45`, effective today. From then
on, new AUD purchases auto-fill that rate (you can still override it on any line).

**GST Rates example:** add a rate for `Sydney` of `10%` effective from a date. Sydney
purchases then calculate 10% GST automatically.

**Tip:** because purchases and sales pick from these lists, make sure the supplier,
customer, category, and currency you need exist *before* you start an entry. If a
dropdown is empty, the list hasn't been set up yet — ask an Admin.

---

## 18. Users (admin only)

Menu: **Users**. **Admins only.** Create and manage the people who can log in.

- **New** — set a **Username** `*`, optional email/name, a **Role** `*` (Admin /
  Purchase User / Sale User / Viewer), and a **Password**.
- **Edit** — change details or role. Leave the password field **blank to keep the
  current one**; type a new one only to reset it.
- Users are never deleted — untick **Active** to disable someone's login instead
  (their history stays intact).

---

## 19. Audit Activity

Menu: **Audit Activity**. A read-only record of everything that happens in the
system: who logged in, who created/edited/deleted what, and when. Click **before /
after** on a row to see exactly what changed. Everyone can view it. Use it to answer
"who changed this, and when?"

---

## 20. Common questions and problems

**I made a mistake on an entry — what do I do?**
Almost everything can be fixed. Use **Edit** to correct it, or **Delete/Undo** to
reverse it. The original always stays in the history, so you can't "break" anything
permanently. For purchases, use **Refunds / Cancellations**; for shipments, use
**Undo** on a receipt or **Cancel**.

**A number is showing in red.**
Red means the stock has gone **negative** at that location — usually because
something was sold, shipped, or adjusted out before it was actually available.
Check the **Stock Ledger** to see what happened, then collect/receive the missing
stock or make an adjustment to correct it.

**The system asked "…take stock negative… anyway?"**
You're about to push stock below zero. If you're sure (e.g. the goods really did
leave), click **OK**. If not, click **Cancel** and check your figures first.

**A button I need (New / Edit / Ship / Receive) isn't there.**
Your role doesn't allow that change, or the record isn't at the right stage (for
example, you can only **Receive** a shipment that has been **Shipped**). Check
Section 3, or ask the right person.

**A dropdown (product, supplier, currency…) is empty.**
That reference list hasn't been set up yet. Ask an Admin to add the item under
**Settings** (or **Products** for products), then try again.

**I can't collect / sell an item.**
Make sure it exists as a **Product** and that there's stock in the right bucket at
the right location. Remember: you can only sell from **Dubai** or **Karachi**.

**The dates look off by a few hours.**
All times are shown in **Dubai time** on purpose, so everyone sees one consistent
"today", regardless of where they are.

**I forgot my password.**
Ask your administrator to reset it on the **Users** screen.

---

## 21. Quick cheat-sheet

| I want to… | Go to… | Then… |
| --- | --- | --- |
| Record buying stock | **Purchases** → New Purchase | Fill the invoice + lines, Save |
| Turn purchased stock into real stock | **Collection / Pending** | Enter qty, click Collect |
| Cancel an order / return goods | **Refunds / Cancellations** | Find invoice, enter qty + reason, Record |
| Move stock between locations | **Shipments** → New Shipment | Save & Ship, then Receive at the other end |
| Record a sale (Dubai/Karachi) | **Sales** → New Sale | Fill customer + lines, Save |
| Fix a stock count (Admin) | **Stock Adjustments** → New Adjustment | Increase/Decrease with a reason |
| Attach an invoice scan | **Purchases**/**Sales** → expand row | Upload file (PDF/image) |
| See how much stock I have | **Dashboard** or **Stock Ledger** | Read the cards / Current Balances |
| Get a printable/Excel report | **Reports** | Pick report, set filters, Export |
| See what stock is worth (Admin) | **Stock Valuation** | Summary or Detail tab |
| See who changed something | **Audit Activity** | Search, expand before/after |

---

*Remember the golden rule: you can't permanently break anything. Every action is
recorded, reversible, and stamped with your name — so record entries with
confidence, and correct mistakes as you find them.*
