"""
Selling-price memory (spec section 6).

Rules implemented here:
  1. Selling price is NEVER stored on the Product - only MRP is.
  2. `get_suggested_price()` returns the most-recently-used price for a
     specific (customer, product) pair, or None if there is no history
     (a brand-new shop, or a shop that has never bought this product).
  3. `record_price()` is called once an invoice is finalized and
     upserts CustomerProductPrice (the "suggestion" row) and appends an
     immutable row to PriceHistoryLog (the audit trail). It must be
     called inside the same DB transaction as invoice creation.
  4. Nothing here ever touches Product.mrp_paise or any historical
     invoice/invoice_item row.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from database.models import CustomerProductPrice, PriceHistoryLog


def get_suggested_price_paise(db: Session, customer_id: int, product_id: int) -> int | None:
    row = (
        db.query(CustomerProductPrice)
        .filter_by(customer_id=customer_id, product_id=product_id)
        .first()
    )
    return row.last_selling_price_paise if row else None


def record_price(db: Session, customer_id: int, product_id: int,
                  selling_price_paise: int, invoice_id: int) -> None:
    """Upsert the suggestion row and append to the permanent audit log.
    Must be called within an existing transaction (session_scope)."""
    row = (
        db.query(CustomerProductPrice)
        .filter_by(customer_id=customer_id, product_id=product_id)
        .first()
    )
    if row is None:
        row = CustomerProductPrice(
            customer_id=customer_id,
            product_id=product_id,
            last_selling_price_paise=selling_price_paise,
            last_invoice_id=invoice_id,
        )
        db.add(row)
    else:
        row.last_selling_price_paise = selling_price_paise
        row.last_invoice_id = invoice_id

    db.add(PriceHistoryLog(
        customer_id=customer_id,
        product_id=product_id,
        invoice_id=invoice_id,
        selling_price_paise=selling_price_paise,
    ))


def get_price_history(db: Session, customer_id: int, product_id: int, limit: int = 50):
    return (
        db.query(PriceHistoryLog)
        .filter_by(customer_id=customer_id, product_id=product_id)
        .order_by(PriceHistoryLog.recorded_at.desc())
        .limit(limit)
        .all()
    )
