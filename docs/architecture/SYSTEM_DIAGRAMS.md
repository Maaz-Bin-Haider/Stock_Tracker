# SwissTech Inventory System Diagrams

This document explains the system using detailed diagrams in this order:

1. Use Case Diagram
2. Activity Diagrams
3. Sequence Diagrams
4. Class Diagram
5. ER Diagram / Database Design

The diagrams use Mermaid syntax, which can be rendered by GitHub and many Markdown tools.

## 1. Use Case Diagram

The use case diagram shows what each type of user can do in the system.

### Main Actors

- Admin
- Purchase User
- Sale User
- Viewer

### Main Use Cases

- Manage users and roles
- Manage settings
- Manage products
- Manage suppliers/parties
- Manage customers
- Create purchases
- Collect pending purchases
- Refund/cancel purchases
- Create shipments
- Receive shipments
- Create sales
- Perform stock adjustments
- View dashboard
- View reports
- Export reports
- View audit activity

```mermaid
flowchart LR
    Admin[Admin]
    PurchaseUser[Purchase User]
    SaleUser[Sale User]
    Viewer[Viewer]

    subgraph System[SwissTech Inventory System]
        Login((Login))
        Dashboard((View Dashboard))
        Products((View Products))
        ManageProducts((Manage Products))
        Suppliers((Manage Suppliers/Parties))
        Customers((Manage Customers))
        Purchases((Create/Update/Delete Purchases))
        Collection((Collect Pending Purchases))
        Refunds((Purchase Refunds/Cancellations))
        Shipments((Manage Shipments))
        ReceiveShipments((Receive Shipments))
        Sales((Create/Update/Delete Sales))
        Adjustments((Stock Adjustments))
        Ledger((View Stock Ledger))
        Reports((View Reports))
        ExportReports((Export Reports))
        Users((Manage Users/Roles))
        Settings((Manage Settings))
        Audit((View Audit Activity))
    end

    Admin --> Login
    Admin --> Dashboard
    Admin --> Products
    Admin --> ManageProducts
    Admin --> Suppliers
    Admin --> Customers
    Admin --> Purchases
    Admin --> Collection
    Admin --> Refunds
    Admin --> Shipments
    Admin --> ReceiveShipments
    Admin --> Sales
    Admin --> Adjustments
    Admin --> Ledger
    Admin --> Reports
    Admin --> ExportReports
    Admin --> Users
    Admin --> Settings
    Admin --> Audit

    PurchaseUser --> Login
    PurchaseUser --> Dashboard
    PurchaseUser --> Products
    PurchaseUser --> ManageProducts
    PurchaseUser --> Suppliers
    PurchaseUser --> Purchases
    PurchaseUser --> Collection
    PurchaseUser --> Refunds
    PurchaseUser --> Ledger
    PurchaseUser --> Reports
    PurchaseUser --> ExportReports
    PurchaseUser --> Audit

    SaleUser --> Login
    SaleUser --> Dashboard
    SaleUser --> Products
    SaleUser --> Customers
    SaleUser --> Sales
    SaleUser --> Ledger
    SaleUser --> Reports
    SaleUser --> ExportReports
    SaleUser --> Audit

    Viewer --> Login
    Viewer --> Dashboard
    Viewer --> Products
    Viewer --> Ledger
    Viewer --> Reports
    Viewer --> Audit

    Purchases --> Collection
    Purchases --> Refunds
    Collection --> Ledger
    Refunds --> Ledger
    Shipments --> Ledger
    ReceiveShipments --> Ledger
    Sales --> Ledger
    Adjustments --> Ledger
    Reports --> ExportReports
```

## 2. Activity Diagrams

Activity diagrams show the step-by-step business flow.

### 2.1 New System Setup Activity

