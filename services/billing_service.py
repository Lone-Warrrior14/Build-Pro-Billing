"""
The core billing workflow (spec sections 10-13, 31, 38).

`create_invoice()` is the single entry point used by the New Bill
screen. Everything it does happens inside ONE database transaction
(the caller wraps it in `session_scope()`), so either the whole invoice
(items, stock reduction, ledger update, price-memory update, payment)
is committed, or none of it is - satisfying the atomicity requirement.

Nothing here reads "live" product/customer data for anything that must
be preserved historically: every field needed to reprint the invoice
exactly as issued is captured into Invoice / InvoiceItem at creation
time.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from database.models import (
    Invoice, InvoiceItem, Customer, Product, CompanySettings,
    InvoiceStatus, PaymentStatus, PaymentMethod, Payment, LedgerEntryType,
)
from services import pricing_service, stock_service, customer_service
from services.invoice_service import reserve_next_invoice_number
from utils.money import to_paise


@dataclass
class BillLineInput:
    product_id: int
    quantity_bags: Decimal
    selling_price_paise: int          # the price the operator confirmed on screen
    gst_rate: Optional[Decimal] = None  # defaults to the product's current gst_rate
    desc: str = ""


@dataclass
class InitialPaymentInput:
    amount_paise: int
    method: PaymentMethod = PaymentMethod.CASH
    notes: str = ""


class BillingError(Exception):
    pass


def _split_gst(taxable_paise: int, gst_rate: Decimal, cgst_rate: Decimal, sgst_rate: Decimal):
    cgst = int(round(taxable_paise * float(cgst_rate) / 100.0))
    sgst = int(round(taxable_paise * float(sgst_rate) / 100.0))
    return cgst, sgst


def create_order_request(
    db: Session,
    customer_id: int,
    lines: list[BillLineInput],
    discount_paise: int = 0,
    transport_paise: int = 0,
    service_charge_paise: int = 0,
    round_off_paise: int = 0,
    notes: str = "",
    maps_location_link: str = "",
    user_id: Optional[int] = None,
    custom_invoice_number: Optional[str] = None,
    billing_type: str = "standard",
) -> Invoice:
    """Creates a sales order request in PENDING_APPROVAL status."""
    if not lines:
        raise BillingError("An order must have at least one item.")

    customer = db.get(Customer, customer_id)
    if customer is None:
        raise BillingError("Selected shop/customer not found.")

    settings = db.query(CompanySettings).first()
    if custom_invoice_number and custom_invoice_number.strip():
        invoice_number = custom_invoice_number.strip()
        existing = db.query(Invoice).filter(Invoice.invoice_number == invoice_number).first()
        if existing:
            raise BillingError(f"Invoice number '{invoice_number}' already exists.")
    else:
        invoice_number = f"REQ-{db.query(Invoice).count() + 1001}"

    invoice = Invoice(
        invoice_number=invoice_number,
        customer_id=customer.id,
        customer_name_snapshot=customer.shop_name,
        customer_address_snapshot=customer.address,
        customer_phone_snapshot=customer.phone,
        customer_gstin_snapshot=customer.gstin,
        company_name_snapshot=settings.company_name,
        company_address_snapshot=settings.address,
        company_gstin_snapshot=settings.gstin,
        logo_path_snapshot=settings.logo_path,
        signature_path_snapshot=settings.signature_path if settings.signature_enabled else None,
        signatory_name_snapshot=settings.signatory_name,
        signatory_designation_snapshot=settings.signatory_designation,
        stamp_path_snapshot=settings.stamp_path if settings.stamp_enabled else None,
        dealer_text_snapshot=settings.dealer_text,
        status=InvoiceStatus.PENDING_APPROVAL,
        notes=notes,
        maps_location_link=maps_location_link,
        created_by_user_id=user_id,
        discount_paise=discount_paise,
        transport_paise=transport_paise,
        service_charge_paise=service_charge_paise,
        round_off_paise=round_off_paise,
        billing_type=billing_type,
    )
    db.add(invoice)
    db.flush()

    subtotal = 0
    total_cgst = 0
    total_sgst = 0

    for line in lines:
        product = db.get(Product, line.product_id) if line.product_id else None
        if product is None and getattr(invoice, "billing_type", "standard") != "construction_sqft":
            raise BillingError(f"Product id {line.product_id} not found.")

        qty = Decimal(str(line.quantity_bags))
        if qty <= 0:
            raise BillingError("Invalid quantity / SqFt measurement.")
        if line.selling_price_paise < 0:
            raise BillingError("Invalid price / rate.")

        is_sqft = getattr(invoice, "billing_type", "standard") == "construction_sqft"
        gst_rate = Decimal(0) if is_sqft else (line.gst_rate if line.gst_rate is not None else (product.gst_rate if product else Decimal("18.0")))
        cgst_rate = Decimal(gst_rate) / 2
        sgst_rate = Decimal(gst_rate) / 2

        line_total = int(round(float(qty) * line.selling_price_paise))

        if is_sqft:
            taxable_amount_paise = line_total
            total_gst_paise = 0
            cgst_amt = 0
            sgst_amt = 0
        else:
            gst_factor = 1.0 + (float(gst_rate) / 100.0)
            taxable_amount_paise = int(round(line_total / gst_factor))
            total_gst_paise = line_total - taxable_amount_paise
            cgst_amt = total_gst_paise // 2
            sgst_amt = total_gst_paise - cgst_amt

        prod_name = line.desc if (line.desc and line.desc.strip()) else (product.product_name if product else "Civil Construction Work")
        prod_brand = product.brand if product else "Construction"
        prod_unit = "SqFt" if is_sqft else (product.unit if product else "Bag")
        mrp_paise = product.mrp_paise if product else line.selling_price_paise

        item = InvoiceItem(
            invoice_id=invoice.id,
            product_id=product.id if product else None,
            product_name_snapshot=prod_name,
            brand_snapshot=prod_brand,
            unit_snapshot=prod_unit,
            quantity_bags=qty,
            mrp_paise=mrp_paise,
            selling_price_paise=line.selling_price_paise,
            gst_rate=gst_rate,
            cgst_rate=cgst_rate,
            sgst_rate=sgst_rate,
            taxable_amount_paise=taxable_amount_paise,
            cgst_amount_paise=cgst_amt,
            sgst_amount_paise=sgst_amt,
            line_total_paise=line_total,
        )
        db.add(item)

        subtotal += taxable_amount_paise
        total_cgst += cgst_amt
        total_sgst += sgst_amt

    grand_total = subtotal - discount_paise + total_cgst + total_sgst + transport_paise + service_charge_paise + round_off_paise
    invoice.subtotal_paise = subtotal
    invoice.total_cgst_paise = total_cgst
    invoice.total_sgst_paise = total_sgst
    invoice.grand_total_paise = grand_total
    invoice.balance_paise = grand_total
    invoice.payment_status = PaymentStatus.UNPAID

    return invoice


def approve_order_request(db: Session, invoice_id: int, user_id: Optional[int] = None, custom_invoice_number: Optional[str] = None) -> Invoice:
    """Approves a PENDING_APPROVAL order request."""
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise BillingError("Order request not found.")
    if invoice.status not in (InvoiceStatus.PENDING_APPROVAL, InvoiceStatus.DRAFT):
        raise BillingError("Order request is not in PENDING_APPROVAL or DRAFT status.")

    if custom_invoice_number and custom_invoice_number.strip():
        new_num = custom_invoice_number.strip()
        existing = db.query(Invoice).filter(Invoice.invoice_number == new_num, Invoice.id != invoice.id).first()
        if existing:
            raise BillingError(f"Invoice number '{new_num}' already exists.")
        invoice.invoice_number = new_num
    elif invoice.invoice_number.startswith("REQ-") or invoice.invoice_number.startswith("ORD-"):
        invoice.invoice_number = reserve_next_invoice_number(db)

    customer = db.get(Customer, invoice.customer_id)

    for item in invoice.items:
        if item.product_id:
            stock_service.stock_out_for_sale(db, item.product_id, item.quantity_bags, invoice.id, user_id=user_id)
            pricing_service.record_price(
                db, customer.id, item.product_id, item.selling_price_paise, invoice.id
            )

    customer_service.add_ledger_entry(
        db, customer, LedgerEntryType.INVOICE,
        description=f"Invoice {invoice.invoice_number}",
        debit_paise=invoice.grand_total_paise,
        reference_invoice_id=invoice.id,
    )

    invoice.status = InvoiceStatus.COMPLETED
    return invoice


def create_invoice(
    db: Session,
    customer_id: int,
    lines: list[BillLineInput],
    discount_paise: int = 0,
    transport_paise: int = 0,
    service_charge_paise: int = 0,
    round_off_paise: int = 0,
    initial_payment: Optional[InitialPaymentInput] = None,
    notes: str = "",
    maps_location_link: str = "",
    user_id: Optional[int] = None,
    custom_invoice_number: Optional[str] = None,
    billing_type: str = "standard",
) -> Invoice:
    if not lines:
        raise BillingError("An invoice must have at least one item.")

    customer = db.get(Customer, customer_id)
    if customer is None:
        raise BillingError("Selected shop/customer not found.")

    settings = db.query(CompanySettings).first()

    if custom_invoice_number and custom_invoice_number.strip():
        invoice_number = custom_invoice_number.strip()
        existing = db.query(Invoice).filter(Invoice.invoice_number == invoice_number).first()
        if existing:
            raise BillingError(f"Invoice number '{invoice_number}' already exists.")
    else:
        invoice_number = reserve_next_invoice_number(db)

    invoice = Invoice(
        invoice_number=invoice_number,
        customer_id=customer.id,
        customer_name_snapshot=customer.shop_name,
        customer_address_snapshot=customer.address,
        customer_phone_snapshot=customer.phone,
        customer_gstin_snapshot=customer.gstin,
        company_name_snapshot=settings.company_name,
        company_address_snapshot=settings.address,
        company_phone_snapshot=settings.phone if hasattr(settings, 'phone') else "",
        company_email_snapshot=settings.email if hasattr(settings, 'email') else "",
        company_website_snapshot=settings.website if hasattr(settings, 'website') else "",
        company_gstin_snapshot=settings.gstin,
        logo_path_snapshot=settings.logo_path,
        signature_path_snapshot=settings.signature_path if settings.signature_enabled else None,
        signatory_name_snapshot=settings.signatory_name,
        signatory_designation_snapshot=settings.signatory_designation,
        stamp_path_snapshot=settings.stamp_path if settings.stamp_enabled else None,
        dealer_text_snapshot=settings.dealer_text,
        status=InvoiceStatus.COMPLETED,
        notes=notes,
        maps_location_link=maps_location_link,
        created_by_user_id=user_id,
        discount_paise=discount_paise,
        transport_paise=transport_paise,
        service_charge_paise=service_charge_paise,
        round_off_paise=round_off_paise,
        billing_type=billing_type,
    )
    db.add(invoice)
    db.flush()  # obtain invoice.id

    subtotal = 0
    total_cgst = 0
    total_sgst = 0

    for line in lines:
        product = db.get(Product, line.product_id) if line.product_id else None
        if product is None and getattr(invoice, "billing_type", "standard") != "construction_sqft":
            raise BillingError(f"Product id {line.product_id} not found.")

        qty = Decimal(str(line.quantity_bags))
        if qty <= 0:
            raise BillingError("Invalid quantity / SqFt measurement.")
        if line.selling_price_paise < 0:
            raise BillingError("Invalid price / rate.")

        is_sqft = getattr(invoice, "billing_type", "standard") == "construction_sqft"
        gst_rate = line.gst_rate if line.gst_rate is not None else (Decimal("18.0") if (is_sqft and getattr(line, 'gst_rate', None) is not None) else (product.gst_rate if product else Decimal("0.0")))
        cgst_rate = Decimal(gst_rate) / 2
        sgst_rate = Decimal(gst_rate) / 2

        line_total_base = int(round(float(qty) * line.selling_price_paise))

        if is_sqft and float(gst_rate) == 0:
            taxable_amount_paise = line_total_base
            total_gst_paise = 0
            cgst_amt = 0
            sgst_amt = 0
            line_total = line_total_base
        elif is_sqft and float(gst_rate) > 0:
            # Inclusive GST calculation for SqFt: Total stays line_total_base, base price is reduced
            gst_factor = 1.0 + (float(gst_rate) / 100.0)
            taxable_amount_paise = int(round(line_total_base / gst_factor))
            total_gst_paise = line_total_base - taxable_amount_paise
            cgst_amt = total_gst_paise // 2
            sgst_amt = total_gst_paise - cgst_amt
            line_total = line_total_base
        else:
            gst_factor = 1.0 + (float(gst_rate) / 100.0)
            taxable_amount_paise = int(round(line_total_base / gst_factor))
            total_gst_paise = line_total_base - taxable_amount_paise
            cgst_amt = total_gst_paise // 2
            sgst_amt = total_gst_paise - cgst_amt
            line_total = line_total_base

        prod_name = line.desc if (line.desc and line.desc.strip()) else (product.product_name if product else "Civil Construction Work")
        prod_brand = product.brand if product else "Construction"
        prod_unit = "SqFt" if is_sqft else (product.unit if product else "Bag")
        mrp_paise = product.mrp_paise if product else line.selling_price_paise

        item = InvoiceItem(
            invoice_id=invoice.id,
            product_id=product.id if product else None,
            product_name_snapshot=prod_name,
            brand_snapshot=prod_brand,
            unit_snapshot=prod_unit,
            quantity_bags=qty,
            mrp_paise=mrp_paise,
            selling_price_paise=line.selling_price_paise,
            gst_rate=gst_rate,
            cgst_rate=cgst_rate,
            sgst_rate=sgst_rate,
            taxable_amount_paise=taxable_amount_paise,
            cgst_amount_paise=cgst_amt,
            sgst_amount_paise=sgst_amt,
            line_total_paise=line_total,
        )
        db.add(item)

        subtotal += taxable_amount_paise
        total_cgst += cgst_amt
        total_sgst += sgst_amt

        # Reduce stock (raises InsufficientStockError if not allowed)
        if product:
            stock_service.stock_out_for_sale(db, product.id, qty, invoice.id, user_id=user_id)
            pricing_service.record_price(
                db, customer.id, product.id, line.selling_price_paise, invoice.id
            )

    grand_total = subtotal - discount_paise + total_cgst + total_sgst + transport_paise + service_charge_paise + round_off_paise
    if grand_total < 0:
        raise BillingError("Grand total cannot be negative.")

    invoice.subtotal_paise = subtotal
    invoice.total_cgst_paise = total_cgst
    invoice.total_sgst_paise = total_sgst
    invoice.grand_total_paise = grand_total

    amount_paid = 0
    if initial_payment and initial_payment.amount_paise > 0:
        amount_paid = initial_payment.amount_paise
        db.add(Payment(
            invoice_id=invoice.id,
            customer_id=customer.id,
            amount_paise=amount_paid,
            method=initial_payment.method,
            notes=initial_payment.notes,
            recorded_by_user_id=user_id,
        ))

    invoice.amount_paid_paise = amount_paid
    invoice.balance_paise = grand_total - amount_paid
    if invoice.balance_paise <= 0:
        invoice.payment_status = PaymentStatus.PAID
    elif amount_paid > 0:
        invoice.payment_status = PaymentStatus.PARTIAL
    else:
        invoice.payment_status = PaymentStatus.UNPAID

    # Update customer ledger: invoice increases what they owe, any
    # immediate payment decreases it again - both as separate entries
    # so the ledger reads naturally.
    customer_service.add_ledger_entry(
        db, customer, LedgerEntryType.INVOICE,
        description=f"Invoice {invoice.invoice_number}",
        debit_paise=grand_total,
        reference_invoice_id=invoice.id,
    )
    if amount_paid > 0:
        customer_service.add_ledger_entry(
            db, customer, LedgerEntryType.PAYMENT,
            description=f"Payment against {invoice.invoice_number}",
            credit_paise=amount_paid,
            reference_invoice_id=invoice.id,
        )

    return invoice


def update_invoice(
    db: Session,
    invoice_id: int,
    customer_id: int,
    lines: list[BillLineInput],
    discount_paise: int = 0,
    transport_paise: int = 0,
    service_charge_paise: int = 0,
    round_off_paise: int = 0,
    initial_payment: Optional[InitialPaymentInput] = None,
    notes: str = "",
    maps_location_link: str = "",
    custom_invoice_number: Optional[str] = None,
    user_id: Optional[int] = None
) -> Invoice:
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise BillingError("Invoice not found.")
    if invoice.status == InvoiceStatus.DELETED:
        raise BillingError("Cannot edit a deleted invoice.")

    customer = db.get(Customer, customer_id)
    if not customer:
        raise BillingError("Selected customer not found.")

    if custom_invoice_number and custom_invoice_number.strip() and custom_invoice_number.strip() != invoice.invoice_number:
        existing = db.query(Invoice).filter(Invoice.invoice_number == custom_invoice_number.strip(), Invoice.id != invoice.id).first()
        if existing:
            raise BillingError(f"Invoice number '{custom_invoice_number}' already exists.")
        invoice.invoice_number = custom_invoice_number.strip()

    was_completed = invoice.status == InvoiceStatus.COMPLETED

    # If it was COMPLETED, revert previous stock deductions
    if was_completed:
        for old_item in invoice.items:
            if old_item.product_id:
                old_prod = db.get(Product, old_item.product_id)
                if old_prod:
                    old_prod.stock_bags += old_item.quantity_bags
                    stock_service.record_stock_in(
                        db, old_prod.id, old_item.quantity_bags,
                        notes=f"Stock restored for edit of Invoice {invoice.invoice_number}",
                        user_id=user_id
                    )

    # Delete old items
    db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice.id).delete()

    # Update basic invoice fields
    invoice.customer_id = customer.id
    invoice.customer_name_snapshot = customer.shop_name
    invoice.customer_address_snapshot = customer.address
    invoice.customer_phone_snapshot = customer.phone
    invoice.customer_gstin_snapshot = customer.gstin
    invoice.notes = notes
    invoice.maps_location_link = maps_location_link
    invoice.discount_paise = discount_paise
    invoice.transport_paise = transport_paise
    invoice.service_charge_paise = service_charge_paise
    invoice.round_off_paise = round_off_paise

    subtotal = 0
    total_cgst = 0
    total_sgst = 0

    for line in lines:
        product = db.get(Product, line.product_id) if line.product_id else None
        if product is None and getattr(invoice, "billing_type", "standard") != "construction_sqft":
            raise BillingError(f"Product id {line.product_id} not found.")

        qty = Decimal(str(line.quantity_bags))
        if qty <= 0:
            raise BillingError("Invalid quantity.")
        if line.selling_price_paise < 0:
            raise BillingError("Invalid price.")

        is_sqft = getattr(invoice, "billing_type", "standard") == "construction_sqft"
        gst_rate = line.gst_rate if line.gst_rate is not None else (Decimal("18.0") if is_sqft else (product.gst_rate if product else Decimal("0.0")))
        cgst_rate = Decimal(gst_rate) / 2
        sgst_rate = Decimal(gst_rate) / 2

        line_total_base = int(round(float(qty) * line.selling_price_paise))

        if is_sqft and float(gst_rate) == 0:
            taxable_amount_paise = line_total_base
            total_gst_paise = 0
            cgst_amt = 0
            sgst_amt = 0
            line_total = line_total_base
        else:
            gst_factor = 1.0 + (float(gst_rate) / 100.0)
            taxable_amount_paise = int(round(line_total_base / gst_factor))
            total_gst_paise = line_total_base - taxable_amount_paise
            cgst_amt = total_gst_paise // 2
            sgst_amt = total_gst_paise - cgst_amt
            line_total = line_total_base

        prod_name = line.desc if (line.desc and line.desc.strip()) else (product.product_name if product else "Civil Construction Work")
        prod_brand = product.brand if product else "Construction"
        prod_unit = "SqFt" if is_sqft else (product.unit if product else "Bag")
        mrp_paise = product.mrp_paise if product else line.selling_price_paise

        item = InvoiceItem(
            invoice_id=invoice.id,
            product_id=product.id if product else None,
            product_name_snapshot=prod_name,
            brand_snapshot=prod_brand,
            unit_snapshot=prod_unit,
            quantity_bags=qty,
            mrp_paise=mrp_paise,
            selling_price_paise=line.selling_price_paise,
            gst_rate=gst_rate,
            cgst_rate=cgst_rate,
            sgst_rate=sgst_rate,
            taxable_amount_paise=taxable_amount_paise,
            cgst_amount_paise=cgst_amt,
            sgst_amount_paise=sgst_amt,
            line_total_paise=line_total,
        )
        db.add(item)

        subtotal += taxable_amount_paise
        total_cgst += cgst_amt
        total_sgst += sgst_amt

        # Deduct new stock if COMPLETED invoice
        if was_completed and product:
            stock_service.stock_out_for_sale(db, product.id, qty, invoice.id, user_id=user_id)
            pricing_service.record_price(
                db, customer.id, product.id, line.selling_price_paise, invoice.id
            )

    grand_total = subtotal - discount_paise + total_cgst + total_sgst + transport_paise + service_charge_paise + round_off_paise
    if grand_total < 0:
        raise BillingError("Grand total cannot be negative.")

    invoice.subtotal_paise = subtotal
    invoice.total_cgst_paise = total_cgst
    invoice.total_sgst_paise = total_sgst
    invoice.grand_total_paise = grand_total

    # Payment updates if provided
    if initial_payment and initial_payment.amount_paise > 0:
        db.add(Payment(
            invoice_id=invoice.id,
            customer_id=customer.id,
            amount_paise=initial_payment.amount_paise,
            method=initial_payment.method,
            notes=initial_payment.notes,
            recorded_by_user_id=user_id,
        ))
        invoice.amount_paid_paise += initial_payment.amount_paise

    invoice.balance_paise = grand_total - invoice.amount_paid_paise
    if invoice.balance_paise <= 0:
        invoice.payment_status = PaymentStatus.PAID
    elif invoice.amount_paid_paise > 0:
        invoice.payment_status = PaymentStatus.PARTIAL
    else:
        invoice.payment_status = PaymentStatus.UNPAID

    return invoice


def record_payment(db: Session, invoice_id: int, amount_paise: int,
                    method: PaymentMethod, notes: str = "", user_id: int = None) -> Payment:
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise BillingError("Invoice not found.")
    if amount_paise <= 0:
        raise BillingError("Payment amount must be positive.")
    if amount_paise > invoice.balance_paise:
        raise BillingError("Payment exceeds outstanding balance.")

    payment = Payment(
        invoice_id=invoice.id, customer_id=invoice.customer_id,
        amount_paise=amount_paise, method=method, notes=notes,
        recorded_by_user_id=user_id,
    )
    db.add(payment)

    invoice.amount_paid_paise += amount_paise
    invoice.balance_paise -= amount_paise
    invoice.payment_status = (
        PaymentStatus.PAID if invoice.balance_paise <= 0
        else PaymentStatus.PARTIAL
    )

    customer = db.get(Customer, invoice.customer_id)
    customer_service.add_ledger_entry(
        db, customer, LedgerEntryType.PAYMENT,
        description=f"Payment against {invoice.invoice_number}",
        credit_paise=amount_paise,
        reference_invoice_id=invoice.id,
        reference_payment_id=None,
    )
    return payment


def cancel_invoice(db: Session, invoice_id: int, reason: str, user_id: int = None) -> Invoice:
    """Voids an invoice without deleting it (spec: never permanently
    delete issued invoices). Reverses stock and ledger impact with new
    offsetting entries rather than mutating history."""
    from datetime import datetime
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise BillingError("Invoice not found.")
    if invoice.status == InvoiceStatus.CANCELLED:
        return invoice

    for item in invoice.items:
        if item.product_id:
            stock_service._apply_movement(  # noqa: SLF001 internal reuse
                db, db.get(Product, item.product_id), Decimal(item.quantity_bags),
                stock_service.StockTxnType.RETURN,
                reference_invoice_id=invoice.id,
                notes=f"Reversal for cancelled invoice {invoice.invoice_number}",
                user_id=user_id,
            )

    customer = db.get(Customer, invoice.customer_id)
    customer_service.add_ledger_entry(
        db, customer, LedgerEntryType.ADJUSTMENT,
        description=f"Cancellation of invoice {invoice.invoice_number}",
        credit_paise=invoice.grand_total_paise - invoice.amount_paid_paise,
        reference_invoice_id=invoice.id,
    )

    invoice.status = InvoiceStatus.CANCELLED
    invoice.cancelled_at = datetime.utcnow()
    invoice.cancelled_reason = reason
    return invoice


def move_to_recycle_bin(db: Session, invoice_id: int) -> Invoice:
    """Soft deletes an invoice by moving it to the Recycle Bin (status=DELETED)."""
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise BillingError("Invoice not found.")
    invoice.status = InvoiceStatus.DELETED
    return invoice


def restore_from_recycle_bin(db: Session, invoice_id: int) -> Invoice:
    """Restores an invoice from Recycle Bin back to COMPLETED status."""
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise BillingError("Invoice not found.")
    invoice.status = InvoiceStatus.COMPLETED
    return invoice


def permanent_delete_invoice(db: Session, invoice_id: int) -> bool:
    """Permanently deletes an invoice and all dependent records from the database."""
    from database.models import CustomerLedger, Payment, InvoiceItem, StockTransaction, PriceHistoryLog, CustomerProductPrice, Return
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise BillingError("Invoice not found.")

    db.query(CustomerProductPrice).filter(CustomerProductPrice.last_invoice_id == invoice.id).update({"last_invoice_id": None}, synchronize_session=False)
    db.query(PriceHistoryLog).filter(PriceHistoryLog.invoice_id == invoice.id).delete(synchronize_session=False)
    db.query(StockTransaction).filter(StockTransaction.reference_invoice_id == invoice.id).delete(synchronize_session=False)
    db.query(Return).filter(Return.original_invoice_id == invoice.id).delete(synchronize_session=False)
    db.query(CustomerLedger).filter(CustomerLedger.reference_invoice_id == invoice.id).delete(synchronize_session=False)
    db.query(Payment).filter(Payment.invoice_id == invoice.id).delete(synchronize_session=False)
    db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice.id).delete(synchronize_session=False)

    db.delete(invoice)
    return True
