# BuildPro Billing Software

A local, offline, Windows desktop billing and management application for
**BuildPro**, a cement dealership in Karnataka, India.

Built with Python 3, PySide6, SQLite (via SQLAlchemy), and ReportLab.

---

## 1. Key features

- Fully offline. All data lives in a single SQLite file (`data/buildpro.db`).
- **Selling-price memory**: the software remembers the last price used for
  every Shop + Product combination and suggests it next time — but the
  price is always editable and never locked.
- Cement sold **by the bag**, with MRP stored on the product and the
  actual selling price entered fresh on every invoice.
- Automatic invoice numbering (`INV-001`, `INV-002`, ...) that survives
  crashes without ever reusing a number.
- 18% default GST (9% CGST + 9% SGST for Karnataka intra-state sales),
  fully configurable, with the rate **frozen onto every historical
  invoice** so later GST changes never alter old invoices.
- Full customer ledger, stock tracking with a complete movement history,
  partial/credit payments, sales returns, and an audit log.
- Professional tax-invoice PDF generation with your logo, "Authorized
  Dealer" section, GST breakdown, signature, and company stamp — all
  configurable from Settings, and all frozen onto each invoice so
  reprints never change.
- Manual and automatic daily backups (SQLite online-backup API), with
  safe restore (the current database is archived before being replaced).
- Two user roles: **Administrator** (full access) and **Billing User**
  (create invoices, search, view, record payments).

## 2. Project structure

```
buildpro/
├── main.py                  # application entry point
├── requirements.txt
├── buildpro.spec            # PyInstaller build spec
├── database/
│   ├── connection.py         # engine/session setup, session_scope()
│   ├── models.py              # SQLAlchemy schema (all tables)
│   └── migrations.py          # first-run defaults (settings, admin user)
├── services/                  # all business logic - the UI never talks
│   │                           # to the database directly
│   ├── billing_service.py     # create_invoice() - the atomic core workflow
│   ├── pricing_service.py     # selling-price memory
│   ├── customer_service.py    # shops + ledger
│   ├── product_service.py
│   ├── stock_service.py       # stock in/out/adjust + history
│   ├── invoice_service.py     # invoice numbering + search
│   ├── returns_service.py
│   ├── backup_service.py
│   ├── report_service.py
│   └── audit_service.py
├── invoices/
│   └── invoice_generator.py   # ReportLab PDF generation
├── ui/                        # PySide6 screens
│   ├── main_window.py, login.py, dashboard.py, billing.py,
│   │   invoices.py, customers.py, products.py, stock.py,
│   │   payments.py, reports.py, settings.py
├── utils/
│   ├── money.py                # paise<->rupee helpers, INR formatting
│   └── security.py             # password hashing
├── assets/                     # uploaded logo/signature/stamp images
├── data/                       # buildpro.db lives here (created on first run)
└── backups/                    # backup_YYYY-MM-DD_HHMMSS.db files
```

## 3. Design notes (why it's built this way)

- **Money is stored as integer paise**, never as float rupees, to avoid
  floating-point rounding drift across years of invoices.
- **Every historical invoice is a frozen snapshot.** `Invoice` and
  `InvoiceItem` rows store the MRP, selling price, GST/CGST/SGST rates,
  customer name/address/GSTIN, and even the company logo/signature/stamp
  paths *as they were at the moment of billing*. Changing a product,
  customer, or Settings value later never rewrites old invoices.
- **`create_invoice()` is fully transactional.** Invoice + items + stock
  reduction + ledger update + price-memory update all happen inside one
  `session_scope()` — if anything fails (e.g. insufficient stock), the
  whole operation rolls back and nothing is half-saved.
- **Nothing is hard-deleted.** Products and shops are soft-deleted
  (`is_active = False`); invoices are only ever cancelled/voided, never
  removed, so historical reports stay accurate.