```mermaid
flowchart TD
    A([Start New System]) --> B[Admin creates users and roles]
    B --> C[Create locations]
    C --> D[Create currencies]
    D --> E[Create exchange rates]
    E --> F[Create GST rates]
    F --> G[Create categories]
    G --> H[Create products]
    H --> I[Create suppliers/parties]
    I --> J[Create customers]
    J --> K[Enter opening stock manually through normal flow]
    K --> L([System ready for daily use])
```

### 2.2 Purchase Entry Activity

```mermaid
flowchart TD
    A([Start Purchase Entry]) --> B[User opens Purchases page]
    B --> C[Enter purchase invoice header]
    C --> D[Select supplier/party and location]
    D --> E[Add product line]
    E --> F{Product exists?}
    F -- No --> G[Create product from purchase entry]
    G --> H[Enter product line quantity and price]
    F -- Yes --> H
    H --> I[Select currency and GST rate]
    I --> J[Enter collected quantity if any]
    J --> K[System calculates pending quantity]
    K --> L[System calculates purchase status]
    L --> M{More product lines?}
    M -- Yes --> E
    M -- No --> N[Attach invoice file if available]
    N --> O[Save purchase invoice]
    O --> P[Audit purchase creation]
    P --> Q{Collected quantity entered?}
    Q -- Yes --> R[Create stock ledger entry for collected stock]
    Q -- No --> S[Keep quantity pending]
    R --> T([Purchase saved])
    S --> T
```

### 2.3 Purchase Collection Activity

```mermaid
flowchart TD
    A([Start Purchase Collection]) --> B[Open Purchase Collection/Pending page]
    B --> C[Search/select purchase invoice]
    C --> D[System shows pending product lines]
    D --> E[Select product line]
    E --> F[Enter collected quantity]
    F --> G{Quantity valid?}
    G -- No --> H[Show validation error]
    H --> F
    G -- Yes --> I[Save collection]
    I --> J[Increase physical stock at collection location]
    J --> K[Reduce pending quantity]
    K --> L[Update line status]
    L --> M[Create stock ledger entry]
    M --> N[Create audit activity entry]
    N --> O([Collection complete])
```

### 2.4 Purchase Refund/Cancellation Activity

```mermaid
flowchart TD
    A([Start Refund/Cancellation]) --> B[Open Purchase Refunds/Cancellations page]
    B --> C[Select purchase invoice/reference]
    C --> D[System loads invoice product lines]
    D --> E[Select product line]
    E --> F[Enter refund/cancellation quantity]
    F --> G[Enter reason and notes]
    G --> H{Quantity available for refund/cancel?}
    H -- No --> I[Show validation error]
    I --> F
    H -- Yes --> J{Quantity already received?}
    J -- Yes --> K[Create stock reversal entry]
    J -- No --> L[Reduce pending quantity only]
    K --> M[Reverse GST where relevant]
    L --> M
    M --> N[Update net quantity and line status]
    N --> O[Create refund/cancellation record]
    O --> P[Create audit activity entry]
    P --> Q([Refund/Cancellation complete])
```

### 2.5 Shipment Activity

```mermaid
flowchart TD
    A([Start Shipment]) --> B[Open Shipments page]
    B --> C[Enter shipment header]
    C --> D[Select from location and to location]
    D --> E[Add product and shipped quantity]
    E --> F{Source stock enough?}
    F -- No --> G[Show negative stock warning]
    G --> H{User confirms?}
    H -- No --> E
    H -- Yes --> I[Save shipment]
    F -- Yes --> I
    I --> J[Reduce source physical stock]
    J --> K[Increase in-transit stock]
    K --> L[Create stock ledger entries]
    L --> M[Create audit activity entry]
    M --> N([Shipment created])
```

### 2.6 Shipment Receiving Activity

