"""Report queries (spec section 29). Read-only aggregations over
existing tables - never mutate anything."""
from __future__ import annotations

import datetime as dt
from collections import defaultdict

from sqlalchemy.orm import Session

from database.models import Invoice, InvoiceItem, Payment, InvoiceStatus, StockTransaction


def sales_by_date_range(db: Session, date_from: dt.date, date_to: dt.date):
    start = dt.datetime.combine(date_from, dt.time.min)
    end = dt.datetime.combine(date_to, dt.time.max)
    return (
        db.query(Invoice)
        .filter(Invoice.invoice_date >= start, Invoice.invoice_date <= end,
                Invoice.status != InvoiceStatus.CANCELLED)
        .order_by(Invoice.invoice_date)
        .all()
    )


def customer_wise_sales(db: Session, date_from: dt.date = None, date_to: dt.date = None):
    invoices = _filtered_invoices(db, date_from, date_to)
    totals = defaultdict(int)
    for inv in invoices:
        totals[inv.customer_name_snapshot] += inv.grand_total_paise
    return sorted(totals.items(), key=lambda kv: -kv[1])


def product_wise_sales(db: Session, date_from: dt.date = None, date_to: dt.date = None):
    invoices = _filtered_invoices(db, date_from, date_to)
    totals = defaultdict(lambda: {"qty": 0.0, "amount": 0})
    for inv in invoices:
        for item in inv.items:
            totals[item.product_name_snapshot]["qty"] += float(item.quantity_bags)
            totals[item.product_name_snapshot]["amount"] += item.line_total_paise
    return sorted(totals.items(), key=lambda kv: -kv[1]["amount"])


def gst_summary(db: Session, date_from: dt.date = None, date_to: dt.date = None):
    invoices = _filtered_invoices(db, date_from, date_to)
    taxable = sum(i.subtotal_paise for i in invoices)
    cgst = sum(i.total_cgst_paise for i in invoices)
    sgst = sum(i.total_sgst_paise for i in invoices)
    return {"taxable_amount": taxable, "cgst": cgst, "sgst": sgst, "total_gst": cgst + sgst}


def outstanding_balances(db: Session):
    return (
        db.query(Invoice)
        .filter(Invoice.balance_paise > 0, Invoice.status != InvoiceStatus.CANCELLED)
        .order_by(Invoice.invoice_date)
        .all()
    )


def payment_history(db: Session, date_from: dt.date = None, date_to: dt.date = None):
    q = db.query(Payment)
    if date_from:
        q = q.filter(Payment.payment_date >= dt.datetime.combine(date_from, dt.time.min))
    if date_to:
        q = q.filter(Payment.payment_date <= dt.datetime.combine(date_to, dt.time.max))
    return q.order_by(Payment.payment_date.desc()).all()


def stock_movement_report(db: Session, date_from: dt.date = None, date_to: dt.date = None):
    q = db.query(StockTransaction)
    if date_from:
        q = q.filter(StockTransaction.created_at >= dt.datetime.combine(date_from, dt.time.min))
    if date_to:
        q = q.filter(StockTransaction.created_at <= dt.datetime.combine(date_to, dt.time.max))
    return q.order_by(StockTransaction.created_at.desc()).all()


def _filtered_invoices(db: Session, date_from, date_to):
    q = db.query(Invoice).filter(Invoice.status != InvoiceStatus.CANCELLED)
    if date_from:
        q = q.filter(Invoice.invoice_date >= dt.datetime.combine(date_from, dt.time.min))
    if date_to:
        q = q.filter(Invoice.invoice_date <= dt.datetime.combine(date_to, dt.time.max))
    return q.all()
