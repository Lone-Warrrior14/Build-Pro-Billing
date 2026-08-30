"""
Invoice numbering (spec section 9) and invoice lookup/history helpers.

The number is generated and the sequence counter incremented inside the
SAME transaction that creates the invoice row (see billing_service).
Because SQLite commits/rolls back the whole transaction atomically, a
crash after "next number computed" but before "invoice row committed"
cannot happen - either both happen or neither does. This guarantees no
duplicate/reused invoice numbers even after a crash.
"""
from __future__ import annotations

from sqlalchemy.orm import Session
from sqlalchemy import select

from database.models import InvoiceSequence, Invoice, CompanySettings


def peek_next_invoice_number(db: Session) -> str:
    """Preview only - does NOT reserve the number. Used for display on
    the New Bill screen before the invoice is actually saved."""
    settings = db.query(CompanySettings).first()
    seq = db.query(InvoiceSequence).filter_by(prefix=settings.invoice_prefix).first()
    next_num = (seq.last_number if seq else 0) + 1
    return f"{settings.invoice_prefix}{next_num:03d}"


def reserve_next_invoice_number(db: Session) -> str:
    """Atomically increments the sequence counter and returns the newly
    reserved invoice number. Must be called inside the invoice-creation
    transaction (session_scope) - if that transaction later rolls back,
    the increment rolls back too, so no gap-free guarantee is broken."""
    settings = db.query(CompanySettings).first()
    seq = (
        db.query(InvoiceSequence)
        .filter_by(prefix=settings.invoice_prefix)
        .with_for_update(read=False)  # no-op on SQLite but harmless; documents intent
        .first()
    )
    if seq is None:
        seq = InvoiceSequence(prefix=settings.invoice_prefix, last_number=0)
        db.add(seq)
        db.flush()

    seq.last_number += 1
    db.flush()
    return f"{settings.invoice_prefix}{seq.last_number:03d}"


def search_invoices(db: Session, invoice_number: str = None, shop_name: str = None,
                     phone: str = None, date_from=None, date_to=None,
                     product_name: str = None, status=None):
    q = db.query(Invoice)
    if invoice_number:
        q = q.filter(Invoice.invoice_number.ilike(f"%{invoice_number}%"))
    if shop_name:
        q = q.filter(Invoice.customer_name_snapshot.ilike(f"%{shop_name}%"))
    if phone:
        q = q.filter(Invoice.customer_phone_snapshot.ilike(f"%{phone}%"))
    if date_from:
        q = q.filter(Invoice.invoice_date >= date_from)
    if date_to:
        q = q.filter(Invoice.invoice_date <= date_to)
    if status:
        q = q.filter(Invoice.status == status)
    if product_name:
        from database.models import InvoiceItem
        q = q.join(InvoiceItem).filter(
            InvoiceItem.product_name_snapshot.ilike(f"%{product_name}%"))
    return q.order_by(Invoice.invoice_date.desc()).all()
