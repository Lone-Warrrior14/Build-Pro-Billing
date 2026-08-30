"""Sales returns (spec section 18). Never deletes/edits the original
invoice - records a separate Return + ReturnItem rows, updates stock
and ledger accordingly."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from database.models import (
    Return, ReturnItem, InvoiceItem, Invoice, Customer, LedgerEntryType,
)
from services import stock_service, customer_service


class ReturnError(Exception):
    pass


def _next_return_number(db: Session) -> str:
    count = db.query(Return).count()
    return f"RET-{count + 1:04d}"


def create_return(db: Session, original_invoice_id: int,
                   item_returns: list[tuple[int, Decimal]], reason: str = "",
                   user_id: int = None) -> Return:
    """`item_returns` is a list of (invoice_item_id, quantity_returned)."""
    invoice = db.get(Invoice, original_invoice_id)
    if invoice is None:
        raise ReturnError("Original invoice not found.")

    ret = Return(
        return_number=_next_return_number(db),
        original_invoice_id=invoice.id,
        customer_id=invoice.customer_id,
        reason=reason,
        created_by_user_id=user_id,
    )
    db.add(ret)
    db.flush()

    total = 0
    for item_id, qty in item_returns:
        item = db.get(InvoiceItem, item_id)
        if item is None or item.invoice_id != invoice.id:
            raise ReturnError("Invoice item does not belong to this invoice.")
        qty = Decimal(str(qty))
        if qty <= 0 or qty > item.quantity_bags:
            raise ReturnError(f"Invalid return quantity for {item.product_name_snapshot}.")

        amount = int(round(float(qty) * item.selling_price_paise))
        cgst = int(round(amount * float(item.cgst_rate) / 100.0))
        sgst = int(round(amount * float(item.sgst_rate) / 100.0))
        line_total = amount + cgst + sgst

        ri = ReturnItem(
            return_id=ret.id,
            original_invoice_item_id=item.id,
            product_id=item.product_id,
            product_name_snapshot=item.product_name_snapshot,
            quantity_bags=qty,
            selling_price_paise=item.selling_price_paise,
            gst_rate=item.gst_rate,
            amount_paise=line_total,
        )
        db.add(ri)
        total += line_total

        if item.product_id:
            stock_service.stock_in_for_return(db, item.product_id, qty, ret.id, user_id=user_id)

    ret.total_amount_paise = total

    customer = db.get(Customer, invoice.customer_id)
    customer_service.add_ledger_entry(
        db, customer, LedgerEntryType.RETURN,
        description=f"Return {ret.return_number} against {invoice.invoice_number}",
        credit_paise=total,
        reference_invoice_id=invoice.id,
    )
    return ret
