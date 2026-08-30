"""
BuildPro billing software - database models.

Design principles (see project spec):
  * Historical invoice data is NEVER derived at read time from current
    product/customer/GST/settings state. Every value that could change
    later (MRP, selling price, GST rate, CGST/SGST, customer name/address/
    GSTIN, company details) is captured and stored directly on the
    invoice / invoice item row at the moment the invoice is completed.
  * Nothing is hard-deleted. Products and shops are soft-deleted via
    `is_active`. Invoices are never deleted, only cancelled/void.
  * Money is stored as integer paise (1/100 rupee) to avoid floating
    point rounding problems. Helper properties expose rupee values.
"""
from __future__ import annotations

import datetime as dt
import enum

from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, ForeignKey, Integer, LargeBinary,
    Numeric, String, Text, UniqueConstraint, Index, CheckConstraint
)
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped


class Base(DeclarativeBase):
    pass


def now_utc() -> dt.datetime:
    return dt.datetime.utcnow()


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    BILLING = "billing"
    SALES_EXECUTIVE = "sales_executive"
    WORKER = "worker"


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DELETED = "deleted"


class PaymentStatus(str, enum.Enum):
    UNPAID = "unpaid"
    PARTIAL = "partial"
    PAID = "paid"


class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    UPI = "upi"
    BANK = "bank"
    OTHER = "other"


class StockTxnType(str, enum.Enum):
    OPENING = "opening"
    PURCHASE = "purchase"
    SALE = "sale"
    RETURN = "return"
    ADJUSTMENT = "adjustment"


class LedgerEntryType(str, enum.Enum):
    OPENING = "opening"
    INVOICE = "invoice"
    PAYMENT = "payment"
    RETURN = "return"
    ADJUSTMENT = "adjustment"


# ---------------------------------------------------------------------------
# Company / Settings
# ---------------------------------------------------------------------------

class CompanySettings(Base):
    """Singleton-ish table (normally a single row, id=1) holding all
    configurable BuildPro settings. Kept as key/value-free explicit
    columns for simplicity and type safety."""
    __tablename__ = "company_settings"

    id = Column(Integer, primary_key=True)

    # Company
    company_name = Column(String, default="BUILD PRO READY MIX")
    logo_path = Column(String, nullable=True)
    address = Column(Text, default="HO: Ground Floor Koya Complex,Near Bajpe Main Bus Stand, Bajpe, D.K - 574142\nBranch: Near Ajanadri Temple, Adkar, Sullia, D.K Karnataka.")
    phone = Column(String, default="+91 7338391073, 9164728829")
    email = Column(String, default="services@buildproreadymix.com")
    website = Column(String, default="buildproreadymix.com")
    gstin = Column(String, default="29DMVPS9392K1ZI")

    # Invoice
    invoice_prefix = Column(String, default="INV-")
    invoice_start_number = Column(Integer, default=1)
    paper_size = Column(String, default="A4")
    invoice_format = Column(String, default="standard")
    show_mrp = Column(Boolean, default=True)
    show_customer_signature = Column(Boolean, default=True)
    show_company_signature = Column(Boolean, default=True)
    show_company_stamp = Column(Boolean, default=True)
    show_authorized_dealer = Column(Boolean, default=True)

    # GST defaults (only affect *new* invoices; historical invoices are
    # never touched)
    default_gst_rate = Column(Numeric(5, 2), default=18.00)
    default_cgst_rate = Column(Numeric(5, 2), default=9.00)
    default_sgst_rate = Column(Numeric(5, 2), default=9.00)

    # Authorized dealer
    dealer_text = Column(Text, default="")

    # Signature
    signatory_name = Column(String, default="")
    signatory_designation = Column(String, default="")
    signature_path = Column(String, nullable=True)
    signature_enabled = Column(Boolean, default=True)
    signature_width_mm = Column(Numeric(6, 2), default=35.0)

    # Stamp
    stamp_path = Column(String, nullable=True)
    stamp_enabled = Column(Boolean, default=True)
    stamp_width_mm = Column(Numeric(6, 2), default=30.0)

    # Printing
    default_printer = Column(String, nullable=True)
    print_copies = Column(Integer, default=1)
    print_margin_mm = Column(Numeric(6, 2), default=10.0)

    # Stock
    allow_negative_stock = Column(Boolean, default=True)
    low_stock_threshold_bags = Column(Integer, default=100)

    # Backup
    backup_folder = Column(String, default="backups")
    auto_backup_enabled = Column(Boolean, default=True)

    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)