```mermaid
flowchart TD
    A([Start Shipment Receiving]) --> B[Open shipment]
    B --> C[System shows shipment product lines]
    C --> D[Enter received quantity per product]
    D --> E{Received more than shipped?}
    E -- Yes --> F[Show over-receiving warning]
    F --> G{User confirms?}
    G -- No --> D
    G -- Yes --> H[Save received quantity]
    E -- No --> H
    H --> I[Reduce in-transit stock]
    I --> J[Increase destination physical stock]
    J --> K[Update shipment line remaining quantity]
    K --> L[Update shipment status]
    L --> M[Create stock ledger entries]
    M --> N[Create audit activity entry]
    N --> O([Receiving complete])
```

### 2.7 Sales Activity

```mermaid
flowchart TD
    A([Start Sale]) --> B[Open Sales page]
    B --> C[Select sale location]
    C --> D{Location is Dubai or Karachi?}
    D -- No --> E[Block sale location]
    D -- Yes --> F[Select customer]
    F --> G[Select existing product]
    G --> H[Enter quantity]
    H --> I{Enough stock?}
    I -- No --> J[Show negative stock warning]
    J --> K{User confirms?}
    K -- No --> H
    K -- Yes --> L[Save sale]
    I -- Yes --> L
    L --> M[Reduce stock at sale location]
    M --> N[Create stock ledger entry]
    N --> O[Create audit activity entry]
    O --> P([Sale complete])
```

### 2.8 Report Export Activity

```mermaid
flowchart TD
    A([Start Report]) --> B[Open Reports page]
    B --> C[Select report type]
    C --> D[Apply filters]
    D --> E[System loads filtered data]
    E --> F[Show quick totals]
    F --> G{Export needed?}
    G -- No --> H([View report only])
    G -- Yes --> I[Select Excel or PDF]
    I --> J[Generate export from filtered data only]
    J --> K[Download report]
    K --> L[Audit export if required]
    L --> M([Report complete])
```

## 3. Sequence Diagrams

Sequence diagrams show how user actions move through the application, service layer, database, stock ledger, and audit system.

### 3.1 Purchase Invoice Creation Sequence

```mermaid
sequenceDiagram
    actor User as Purchase User/Admin
    participant UI as Web App UI
    participant PurchaseService as Purchase Service
    participant ProductService as Product Service
    participant DB as Database
    participant Ledger as Stock Ledger Service
    participant Audit as Audit Service

    User->>UI: Open Purchases page
    User->>UI: Enter invoice header and product lines
    UI->>ProductService: Validate selected products
    ProductService->>DB: Check product records
    DB-->>ProductService: Product validation result
    ProductService-->>UI: Products valid
    UI->>PurchaseService: Submit purchase invoice
    PurchaseService->>PurchaseService: Calculate pending quantities and statuses
    PurchaseService->>PurchaseService: Calculate GST and AED values
    PurchaseService->>DB: Save purchase header and lines
    DB-->>PurchaseService: Purchase saved
    PurchaseService->>Ledger: Create ledger entries for collected quantities
    Ledger->>DB: Insert stock ledger records
    PurchaseService->>Audit: Record purchase creation
    Audit->>DB: Insert audit record
    PurchaseService-->>UI: Return saved purchase
    UI-->>User: Show success message
```

### 3.2 Purchase Refund/Cancellation Sequence

```mermaid
sequenceDiagram
    actor User as Purchase User/Admin
    participant UI as Web App UI
    participant RefundService as Refund/Cancellation Service
    participant PurchaseService as Purchase Service
    participant Ledger as Stock Ledger Service
    participant GST as GST Service
    participant DB as Database
    participant Audit as Audit Service

    User->>UI: Open Purchase Refunds/Cancellations
    User->>UI: Select purchase invoice
    UI->>PurchaseService: Load invoice details
    PurchaseService->>DB: Fetch purchase and lines
    DB-->>PurchaseService: Return invoice lines
    PurchaseService-->>UI: Show refundable/cancellable quantities
    User->>UI: Enter refund/cancellation quantity and reason
    UI->>RefundService: Submit refund/cancellation request
    RefundService->>DB: Validate available line quantity
    DB-->>RefundService: Quantity is valid
    RefundService->>DB: Save refund/cancellation header and lines
    RefundService->>Ledger: Create reversal ledger entries
    Ledger->>DB: Insert reversal stock entries
    RefundService->>GST: Calculate GST reversal
    GST->>DB: Save GST reversal impact
    RefundService->>PurchaseService: Update line net quantity and status
    PurchaseService->>DB: Update purchase line summary fields
    RefundService->>Audit: Record refund/cancellation activity
    Audit->>DB: Insert audit record with before/after values
    RefundService-->>UI: Return success
    UI-->>User: Show updated invoice status
```

