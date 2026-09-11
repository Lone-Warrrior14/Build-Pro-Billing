# Graph Report - buildpro  (2026-09-10)

## Corpus Check
- 62 files · ~268,200 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 670 nodes · 1994 edges · 36 communities
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 293 edges (avg confidence: 0.95)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Web Application Backend
- Client Frontend Javascript
- Local Frontend Javascript
- Desktop GUI Interface
- System Startup & Backups
- Client Billing Service
- Customers and Payments
- Stock and Inventory
- Audit and Returns Models
- Client Database Models
- Invoice Data Service
- Core Billing Logic
- Product Management Service
- Desktop Stock UI
- Desktop Customers UI
- Ledgers and Types
- Reporting Service
- Returns Logic
- Desktop Products UI
- Invoice Sequence Generator
- Pricing History Service

## God Nodes (most connected - your core abstractions)
1. `session_scope()` - 102 edges
2. `Invoice` - 57 edges
3. `InvoiceStatus` - 43 edges
4. `Customer` - 33 edges
5. `Product` - 31 edges
6. `BillingScreen` - 30 edges
7. `create_invoice()` - 24 edges
8. `to_paise()` - 24 edges
9. `create_invoice()` - 22 edges
10. `Invoice` - 21 edges

## Surprising Connections (you probably didn't know these)
- `get_dashboard_stats()` --uses--> `Product`  [INFERRED]
  app_web.py → client_update_files/database/models.py
- `manage_customers()` --uses--> `Customer`  [INFERRED]
  app_web.py → client_update_files/database/models.py
- `delete_customer()` --uses--> `Customer`  [INFERRED]
  app_web.py → client_update_files/database/models.py
- `update_customer()` --uses--> `Customer`  [INFERRED]
  app_web.py → client_update_files/database/models.py
- `get_customer_ledger()` --uses--> `Customer`  [INFERRED]
  app_web.py → client_update_files/database/models.py

## Import Cycles
- None detected.

## Communities (36 total, 0 thin omitted)

### Community 0 - "Web Application Backend"
Cohesion: 0.06
Nodes (93): admin_reset_password(), change_own_password(), delete_customer(), delete_invoice(), delete_product(), delete_user(), download_invoice_pdf(), get_current_user() (+85 more)

### Community 1 - "Client Frontend Javascript"
Cohesion: 0.06
Nodes (71): addBillLine(), addSqftBillLine(), approveOrder(), checkSession(), closeLoginOverlay(), deleteCustomer(), deleteInvoice(), deleteProduct() (+63 more)

### Community 2 - "Local Frontend Javascript"
Cohesion: 0.06
Nodes (71): addBillLine(), addSqftBillLine(), approveOrder(), checkSession(), closeLoginOverlay(), deleteCustomer(), deleteInvoice(), deleteProduct() (+63 more)

### Community 3 - "Desktop GUI Interface"
Cohesion: 0.05
Nodes (27): Flowable, generate_invoice_pdf(), OverlaidSealSign, BuildPro tax invoice PDF generator. Clean, professional layout that perfectly…, Flowable that renders seal.png with sign.png superimposed centered over it., resolve_image_path(), _safe_image(), QGroupBox (+19 more)

### Community 4 - "System Startup & Backups"
Cohesion: 0.07
Nodes (47): init_app(), init_app(), export_successful_sql_dump(), get_app_dir(), get_data_dir(), get_db_path(), get_engine(), get_mirror_db_path() (+39 more)

### Community 5 - "Client Billing Service"
Cohesion: 0.15
Nodes (24): BillingError, BillLineInput, cancel_invoice(), create_invoice(), create_order_request(), InitialPaymentInput, move_to_recycle_bin(), permanent_delete_invoice() (+16 more)

### Community 6 - "Customers and Payments"
Cohesion: 0.16
Nodes (19): Customer, LedgerEntryType, PaymentMethod, PaymentStatus, str, approve_order_request(), Approves a ORDER_REQUESTED order request., record_payment() (+11 more)

### Community 7 - "Stock and Inventory"
Cohesion: 0.18
Nodes (19): Product, StockTransaction, StockTxnType, StockTransaction, create_product(), Product, adjust_stock(), _apply_movement() (+11 more)

### Community 8 - "Audit and Returns Models"
Cohesion: 0.14
Nodes (17): AuditLog, AuthorizedDealerBrand, Base, Customer, now_utc(), PriceHistoryLog, datetime, DeclarativeBase (+9 more)

### Community 9 - "Client Database Models"
Cohesion: 0.15
Nodes (17): AuditLog, AuthorizedDealerBrand, Base, CustomerProductPrice, InvoiceSequence, now_utc(), Payment, PriceHistoryLog (+9 more)