- **Invoice numbers can't be reused**, even after a crash, because the
  sequence counter is incremented in the same transaction as the invoice
  row — SQLite guarantees both happen or neither does.

## 4. Setup (development)

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 5. Running the app

```bash
python main.py
```

On first run this will:
- Create `data/buildpro.db` and all tables.
- Create a default company-settings row (18% GST, `INV-` prefix).
- Create a default administrator account:
  - **Username:** `admin`
  - **Password:** `admin123`
  - **Change this password immediately** (via Settings — see note below;
    a "Change Password" UI hook can be added to the Users/Settings screen
    for production rollout).
- Take an automatic backup if none exists for today.

## 6. First-time configuration checklist

1. Log in as `admin`.
2. Go to **Settings → Company** and enter BuildPro's name, address,
   phone, GSTIN, and upload the logo.
3. Go to **Settings → GST** and confirm the default rate (18%, 9%+9%).
4. Go to **Settings → Authorized Dealer** and enter the dealer text
   (e.g. "Authorized Dealer of UltraTech Cement, ACC Cement").
5. Go to **Settings → Signature** and **Settings → Company Stamp** and
   upload images, enter the signatory's name/designation.
6. Go to **Products** and add your cement products (brand, variant, MRP,
   GST rate, opening stock).
7. Go to **Shops** and add your regular customers (or add them on the fly
   from the New Bill screen).
8. Start billing from **New Bill**.

## 7. Building the Windows .exe

On a Windows machine (PyInstaller must build on the target OS):

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pyinstaller buildpro.spec
```

The finished app will be in `dist/BuildPro/BuildPro.exe`. Copy the whole
`dist/BuildPro` folder to the target computer — `data/`, `backups/`, and
`generated_invoices/` folders will be created next to the .exe on first
run.

```
BuildPro/
├── BuildPro.exe
├── data/
│   └── buildpro.db
├── backups/
│   └── backup_2026-08-27_090000.db
└── generated_invoices/
    └── INV-001.pdf
```

## 8. Backups

- An automatic backup is taken once per day on startup if one hasn't
  already been taken that day.
- Manual backups: **Settings → Backup → Backup Now**.
- Restoring: **Settings → Backup → Restore from Backup...** — the
  current database is archived first, so a restore can itself be undone.
- Back up the whole `backups/` folder off-machine periodically (USB
  drive, email, cloud drive) — BuildPro does not currently upload
  backups anywhere automatically.

## 9. Known limitations / suggested next steps

This is a complete, working v1 focused on reliability and correctness
of the core billing/pricing/stock/ledger workflow, per the original
spec's emphasis on a low daily volume (~10 invoices/day). A few things
worth adding before/after wider rollout:

- A "Change Password" and "Manage Users" screen (the `User`/role model
  and password hashing are already fully implemented in
  `database/models.py` / `utils/security.py` — only the CRUD screen is
  not yet wired into the UI).
- Printer selection/margins UI (the `CompanySettings` fields exist;
  wiring them to `QPrinter` for direct printing rather than
  open-the-PDF is a small addition).
- Multiple authorized-dealer brand logos on the invoice (the
  `AuthorizedDealerBrand` table exists; only a management UI is pending).
- Barcode scanning, multi-computer/network access, and cloud backup are
  intentionally out of scope for v1, per the spec, but the service-layer
  architecture (UI never touches the DB directly) is structured so they
  can be added later without a rewrite.

## 10. Running tests / sanity-checking core logic

There is no formal test suite bundled, but the core billing engine was
verified interactively during development to confirm:
- Selling-price memory suggests, then updates correctly per Shop+Product.
- MRP and historical invoices never change when prices/settings change.
- Insufficient-stock sales are blocked and roll back cleanly.
- Returns and invoice cancellations correctly reverse stock/ledger
  without deleting the original invoice.
- Invoice PDFs generate correctly from the frozen invoice snapshot.

You can re-run similar checks yourself via a Python shell using the
`services/*` modules directly against a scratch SQLite file.
