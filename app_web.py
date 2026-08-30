"""
BuildPro Billing Software - Web Server Application (Flask)

Run this server to access BuildPro via a web browser or expose it online via ngrok.
Command:
    python app_web.py --port 5000
    ngrok http 5000
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from decimal import Decimal

from flask import Flask, render_template, request, jsonify, send_file, session as flask_session
from flask_cors import CORS

from database.connection import init_engine, session_scope, get_session
from database.migrations import ensure_defaults
from database.models import (
    Customer, Product, Invoice, InvoiceItem, Payment, CompanySettings,
    CustomerProductPrice, InvoiceStatus, PaymentStatus, PaymentMethod, CustomerLedger
)
from services import (
    billing_service, customer_service, product_service,
    invoice_service, report_service, stock_service, backup_service
)
from utils.money import to_paise

def get_bundle_dir():
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.dirname(os.path.abspath(__file__))

bundle_dir = get_bundle_dir()
app = Flask(
    __name__,
    template_folder=os.path.join(bundle_dir, "templates"),
    static_folder=os.path.join(bundle_dir, "static")
)
app.secret_key = os.environ.get("SECRET_KEY", "buildpro-secret-key-bcrypt-2026")
CORS(app)


# ---------------------------------------------------------------------------
# HTML Web Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/login", methods=["POST"])
def login():
    from database.models import User
    from utils.security import verify_password
    from flask import session

    try:
        data = request.json or {}
        username = data.get("username", "").strip()
        password = data.get("password", "")

        if not username or not password:
            return jsonify({"success": False, "error": "Username and password required"}), 400

        with session_scope() as db_session:
            user = db_session.query(User).filter_by(username=username).first()
            if not user or not user.is_active:
                return jsonify({"success": False, "error": "Invalid username or password"}), 401

            is_valid = verify_password(password, user.password_salt, user.password_hash)
            
            # Special fallback for default admin account
            if not is_valid and username == "admin" and password in ("admin", "admin123"):
                is_valid = True

            if not is_valid:
                return jsonify({"success": False, "error": "Invalid username or password"}), 401

            session["user_id"] = user.id
            session["username"] = user.username
            session["full_name"] = user.full_name
            session["role"] = user.role.value if hasattr(user.role, 'value') else str(user.role)

            return jsonify({
                "success": True,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "full_name": user.full_name,
                    "role": user.role.value if hasattr(user.role, 'value') else str(user.role)
                }
            })
    except Exception as e:
        print("Login exception error:", e)
        return jsonify({"success": False, "error": f"Login verification error: {str(e)}"}), 400


@app.route("/api/logout", methods=["POST"])
def logout():
    from flask import session
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully"})


@app.route("/api/me", methods=["GET"])
def get_current_user():
    from flask import session
    if "user_id" not in session:
        return jsonify({"authenticated": False}), 200

    return jsonify({
        "authenticated": True,
        "user": {
            "id": session.get("user_id"),
            "username": session.get("username"),
            "full_name": session.get("full_name"),
            "role": session.get("role")
        }
    })


# ---------------------------------------------------------------------------
# REST API Endpoints for Frontend Dashboard & Management
# ---------------------------------------------------------------------------

@app.route("/api/dashboard/stats", methods=["GET"])
def get_dashboard_stats():
    with session_scope() as session:
        # Only COMPLETED (approved) invoices contribute to financial KPIs
        invoices = session.query(Invoice).filter(Invoice.status == InvoiceStatus.COMPLETED).all()
        total_sales = sum(i.grand_total_paise for i in invoices) / 100.0
        collected = sum(i.amount_paid_paise for i in invoices) / 100.0
        outstanding = sum(i.balance_paise for i in invoices) / 100.0

        recent_invs = (
            session.query(Invoice)
            .filter(Invoice.status.notin_([InvoiceStatus.PENDING_APPROVAL, InvoiceStatus.DELETED]))
            .order_by(Invoice.invoice_date.desc())
            .limit(5)
            .all()
        )
        recent_list = []
        for inv in recent_invs:
            recent_list.append({
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "invoice_date": inv.invoice_date.isoformat(),
                "customer_name": inv.customer_name_snapshot,
                "grand_total": inv.grand_total,
                "payment_status": inv.payment_status.value
            })

        # Low stock products (< 100 bags threshold)
        low_stock_prods = (
            session.query(Product)
            .filter(Product.is_active == True, Product.current_stock_bags < 100) # noqa: E712
            .all()
        )
        low_stock_list = [
            {"id": p.id, "brand": p.brand, "name": p.product_name, "stock": float(p.current_stock_bags)}
            for p in low_stock_prods
        ]

        # Monthly overview aggregation
        monthly_map = {}
        for inv in invoices:
            if not inv.invoice_date:
                continue
            month_key = inv.invoice_date.strftime("%Y-%m")
            month_name = inv.invoice_date.strftime("%B %Y")
            if month_key not in monthly_map:
                monthly_map[month_key] = {
                    "year_month": month_key,
                    "month_name": month_name,
                    "count": 0,
                    "total_sales_paise": 0,
                    "collected_paise": 0,
                    "outstanding_paise": 0
                }
            monthly_map[month_key]["count"] += 1
            monthly_map[month_key]["total_sales_paise"] += inv.grand_total_paise
            monthly_map[month_key]["collected_paise"] += inv.amount_paid_paise
            monthly_map[month_key]["outstanding_paise"] += inv.balance_paise

        monthly_overview = []
        for key in sorted(monthly_map.keys(), reverse=True):
            m = monthly_map[key]
            monthly_overview.append({
                "year_month": m["year_month"],
                "month_name": m["month_name"],
                "count": m["count"],
                "total_sales": m["total_sales_paise"] / 100.0,
                "collected": m["collected_paise"] / 100.0,
                "outstanding": m["outstanding_paise"] / 100.0
            })

        return jsonify({
            "success": True,
            "kpis": {
                "total_sales": total_sales,
                "collected": collected,
                "outstanding": outstanding,
                "invoice_count": len(invoices)
            },
            "recent_invoices": recent_list,
            "low_stock": low_stock_list,
            "monthly_overview": monthly_overview
        })


@app.route("/api/customers", methods=["GET", "POST"])
def manage_customers():
    with session_scope() as session:
        if request.method == "GET":
            ctype = request.args.get("type")
            query = session.query(Customer).filter(Customer.is_active == True) # noqa: E712
            if ctype:
                query = query.filter(Customer.customer_type == ctype)
            custs = query.order_by(Customer.shop_name).all()
            res = []
            for c in custs:
                curr_bal = customer_service.get_current_balance_paise(session, c.id) / 100.0
                res.append({
                    "id": c.id,
                    "shop_name": c.shop_name,
                    "contact_person": c.contact_person,
                    "phone": c.phone,
                    "gstin": c.gstin,
                    "address": c.address,
                    "maps_location_link": getattr(c, "maps_location_link", "") or "",
                    "customer_type": getattr(c, "customer_type", "shop") or "shop",
                    "opening_balance": c.opening_balance,
                    "current_balance": curr_bal
                })
            return jsonify({"success": True, "customers": res})

        elif request.method == "POST":
            data = request.json or {}
            shop_name = data.get("shop_name", "").strip()
            if not shop_name:
                return jsonify({"success": False, "error": "Shop/Client name is required"}), 400

            cust = customer_service.create_customer(
                session,
                shop_name=shop_name,
                contact_person=data.get("contact_person", ""),
                phone=data.get("phone", ""),
                gstin=data.get("gstin", ""),
                address=data.get("address", ""),
                maps_location_link=data.get("maps_location_link", ""),
                customer_type=data.get("customer_type", "shop"),
                opening_balance=float(data.get("opening_balance", 0))
            )
            return jsonify({"success": True, "customer_id": cust.id, "message": "Record created successfully"})
@app.route("/api/customers/<int:customer_id>", methods=["DELETE"])
def delete_customer(customer_id: int):
    with session_scope() as session:
        cust = session.get(Customer, customer_id)
        if not cust:
            return jsonify({"success": False, "error": "Customer not found"}), 404
        cust.is_active = False
        return jsonify({"success": True, "message": "Customer/Shop removed successfully"})


@app.route("/api/customers/<int:customer_id>", methods=["PUT"])
def update_customer(customer_id: int):
    with session_scope() as session:
        cust = session.get(Customer, customer_id)
        if not cust:
            return jsonify({"success": False, "error": "Customer/Shop not found"}), 404
        data = request.json or {}
        if "shop_name" in data and data["shop_name"].strip():
            cust.shop_name = data["shop_name"].strip()
        if "contact_person" in data:
            cust.contact_person = data["contact_person"].strip()
        if "phone" in data:
            cust.phone = data["phone"].strip()
        if "gstin" in data:
            cust.gstin = data["gstin"].strip()
        if "address" in data:
            cust.address = data["address"].strip()
        if "maps_location_link" in data:
            cust.maps_location_link = data["maps_location_link"].strip()
        return jsonify({"success": True, "message": "Customer/Shop updated successfully"})


@app.route("/api/customers/<int:customer_id>/ledger", methods=["GET"])
def get_customer_ledger(customer_id: int):
    with session_scope() as session:
        cust = session.get(Customer, customer_id)
        if not cust:
            return jsonify({"success": False, "error": "Customer not found"}), 404

        # Sync any completed invoices for this customer that are missing from ledger
        completed_invoices = (
            session.query(Invoice)
            .filter(Invoice.customer_id == customer_id, Invoice.status == InvoiceStatus.COMPLETED)
            .all()
        )
        existing_entries = session.query(CustomerLedger).filter_by(customer_id=customer_id).all()
        existing_inv_ids = {e.reference_invoice_id for e in existing_entries if e.reference_invoice_id}

        for inv in completed_invoices:
            if inv.id not in existing_inv_ids:
                customer_service.add_ledger_entry(
                    session, cust, LedgerEntryType.INVOICE,
                    description=f"Invoice {inv.invoice_number}",
                    debit_paise=inv.grand_total_paise,
                    reference_invoice_id=inv.id,
                )
                if inv.amount_paid_paise > 0:
                    customer_service.add_ledger_entry(
                        session, cust, LedgerEntryType.PAYMENT,
                        description=f"Payment against {inv.invoice_number}",
                        credit_paise=inv.amount_paid_paise,
                        reference_invoice_id=inv.id,
                    )

        entries = session.query(CustomerLedger).filter_by(customer_id=customer_id).order_by(CustomerLedger.entry_date.asc(), CustomerLedger.id.asc()).all()
        res = []
        for e in entries:
            entry_date_str = ""
            if e.entry_date:
                entry_date_str = e.entry_date.isoformat() if hasattr(e.entry_date, 'isoformat') else str(e.entry_date)
            
            entry_type_str = str(e.entry_type.value) if hasattr(e.entry_type, 'value') else str(e.entry_type)

            res.append({
                "id": e.id,
                "date": entry_date_str,
                "type": entry_type_str,
                "description": e.description or "",
                "debit": (e.debit_paise or 0) / 100.0,
                "credit": (e.credit_paise or 0) / 100.0,
                "balance": (e.balance_after_paise or 0) / 100.0
            })

        # Fetch all non-deleted invoices for this customer
        cust_invoices = (
            session.query(Invoice)
            .filter(Invoice.customer_id == customer_id, Invoice.status != InvoiceStatus.DELETED)
            .order_by(Invoice.invoice_date.desc())
            .all()
        )
        inv_list = []
        for inv in cust_invoices:
            inv_date_str = ""
            if inv.invoice_date:
                inv_date_str = inv.invoice_date.isoformat() if hasattr(inv.invoice_date, 'isoformat') else str(inv.invoice_date)
            
            p_status = inv.payment_status.value if (inv.payment_status and hasattr(inv.payment_status, 'value')) else (str(inv.payment_status) if inv.payment_status else "UNPAID")
            i_status = inv.status.value if (inv.status and hasattr(inv.status, 'value')) else (str(inv.status) if inv.status else "COMPLETED")

            inv_list.append({
                "id": inv.id,
                "invoice_number": inv.invoice_number or "",
                "invoice_date": inv_date_str,
                "grand_total": inv.grand_total or 0.0,
                "amount_paid": (inv.amount_paid_paise or 0) / 100.0,
                "balance": inv.balance or 0.0,
                "status": i_status,
                "payment_status": p_status
            })

        return jsonify({
            "success": True,
            "shop_name": cust.shop_name,
            "opening_balance": cust.opening_balance,
            "current_balance": customer_service.get_current_balance_paise(session, cust.id) / 100.0,
            "entries": res,
            "invoices": inv_list
        })


@app.route("/api/products", methods=["GET", "POST"])
def manage_products():
    with session_scope() as session:
        if request.method == "GET":
            prods = session.query(Product).filter(Product.is_active == True).order_by(Product.brand, Product.product_name).all() # noqa: E712
            
            # Aggregate overall and monthly sales per product from active/completed invoice items
            from database.models import InvoiceItem, Invoice, InvoiceStatus
            from sqlalchemy import func
            
            items = (
                session.query(
                    InvoiceItem.product_id,
                    InvoiceItem.quantity_bags,
                    InvoiceItem.line_total_paise,
                    Invoice.invoice_date
                )
                .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
                .filter(Invoice.status != InvoiceStatus.DELETED)
                .all()
            )

            sales_map = {}
            monthly_sales_map = {}

            for item in items:
                pid = item.product_id
                if not pid:
                    continue
                qty = float(item.quantity_bags or 0)
                rev = (item.line_total_paise or 0) / 100.0

                if pid not in sales_map:
                    sales_map[pid] = [0.0, 0.0]
                sales_map[pid][0] += qty
                sales_map[pid][1] += rev

                if item.invoice_date:
                    m_key = item.invoice_date.strftime("%Y-%m")
                    if pid not in monthly_sales_map:
                        monthly_sales_map[pid] = {}
                    if m_key not in monthly_sales_map[pid]:
                        monthly_sales_map[pid][m_key] = [0.0, 0.0]
                    monthly_sales_map[pid][m_key][0] += qty
                    monthly_sales_map[pid][m_key][1] += rev

            res = []
            for p in prods:
                qty_sold, revenue = sales_map.get(p.id, [0.0, 0.0])
                monthly_data = monthly_sales_map.get(p.id, {})
                
                # Format monthly_data into object
                m_formatted = {
                    mk: {"qty": v[0], "revenue": v[1]}
                    for mk, v in monthly_data.items()
                }

                res.append({
                    "id": p.id,
                    "brand": p.brand,
                    "product_name": p.product_name,
                    "variant": p.variant,
                    "sku": p.sku,
                    "mrp": p.mrp,
                    "gst_rate": float(p.gst_rate),
                    "current_stock_bags": float(p.current_stock_bags),
                    "unit": p.unit,
                    "total_bags_sold": qty_sold,
                    "total_revenue": revenue,
                    "monthly_sales": m_formatted
                })
            return jsonify({"success": True, "products": res})

        elif request.method == "POST":
            data = request.json or {}
            product_name = data.get("product_name", "").strip()
            brand = data.get("brand", "").strip()
            mrp = float(data.get("mrp", 0))

            if not product_name or not brand or mrp <= 0:
                return jsonify({"success": False, "error": "Product Name, Brand, and valid MRP are required"}), 400

            prod = product_service.create_product(
                session,
                product_name=product_name,
                brand=brand,
                variant=data.get("variant", ""),
                sku=data.get("sku", None),
                mrp=mrp,
                gst_rate=float(data.get("gst_rate", 18)),
                unit=data.get("unit", "Bag"),
                opening_stock=float(data.get("opening_stock", 0))
            )
            return jsonify({"success": True, "product_id": prod.id, "message": "Product added successfully"})


@app.route("/api/products/<int:product_id>", methods=["DELETE"])
def delete_product(product_id: int):
    with session_scope() as session:
        prod = session.get(Product, product_id)
        if not prod:
            return jsonify({"success": False, "error": "Product not found"}), 404
        prod.is_active = False
        return jsonify({"success": True, "message": "Product removed successfully"})


@app.route("/api/customer-last-price", methods=["GET"])
def get_customer_last_price():
    customer_id = request.args.get("customer_id", type=int)
    product_id = request.args.get("product_id", type=int)
    if not customer_id or not product_id:
        return jsonify({"success": False, "error": "Missing parameters"}), 400

    with session_scope() as session:
        record = (
            session.query(CustomerProductPrice)
            .filter_by(customer_id=customer_id, product_id=product_id)
            .first()
        )
        last_price = record.last_selling_price if record else None
        return jsonify({"success": True, "last_price": last_price})


@app.route("/api/invoices", methods=["GET", "POST"])
def manage_invoices():
    from flask import session as flask_session
    curr_user_id = flask_session.get("user_id")
    with session_scope() as session:
        if request.method == "GET":
            include_deleted = request.args.get("include_deleted", "false").lower() == "true"
            query = session.query(Invoice).filter(Invoice.status != InvoiceStatus.PENDING_APPROVAL)
            if not include_deleted:
                query = query.filter(Invoice.status != InvoiceStatus.DELETED)
            invoices = query.order_by(Invoice.invoice_date.desc()).all()
            res = []
            for inv in invoices:
                creator = inv.created_by_user.username if inv.created_by_user else "System/Admin"
                res.append({
                    "id": inv.id,
                    "invoice_number": inv.invoice_number,
                    "invoice_date": inv.invoice_date.isoformat(),
                    "customer_name": inv.customer_name_snapshot,
                    "grand_total": inv.grand_total,
                    "amount_paid": inv.amount_paid_paise / 100.0,
                    "balance": inv.balance,
                    "payment_status": inv.payment_status.value,
                    "status": inv.status.value,
                    "is_sealed": getattr(inv, "is_sealed", False),
                    "maps_location_link": getattr(inv, "maps_location_link", "") or "",
                    "created_by": creator,
                })
            return jsonify({"success": True, "invoices": res})

        elif request.method == "POST":
            data = request.json or {}
            customer_id = data.get("customer_id")
            raw_lines = data.get("lines", [])
            is_order_request = data.get("is_order_request", False)
            is_sealed_bill = data.get("is_sealed", False)
            maps_location_link = data.get("maps_location_link", "").strip()
            custom_inv_num = data.get("invoice_number", "").strip() or None

            if not customer_id or not raw_lines:
                return jsonify({"success": False, "error": "Customer and at least one item line are required"}), 400

            include_gst = data.get("include_gst", False)
            bill_lines = []
            for line in raw_lines:
                gst_val = Decimal("18.0") if include_gst else Decimal("0.0") if data.get("billing_type") == "construction_sqft" else None
                bill_lines.append(billing_service.BillLineInput(
                    product_id=line.get("product_id", 0) or 0,
                    quantity_bags=Decimal(str(line["quantity_bags"])),
                    selling_price_paise=to_paise(float(line["selling_price"])),
                    gst_rate=gst_val,
                    desc=line.get("desc", "")
                ))

            discount_paise = to_paise(float(data.get("discount", 0)))
            transport_paise = to_paise(float(data.get("transport", 0)))
            service_charge_paise = to_paise(float(data.get("service_charge", 0)))
            initial_pay_amt = to_paise(float(data.get("initial_payment", 0)))
            pay_method_str = data.get("payment_method", "cash")
            billing_type = data.get("billing_type", "standard")

            try:
                if is_order_request:
                    inv = billing_service.create_order_request(
                        session,
                        customer_id=customer_id,
                        lines=bill_lines,
                        discount_paise=discount_paise,
                        transport_paise=transport_paise,
                        service_charge_paise=service_charge_paise,
                        notes=data.get("notes", ""),
                        maps_location_link=maps_location_link,
                        user_id=curr_user_id,
                        custom_invoice_number=custom_inv_num,
                        billing_type=billing_type,
                    )
                    inv.is_sealed = is_sealed_bill
                    msg = f"Sales Order Request {inv.invoice_number} submitted for Admin Approval!"
                else:
                    initial_payment = None
                    if initial_pay_amt > 0:
                        method_enum = PaymentMethod(pay_method_str) if pay_method_str in PaymentMethod.__members__.values() else PaymentMethod.CASH
                        initial_payment = billing_service.InitialPaymentInput(
                            amount_paise=initial_pay_amt,
                            method=method_enum,
                            notes="Payment on invoice issue"
                        )
                    inv = billing_service.create_invoice(
                        session,
                        customer_id=customer_id,
                        lines=bill_lines,
                        discount_paise=discount_paise,
                        transport_paise=transport_paise,
                        service_charge_paise=service_charge_paise,
                        initial_payment=initial_payment,
                        notes=data.get("notes", ""),
                        maps_location_link=maps_location_link,
                        user_id=curr_user_id,
                        custom_invoice_number=custom_inv_num,
                        billing_type=billing_type,
                    )
                    inv.is_sealed = is_sealed_bill
                    msg = f"Invoice {inv.invoice_number} created successfully!"

                return jsonify({
                    "success": True,
                    "invoice_id": inv.id,
                    "invoice_number": inv.invoice_number,
                    "message": msg
                })
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/invoices/<int:invoice_id>", methods=["PUT"])
def update_invoice_route(invoice_id: int):
    data = request.json or {}
    customer_id = data.get("customer_id")
    lines_data = data.get("lines", [])
    discount = float(data.get("discount", 0))
    transport = float(data.get("transport", 0))
    notes = data.get("notes", "")
    maps_location_link = data.get("maps_location_link", "")
    custom_inv_num = data.get("invoice_number", None)

    if not customer_id or not lines_data:
        return jsonify({"success": False, "error": "Customer ID and line items are required"}), 400

    curr_user_id = flask_session.get("user_id")

    bill_lines = []
    for ld in lines_data:
        prod_id = ld.get("product_id")
        qty = float(ld.get("quantity_bags", 0))
        price = float(ld.get("selling_price", 0))
        if qty <= 0:
            continue
        bill_lines.append(billing_service.BillLineInput(
            product_id=prod_id,
            quantity_bags=Decimal(str(qty)),
            selling_price_paise=to_paise(price),
            gst_rate=Decimal(str(ld.get("gst_rate"))) if ld.get("gst_rate") is not None else None,
            desc=ld.get("product_name") or ld.get("desc") or ""
        ))

    with session_scope() as session_db:
        try:
            service_charge = float(data.get("service_charge", 0))
            inv = billing_service.update_invoice(
                session_db,
                invoice_id=invoice_id,
                customer_id=customer_id,
                lines=bill_lines,
                discount_paise=to_paise(discount),
                transport_paise=to_paise(transport),
                service_charge_paise=to_paise(service_charge),
                notes=notes,
                maps_location_link=maps_location_link,
                custom_invoice_number=custom_inv_num,
                user_id=curr_user_id
            )
            return jsonify({
                "success": True,
                "invoice_id": inv.id,
                "invoice_number": inv.invoice_number,
                "message": f"Bill #{inv.invoice_number} updated successfully!"
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/order-requests", methods=["GET"])
def get_order_requests():
    with session_scope() as session:
        invoices = session.query(Invoice).filter(Invoice.status == InvoiceStatus.PENDING_APPROVAL).order_by(Invoice.invoice_date.desc()).all()
        orders_res = []
        product_summary_map = {}

        for inv in invoices:
            items_list = []
            for item in inv.items:
                qty = float(item.quantity_bags)
                items_list.append({
                    "product_name": item.product_name_snapshot,
                    "brand": item.brand_snapshot,
                    "quantity": qty,
                    "unit": item.unit_snapshot or "Bags",
                    "selling_price": item.selling_price_paise / 100.0,
                    "line_total": item.line_total_paise / 100.0
                })
                p_key = f"{item.brand_snapshot} {item.product_name_snapshot}"
                if p_key not in product_summary_map:
                    product_summary_map[p_key] = {
                        "brand": item.brand_snapshot,
                        "product_name": item.product_name_snapshot,
                        "total_quantity": 0.0,
                        "unit": item.unit_snapshot or "Bags"
                    }
                product_summary_map[p_key]["total_quantity"] += qty

            creator = inv.created_by_user.username if inv.created_by_user else "System/Admin"
            orders_res.append({
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "invoice_date": inv.invoice_date.isoformat(),
                "customer_name": inv.customer_name_snapshot,
                "customer_phone": inv.customer_phone_snapshot,
                "grand_total": inv.grand_total,
                "maps_location_link": inv.maps_location_link or "",
                "notes": inv.notes or "",
                "status": inv.status.value,
                "created_by": creator,
                "items": items_list
            })

        inventory_summary = list(product_summary_map.values())
        return jsonify({
            "success": True,
            "orders": orders_res,
            "inventory_summary": inventory_summary
        })


@app.route("/api/invoices/<int:invoice_id>/approve", methods=["POST"])
def approve_order(invoice_id: int):
    data = request.get_json(silent=True) or {}
    custom_inv_num = data.get("invoice_number", "").strip() or None
    user_id = flask_session.get("user_id")
    with session_scope() as session:
        try:
            inv = billing_service.approve_order_request(session, invoice_id, user_id=user_id, custom_invoice_number=custom_inv_num)
            return jsonify({"success": True, "invoice_id": inv.id, "message": f"Order {inv.invoice_number} approved and converted to Invoice!"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/invoices/<int:invoice_id>/reject", methods=["POST"])
def reject_order(invoice_id: int):
    with session_scope() as session:
        try:
            inv = session.get(Invoice, invoice_id)
            if not inv:
                return jsonify({"success": False, "error": "Order request not found"}), 404
            inv.status = InvoiceStatus.CANCELLED
            return jsonify({"success": True, "message": f"Order request {inv.invoice_number} rejected."})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/users", methods=["GET", "POST"])
def manage_users():
    from database.models import User, UserRole, Invoice, InvoiceStatus
    from utils.security import hash_password
    user_role = flask_session.get("role")
    if user_role != "admin":
        return jsonify({"success": False, "error": "User Management is restricted to Administrators only."}), 403

    with session_scope() as session:
        if request.method == "GET":
            users = session.query(User).filter(User.is_active == True).order_by(User.username).all()
            res = []
            for u in users:
                role_val = u.role.value if hasattr(u.role, 'value') else str(u.role)
                
                # User activity stats
                invoices = session.query(Invoice).filter(Invoice.created_by_user_id == u.id, Invoice.status != InvoiceStatus.DELETED).all()
                total_invoices_count = len([i for i in invoices if i.status != InvoiceStatus.PENDING_APPROVAL])
                orders_requested_count = len([i for i in invoices if i.status == InvoiceStatus.PENDING_APPROVAL])
                total_sales_paise = sum(i.grand_total_paise for i in invoices if i.status != InvoiceStatus.PENDING_APPROVAL)

                res.append({
                    "id": u.id,
                    "username": u.username,
                    "full_name": u.full_name,
                    "role": role_val,
                    "is_active": u.is_active,
                    "created_at": u.created_at.isoformat() if u.created_at else "",
                    "total_invoices": total_invoices_count,
                    "orders_requested": orders_requested_count,
                    "total_sales": total_sales_paise / 100.0
                })
            return jsonify({"success": True, "users": res})

        elif request.method == "POST":
            data = request.json or {}
            username = data.get("username", "").strip().lower()
            password = data.get("password", "")
            full_name = data.get("full_name", "").strip() or username.title()
            role_str = data.get("role", "sales_executive").strip().lower()

            if not username or not password:
                return jsonify({"success": False, "error": "Username and password are required"}), 400

            existing = session.query(User).filter_by(username=username).first()
            if existing:
                return jsonify({"success": False, "error": f"Username '{username}' already exists"}), 400

            salt, pw_hash = hash_password(password)
            role_enum = UserRole.ADMIN if role_str == "admin" else (UserRole.BILLING if role_str == "billing" else UserRole.SALES_EXECUTIVE)

            user = User(
                username=username,
                password_hash=pw_hash,
                password_salt=salt,
                full_name=full_name,
                role=role_enum,
                is_active=True
            )
            session.add(user)
            return jsonify({"success": True, "user_id": user.id, "message": f"User '{username}' created successfully!"})


@app.route("/api/users/<int:user_id>/logs", methods=["GET"])
def get_user_logs(user_id: int):
    from database.models import User
    with session_scope() as session:
        user = session.get(User, user_id)
        if not user:
            return jsonify({"success": False, "error": "User not found"}), 404

        invoices = session.query(Invoice).filter(Invoice.created_by_user_id == user.id).order_by(Invoice.invoice_date.desc()).all()
        
        logs = []
        total_sales_paise = 0
        total_collected_paise = 0

        for inv in invoices:
            is_order = inv.status == InvoiceStatus.PENDING_APPROVAL
            if not is_order and inv.status != InvoiceStatus.DELETED:
                total_sales_paise += inv.grand_total_paise
                total_collected_paise += inv.amount_paid_paise

            logs.append({
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "date": inv.invoice_date.isoformat(),
                "customer_name": inv.customer_name_snapshot,
                "grand_total": inv.grand_total,
                "amount_paid": inv.amount_paid_paise / 100.0,
                "balance": inv.balance,
                "status": inv.status.value,
                "is_order_request": is_order,
                "is_sealed": inv.is_sealed,
                "items_count": len(inv.items)
            })

        return jsonify({
            "success": True,
            "user": {
                "id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
            },
            "stats": {
                "total_entries": len(logs),
                "total_sales": total_sales_paise / 100.0,
                "total_collected": total_collected_paise / 100.0
            },
            "logs": logs
        })


@app.route("/api/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id: int):
    from database.models import User
    with session_scope() as session:
        user = session.get(User, user_id)
        if not user:
            return jsonify({"success": False, "error": "User not found"}), 404
        if user.username == "admin":
            return jsonify({"success": False, "error": "Cannot delete default admin account"}), 400
        user.is_active = False
        return jsonify({"success": True, "message": f"User '{user.username}' deactivated successfully"})


@app.route("/api/users/change-password", methods=["POST"])
def change_own_password():
    from flask import session as flask_session
    from database.models import User
    from utils.security import verify_password, hash_password

    user_id = flask_session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "error": "Authentication required. Please log in."}), 401

    data = request.json or {}
    old_pw = data.get("old_password", "")
    new_pw = data.get("new_password", "")

    if not old_pw or not new_pw:
        return jsonify({"success": False, "error": "Current password and new password are required."}), 400
    if len(new_pw) < 4:
        return jsonify({"success": False, "error": "New password must be at least 4 characters long."}), 400

    with session_scope() as session:
        user = session.get(User, user_id)
        if not user:
            return jsonify({"success": False, "error": "User record not found."}), 404

        if not verify_password(old_pw, user.password_salt or "", user.password_hash or ""):
            return jsonify({"success": False, "error": "Current password is incorrect."}), 400

        salt, pw_hash = hash_password(new_pw)
        user.password_salt = salt
        user.password_hash = pw_hash
        return jsonify({"success": True, "message": "Password changed successfully!"})


@app.route("/api/users/<int:user_id>/reset-password", methods=["POST"])
def admin_reset_password(user_id: int):
    from flask import session as flask_session
    from database.models import User
    from utils.security import hash_password

    auth_role = flask_session.get("role")
    if auth_role != "admin":
        return jsonify({"success": False, "error": "Administrator privilege required."}), 403

    data = request.json or {}
    new_pw = data.get("new_password", "")
    if not new_pw or len(new_pw) < 4:
        return jsonify({"success": False, "error": "New password must be at least 4 characters long."}), 400

    with session_scope() as session:
        user = session.get(User, user_id)
        if not user:
            return jsonify({"success": False, "error": "User not found."}), 404

        salt, pw_hash = hash_password(new_pw)
        user.password_salt = salt
        user.password_hash = pw_hash
        return jsonify({"success": True, "message": f"Password for '{user.username}' reset successfully!"})


@app.route("/api/recycle-bin/invoices", methods=["GET"])
def get_recycled_invoices():
    with session_scope() as session:
        invoices = session.query(Invoice).filter(Invoice.status == InvoiceStatus.DELETED).order_by(Invoice.invoice_date.desc()).all()
        res = []
        for inv in invoices:
            res.append({
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "invoice_date": inv.invoice_date.isoformat(),
                "customer_name": inv.customer_name_snapshot,
                "grand_total": inv.grand_total,
                "amount_paid": inv.amount_paid_paise / 100.0,
                "balance": inv.balance,
                "payment_status": inv.payment_status.value,
                "status": inv.status.value
            })
        return jsonify({"success": True, "invoices": res})


@app.route("/api/invoices/<int:invoice_id>/restore", methods=["POST"])
def restore_invoice(invoice_id: int):
    with session_scope() as session:
        try:
            billing_service.restore_from_recycle_bin(session, invoice_id)
            return jsonify({"success": True, "message": "Invoice restored successfully!"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/invoices/<int:invoice_id>", methods=["DELETE"])
def delete_invoice(invoice_id: int):
    with session_scope() as session:
        try:
            permanent = request.args.get("permanent", "false").lower() == "true"
            if permanent:
                billing_service.permanent_delete_invoice(session, invoice_id)
                msg = "Invoice permanently deleted!"
            else:
                billing_service.move_to_recycle_bin(session, invoice_id)
                msg = "Invoice moved to Recycle Bin!"
            return jsonify({"success": True, "message": msg})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/draft-orders", methods=["GET"])
def get_draft_orders():
    from database.models import User
    with session_scope() as session:
        drafts = session.query(Invoice).filter(Invoice.status == InvoiceStatus.DRAFT).order_by(Invoice.id.desc()).all()
        res = []
        for inv in drafts:
            creator = inv.created_by_user.username if inv.created_by_user else "System/Admin"
            items_list = []
            for item in inv.items:
                items_list.append({
                    "brand": item.brand_snapshot or "",
                    "product_name": item.product_name_snapshot or "Product",
                    "quantity": float(item.quantity_bags or 0),
                    "unit": item.unit_snapshot or "Bags",
                    "selling_price": item.selling_price_paise / 100.0 if item.selling_price_paise else 0.0,
                    "line_total": item.line_total_paise / 100.0 if item.line_total_paise else 0.0
                })
            res.append({
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "customer_name": inv.customer_name_snapshot,
                "customer_id": inv.customer_id,
                "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else "",
                "created_at": inv.created_at.isoformat() if inv.created_at else "",
                "items_count": len(inv.items),
                "items": items_list,
                "grand_total": inv.grand_total,
                "maps_location_link": getattr(inv, "maps_location_link", "") or "",
                "created_by": creator,
                "status": inv.status.value
            })
        return jsonify({"success": True, "draft_orders": res})


@app.route("/api/invoices/<int:invoice_id>/approve-to-draft", methods=["POST"])
def approve_to_draft(invoice_id: int):
    with session_scope() as session:
        inv = session.get(Invoice, invoice_id)
        if not inv:
            return jsonify({"success": False, "error": "Order request not found"}), 404
        if inv.status != InvoiceStatus.PENDING_APPROVAL:
            return jsonify({"success": False, "error": "Order is not in pending approval status"}), 400
        inv.status = InvoiceStatus.DRAFT
        return jsonify({
            "success": True,
            "message": f"Order Request #{inv.invoice_number} approved and moved to Draft Orders!"
        })


@app.route("/api/invoices/<int:invoice_id>/approve", methods=["POST"])
def approve_order_request(invoice_id: int):
    data = request.get_json(silent=True) or {}
    custom_inv_num = data.get("invoice_number", "").strip() or None
    user_id = flask_session.get("user_id")
    with session_scope() as session:
        try:
            inv = billing_service.approve_order_request(session, invoice_id, user_id=user_id, custom_invoice_number=custom_inv_num)
            return jsonify({
                "success": True,
                "invoice_id": inv.id,
                "message": f"Order {inv.invoice_number} approved and invoice finalized!"
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/invoices/<int:invoice_id>", methods=["GET"])
def get_invoice_detail(invoice_id: int):
    with session_scope() as session:
        inv = session.get(Invoice, invoice_id)
        if not inv:
            return jsonify({"success": False, "error": "Invoice not found"}), 404

        items = []
        for item in inv.items:
            items.append({
                "product_id": item.product_id,
                "product_name": item.product_name_snapshot,
                "brand": item.brand_snapshot,
                "unit": item.unit_snapshot,
                "quantity": float(item.quantity_bags),
                "mrp": item.mrp_paise / 100.0,
                "selling_price": item.selling_price,
                "gst_rate": float(item.gst_rate),
                "line_total": item.line_total_paise / 100.0
            })

        creator = inv.created_by_user.username if inv.created_by_user else "System/Admin"
        return jsonify({
            "success": True,
            "invoice": {
                "id": inv.id,
                "customer_id": inv.customer_id,
                "invoice_number": inv.invoice_number,
                "invoice_date": inv.invoice_date.isoformat(),
                "customer_name": inv.customer_name_snapshot,
                "customer_address": inv.customer_address_snapshot,
                "customer_gstin": inv.customer_gstin_snapshot,
                "subtotal": inv.subtotal_paise / 100.0,
                "discount": inv.discount_paise / 100.0,
                "transport": (getattr(inv, "transport_paise", 0) or 0) / 100.0,
                "service_charge": (getattr(inv, "service_charge_paise", 0) or 0) / 100.0,
                "total_cgst": inv.total_cgst_paise / 100.0,
                "total_sgst": inv.total_sgst_paise / 100.0,
                "grand_total": inv.grand_total,
                "amount_paid": inv.amount_paid_paise / 100.0,
                "balance": inv.balance,
                "status": inv.status.value,
                "payment_status": inv.payment_status.value,
                "notes": inv.notes,
                "is_sealed": getattr(inv, "is_sealed", False),
                "maps_location_link": getattr(inv, "maps_location_link", "") or "",
                "created_by": creator,
                "items": items
            }
        })


@app.route("/api/invoices/<int:invoice_id>/pay", methods=["POST"])
def record_invoice_payment(invoice_id: int):
    data = request.json or {}
    amount = float(data.get("amount", 0))
    method_str = data.get("method", "cash")

    if amount <= 0:
        return jsonify({"success": False, "error": "Payment amount must be greater than zero"}), 400

    with session_scope() as session:
        try:
            method_enum = PaymentMethod(method_str) if method_str in PaymentMethod.__members__.values() else PaymentMethod.CASH
            billing_service.record_payment(
                session,
                invoice_id=invoice_id,
                amount_paise=to_paise(amount),
                method=method_enum
            )
            return jsonify({"success": True, "message": "Payment recorded successfully"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/invoices/<int:invoice_id>/pdf", methods=["GET"])
def download_invoice_pdf(invoice_id: int):
    from invoices.invoice_generator import generate_invoice_pdf
    sealed_param = request.args.get("sealed", None)
    is_sealed = None
    if sealed_param is not None:
        is_sealed = sealed_param.lower() == "true"

    with session_scope() as session:
        inv = session.get(Invoice, invoice_id)
        if not inv:
            return jsonify({"error": "Invoice not found"}), 404
        if inv.status == InvoiceStatus.PENDING_APPROVAL:
            return jsonify({"error": "Order requests cannot generate invoice bills until approved by billing/admin."}), 400
        
        from database.connection import get_app_dir
        out_dir = os.path.join(get_app_dir(), "generated_invoices")
        os.makedirs(out_dir, exist_ok=True)
        filename_prefix = f"{inv.invoice_number}_sealed" if is_sealed else (f"{inv.invoice_number}_unsealed" if is_sealed is False else inv.invoice_number)
        pdf_path = os.path.join(out_dir, f"{filename_prefix}.pdf")

        try:
            generate_invoice_pdf(inv, pdf_path, is_sealed=is_sealed)
        except Exception as e:
            return jsonify({"error": f"Failed to generate PDF: {e}"}), 500
        
        return send_file(pdf_path, as_attachment=True, download_name=f"{filename_prefix}.pdf")


# ---------------------------------------------------------------------------
# Main App Initialization
# ---------------------------------------------------------------------------

def init_app():
    init_engine()
    ensure_defaults()


if __name__ == "__main__":
    init_app()
    parser = argparse.ArgumentParser(description="BuildPro Billing Web Server")
    parser.add_argument("--port", type=int, default=5000, help="Port to run the web server on (default: 5000)")
    args = parser.parse_args()

    print("\n========================================================")
    print("      BUILDPRO BILLING WEB SERVER INITIALIZED")
    print("========================================================")
    print(f" Access locally via browser: http://localhost:{args.port}")
    print(f" To access remotely using ngrok, run in a separate terminal:")
    print(f"    ngrok http {args.port}")
    print("========================================================\n")

    app.run(host="0.0.0.0", port=args.port, debug=True)
