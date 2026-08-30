from __future__ import annotations

import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QMessageBox, QDialog, QAbstractItemView, QInputDialog,
    QLabel
)

from database.connection import session_scope
from database.models import Invoice, InvoiceStatus
from services.invoice_service import search_invoices
from services.billing_service import cancel_invoice, BillingError
from invoices.invoice_generator import generate_invoice_pdf
from utils.money import format_inr


class InvoicesScreen(QWidget):
    def __init__(self, current_user_id: int, current_role: str):
        super().__init__()
        self.current_user_id = current_user_id
        self.current_role = current_role
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        self.search_number = QLineEdit()
        self.search_number.setPlaceholderText("Invoice #")
        self.search_shop = QLineEdit()
        self.search_shop.setPlaceholderText("Shop name")
        self.search_phone = QLineEdit()
        self.search_phone.setPlaceholderText("Phone")
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self._refresh)
        top.addWidget(self.search_number)
        top.addWidget(self.search_shop)
        top.addWidget(self.search_phone)
        top.addWidget(search_btn)
        layout.addLayout(top)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Invoice #", "Date", "Shop", "Total", "Balance", "Status", ""])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)

    def _refresh(self):
        with session_scope() as db:
            invoices = search_invoices(
                db,
                invoice_number=self.search_number.text().strip() or None,
                shop_name=self.search_shop.text().strip() or None,
                phone=self.search_phone.text().strip() or None,
            )
            self.table.setRowCount(0)
            for row, inv in enumerate(invoices):
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(inv.invoice_number))
                self.table.setItem(row, 1, QTableWidgetItem(inv.invoice_date.strftime("%d-%m-%Y")))
                self.table.setItem(row, 2, QTableWidgetItem(inv.customer_name_snapshot))
                self.table.setItem(row, 3, QTableWidgetItem(format_inr(inv.grand_total_paise)))
                self.table.setItem(row, 4, QTableWidgetItem(format_inr(inv.balance_paise)))
                status_text = f"{inv.status.value} / {inv.payment_status.value}"
                self.table.setItem(row, 5, QTableWidgetItem(status_text))

                actions = QWidget()
                actions_layout = QHBoxLayout(actions)
                actions_layout.setContentsMargins(0, 0, 0, 0)
                reprint_btn = QPushButton("Reprint")
                reprint_btn.clicked.connect(lambda checked=False, iid=inv.id: self._reprint(iid))
                actions_layout.addWidget(reprint_btn)
                if self.current_role == "admin" and inv.status != InvoiceStatus.CANCELLED:
                    cancel_btn = QPushButton("Void")
                    cancel_btn.clicked.connect(lambda checked=False, iid=inv.id: self._cancel(iid))
                    actions_layout.addWidget(cancel_btn)
                self.table.setCellWidget(row, 6, actions)

    def _reprint(self, invoice_id: int):
        with session_scope() as db:
            invoice = db.get(Invoice, invoice_id)
            out_dir = os.path.join(os.getcwd(), "generated_invoices")
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, f"{invoice.invoice_number}.pdf")
            try:
                generate_invoice_pdf(invoice, out_path)
            except Exception as e:
                QMessageBox.critical(self, "PDF generation failed", str(e))
                return
        try:
            os.startfile(out_path)
        except Exception:
            QMessageBox.information(self, "Saved", f"PDF saved to:\n{out_path}")

    def _cancel(self, invoice_id: int):
        reason, ok = QInputDialog.getText(self, "Void Invoice", "Reason for cancellation:")
        if not ok or not reason.strip():
            return
        try:
            with session_scope() as db:
                cancel_invoice(db, invoice_id, reason.strip(), user_id=self.current_user_id)
        except BillingError as e:
            QMessageBox.critical(self, "Could not cancel", str(e))
            return
        self._refresh()