### 3.3 Shipment and Receiving Sequence

```mermaid
sequenceDiagram
    actor User as Admin/Shipment User
    participant UI as Web App UI
    participant ShipmentService as Shipment Service
    participant StockService as Stock Service
    participant Ledger as Stock Ledger Service
    participant DB as Database
    participant Audit as Audit Service

    User->>UI: Create shipment
    UI->>ShipmentService: Submit shipment header and lines
    ShipmentService->>StockService: Validate source stock
    StockService->>DB: Check current stock balance/ledger
    DB-->>StockService: Return stock quantity
    StockService-->>ShipmentService: Stock valid or warning needed
    ShipmentService->>DB: Save shipment and lines
    ShipmentService->>Ledger: Record shipment out and in-transit entries
    Ledger->>DB: Insert ledger entries
    ShipmentService->>Audit: Record shipment creation
    Audit->>DB: Insert audit record
    ShipmentService-->>UI: Shipment saved

    User->>UI: Enter received quantity
    UI->>ShipmentService: Submit receiving details
    ShipmentService->>DB: Validate shipment lines
    ShipmentService->>Ledger: Reverse in-transit and increase destination stock
    Ledger->>DB: Insert receiving ledger entries
    ShipmentService->>DB: Update shipment received/remaining quantities
    ShipmentService->>Audit: Record shipment receiving
    Audit->>DB: Insert audit record
    ShipmentService-->>UI: Receiving saved
    UI-->>User: Show updated shipment status
```

### 3.4 Sale Entry Sequence

```mermaid
sequenceDiagram
    actor User as Sale User/Admin
    participant UI as Web App UI
    participant SaleService as Sale Service
    participant StockService as Stock Service
    participant Ledger as Stock Ledger Service
    participant DB as Database
    participant Audit as Audit Service

    User->>UI: Open Sales page
    User->>UI: Enter sale details
    UI->>SaleService: Submit sale
    SaleService->>SaleService: Validate sale location is Dubai or Karachi
    SaleService->>StockService: Check stock availability
    StockService->>DB: Query current stock
    DB-->>StockService: Return quantity
    StockService-->>SaleService: Stock status
    SaleService-->>UI: Warning if negative stock
    User->>UI: Confirm warning if needed
    UI->>SaleService: Confirm save
    SaleService->>DB: Save sale record
    SaleService->>Ledger: Create sale stock-out ledger entry
    Ledger->>DB: Insert ledger entry
    SaleService->>Audit: Record sale activity
    Audit->>DB: Insert audit record
    SaleService-->>UI: Sale saved
    UI-->>User: Show success message
```

## 4. Class Diagram

The class diagram shows the main business objects and how they relate to each other.

