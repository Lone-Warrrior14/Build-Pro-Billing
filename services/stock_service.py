"""
Stock management (spec sections 15-16).

Every movement is recorded as an immutable StockTransaction row that
carries the resulting balance at that point in time - the current stock
is never simply overwritten; it is always derived from applying a delta
and recording both the delta and the resulting balance.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from database.models import Product, StockTransaction, StockTxnType, CompanySettings


class InsufficientStockError(Exception):
    pass


def _apply_movement(db: Session, product: Product, delta_bags: Decimal,
                     txn_type: StockTxnType, reference_invoice_id: int = None,
                     reference_return_id: int = None, reason: str = "",
                     notes: str = "", user_id: int = None) -> StockTransaction:
    new_balance = Decimal(product.current_stock_bags or 0) + delta_bags

    product.current_stock_bags = new_balance
    txn = StockTransaction(
        product_id=product.id,
        txn_type=txn_type,
        quantity_bags=delta_bags,
        balance_after_bags=new_balance,
        reference_invoice_id=reference_invoice_id,
        reference_return_id=reference_return_id,
        reason=reason,
        notes=notes,
        user_id=user_id,
    )
    db.add(txn)
    return txn


def stock_in(db: Session, product_id: int, quantity_bags, notes: str = "",
             user_id: int = None, txn_type: StockTxnType = StockTxnType.PURCHASE):
    product = db.get(Product, product_id)
    return _apply_movement(db, product, Decimal(str(quantity_bags)), txn_type,
                            notes=notes, user_id=user_id)


def stock_out_for_sale(db: Session, product_id: int, quantity_bags, invoice_id: int,
                        user_id: int = None):
    product = db.get(Product, product_id)
    return _apply_movement(db, product, -Decimal(str(quantity_bags)), StockTxnType.SALE,
                            reference_invoice_id=invoice_id, user_id=user_id)


def stock_in_for_return(db: Session, product_id: int, quantity_bags, return_id: int,
                         user_id: int = None):
    product = db.get(Product, product_id)
    return _apply_movement(db, product, Decimal(str(quantity_bags)), StockTxnType.RETURN,
                            reference_return_id=return_id, user_id=user_id)


def adjust_stock(db: Session, product_id: int, new_physical_count_bags, reason: str,
                  notes: str = "", user_id: int = None):
    """Reconciles system stock to a physical count. `reason` should be
    one of: Damaged, Missing, Counting correction, Other."""
    product = db.get(Product, product_id)
    delta = Decimal(str(new_physical_count_bags)) - Decimal(product.current_stock_bags or 0)
    return _apply_movement(db, product, delta, StockTxnType.ADJUSTMENT,
                            reason=reason, notes=notes, user_id=user_id)


def get_low_stock_products(db: Session):
    settings = db.query(CompanySettings).first()
    threshold = settings.low_stock_threshold_bags if settings else 100
    return (
        db.query(Product)
        .filter(Product.is_active == True, Product.current_stock_bags <= threshold)  # noqa: E712
        .all()
    )


def get_stock_history(db: Session, product_id: int, limit: int = 200):
    return (
        db.query(StockTransaction)
        .filter_by(product_id=product_id)
        .order_by(StockTransaction.created_at.desc())
        .limit(limit)
        .all()
    )
