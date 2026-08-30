"""Shop/customer CRUD, duplicate-name warning, and ledger management
(spec sections 7, 8, 14)."""
from __future__ import annotations

import difflib

from sqlalchemy.orm import Session

from database.models import Customer, CustomerLedger, LedgerEntryType


def find_similar_customers(db: Session, shop_name: str, threshold: float = 0.75):
    """Fuzzy duplicate-name check used when adding a new shop, so the
    operator can be warned before creating 'ABC Traders' twice."""
    candidates = db.query(Customer).filter(Customer.is_active == True).all()  # noqa: E712
    matches = []
    name_lower = shop_name.strip().lower()
    for c in candidates:
        ratio = difflib.SequenceMatcher(None, name_lower, c.shop_name.strip().lower()).ratio()
        if ratio >= threshold:
            matches.append((c, ratio))
    matches.sort(key=lambda t: -t[1])
    return matches


def search_customers(db: Session, term: str):
    term_like = f"%{term}%"
    return (
        db.query(Customer)
        .filter(
            Customer.is_active == True,  # noqa: E712
            (Customer.shop_name.ilike(term_like))
            | (Customer.phone.ilike(term_like))
            | (Customer.gstin.ilike(term_like)),
        )
        .order_by(Customer.shop_name)
        .limit(50)
        .all()
    )


def create_customer(db: Session, **kwargs) -> Customer:
    from utils.money import to_paise
    opening_balance = kwargs.pop("opening_balance", 0) or 0
    maps_location_link = kwargs.pop("maps_location_link", "") or ""
    customer_type = kwargs.pop("customer_type", "shop") or "shop"
    customer = Customer(
        opening_balance_paise=to_paise(opening_balance),
        maps_location_link=maps_location_link,
        customer_type=customer_type,
        **kwargs
    )
    db.add(customer)
    db.flush()
    if customer.opening_balance_paise:
        add_ledger_entry(
            db, customer,
            entry_type=LedgerEntryType.OPENING,
            description="Opening balance",
            debit_paise=customer.opening_balance_paise,
        )
    else:
        add_ledger_entry(db, customer, entry_type=LedgerEntryType.OPENING,
                          description="Account opened", debit_paise=0)
    return customer


def get_current_balance_paise(db: Session, customer_id: int) -> int:
    last = (
        db.query(CustomerLedger)
        .filter_by(customer_id=customer_id)
        .order_by(CustomerLedger.entry_date.desc(), CustomerLedger.id.desc())
        .first()
    )
    return last.balance_after_paise if last else 0


def add_ledger_entry(db: Session, customer: Customer, entry_type: LedgerEntryType,
                      description: str, debit_paise: int = 0, credit_paise: int = 0,
                      reference_invoice_id: int = None, reference_payment_id: int = None):
    """Appends one immutable ledger row. Balance is always computed from
    the last stored balance + this movement, never recalculated from
    scratch - so past ledger rows are never rewritten."""
    prev_balance = get_current_balance_paise(db, customer.id)
    new_balance = prev_balance + debit_paise - credit_paise
    entry = CustomerLedger(
        customer_id=customer.id,
        entry_type=entry_type,
        reference_invoice_id=reference_invoice_id,
        reference_payment_id=reference_payment_id,
        description=description,
        debit_paise=debit_paise,
        credit_paise=credit_paise,
        balance_after_paise=new_balance,
    )
    db.add(entry)
    return entry


def get_ledger(db: Session, customer_id: int):
    return (
        db.query(CustomerLedger)
        .filter_by(customer_id=customer_id)
        .order_by(CustomerLedger.entry_date, CustomerLedger.id)
        .all()
    )