```mermaid
classDiagram
    class User {
        +id
        +name
        +email
        +passwordHash
        +roleId
        +status
        +createdAt
        +updatedAt
    }

    class Role {
        +id
        +name
        +description
    }

    class Product {
        +id
        +sku
        +name
        +categoryId
        +brand
        +model
        +storageSpecs
        +isActive
    }

    class Category {
        +id
        +name
        +isActive
    }

    class Location {
        +id
        +name
        +country
        +city
        +type
        +canPurchase
        +canSell
        +isActive
    }

    class Supplier {
        +id
        +name
        +phone
        +email
        +address
        +isActive
    }

    class Customer {
        +id
        +name
        +phone
        +email
        +address
        +isActive
    }

    class Purchase {
        +id
        +invoiceNo
        +purchaseDate
        +locationId
        +supplierId
        +status
        +notes
    }

    class PurchaseLine {
        +id
        +purchaseId
        +productId
        +quantity
        +unitPrice
        +currencyId
        +gstRateId
        +collectedQty
        +pendingQty
        +cancelledRefundedQty
        +netQty
        +status
    }

    class PurchaseCollection {
        +id
        +purchaseId
        +collectionDate
        +locationId
        +notes
    }

    class PurchaseCollectionLine {
        +id
        +collectionId
        +purchaseLineId
        +collectedQty
    }

    class PurchaseRefund {
        +id
        +purchaseId
        +refundDate
        +reason
        +notes
    }

    class PurchaseRefundLine {
        +id
        +refundId
        +purchaseLineId
        +quantity
        +gstReversal
        +valueReversal
    }

    class Shipment {
        +id
        +shipmentNo
        +shipmentDate
        +fromLocationId
        +toLocationId
        +shippingCost
        +status
        +notes
    }

    class ShipmentLine {
        +id
        +shipmentId
        +productId
        +shippedQty
        +receivedQty
        +remainingQty
        +status
    }

    class Sale {
        +id
        +saleNo
        +saleDate
        +locationId
        +customerId
        +notes
    }

    class SaleLine {
        +id
        +saleId
        +productId
        +quantity
        +salePrice
    }

    class StockAdjustment {
        +id
        +adjustmentDate
        +locationId
        +productId
        +quantity
        +reason
        +notes
    }

    class StockLedger {
        +id
        +transactionDate
        +transactionType
        +sourceModule
        +sourceRecordId
        +sourceLineId
        +productId
        +locationId
        +quantityIn
        +quantityOut
        +netQuantity
        +stockBucket
        +aedValue
        +gstValue
    }

    class Currency {
        +id
        +code
        +name
        +isActive
    }

    class ExchangeRate {
        +id
        +currencyId
        +rateToAed
        +effectiveDate
    }

    class GstRate {
        +id
        +locationId
        +rate
        +effectiveFrom
        +effectiveTo
        +isActive
    }

    class FileAttachment {
        +id
        +module
        +recordId
        +fileName
        +filePath
        +fileType
        +uploadedBy
    }

    class AuditLog {
        +id
        +userId
        +action
        +module
        +recordId
        +beforeValues
        +afterValues
        +createdAt
    }

    User --> Role
    Product --> Category
    Purchase --> Supplier
    Purchase --> Location
    Purchase "1" --> "many" PurchaseLine
    PurchaseLine --> Product
    PurchaseLine --> Currency
    PurchaseLine --> GstRate
    PurchaseCollection --> Purchase
    PurchaseCollection --> Location
    PurchaseCollection "1" --> "many" PurchaseCollectionLine
    PurchaseCollectionLine --> PurchaseLine
    PurchaseRefund --> Purchase
    PurchaseRefund "1" --> "many" PurchaseRefundLine
    PurchaseRefundLine --> PurchaseLine
    Shipment --> Location : from
    Shipment --> Location : to
    Shipment "1" --> "many" ShipmentLine
    ShipmentLine --> Product
    Sale --> Customer
    Sale --> Location
    Sale "1" --> "many" SaleLine
    SaleLine --> Product
    StockAdjustment --> Product
    StockAdjustment --> Location
    StockLedger --> Product
    StockLedger --> Location
    ExchangeRate --> Currency
    GstRate --> Location
    FileAttachment --> User
    AuditLog --> User
```

## 5. ER Diagram / Database Design

The ER diagram shows the database tables and their relationships.

### 5.1 Main ER Diagram

