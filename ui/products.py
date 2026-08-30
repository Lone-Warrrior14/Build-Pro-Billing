from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QMessageBox, QDialog, QFormLayout, QDialogButtonBox,
    QDoubleSpinBox, QComboBox, QAbstractItemView
)

from database.connection import session_scope
from database.models import Product, CompanySettings
from services import product_service


class ProductEditDialog(QDialog):
    def __init__(self, product_id: int | None = None):
        super().__init__()
        self.product_id = product_id
        self.setWindowTitle("Edit Product" if product_id else "Add Product")
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.product_name = QLineEdit()
        self.brand = QLineEdit()
        self.variant = QLineEdit()
        self.sku = QLineEdit()
        self.mrp = QDoubleSpinBox()
        self.mrp.setMaximum(1_000_000)
        self.gst_rate = QDoubleSpinBox()
        self.gst_rate.setMaximum(100)
        self.gst_rate.setSuffix(" %")
        self.unit = QComboBox()
        self.unit.addItems(["Bag"])
        self.opening_stock = QDoubleSpinBox()
        self.opening_stock.setMaximum(1_000_000)

        form.addRow("Product Name*:", self.product_name)
        form.addRow("Brand:", self.brand)
        form.addRow("Type/Variant:", self.variant)
        form.addRow("SKU/Code:", self.sku)
        form.addRow("MRP per Bag (₹)*:", self.mrp)
        form.addRow("GST Rate:", self.gst_rate)
        form.addRow("Unit:", self.unit)
        if not product_id:
            form.addRow("Opening Stock (bags):", self.opening_stock)
        layout.addLayout(form)

        with session_scope() as db:
            settings = db.query(CompanySettings).first()
            self.gst_rate.setValue(float(settings.default_gst_rate) if settings else 18.0)

        if product_id:
            with session_scope() as db:
                p = db.get(Product, product_id)
                self.product_name.setText(p.product_name)
                self.brand.setText(p.brand or "")
                self.variant.setText(p.variant or "")
                self.sku.setText(p.sku or "")
                self.mrp.setValue(p.mrp)
                self.gst_rate.setValue(float(p.gst_rate))

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self):
        name = self.product_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing name", "Product name is required.")
            return
        with session_scope() as db:
            if self.product_id is None:
                product_service.create_product(
                    db, product_name=name, brand=self.brand.text().strip(),
                    variant=self.variant.text().strip(), sku=self.sku.text().strip() or None,
                    mrp=self.mrp.value(), gst_rate=self.gst_rate.value(),
                    unit=self.unit.currentText(), opening_stock=self.opening_stock.value(),
                )
            else:
                product_service.update_product(
                    db, self.product_id, product_name=name, brand=self.brand.text().strip(),
                    variant=self.variant.text().strip(), sku=self.sku.text().strip() or None,
                    mrp=self.mrp.value(), gst_rate=self.gst_rate.value(),
                    unit=self.unit.currentText(),
                )
        self.accept()


class ProductsScreen(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search by name, brand, or SKU...")
        self.search_box.textChanged.connect(self._refresh)
        top.addWidget(self.search_box)

        add_btn = QPushButton("+ Add Product")
        add_btn.clicked.connect(self._add_product)
        top.addWidget(add_btn)
        layout.addLayout(top)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Product", "Brand", "Variant", "MRP", "GST %", "Stock (bags)", ""])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)

    def _refresh(self):
        term = self.search_box.text().strip()
        with session_scope() as db:
            products = product_service.search_products(db, term)
            self.table.setRowCount(0)
            for row, p in enumerate(products):
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(p.product_name))
                self.table.setItem(row, 1, QTableWidgetItem(p.brand or ""))
                self.table.setItem(row, 2, QTableWidgetItem(p.variant or ""))
                self.table.setItem(row, 3, QTableWidgetItem(f"₹{p.mrp:.2f}"))
                self.table.setItem(row, 4, QTableWidgetItem(f"{float(p.gst_rate):g}%"))
                self.table.setItem(row, 5, QTableWidgetItem(f"{p.current_stock_bags:g}"))

                edit_btn = QPushButton("Edit")
                edit_btn.clicked.connect(lambda checked=False, pid=p.id: self._edit_product(pid))
                self.table.setCellWidget(row, 6, edit_btn)

    def _add_product(self):
        if ProductEditDialog().exec():
            self._refresh()

    def _edit_product(self, product_id: int):
        if ProductEditDialog(product_id).exec():
            self._refresh()
