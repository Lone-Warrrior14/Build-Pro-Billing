# BuildPro Billing & Inventory System

A modern, offline-first billing, inventory, and delivery tracking application built for **BuildPro Ready Mix** (Permude, Mangalore, Karnataka, India).

The software provides a comprehensive solution for managing day-to-day operations: creating GST tax invoices, managing customer orders and ledgers, tracking bag-level product stock and pricing memory, handling delivery requests, printing official invoices, and automating daily database backups.

---

## 🚀 Key Features

### 1. Billing & Order Fulfillment Lifecycle
- **Order Workflow**:
  1. **Order Requested**: Initial booking of orders / pending dispatch.
  2. **Stock Ready**: Items packed, stock verified and prepared for shipment.
  3. **Delivered**: Dispatched to the customer. Delivered orders feature an **Undo** capability (to return to `stock_ready` if needed) and are **auto-purged after 30 days**.
- **Selling Price Memory**: Remembers the last customized price for each Customer + Product combination and auto-suggests it on subsequent bills while remaining fully editable.
- **Strict Invoice Numbering & Recycle Bin**: Crash-safe sequence counters (`INV-001`, `INV-002`, ...). Deleted invoices are archived into a Recycle Bin to keep numbering sequences intact and audits transparent.
- **Delivery Restrictions**: Invoices cannot be printed/finalized while in draft or order-request states—preventing premature invoicing until stock is processed and verified.

### 2. GST & Financial Precision
- **Integer Paise Architecture**: All monetary calculations are performed in integer paise (1 INR = 100 paise) to completely prevent IEEE 754 floating-point rounding drift.
- **Frozen Invoices**: Invoices freeze product details, rates, customer GSTIN, tax percentages (18% GST with CGST/SGST breakdown), and company signatures at the exact moment of issuance.
- **Transport & Service Charges**: Includes dedicated transport charge calculations (paise) and optional service fee accounting.

### 3. Customer Ledger & Inventory Management
- **Customer Types**: Distinguishes between Shop and Direct/Site customer types with Google Maps location links for easy navigation and deliveries.
- **Stock Movements**: Full audit log for stock-in, stock-out, returns, and inventory adjustments.
- **Credit & Ledger Tracking**: Tracks partial payments, credit histories, and customer balances.

### 4. Security & Administration
- **Role-Based Access**: Multi-tier permissions (Administrator, Sales Executive, Billing User, Driver/Delivery).
- **User & Password Management**: Includes self-service password changes and administrative password resets with bcrypt salting.
- **Automatic Backups**: Scheduled daily post-12 PM automated SQLite backups to the `backups/` directory, with manual snapshot and safe-restore capabilities.

---

## 🛠️ Technology Stack

- **Backend**: Python 3, Flask, SQLAlchemy ORM, SQLite
- **Frontend**: Vanilla JavaScript (ES6+), HTML5, Responsive Modern CSS, FontAwesome
- **Reporting & Documents**: ReportLab (High-resolution Tax Invoice PDF generation)
- **Networking & Access**: Built-in support for local network access, Cloudflare tunnels (`pycloudflared`), and Ngrok tunnels.

---

## 📂 Project Structure

```
Build-Pro-Billing/
├── main.py                  # Main application entry point & service coordinator
├── app_web.py               # Flask web application & REST API routes
├── requirements.txt         # Python runtime dependencies
├── buildpro.spec            # PyInstaller build configuration
├── database/
│   ├── connection.py        # Database engine & transactional session_scope()
│   ├── models.py            # SQLAlchemy database schemas & Enums
│   └── migrations.py        # Auto-migration & first-run defaults
├── services/
│   ├── billing_service.py   # Atomic invoice creation, order states & 30-day purge
│   ├── backup_service.py    # Auto-backup scheduling & restore utilities
│   ├── pricing_service.py   # Customer-product price memory
│   ├── stock_service.py     # Inventory adjustments & stock ledger
│   ├── customer_service.py  # Customer accounts & ledgers
│   └── invoice_service.py   # Numbering sequences & search
├── invoices/
│   └── invoice_generator.py # ReportLab PDF invoice generation
├── static/
│   ├── app.js               # Frontend business logic & modal management
│   └── style.css            # Responsive layout styling
├── templates/
│   └── index.html           # Single-Page Web UI layout
├── client_update_files/     # Deployment-ready update package for client machines
├── migrate_requests.py      # Standalone schema and enum migration runner
├── data/                    # SQLite database storage (buildpro.db)
└── backups/                 # Timestamped daily & manual database backups
```

---

## 💻 Installation & Setup

### Prerequisites
- Python 3.10+ (Python 3.11 / 3.12 recommended)
- Git

### 1. Clone & Set Up Virtual Environment

```bash
git clone https://github.com/Lone-Warrrior14/Build-Pro-Billing.git
cd Build-Pro-Billing

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run the Application

```bash
python main.py
```

On initial launch:
- Creates `data/buildpro.db` with all required tables and default configurations.
- Default Admin Credentials:
  - **Username**: `admin`
  - **Password**: `admin123`
- Automatically opens your default browser at `http://127.0.0.1:5000`.

---

## 📦 Client PC Updates

To deploy updates to an existing client installation:
1. Copy the contents of the [`client_update_files/`](client_update_files/) folder.
2. Paste and overwrite the files inside the client's application directory.
3. Start the application or run:
   ```bash
   python migrate_requests.py
   ```
   All database schema changes (such as `delivered_at` timestamping) and enum migrations will apply automatically.

---

## 📄 License & Ownership

Proprietary software developed for **BuildPro Ready Mix**, Mangalore. All rights reserved.