```mermaid
erDiagram
    roles ||--o{ users : has
    categories ||--o{ products : groups
    locations ||--o{ purchases : purchase_location
    suppliers ||--o{ purchases : supplies
    purchases ||--o{ purchase_lines : contains
    products ||--o{ purchase_lines : purchased
    currencies ||--o{ purchase_lines : priced_in
    gst_rates ||--o{ purchase_lines : applies

    purchases ||--o{ purchase_collections : collected_by
    locations ||--o{ purchase_collections : collection_location
    purchase_collections ||--o{ purchase_collection_lines : contains
    purchase_lines ||--o{ purchase_collection_lines : collected_line

    purchases ||--o{ purchase_refunds : refunded_by
    purchase_refunds ||--o{ purchase_refund_lines : contains
    purchase_lines ||--o{ purchase_refund_lines : refunded_line

    locations ||--o{ shipments : from_location
    locations ||--o{ shipments : to_location
    shipments ||--o{ shipment_lines : contains
    products ||--o{ shipment_lines : shipped

    customers ||--o{ sales : buys
    locations ||--o{ sales : sale_location
    sales ||--o{ sale_lines : contains
    products ||--o{ sale_lines : sold

    products ||--o{ stock_adjustments : adjusted
    locations ||--o{ stock_adjustments : adjusted_at

    products ||--o{ stock_ledger : ledger_product
    locations ||--o{ stock_ledger : ledger_location
    users ||--o{ audit_logs : performs
    users ||--o{ file_attachments : uploads
    currencies ||--o{ exchange_rates : has
    locations ||--o{ gst_rates : has

    roles {
        bigint id PK
        string name
        text description
        datetime created_at
    }

    users {
        bigint id PK
        bigint role_id FK
        string name
        string email
        string password_hash
        string status
        datetime last_login_at
        datetime created_at
        datetime updated_at
    }

    categories {
        bigint id PK
        string name
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    products {
        bigint id PK
        bigint category_id FK
        string sku
        string name
        string brand
        string model
        string storage_specs
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    locations {
        bigint id PK
        string name
        string country
        string city
        string type
        boolean can_purchase
        boolean can_sell
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    suppliers {
        bigint id PK
        string name
        string phone
        string email
        text address
        text notes
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    customers {
        bigint id PK
        string name
        string phone
        string email
        text address
        text notes
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    currencies {
        bigint id PK
        string code
        string name
        boolean is_active
    }

    exchange_rates {
        bigint id PK
        bigint currency_id FK
        decimal rate_to_aed
        date effective_date
        boolean is_active
    }

    gst_rates {
        bigint id PK
        bigint location_id FK
        decimal rate
        date effective_from
        date effective_to
        boolean is_active
    }

    purchases {
        bigint id PK
        string invoice_no
        date purchase_date
        bigint location_id FK
        bigint supplier_id FK
        string status
        text notes
        bigint created_by FK
        datetime created_at
        datetime updated_at
    }

    purchase_lines {
        bigint id PK
        bigint purchase_id FK
        bigint product_id FK
        decimal quantity
        decimal unit_price
        bigint currency_id FK
        bigint gst_rate_id FK
        decimal collected_qty
        decimal pending_qty
        decimal cancelled_refunded_qty
        decimal net_qty
        decimal gross_value_original
        decimal gst_amount_original
        decimal gst_reversal_original
        string status
    }

    purchase_collections {
        bigint id PK
        bigint purchase_id FK
        date collection_date
        bigint location_id FK
        text notes
        bigint created_by FK
        datetime created_at
    }

    purchase_collection_lines {
        bigint id PK
        bigint collection_id FK
        bigint purchase_line_id FK
        decimal collected_qty
    }

    purchase_refunds {
        bigint id PK
        bigint purchase_id FK
        date refund_date
        string refund_no
        text reason
        text notes
        bigint created_by FK
        datetime created_at
    }

    purchase_refund_lines {
        bigint id PK
        bigint refund_id FK
        bigint purchase_line_id FK
        decimal quantity
        decimal gst_reversal_original
        decimal value_reversal_original
    }

    shipments {
        bigint id PK
        string shipment_no
        date shipment_date
        bigint from_location_id FK
        bigint to_location_id FK
        decimal shipping_cost
        string status
        text notes
        bigint created_by FK
        datetime created_at
    }

    shipment_lines {
        bigint id PK
        bigint shipment_id FK
        bigint product_id FK
        decimal shipped_qty
        decimal received_qty
        decimal remaining_qty
        decimal over_received_qty
        string status
    }

    sales {
        bigint id PK
        string sale_no
        date sale_date
        bigint location_id FK
        bigint customer_id FK
        text notes
        bigint created_by FK
        datetime created_at
    }

    sale_lines {
        bigint id PK
        bigint sale_id FK
        bigint product_id FK
        decimal quantity
        decimal sale_price
    }

    stock_adjustments {
        bigint id PK
        date adjustment_date
        bigint location_id FK
        bigint product_id FK
        decimal quantity
        string adjustment_type
        text reason
        text notes
        bigint created_by FK
        datetime created_at
    }

    stock_ledger {
        bigint id PK
        datetime transaction_at
        string transaction_type
        string source_module
        bigint source_record_id
        bigint source_line_id
        bigint product_id FK
        bigint location_id FK
        decimal quantity_in
        decimal quantity_out
        decimal net_quantity
        string stock_bucket
        decimal aed_value
        decimal gst_value
        text notes
        bigint created_by FK
        datetime created_at
    }

    file_attachments {
        bigint id PK
        string module
        bigint record_id
        string file_name
        string file_path
        string file_type
        bigint uploaded_by FK
        datetime uploaded_at
    }

    audit_logs {
        bigint id PK
        bigint user_id FK
        string action
        string module
        bigint record_id
        json before_values
        json after_values
        string ip_address
        string device_info
        datetime created_at
    }
```

