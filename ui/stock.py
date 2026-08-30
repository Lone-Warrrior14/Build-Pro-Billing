from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QComboBox, QDoubleSpinBox, QMessageBox, QDialog, QFormLayout, QDialogButtonBox,
    QLineEdit, QAbstractItemView, QLabel
)

from database.connection import session_scope
from database.models import Product
from services import product_service, stock_service


class StockInDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stock In / Purchase")
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.product_combo = QComboBox()
        with session_scope() as db:
            for p in product_service.search_products(db):
                self.product_combo.addItem(f"{p.brand} {p.product_name}", p.id)
        self.qty = QDoubleSpinBox()
        self.qty.setMaximum(1_000_000)
        self.notes = QLineEdit()
        form.addRow("Product:", self.product_combo)
        form.addRow("Quantity (bags):", self.qty)
        form.addRow("Notes:", self.notes)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self):
        if self.qty.value() <= 0:
            QMessageBox.warning(self, "Invalid", "Enter a quantity greater than zero.")
            return
        with session_scope() as db:
            stock_service.stock_in(
                db, self.product_combo.currentData(), self.qty.value(),
                notes=self.notes.text().strip())
        self.accept()


class StockAdjustDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stock Adjustment (Physical Count)")
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.product_combo = QComboBox()
        with session_scope() as db:
            for p in product_service.search_products(db):
                self.product_combo.addItem(
                    f"{p.brand} {p.product_name} (current: {p.current_stock_bags:g})", p.id)
        self.new_count = QDoubleSpinBox()
        self.new_count.setMaximum(1_000_000)
        self.reason = QComboBox()
        self.reason.addItems(["Damaged", "Missing", "Counting correction", "Other"])
        self.notes = QLineEdit()
        form.addRow("Product:", self.product_combo)
        form.addRow("Physical Count (bags):", self.new_count)
        form.addRow("Reason*:", self.reason)
        form.addRow("Notes:", self.notes)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self):
        with session_scope() as db:
            stock_service.adjust_stock(
                db, self.product_combo.currentData(), self.new_count.value(),
                reason=self.reason.currentText(), notes=self.notes.text().strip())
        self.accept()


class StockScreen(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        stock_in_btn = QPushButton("+ Stock In / Purchase")
        stock_in_btn.clicked.connect(self._stock_in)
        top.addWidget(stock_in_btn)

        adjust_btn = QPushButton("Adjust Stock (Physical Count)")
        adjust_btn.clicked.connect(self._adjust)
        top.addWidget(adjust_btn)
        top.addStretch()
        layout.addLayout(top)

        self.low_stock_label = QLabel("")
        self.low_stock_label.setStyleSheet("color: #b00; font-weight: bold;")
        layout.addWidget(self.low_stock_label)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Product", "Brand", "Current Stock (bags)", "History"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)

    def _refresh(self):
        with session_scope() as db:
            products = product_service.search_products(db)
            low_stock = stock_service.get_low_stock_products(db)
            if low_stock:
                names = ", ".join(p.product_name for p in low_stock)
                self.low_stock_label.setText(f"⚠ Low stock: {names}")
            else:
                self.low_stock_label.setText("")

            self.table.setRowCount(0)
            for row, p in enumerate(products):
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(p.product_name))
                self.table.setItem(row, 1, QTableWidgetItem(p.brand or ""))
                self.table.setItem(row, 2, QTableWidgetItem(f"{p.current_stock_bags:g}"))
                history_btn = QPushButton("View History")
                history_btn.clicked.connect(lambda checked=False, pid=p.id: self._show_history(pid))
                self.table.setCellWidget(row, 3, history_btn)

    def _stock_in(self):
        if StockInDialog().exec():
            self._refresh()

    def _adjust(self):
        if StockAdjustDialog().exec():
            self._refresh()

    def _show_history(self, product_id: int):
        dlg = QDialog(self)
        dlg.setWindowTitle("Stock Movement History")
        dlg.setMinimumSize(600, 400)
        layout = QVBoxLayout(dlg)
        with session_scope() as db:
            history = stock_service.get_stock_history(db, product_id)
            table = QTableWidget(len(history), 5)
            table.setHorizontalHeaderLabels(["Date", "Type", "Qty", "Balance After", "Notes/Reason"])
            for row, h in enumerate(history):
                table.setItem(row, 0, QTableWidgetItem(h.created_at.strftime("%d-%m-%Y %H:%M")))
                table.setItem(row, 1, QTableWidgetItem(h.txn_type.value))
                table.setItem(row, 2, QTableWidgetItem(f"{h.quantity_bags:g}"))
                table.setItem(row, 3, QTableWidgetItem(f"{h.balance_after_bags:g}"))
                table.setItem(row, 4, QTableWidgetItem(h.reason or h.notes or ""))
            layout.addWidget(table)
        dlg.exec()
