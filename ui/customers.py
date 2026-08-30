from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QMessageBox, QDialog, QFormLayout, QDialogButtonBox,
    QTextEdit, QDoubleSpinBox, QAbstractItemView, QTabWidget, QLabel
)

from database.connection import session_scope
from database.models import Customer
from services import customer_service
from utils.money import format_inr, to_paise


class CustomerEditDialog(QDialog):
    def __init__(self, customer_id: int | None = None):
        super().__init__()
        self.customer_id = customer_id
        self.setWindowTitle("Edit Shop" if customer_id else "Add Shop")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.shop_name = QLineEdit()
        self.contact_person = QLineEdit()
        self.phone = QLineEdit()
        self.address = QTextEdit()
        self.address.setMaximumHeight(60)
        self.gstin = QLineEdit()
        self.opening_balance = QDoubleSpinBox()
        self.opening_balance.setMaximum(10_000_000)
        self.notes = QTextEdit()
        self.notes.setMaximumHeight(50)

        form.addRow("Shop Name*:", self.shop_name)
        form.addRow("Contact Person:", self.contact_person)
        form.addRow("Phone:", self.phone)
        form.addRow("Address:", self.address)
        form.addRow("GSTIN:", self.gstin)
        form.addRow("Opening Balance (₹):", self.opening_balance)
        form.addRow("Notes:", self.notes)
        layout.addLayout(form)

        if customer_id:
            with session_scope() as db:
                c = db.get(Customer, customer_id)
                self.shop_name.setText(c.shop_name)
                self.contact_person.setText(c.contact_person or "")
                self.phone.setText(c.phone or "")
                self.address.setPlainText(c.address or "")
                self.gstin.setText(c.gstin or "")
                self.opening_balance.setValue(c.opening_balance)
                self.opening_balance.setEnabled(False)  # opening balance is set once at creation
                self.notes.setPlainText(c.notes or "")

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self):
        name = self.shop_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing name", "Shop name is required.")
            return

        with session_scope() as db:
            if self.customer_id is None:
                dups = customer_service.find_similar_customers(db, name)
                if dups:
                    names = ", ".join(f"{c.shop_name} ({r:.0%} match)" for c, r in dups[:3])
                    reply = QMessageBox.question(
                        self, "Possible duplicate shop",
                        f"A similar shop already exists: {names}\n\nCreate anyway?",
                        QMessageBox.Yes | QMessageBox.No,
                    )
                    if reply != QMessageBox.Yes:
                        return
                customer_service.create_customer(
                    db, shop_name=name, contact_person=self.contact_person.text().strip(),
                    phone=self.phone.text().strip(), address=self.address.toPlainText().strip(),
                    gstin=self.gstin.text().strip(), opening_balance=self.opening_balance.value(),
                    notes=self.notes.toPlainText().strip(),
                )
            else:
                c = db.get(Customer, self.customer_id)
                c.shop_name = name
                c.contact_person = self.contact_person.text().strip()
                c.phone = self.phone.text().strip()
                c.address = self.address.toPlainText().strip()
                c.gstin = self.gstin.text().strip()
                c.notes = self.notes.toPlainText().strip()
        self.accept()


class LedgerDialog(QDialog):
    def __init__(self, customer_id: int):
        super().__init__()
        self.setWindowTitle("Customer Ledger")
        self.setMinimumSize(600, 400)
        layout = QVBoxLayout(self)

        with session_scope() as db:
            c = db.get(Customer, customer_id)
            layout.addWidget(QLabel(f"<b>{c.shop_name}</b> - {c.phone}"))
            entries = customer_service.get_ledger(db, customer_id)

            table = QTableWidget(len(entries), 5)
            table.setHorizontalHeaderLabels(["Date", "Type", "Description", "Amount", "Balance"])
            for row, e in enumerate(entries):
                amount = e.debit_paise if e.debit_paise else -e.credit_paise
                table.setItem(row, 0, QTableWidgetItem(e.entry_date.strftime("%d-%m-%Y %H:%M")))
                table.setItem(row, 1, QTableWidgetItem(e.entry_type.value))
                table.setItem(row, 2, QTableWidgetItem(e.description))
                table.setItem(row, 3, QTableWidgetItem(format_inr(amount)))
                table.setItem(row, 4, QTableWidgetItem(format_inr(e.balance_after_paise)))
            layout.addWidget(table)


class CustomersScreen(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search by shop name, phone, or GSTIN...")
        self.search_box.textChanged.connect(self._refresh)
        top.addWidget(self.search_box)

        add_btn = QPushButton("+ Add Shop")
        add_btn.clicked.connect(self._add_shop)
        top.addWidget(add_btn)
        layout.addLayout(top)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Shop Name", "Phone", "GSTIN", "Outstanding", "", ""])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)

    def _refresh(self):
        term = self.search_box.text().strip()
        with session_scope() as db:
            customers = customer_service.search_customers(db, term) if term else (
                db.query(Customer).filter_by(is_active=True).order_by(Customer.shop_name).all()
            )
            self.table.setRowCount(0)
            for row, c in enumerate(customers):
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(c.shop_name))
                self.table.setItem(row, 1, QTableWidgetItem(c.phone or ""))
                self.table.setItem(row, 2, QTableWidgetItem(c.gstin or ""))
                balance = customer_service.get_current_balance_paise(db, c.id)
                self.table.setItem(row, 3, QTableWidgetItem(format_inr(balance)))

                ledger_btn = QPushButton("Ledger")
                ledger_btn.clicked.connect(lambda checked=False, cid=c.id: self._show_ledger(cid))
                self.table.setCellWidget(row, 4, ledger_btn)

                edit_btn = QPushButton("Edit")
                edit_btn.clicked.connect(lambda checked=False, cid=c.id: self._edit_shop(cid))
                self.table.setCellWidget(row, 5, edit_btn)

    def _add_shop(self):
        dlg = CustomerEditDialog()
        if dlg.exec():
            self._refresh()

    def _edit_shop(self, customer_id: int):
        dlg = CustomerEditDialog(customer_id)
        if dlg.exec():
            self._refresh()

    def _show_ledger(self, customer_id: int):
        LedgerDialog(customer_id).exec()