class AuthorizedDealerBrand(Base):
    """A BuildPro invoice can show one or more authorized-dealer brand
    logos (e.g. 'Authorized Dealer of UltraTech, ACC')."""
    __tablename__ = "authorized_dealer_brands"

    id = Column(Integer, primary_key=True)
    brand_name = Column(String, nullable=False)
    logo_path = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    password_salt = Column(String, nullable=False)
    full_name = Column(String, default="")
    role = Column(Enum(UserRole), default=UserRole.BILLING, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now_utc)


# ---------------------------------------------------------------------------
# Customers / Shops
# ---------------------------------------------------------------------------

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True)
    shop_name = Column(String, nullable=False, index=True)
    contact_person = Column(String, default="")
    phone = Column(String, default="", index=True)
    address = Column(Text, default="")
    gstin = Column(String, default="")
    maps_location_link = Column(String, default="")
    customer_type = Column(String, default="shop", index=True)  # 'shop' for standard products, 'client' for construction sqft
    opening_balance_paise = Column(Integer, default=0)  # +ve = customer owes BuildPro
    notes = Column(Text, default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now_utc)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)

    price_history: Mapped[list["CustomerProductPrice"]] = relationship(
        back_populates="customer")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="customer")
    ledger_entries: Mapped[list["CustomerLedger"]] = relationship(
        back_populates="customer", order_by="CustomerLedger.entry_date")

    @property
    def opening_balance(self) -> float:
        return self.opening_balance_paise / 100.0

    def __repr__(self):
        return f"<Customer {self.shop_name}>"


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    product_name = Column(String, nullable=False, index=True)
    brand = Column(String, default="", index=True)
    variant = Column(String, default="")  # e.g. OPC 53 Grade, PPC
    sku = Column(String, unique=True, nullable=True)
    mrp_paise = Column(Integer, nullable=False, default=0)
    gst_rate = Column(Numeric(5, 2), nullable=False, default=18.00)
    unit = Column(String, default="Bag")
    current_stock_bags = Column(Numeric(12, 2), default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now_utc)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)

    price_history: Mapped[list["CustomerProductPrice"]] = relationship(
        back_populates="product")

    @property
    def mrp(self) -> float:
        return self.mrp_paise / 100.0

    def __repr__(self):
        return f"<Product {self.brand} {self.product_name}>"


class CustomerProductPrice(Base):
    """Selling-price MEMORY: the most-recently-used selling price for a
    given (customer, product) pair. This is only ever a *suggestion* on
    the New Bill screen - it is looked up fresh each time and can always
    be overridden. It is updated (not appended) every time an invoice is
    completed with a new price. Full price history is kept separately in
    PriceHistoryLog for audit/reporting purposes.
    """
    __tablename__ = "customer_product_price_history"
    __table_args__ = (
        UniqueConstraint("customer_id", "product_id", name="uq_customer_product"),
    )

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    last_selling_price_paise = Column(Integer, nullable=False)
    last_invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)

    customer: Mapped["Customer"] = relationship(back_populates="price_history")
    product: Mapped["Product"] = relationship(back_populates="price_history")

    @property
    def last_selling_price(self) -> float:
        return self.last_selling_price_paise / 100.0


class PriceHistoryLog(Base):
    """Append-only audit trail of every selling price ever used for a
    customer+product, one row per invoice item. Never modified or
    deleted."""
    __tablename__ = "price_history_log"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    selling_price_paise = Column(Integer, nullable=False)
    recorded_at = Column(DateTime, default=now_utc)


# ---------------------------------------------------------------------------
# Invoice sequence
# ---------------------------------------------------------------------------

