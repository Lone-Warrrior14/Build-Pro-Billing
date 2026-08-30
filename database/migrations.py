"""
First-run initialization: creates the singleton CompanySettings row, the
default invoice sequence, and a default admin user if none exist yet.
Safe to call every startup - it is a no-op if data already exists.
"""
from __future__ import annotations

from database.connection import session_scope
from database.models import CompanySettings, InvoiceSequence, User, UserRole
from utils.security import hash_password


def ensure_defaults():
    with session_scope() as db:
        settings = db.query(CompanySettings).first()
        if settings is None:
            settings = CompanySettings(
                id=1,
                company_name="BUILD PRO READY MIX",
                address="HO: No. 3-58/B, Mariam Commercial Complex, Permude, Mangalore - 574509",
                phone="+91 7338391073, 9164728829",
                email="services@buildproreadymix.com",
                website="buildproreadymix.com",
                gstin="29DMVPS9392K1ZI",
                invoice_prefix="INV-",
                invoice_start_number=1,
                default_gst_rate=18.00,
                default_cgst_rate=9.00,
                default_sgst_rate=9.00,
            )
            db.add(settings)
            db.flush()
        else:
            # Update existing single settings row if empty/default
            if not settings.company_name or settings.company_name == "BuildPro":
                settings.company_name = "BUILD PRO READY MIX"
            settings.address = "HO: No. 3-58/B, Mariam Commercial Complex, Near Canara Bank, Permude, Mangalore - 574509"
            settings.phone = "+91 7338391073, 9164728829"
            settings.email = "services@buildproreadymix.com"
            settings.website = "buildproreadymix.com"
            settings.gstin = "29DMVPS9392K1ZI"

        seq = db.query(InvoiceSequence).filter_by(
            prefix=settings.invoice_prefix).first()
        if seq is None:
            seq = InvoiceSequence(
                prefix=settings.invoice_prefix,
                last_number=settings.invoice_start_number - 1,
            )
            db.add(seq)

        admin = db.query(User).filter_by(username="admin").first()
        if admin is None:
            salt, pw_hash = hash_password("admin123")
            admin = User(
                username="admin",
                password_hash=pw_hash,
                password_salt=salt,
                full_name="Administrator",
                role=UserRole.ADMIN,
                is_active=True,
            )
            db.add(admin)

        sales = db.query(User).filter_by(username="sales").first()
        if sales is None:
            s_salt, s_hash = hash_password("sales123")
            sales = User(
                username="sales",
                password_hash=s_hash,
                password_salt=s_salt,
                full_name="Sales Executive",
                role=UserRole.SALES_EXECUTIVE,
                is_active=True,
            )
            db.add(sales)

        # Migration: Ensure maps_location_link & transport_paise columns exist on invoices
        try:
            from sqlalchemy import text
            db.execute(text("ALTER TABLE invoices ADD COLUMN maps_location_link TEXT"))
        except Exception:
            pass

        try:
            from sqlalchemy import text
            db.execute(text("ALTER TABLE invoices ADD COLUMN transport_paise INTEGER DEFAULT 0"))
        except Exception:
            pass

        try:
            from sqlalchemy import text
            db.execute(text("ALTER TABLE invoices ADD COLUMN service_charge_paise INTEGER DEFAULT 0"))
        except Exception:
            pass

        try:
            from sqlalchemy import text
            db.execute(text("ALTER TABLE invoices ADD COLUMN billing_type TEXT DEFAULT 'standard'"))
        except Exception:
            pass

        try:
            from sqlalchemy import text
            db.execute(text("ALTER TABLE customers ADD COLUMN maps_location_link TEXT"))
        except Exception:
            pass

        try:
            from sqlalchemy import text
            db.execute(text("ALTER TABLE customers ADD COLUMN customer_type TEXT DEFAULT 'shop'"))
        except Exception:
            pass

