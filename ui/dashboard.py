from __future__ import annotations

import datetime as dt

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QGridLayout,
    QTableWidget, QTableWidgetItem, QAbstractItemView
)

from database.connection import session_scope
from database.models import Invoice, Payment, InvoiceStatus
from services import stock_service, invoice_service
from utils.money import format_inr


def _card(title: str, value: str, color: str = "#2b3a55") -> QGroupBox:
    box = QGroupBox()
    box.setStyleSheet(f"QGroupBox {{ border: 1px solid {color}; border-radius: 6px; }}")
    layout = QVBoxLayout(box)
    title_label = QLabel(title)
    title_label.setStyleSheet("color: gray; font-size: 11px;")
    value_label = QLabel(value)
    value_label.setStyleSheet(f"color: {color}; font-size: 22px; font-weight: bold;")
    layout.addWidget(title_label)
    layout.addWidget(value_label)
    return box


class DashboardScreen(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        self.layout_root = QVBoxLayout(self)
        self.cards_layout = QGridLayout()
        self.layout_root.addLayout(self.cards_layout)

        recent_box = QGroupBox("Recent Invoices")
        recent_layout = QVBoxLayout(recent_box)
        self.recent_invoices_table = QTableWidget(0, 4)
        self.recent_invoices_table.setHorizontalHeaderLabels(["Invoice #", "Shop", "Total", "Status"])
        self.recent_invoices_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        recent_layout.addWidget(self.recent_invoices_table)
        self.layout_root.addWidget(recent_box)

        payments_box = QGroupBox("Recent Payments")
        payments_layout = QVBoxLayout(payments_box)
        self.recent_payments_table = QTableWidget(0, 3)
        self.recent_payments_table.setHorizontalHeaderLabels(["Invoice #", "Amount", "Method"])
        self.recent_payments_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        payments_layout.addWidget(self.recent_payments_table)
        self.layout_root.addWidget(payments_box)

    def refresh(self):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        today = dt.datetime.combine(dt.date.today(), dt.time.min)
        with session_scope() as db:
            todays_invoices = (
                db.query(Invoice)
                .filter(Invoice.invoice_date >= today, Invoice.status != InvoiceStatus.CANCELLED)
                .all()
            )
            todays_sales = sum(i.grand_total_paise for i in todays_invoices)
            todays_payments = (
                db.query(Payment).filter(Payment.payment_date >= today).all()
            )
            todays_payment_total = sum(p.amount_paise for p in todays_payments)

            outstanding = (
                db.query(Invoice)
                .filter(Invoice.status != InvoiceStatus.CANCELLED, Invoice.balance_paise > 0)
                .all()
            )
            outstanding_total = sum(i.balance_paise for i in outstanding)

            from database.models import Product
            total_stock = db.query(Product).filter_by(is_active=True).all()
            total_bags = sum(float(p.current_stock_bags or 0) for p in total_stock)
            low_stock = stock_service.get_low_stock_products(db)

            recent_invoices = (
                db.query(Invoice).order_by(Invoice.invoice_date.desc()).limit(10).all()
            )
            recent_payments = (
                db.query(Payment).order_by(Payment.payment_date.desc()).limit(10).all()
            )

            self.cards_layout.addWidget(_card("Today's Sales", format_inr(todays_sales)), 0, 0)
            self.cards_layout.addWidget(_card("Today's Invoices", str(len(todays_invoices))), 0, 1)
            self.cards_layout.addWidget(_card("Today's Payments", format_inr(todays_payment_total)), 0, 2)
            self.cards_layout.addWidget(
                _card("Outstanding Balance", format_inr(outstanding_total), color="#b00"), 0, 3)
            self.cards_layout.addWidget(_card("Current Stock (bags)", f"{total_bags:g}"), 1, 0)
            self.cards_layout.addWidget(
                _card("Low Stock Items", str(len(low_stock)), color="#b00" if low_stock else "#2b3a55"), 1, 1)

            self.recent_invoices_table.setRowCount(0)
            for row, inv in enumerate(recent_invoices):
                self.recent_invoices_table.insertRow(row)
                self.recent_invoices_table.setItem(row, 0, QTableWidgetItem(inv.invoice_number))
                self.recent_invoices_table.setItem(row, 1, QTableWidgetItem(inv.customer_name_snapshot))
                self.recent_invoices_table.setItem(row, 2, QTableWidgetItem(format_inr(inv.grand_total_paise)))
                self.recent_invoices_table.setItem(row, 3, QTableWidgetItem(inv.status.value))

            self.recent_payments_table.setRowCount(0)
            for row, p in enumerate(recent_payments):
                inv = db.get(Invoice, p.invoice_id)
                self.recent_payments_table.insertRow(row)
                self.recent_payments_table.setItem(
                    row, 0, QTableWidgetItem(inv.invoice_number if inv else "?"))
                self.recent_payments_table.setItem(row, 1, QTableWidgetItem(format_inr(p.amount_paise)))
                self.recent_payments_table.setItem(row, 2, QTableWidgetItem(p.method.value))