class InvoiceSequence(Base):
    """Durable counter for invoice numbering. A row is (prefix ->
    last_used_number). Incremented inside the same DB transaction as
    invoice creation so a crash can never cause number reuse."""
    __tablename__ = "invoice_sequences"

    id = Column(Integer, primary_key=True)
    prefix = Column(String, unique=True, nullable=False)
    last_number = Column(Integer, nullable=False, default=0)


# ---------------------------------------------------------------------------
# Invoices
# ---------------------------------------------------------------------------

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True)
    invoice_number = Column(String, unique=True, nullable=False, index=True)
    invoice_date = Column(DateTime, default=now_utc, nullable=False)

    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)

    # Snapshot of customer details AT THE TIME of invoicing, so that
    # later edits to the Customer record never alter a historical
    # invoice's printed details.
    customer_name_snapshot = Column(String, nullable=False)
    customer_address_snapshot = Column(Text, default="")
    customer_phone_snapshot = Column(String, default="")
    customer_gstin_snapshot = Column(String, default="")

    # Snapshot of company details/branding at time of issue
    company_name_snapshot = Column(String, default="")
    company_address_snapshot = Column(Text, default="")
    company_phone_snapshot = Column(String, default="")
    company_email_snapshot = Column(String, default="")
    company_website_snapshot = Column(String, default="")
    company_gstin_snapshot = Column(String, default="")
    logo_path_snapshot = Column(String, nullable=True)
    signature_path_snapshot = Column(String, nullable=True)
    signatory_name_snapshot = Column(String, default="")
    signatory_designation_snapshot = Column(String, default="")
    stamp_path_snapshot = Column(String, nullable=True)
    dealer_text_snapshot = Column(Text, default="")
    is_sealed = Column(Boolean, default=False)
    billing_type = Column(String, default="standard") # 'standard' or 'construction_sqft'
    maps_location_link = Column(Text, nullable=True)

    subtotal_paise = Column(Integer, default=0)          # sum of taxable amounts
    discount_paise = Column(Integer, default=0)
    transport_paise = Column(Integer, default=0)         # extra transport/freight (GST-free)
    service_charge_paise = Column(Integer, default=0)    # extra service charge (GST-free)
    total_cgst_paise = Column(Integer, default=0)
    total_sgst_paise = Column(Integer, default=0)
    round_off_paise = Column(Integer, default=0)
    grand_total_paise = Column(Integer, default=0)

    amount_paid_paise = Column(Integer, default=0)
    balance_paise = Column(Integer, default=0)

    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.COMPLETED, nullable=False)
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.UNPAID, nullable=False)

    notes = Column(Text, default="")
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=now_utc)
    cancelled_at = Column(DateTime, nullable=True)
    cancelled_reason = Column(Text, nullable=True)

    customer: Mapped["Customer"] = relationship(back_populates="invoices")
    created_by_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_user_id])
    items: Mapped[list["InvoiceItem"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan",
        order_by="InvoiceItem.id")
    payments: Mapped[list["Payment"]] = relationship(back_populates="invoice")

    @property
    def grand_total(self) -> float:
        return self.grand_total_paise / 100.0

    @property
    def balance(self) -> float:
        return self.balance_paise / 100.0

    def __repr__(self):
        return f"<Invoice {self.invoice_number}>"


class InvoiceItem(Base):
    """Every value here is a frozen snapshot at time of billing. Changing
    the Product row later (MRP, GST rate, name) must never alter this
    row."""
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)  # nullable: product may later be deleted

    product_name_snapshot = Column(String, nullable=False)
    brand_snapshot = Column(String, default="")
    unit_snapshot = Column(String, default="Bag")

    quantity_bags = Column(Numeric(12, 2), nullable=False)
    mrp_paise = Column(Integer, nullable=False)
    selling_price_paise = Column(Integer, nullable=False)
    gst_rate = Column(Numeric(5, 2), nullable=False)
    cgst_rate = Column(Numeric(5, 2), nullable=False)
    sgst_rate = Column(Numeric(5, 2), nullable=False)

    taxable_amount_paise = Column(Integer, nullable=False)
    cgst_amount_paise = Column(Integer, nullable=False)
    sgst_amount_paise = Column(Integer, nullable=False)
    line_total_paise = Column(Integer, nullable=False)

    invoice: Mapped["Invoice"] = relationship(back_populates="items")

    @property
    def selling_price(self) -> float:
        return self.selling_price_paise / 100.0


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    amount_paise = Column(Integer, nullable=False)
    method = Column(Enum(PaymentMethod), default=PaymentMethod.CASH, nullable=False)
    payment_date = Column(DateTime, default=now_utc, nullable=False)
    notes = Column(Text, default="")
    recorded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=now_utc)

    invoice: Mapped["Invoice"] = relationship(back_populates="payments")

    @property
    def amount(self) -> float:
        return self.amount_paise / 100.0


