from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QMessageBox, QDialog, QFormLayout, QDialogButtonBox,
    QDoubleSpinBox, QComboBox, QAbstractItemView
)

from database.connection import session_scope
from database.models import Invoice, PaymentMethod
from services.invoice_service import search_invoices
from services.billing_service import record_payment, BillingError
from utils.money import format_inr, to_paise


class RecordPaymentDialog(QDialog):
    def __init__(self, invoice_id: int, user_id: int):
        super().__init__()
        self.invoice_id = invoice_id
        self.user_id = user_id
        self.setWindowTitle("Record Payment")
        layout = QVBoxLayout(self)

        with session_scope() as db:
            invoice = db.get(Invoice, invoice_id)
            balance = invoice.balance_paise

        form = QFormLayout()
        form.addRow("Invoice:", QLineEdit(invoice.invoice_number if False else ""))
        self.balance_label = QLineEdit(format_inr(balance))
        self.balance_label.setReadOnly(True)
        form.addRow("Outstanding Balance:", self.balance_label)

        self.amount = QDoubleSpinBox()
        self.amount.setMaximum(balance / 100.0)
        self.amount.setValue(balance / 100.0)
        form.addRow("Amount:", self.amount)

        self.method = QComboBox()
        self.method.addItems([m.value.upper() for m in PaymentMethod])
        form.addRow("Method:", self.method)

        self.notes = QLineEdit()
        form.addRow("Notes:", self.notes)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self):
        try:
            with session_scope() as db:
                record_payment(
                    db, self.invoice_id, to_paise(self.amount.value()),
                    PaymentMethod(self.method.currentText().lower()),
                    notes=self.notes.text().strip(), user_id=self.user_id,
                )
        except BillingError as e:
            QMessageBox.critical(self, "Could not record payment", str(e))
            return
        self.accept()


class PaymentsScreen(QWidget):
    def __init__(self, current_user_id: int):
        super().__init__()
        self.current_user_id = current_user_id
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        self.search_shop = QLineEdit()
        self.search_shop.setPlaceholderText("Filter by shop name...")
        self.search_shop.textChanged.connect(self._refresh)
        top.addWidget(self.search_shop)
        layout.addLayout(top)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Invoice #", "Shop", "Total", "Balance Due", ""])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)

    def _refresh(self):
        with session_scope() as db:
            invoices = [
                inv for inv in search_invoices(db, shop_name=self.search_shop.text().strip() or None)
                if inv.balance_paise > 0
            ]
            self.table.setRowCount(0)
            for row, inv in enumerate(invoices):
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(inv.invoice_number))
                self.table.setItem(row, 1, QTableWidgetItem(inv.customer_name_snapshot))
                self.table.setItem(row, 2, QTableWidgetItem(format_inr(inv.grand_total_paise)))
                self.table.setItem(row, 3, QTableWidgetItem(format_inr(inv.balance_paise)))
                pay_btn = QPushButton("Record Payment")
                pay_btn.clicked.connect(lambda checked=False, iid=inv.id: self._record(iid))
                self.table.setCellWidget(row, 4, pay_btn)

    def _record(self, invoice_id: int):
        if RecordPaymentDialog(invoice_id, self.current_user_id).exec():
            self._refresh()
