"""Product CRUD and search (spec section 4)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from database.models import Product, CompanySettings
from utils.money import to_paise


def search_products(db: Session, term: str = ""):
    q = db.query(Product).filter(Product.is_active == True)  # noqa: E712
    if term:
        term_like = f"%{term}%"
        q = q.filter(
            (Product.product_name.ilike(term_like))
            | (Product.brand.ilike(term_like))
            | (Product.sku.ilike(term_like))
        )
    return q.order_by(Product.brand, Product.product_name).all()


def create_product(db: Session, product_name: str, brand: str = "", variant: str = "",
                    sku: str = None, mrp: float = 0, gst_rate: float = None,
                    unit: str = "Bag", opening_stock: float = 0) -> Product:
    if gst_rate is None:
        settings = db.query(CompanySettings).first()
        gst_rate = float(settings.default_gst_rate) if settings else 18.0
    product = Product(
        product_name=product_name, brand=brand, variant=variant, sku=sku or None,
        mrp_paise=to_paise(mrp), gst_rate=gst_rate, unit=unit,
        current_stock_bags=opening_stock,
    )
    db.add(product)
    db.flush()
    if opening_stock:
        from services.stock_service import stock_in
        from database.models import StockTxnType
        # opening_stock already applied above directly on the new row;
        # still log an OPENING transaction for the audit trail.
        from database.models import StockTransaction
        db.add(StockTransaction(
            product_id=product.id, txn_type=StockTxnType.OPENING,
            quantity_bags=opening_stock, balance_after_bags=opening_stock,
            notes="Opening stock on product creation",
        ))
    return product


def update_product(db: Session, product_id: int, **fields) -> Product:
    """Edits the product master record. Does NOT touch any historical
    invoice_items, which carry their own frozen snapshots."""
    product = db.get(Product, product_id)
    if "mrp" in fields:
        product.mrp_paise = to_paise(fields.pop("mrp"))
    for k, v in fields.items():
        setattr(product, k, v)
    return product


def deactivate_product(db: Session, product_id: int):
    """Soft-delete only - historical invoices referencing this product
    keep their own product_name_snapshot etc. and are unaffected."""
    product = db.get(Product, product_id)
    product.is_active = False
    return product