# ---------------------------------------------------------------------------
# Customer ledger
# ---------------------------------------------------------------------------

class CustomerLedger(Base):
    """Append-only running ledger per customer. `balance_after_paise` is
    computed and stored at insert time (never recalculated
    retroactively) so that the ledger reads exactly as it did the day it
    was recorded."""
    __tablename__ = "customer_ledger"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    entry_type = Column(Enum(LedgerEntryType), nullable=False)
    reference_invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    reference_payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)
    description = Column(String, default="")
    debit_paise = Column(Integer, default=0)   # increases what customer owes
    credit_paise = Column(Integer, default=0)  # decreases what customer owes
    balance_after_paise = Column(Integer, nullable=False)
    entry_date = Column(DateTime, default=now_utc, nullable=False)

    customer: Mapped["Customer"] = relationship(back_populates="ledger_entries")


# ---------------------------------------------------------------------------
# Stock
# ---------------------------------------------------------------------------

class StockTransaction(Base):
    __tablename__ = "stock_transactions"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    txn_type = Column(Enum(StockTxnType), nullable=False)
    quantity_bags = Column(Numeric(12, 2), nullable=False)  # signed: +in, -out
    balance_after_bags = Column(Numeric(12, 2), nullable=False)
    reference_invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    reference_return_id = Column(Integer, ForeignKey("returns.id"), nullable=True)
    reason = Column(String, default="")  # for adjustments: Damaged/Missing/Counting/Other
    notes = Column(Text, default="")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=now_utc, nullable=False)


# ---------------------------------------------------------------------------
# Returns
# ---------------------------------------------------------------------------

class Return(Base):
    __tablename__ = "returns"

    id = Column(Integer, primary_key=True)
    return_number = Column(String, unique=True, nullable=False)
    original_invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    return_date = Column(DateTime, default=now_utc, nullable=False)
    total_amount_paise = Column(Integer, default=0)
    reason = Column(Text, default="")
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    items: Mapped[list["ReturnItem"]] = relationship(
        back_populates="return_", cascade="all, delete-orphan")


class ReturnItem(Base):
    __tablename__ = "return_items"

    id = Column(Integer, primary_key=True)
    return_id = Column(Integer, ForeignKey("returns.id"), nullable=False)
    original_invoice_item_id = Column(Integer, ForeignKey("invoice_items.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    product_name_snapshot = Column(String, nullable=False)
    quantity_bags = Column(Numeric(12, 2), nullable=False)
    selling_price_paise = Column(Integer, nullable=False)
    gst_rate = Column(Numeric(5, 2), nullable=False)
    amount_paise = Column(Integer, nullable=False)

    return_: Mapped["Return"] = relationship(back_populates="items")


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    username_snapshot = Column(String, default="")
    action = Column(String, nullable=False)
    entity_type = Column(String, default="")
    entity_id = Column(Integer, nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now_utc, nullable=False)


Index("ix_invoice_items_invoice", InvoiceItem.invoice_id)
Index("ix_stock_txn_product", StockTransaction.product_id)
Index("ix_ledger_customer", CustomerLedger.customer_id)
Index("ix_payments_invoice", Payment.invoice_id)
