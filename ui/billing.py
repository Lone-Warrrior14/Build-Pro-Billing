"""
New Bill screen (spec sections 10-13, 35-36).

Fast workflow: search shop -> search & add products -> price is
auto-suggested from Shop+Product memory but always editable -> GST is
computed live -> save is one atomic transaction.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QCompleter, QListWidget, QListWidgetItem,
    QComboBox, QDoubleSpinBox, QMessageBox, QGroupBox, QFormLayout, QSplitter,
    QAbstractItemView, QFileDialog
)

from database.connection import session_scope
from database.models import Customer, Product, PaymentMethod
from services import customer_service, product_service, pricing_service, billing_service
from services.invoice_service import peek_next_invoice_number
from services.billing_service import BillLineInput, InitialPaymentInput, BillingError
from services.stock_service import InsufficientStockError
from utils.money import to_paise, to_rupees, format_inr
from invoices.invoice_generator import generate_invoice_pdf
import os


COL_PRODUCT, COL_QTY, COL_MRP, COL_PRICE, COL_GST, COL_TAXABLE, COL_AMOUNT, COL_REMOVE = range(8)


class BillingScreen(QWidget):
    invoice_saved = Signal()

    def __init__(self, current_user_id: int):
        super().__init__()
        self.current_user_id = current_user_id
        self.selected_customer_id: int | None = None
        self.line_items: list[dict] = []  # holds computed line data parallel to table rows

        self._build_ui()
        self._refresh_next_invoice_number()

    # ------------------------------------------------------------------ UI

    def _build_ui(self):
        root = QVBoxLayout(self)

        header = QHBoxLayout()
        self.invoice_number_label = QLabel("Invoice: —")
        self.invoice_number_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header.addWidget(self.invoice_number_label)
        header.addStretch()
        root.addLayout(header)

        splitter = QSplitter(Qt.Vertical)

        # ---- Shop search -------------------------------------------------
        shop_box = QGroupBox("1. Shop / Customer")
        shop_layout = QVBoxLayout(shop_box)
        search_row = QHBoxLayout()
        self.shop_search = QLineEdit()
        self.shop_search.setPlaceholderText("Type shop name, phone, or GSTIN to search...")
        self.shop_search.textChanged.connect(self._on_shop_search)
        search_row.addWidget(self.shop_search)
        shop_layout.addLayout(search_row)

        self.shop_results = QListWidget()
        self.shop_results.setMaximumHeight(90)
        self.shop_results.itemClicked.connect(self._on_shop_selected)
        shop_layout.addWidget(self.shop_results)

        self.shop_info_label = QLabel("No shop selected.")
        self.shop_info_label.setStyleSheet("color: #444;")
        shop_layout.addWidget(self.shop_info_label)
        splitter.addWidget(shop_box)

        # ---- Add product ---------------------------------------------------
        product_box = QGroupBox("2. Add Cement Product")
        product_layout = QVBoxLayout(product_box)
        add_row = QHBoxLayout()

        self.product_search = QLineEdit()
        self.product_search.setPlaceholderText("Search product / brand / SKU...")
        self.product_search.textChanged.connect(self._on_product_search)
        add_row.addWidget(self.product_search, 3)

        self.product_results = QComboBox()
        self.product_results.setMinimumWidth(260)
        self.product_results.currentIndexChanged.connect(self._on_product_pick)
        add_row.addWidget(self.product_results, 2)

        self.qty_input = QDoubleSpinBox()
        self.qty_input.setDecimals(2)
        self.qty_input.setMaximum(100000)
        self.qty_input.setMinimum(0.01)
        self.qty_input.setValue(1)
        self.qty_input.setPrefix("Qty: ")
        add_row.addWidget(self.qty_input, 1)

        self.price_input = QDoubleSpinBox()
        self.price_input.setDecimals(2)
        self.price_input.setMaximum(1_000_000)
        self.price_input.setPrefix("₹")
        add_row.addWidget(self.price_input, 1)

        self.add_item_btn = QPushButton("Add to Bill")
        self.add_item_btn.clicked.connect(self._add_line_item)
        add_row.addWidget(self.add_item_btn)

        product_layout.addLayout(add_row)
        self.price_hint_label = QLabel("")
        self.price_hint_label.setStyleSheet("color: #0a6;")
        product_layout.addWidget(self.price_hint_label)
        splitter.addWidget(product_box)

        # ---- Bill table ------------------------------------------------------
        table_box = QGroupBox("3. Bill Items")
        table_layout = QVBoxLayout(table_box)
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            ["Product", "Qty", "MRP", "Selling Price", "GST %", "Taxable Amt", "Amount", ""])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table_layout.addWidget(self.table)
        splitter.addWidget(table_box)

        root.addWidget(splitter, 1)

        # ---- Totals + payment -------------------------------------------------
        bottom = QHBoxLayout()

        totals_box = QGroupBox("Totals")
        totals_form = QFormLayout(totals_box)
        self.discount_input = QDoubleSpinBox()
        self.discount_input.setPrefix("₹")
        self.discount_input.setMaximum(1_000_000)
        self.discount_input.valueChanged.connect(self._recalculate_totals)
        totals_form.addRow("Discount:", self.discount_input)

        self.roundoff_input = QDoubleSpinBox()
        self.roundoff_input.setPrefix("₹")
        self.roundoff_input.setRange(-100, 100)
        self.roundoff_input.valueChanged.connect(self._recalculate_totals)
        totals_form.addRow("Round Off:", self.roundoff_input)

        self.subtotal_label = QLabel("₹0.00")
        self.cgst_label = QLabel("₹0.00")
        self.sgst_label = QLabel("₹0.00")
        self.grand_total_label = QLabel("₹0.00")
        self.grand_total_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        totals_form.addRow("Subtotal:", self.subtotal_label)
        totals_form.addRow("Total CGST:", self.cgst_label)
        totals_form.addRow("Total SGST:", self.sgst_label)
        totals_form.addRow("Grand Total:", self.grand_total_label)
        bottom.addWidget(totals_box)

        payment_box = QGroupBox("Payment")
        payment_form = QFormLayout(payment_box)
        self.payment_method = QComboBox()
        self.payment_method.addItems([m.value.upper() for m in PaymentMethod])
        payment_form.addRow("Method:", self.payment_method)

        self.amount_paid_input = QDoubleSpinBox()
        self.amount_paid_input.setPrefix("₹")
        self.amount_paid_input.setMaximum(10_000_000)
        payment_form.addRow("Amount Paid Now:", self.amount_paid_input)

        pay_full_btn = QPushButton("Mark Fully Paid")
        pay_full_btn.clicked.connect(self._mark_fully_paid)
        payment_form.addRow(pay_full_btn)
        bottom.addWidget(payment_box)

        action_box = QVBoxLayout()
        self.save_btn = QPushButton("💾 Save Invoice")
        self.save_btn.setStyleSheet(
            "font-size: 15px; font-weight: bold; padding: 10px; background:#2b7a3d; color:white;")
        self.save_btn.clicked.connect(self._save_invoice)
        action_box.addWidget(self.save_btn)

        clear_btn = QPushButton("Clear Bill")
        clear_btn.clicked.connect(self._clear_bill)
        action_box.addWidget(clear_btn)
        bottom.addLayout(action_box)

        root.addLayout(bottom)

    # ------------------------------------------------------------ shop search

    def _on_shop_search(self, text: str):
        self.shop_results.clear()
        if len(text.strip()) < 1:
            return
        with session_scope() as db:
            results = customer_service.search_customers(db, text.strip())
            for c in results:
                item = QListWidgetItem(f"{c.shop_name}  |  {c.phone}  |  {c.address[:40]}")
                item.setData(Qt.UserRole, c.id)
                self.shop_results.addItem(item)

    def _on_shop_selected(self, item: QListWidgetItem):
        customer_id = item.data(Qt.UserRole)
        self.selected_customer_id = customer_id
        with session_scope() as db:
            c = db.get(Customer, customer_id)
            balance = customer_service.get_current_balance_paise(db, customer_id)
            self.shop_info_label.setText(
                f"<b>{c.shop_name}</b> | {c.phone} | {c.address}\n"
                f"Outstanding balance: {format_inr(balance)}"
            )
        self.shop_search.setText(item.text().split("  |  ")[0])
        self.shop_results.clear()
        self._maybe_update_price_hint()

    # --------------------------------------------------------- product search

    def _on_product_search(self, text: str):
        self.product_results.blockSignals(True)
        self.product_results.clear()
        with session_scope() as db:
            results = product_service.search_products(db, text.strip())
            for p in results:
                label = f"{p.brand} {p.product_name} ({p.variant}) - MRP ₹{p.mrp:.2f} - Stock {p.current_stock_bags}"
                self.product_results.addItem(label, userData=p.id)
        self.product_results.blockSignals(False)
        self._maybe_update_price_hint()

    def _on_product_pick(self, index: int):
        self._maybe_update_price_hint()

    def _current_product_id(self) -> int | None:
        return self.product_results.currentData()

    def _maybe_update_price_hint(self):
        product_id = self._current_product_id()
        if not product_id or not self.selected_customer_id:
            self.price_hint_label.setText("")
            return
        with session_scope() as db:
            product = db.get(Product, product_id)
            suggested = pricing_service.get_suggested_price_paise(
                db, self.selected_customer_id, product_id)
            if suggested is not None:
                self.price_input.setValue(to_rupees(suggested))
                self.price_hint_label.setText(
                    f"Suggested price (last used for this shop): {format_inr(suggested)}  "
                    f"| MRP: ₹{product.mrp:.2f}")
            else:
                self.price_input.setValue(product.mrp)
                self.price_hint_label.setText(
                    f"No price history for this shop yet - defaulted to MRP ₹{product.mrp:.2f}. "
                    f"Enter the agreed selling price.")

    # ------------------------------------------------------------- bill lines

    def _add_line_item(self):
        product_id = self._current_product_id()
        if not product_id:
            QMessageBox.warning(self, "No product", "Please search and select a product first.")
            return
        if not self.selected_customer_id:
            QMessageBox.warning(self, "No shop", "Please select a shop/customer first.")
            return

        qty = Decimal(str(self.qty_input.value()))
        price_paise = to_paise(self.price_input.value())
        if qty <= 0:
            QMessageBox.warning(self, "Invalid quantity", "Quantity must be greater than zero.")
            return

        with session_scope() as db:
            product = db.get(Product, product_id)
            gst_rate = product.gst_rate
            taxable = int(round(float(qty) * price_paise))
            cgst = int(round(taxable * float(gst_rate) / 200.0))
            sgst = int(round(taxable * float(gst_rate) / 200.0))
            amount = taxable + cgst + sgst

            self.line_items.append(dict(
                product_id=product_id,
                product_name=f"{product.brand} {product.product_name}".strip(),
                qty=qty,
                mrp_paise=product.mrp_paise,
                price_paise=price_paise,
                gst_rate=gst_rate,
                taxable_paise=taxable,
                cgst_paise=cgst,
                sgst_paise=sgst,
                amount_paise=amount,
            ))

        self._render_table()
        self._recalculate_totals()

    def _render_table(self):
        self.table.setRowCount(0)
        for row_idx, line in enumerate(self.line_items):
            self.table.insertRow(row_idx)
            self.table.setItem(row_idx, 0, QTableWidgetItem(line["product_name"]))
            self.table.setItem(row_idx, 1, QTableWidgetItem(f"{line['qty']:g}"))
            self.table.setItem(row_idx, 2, QTableWidgetItem(format_inr(line["mrp_paise"])))
            self.table.setItem(row_idx, 3, QTableWidgetItem(format_inr(line["price_paise"])))
            self.table.setItem(row_idx, 4, QTableWidgetItem(f"{float(line['gst_rate']):g}%"))
            self.table.setItem(row_idx, 5, QTableWidgetItem(format_inr(line["taxable_paise"])))
            self.table.setItem(row_idx, 6, QTableWidgetItem(format_inr(line["amount_paise"])))
            remove_btn = QPushButton("Remove")
            remove_btn.clicked.connect(lambda checked=False, r=row_idx: self._remove_line(r))
            self.table.setCellWidget(row_idx, 7, remove_btn)

    def _remove_line(self, row_idx: int):
        del self.line_items[row_idx]
        self._render_table()
        self._recalculate_totals()

    def _recalculate_totals(self):
        subtotal = sum(l["taxable_paise"] for l in self.line_items)
        cgst = sum(l["cgst_paise"] for l in self.line_items)
        sgst = sum(l["sgst_paise"] for l in self.line_items)
        discount_paise = to_paise(self.discount_input.value())
        roundoff_paise = to_paise(self.roundoff_input.value())
        grand_total = subtotal - discount_paise + cgst + sgst + roundoff_paise

        self.subtotal_label.setText(format_inr(subtotal))
        self.cgst_label.setText(format_inr(cgst))
        self.sgst_label.setText(format_inr(sgst))
        self.grand_total_label.setText(format_inr(max(grand_total, 0)))
        self._current_grand_total_paise = max(grand_total, 0)

    def _mark_fully_paid(self):
        total = getattr(self, "_current_grand_total_paise", 0)
        self.amount_paid_input.setValue(to_rupees(total))

    # ------------------------------------------------------------------ save

    def _refresh_next_invoice_number(self):
        with session_scope() as db:
            self.invoice_number_label.setText(f"Next Invoice: {peek_next_invoice_number(db)}")

    def _save_invoice(self):
        if not self.selected_customer_id:
            QMessageBox.warning(self, "No shop", "Please select a shop/customer.")
            return
        if not self.line_items:
            QMessageBox.warning(self, "No items", "Add at least one product to the bill.")
            return

        discount_paise = to_paise(self.discount_input.value())
        roundoff_paise = to_paise(self.roundoff_input.value())
        amount_paid_paise = to_paise(self.amount_paid_input.value())
        method = PaymentMethod(self.payment_method.currentText().lower())

        lines = [
            BillLineInput(
                product_id=l["product_id"], quantity_bags=l["qty"],
                selling_price_paise=l["price_paise"], gst_rate=l["gst_rate"],
            ) for l in self.line_items
        ]
        initial_payment = (
            InitialPaymentInput(amount_paise=amount_paid_paise, method=method)
            if amount_paid_paise > 0 else None
        )

        try:
            with session_scope() as db:
                invoice = billing_service.create_invoice(
                    db, customer_id=self.selected_customer_id, lines=lines,
                    discount_paise=discount_paise, round_off_paise=roundoff_paise,
                    initial_payment=initial_payment, user_id=self.current_user_id,
                )
                db.flush()
                invoice_number = invoice.invoice_number
                invoice_id = invoice.id
        except (BillingError, InsufficientStockError) as e:
            QMessageBox.critical(self, "Could not save invoice", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "Unexpected error",
                                  f"The invoice could not be saved and no changes were made.\n{e}")
            return

        QMessageBox.information(self, "Invoice Saved", f"Invoice {invoice_number} saved successfully.")

        # Offer to generate/print PDF
        self._generate_and_offer_pdf(invoice_id)

        self._clear_bill()
        self._refresh_next_invoice_number()
        self.invoice_saved.emit()

    def _generate_and_offer_pdf(self, invoice_id: int):
        from database.models import Invoice
        with session_scope() as db:
            invoice = db.get(Invoice, invoice_id)
            out_dir = os.path.join(os.getcwd(), "generated_invoices")
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, f"{invoice.invoice_number}.pdf")
            try:
                generate_invoice_pdf(invoice, out_path)
            except Exception as e:
                QMessageBox.warning(self, "PDF generation failed",
                                     f"Invoice was saved but the PDF could not be generated:\n{e}")
                return

        reply = QMessageBox.question(
            self, "Print Invoice", f"PDF generated at:\n{out_path}\n\nOpen it now?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            try:
                os.startfile(out_path)  # Windows
            except Exception:
                QMessageBox.information(self, "Open manually", f"Please open:\n{out_path}")

    def _clear_bill(self):
        self.line_items = []
        self._render_table()
        self.discount_input.setValue(0)
        self.roundoff_input.setValue(0)
        self.amount_paid_input.setValue(0)
        self._recalculate_totals()
        self.selected_customer_id = None
        self.shop_search.clear()
        self.shop_info_label.setText("No shop selected.")
        self.price_hint_label.setText("")
