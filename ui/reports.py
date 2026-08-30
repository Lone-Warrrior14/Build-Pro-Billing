from __future__ import annotations

import csv
import datetime as dt

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, QTableWidget,
    QTableWidgetItem, QDateEdit, QLabel, QFileDialog, QMessageBox, QAbstractItemView
)
from PySide6.QtCore import QDate

from database.connection import session_scope
from services import report_service
from utils.money import format_inr

REPORT_OPTIONS = [
    "Sales by Date Range",
    "Customer-wise Sales",
    "Product-wise Sales",
    "GST Summary",
    "Outstanding Balances",
    "Payment History",
    "Stock Movement History",
]


class ReportsScreen(QWidget):
    def __init__(self):
        super().__init__()
        self._last_headers = []
        self._last_rows = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        self.report_combo = QComboBox()
        self.report_combo.addItems(REPORT_OPTIONS)
        top.addWidget(self.report_combo)

        self.date_from = QDateEdit(calendarPopup=True)
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_to = QDateEdit(calendarPopup=True)
        self.date_to.setDate(QDate.currentDate())
        top.addWidget(QLabel("From:"))
        top.addWidget(self.date_from)
        top.addWidget(QLabel("To:"))
        top.addWidget(self.date_to)

        run_btn = QPushButton("Run Report")
        run_btn.clicked.connect(self._run_report)
        top.addWidget(run_btn)

        export_btn = QPushButton("Export CSV")
        export_btn.clicked.connect(self._export_csv)
        top.addWidget(export_btn)

        layout.addLayout(top)

        self.table = QTableWidget(0, 0)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)

    def _run_report(self):
        report = self.report_combo.currentText()
        date_from = self.date_from.date().toPython()
        date_to = self.date_to.date().toPython()

        with session_scope() as db:
            if report == "Sales by Date Range":
                invoices = report_service.sales_by_date_range(db, date_from, date_to)
                headers = ["Invoice #", "Date", "Shop", "Total"]
                rows = [[i.invoice_number, i.invoice_date.strftime("%d-%m-%Y"),
                         i.customer_name_snapshot, format_inr(i.grand_total_paise)]
                        for i in invoices]

            elif report == "Customer-wise Sales":
                data = report_service.customer_wise_sales(db, date_from, date_to)
                headers = ["Shop", "Total Sales"]
                rows = [[name, format_inr(total)] for name, total in data]

            elif report == "Product-wise Sales":
                data = report_service.product_wise_sales(db, date_from, date_to)
                headers = ["Product", "Qty Sold (bags)", "Total Sales"]
                rows = [[name, f"{v['qty']:g}", format_inr(v["amount"])] for name, v in data]

            elif report == "GST Summary":
                summary = report_service.gst_summary(db, date_from, date_to)
                headers = ["Metric", "Amount"]
                rows = [
                    ["Taxable Amount", format_inr(summary["taxable_amount"])],
                    ["Total CGST", format_inr(summary["cgst"])],
                    ["Total SGST", format_inr(summary["sgst"])],
                    ["Total GST", format_inr(summary["total_gst"])],
                ]

            elif report == "Outstanding Balances":
                invoices = report_service.outstanding_balances(db)
                headers = ["Invoice #", "Shop", "Total", "Balance"]
                rows = [[i.invoice_number, i.customer_name_snapshot,
                         format_inr(i.grand_total_paise), format_inr(i.balance_paise)]
                        for i in invoices]

            elif report == "Payment History":
                payments = report_service.payment_history(db, date_from, date_to)
                headers = ["Date", "Invoice ID", "Amount", "Method"]
                rows = [[p.payment_date.strftime("%d-%m-%Y %H:%M"), str(p.invoice_id),
                         format_inr(p.amount_paise), p.method.value] for p in payments]

            else:  # Stock Movement History
                txns = report_service.stock_movement_report(db, date_from, date_to)
                headers = ["Date", "Product ID", "Type", "Qty", "Balance After"]
                rows = [[t.created_at.strftime("%d-%m-%Y %H:%M"), str(t.product_id),
                         t.txn_type.value, f"{t.quantity_bags:g}", f"{t.balance_after_bags:g}"]
                        for t in txns]

        self._last_headers, self._last_rows = headers, rows
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                self.table.setItem(r, c, QTableWidgetItem(str(val)))

    def _export_csv(self):
        if not self._last_rows:
            QMessageBox.information(self, "No data", "Run a report first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "report.csv", "CSV (*.csv)")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(self._last_headers)
            writer.writerows(self._last_rows)
        QMessageBox.information(self, "Exported", f"Report exported to:\n{path}")