### Community 10 - "Invoice Data Service"
Cohesion: 0.22
Nodes (6): Invoice, InvoiceStatus, Invoice numbering (spec section 9) and invoice lookup/history helpers. The…, search_invoices(), New Bill screen (spec sections 10-13, 35-36). Fast workflow: search shop ->…, All monetary values are stored in the database as integer paise (1 rupee = 100…

### Community 11 - "Core Billing Logic"
Cohesion: 0.20
Nodes (17): approve_order_request(), BillingError, cancel_invoice(), create_invoice(), create_order_request(), InitialPaymentInput, Exception, Invoice (+9 more)

### Community 12 - "Product Management Service"
Cohesion: 0.18
Nodes (10): CompanySettings, Product, Singleton-ish table (normally a single row, id=1) holding all configurable…, deactivate_product(), Session, Product CRUD and search (spec section 4)., Edits the product master record. Does NOT touch any historical invoice_items,…, Soft-delete only - historical invoices referencing this product keep their own… (+2 more)

### Community 13 - "Desktop Stock UI"
Cohesion: 0.22
Nodes (5): QDialog, QWidget, StockAdjustDialog, StockInDialog, StockScreen

### Community 14 - "Desktop Customers UI"
Cohesion: 0.24
Nodes (5): CustomerEditDialog, CustomersScreen, LedgerDialog, QDialog, QWidget

### Community 15 - "Ledgers and Types"
Cohesion: 0.23
Nodes (10): CustomerLedger, LedgerEntryType, PaymentStatus, str, Append-only running ledger per customer. `balance_after_paise` is computed and…, StockTxnType, Decimal, The core billing workflow (spec sections 10-13, 31, 38). `create_invoice()` is… (+2 more)

### Community 16 - "Reporting Service"
Cohesion: 0.39
Nodes (11): date, customer_wise_sales(), _filtered_invoices(), gst_summary(), outstanding_balances(), payment_history(), product_wise_sales(), Session (+3 more)

### Community 17 - "Returns Logic"
Cohesion: 0.20
Nodes (10): InvoiceItem, Every value here is a frozen snapshot at time of billing. Changing the Product…, Return, create_return(), _next_return_number(), Decimal, Exception, Session (+2 more)

### Community 18 - "Desktop Products UI"
Cohesion: 0.29
Nodes (4): ProductEditDialog, ProductsScreen, QDialog, QWidget

### Community 19 - "Invoice Sequence Generator"
Cohesion: 0.25
Nodes (9): CompanySettings, Singleton-ish table (normally a single row, id=1) holding all configurable…, InvoiceSequence, Durable counter for invoice numbering. A row is (prefix -> last_used_number).…, peek_next_invoice_number(), Session, Preview only - does NOT reserve the number. Used for display on the New Bill…, Atomically increments the sequence counter and returns the newly reserved… (+1 more)

### Community 20 - "Pricing History Service"
Cohesion: 0.29
Nodes (6): CustomerProductPrice, Selling-price MEMORY: the most-recently-used selling price for a given…, get_price_history(), get_suggested_price_paise(), Session, Selling-price memory (spec section 6). Rules implemented here: 1. Selling price…

## Knowledge Gaps
- **2 isolated node(s):** `state`, `state`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 165 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `session_scope()` connect `Web Application Backend` to `Desktop GUI Interface`, `System Startup & Backups`, `Invoice Data Service`, `Product Management Service`, `Desktop Stock UI`, `Desktop Customers UI`, `Desktop Products UI`?**
  _High betweenness centrality (0.108) - this node is a cross-community bridge._
- **Why does `Invoice` connect `Web Application Backend` to `Desktop GUI Interface`, `Client Billing Service`, `Customers and Payments`, `Client Database Models`, `Invoice Data Service`, `Core Billing Logic`, `Reporting Service`, `Returns Logic`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._
- **Why does `BillingScreen` connect `Desktop GUI Interface` to `Web Application Backend`, `Client Billing Service`, `Customers and Payments`, `Stock and Inventory`, `Invoice Data Service`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Are the 52 inferred relationships involving `Invoice` (e.g. with `download_invoice_pdf()` and `get_customer_ledger()`) actually correct?**
  _`Invoice` has 52 INFERRED edges - model-reasoned connections that need verification._
- **Are the 41 inferred relationships involving `InvoiceStatus` (e.g. with `download_invoice_pdf()` and `get_customer_ledger()`) actually correct?**
  _`InvoiceStatus` has 41 INFERRED edges - model-reasoned connections that need verification._
- **Are the 29 inferred relationships involving `Customer` (e.g. with `delete_customer()` and `get_customer_ledger()`) actually correct?**
  _`Customer` has 29 INFERRED edges - model-reasoned connections that need verification._
- **Are the 27 inferred relationships involving `Product` (e.g. with `delete_product()` and `get_dashboard_stats()`) actually correct?**
  _`Product` has 27 INFERRED edges - model-reasoned connections that need verification._