### 5.2 Table Design Notes

#### users

Stores system users. Every business action should be linked to the user who performed it.

Important relationships:

- belongs to role
- creates purchases, sales, shipments, refunds, adjustments, files, and audit logs

#### roles

Stores system roles:

- admin
- purchase user
- sale user
- viewer

#### products

Stores standard Product Master records.

Important rules:

- exact duplicate products should be prevented
- same name with different storage/specs is allowed
- inactive products should not appear in normal entry forms

#### locations

Stores all purchase, stock, sales, and transfer locations.

Important rules:

- Dubai and Karachi can sell
- all current locations can purchase
- Sydney, Melbourne, and Perth remain separate locations

#### purchases and purchase_lines

`purchases` stores invoice-level information.

`purchase_lines` stores product-level purchase details.

One purchase invoice can have many purchase lines.

#### purchase_collections and purchase_collection_lines

These tables track received/collected quantities against purchase lines.

Collection increases physical stock and creates ledger entries.

#### purchase_refunds and purchase_refund_lines

These tables track refund/cancellation events against a selected purchase invoice and specific purchase lines.

Refund/cancellation creates reversal entries and preserves original purchase history.

#### shipments and shipment_lines

These tables track stock transfer between locations.

Shipment lines track shipped, received, remaining, and over-received quantities.

#### sales and sale_lines

These tables track sales from Dubai and Karachi.

Sales reduce stock and create stock ledger entries.

#### stock_ledger

This is the central stock movement table.

All stock-changing actions create ledger entries.

Stock reports should be calculated from this table or from stock balances reconciled against this table.

#### audit_logs

Stores user activity.

Must include create, update, delete, login, settings changes, product creation, party creation, refund/cancellation, and other important actions.

## 6. Recommended Diagram File Split

This combined document is useful for review. If the project grows, these diagrams can later be split into:

- `docs/architecture/use-case-diagram.md`
- `docs/architecture/activity-diagrams.md`
- `docs/architecture/sequence-diagrams.md`
- `docs/architecture/class-diagram.md`
- `docs/architecture/er-diagram.md`

