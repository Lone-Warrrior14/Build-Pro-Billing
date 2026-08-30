from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QStackedWidget, QListWidget, QListWidgetItem, QWidget, QHBoxLayout, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

from ui.dashboard import DashboardScreen
from ui.billing import BillingScreen
from ui.invoices import InvoicesScreen
from ui.customers import CustomersScreen
from ui.products import ProductsScreen
from ui.stock import StockScreen
from ui.payments import PaymentsScreen
from ui.reports import ReportsScreen
from ui.settings import SettingsScreen


NAV_ITEMS = [
    "Dashboard", "New Bill", "Invoices", "Shops", "Products",
    "Stock", "Payments", "Reports", "Settings",
]


class MainWindow(QMainWindow):
    def __init__(self, user_id: int, username: str, role: str):
        super().__init__()
        self.user_id = user_id
        self.username = username
        self.role = role

        self.setWindowTitle(f"BuildPro Billing - logged in as {username} ({role})")
        self.resize(1200, 800)

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)

        self.nav_list = QListWidget()
        self.nav_list.setMaximumWidth(160)
        self.nav_list.addItems(NAV_ITEMS)
        self.nav_list.currentRowChanged.connect(self._on_nav_changed)
        root_layout.addWidget(self.nav_list)

        right_panel = QVBoxLayout()
        self.stack = QStackedWidget()
        right_panel.addWidget(self.stack)
        root_layout.addLayout(right_panel, 1)

        self.dashboard_screen = DashboardScreen()
        self.billing_screen = BillingScreen(current_user_id=self.user_id)
        self.billing_screen.invoice_saved.connect(self.dashboard_screen.refresh)
        self.invoices_screen = InvoicesScreen(current_user_id=self.user_id, current_role=self.role)
        self.customers_screen = CustomersScreen()
        self.products_screen = ProductsScreen()
        self.stock_screen = StockScreen()
        self.payments_screen = PaymentsScreen(current_user_id=self.user_id)
        self.reports_screen = ReportsScreen()
        self.settings_screen = SettingsScreen(current_role=self.role)

        for screen in [
            self.dashboard_screen, self.billing_screen, self.invoices_screen,
            self.customers_screen, self.products_screen, self.stock_screen,
            self.payments_screen, self.reports_screen, self.settings_screen,
        ]:
            self.stack.addWidget(screen)

        self.nav_list.setCurrentRow(0)

    def _on_nav_changed(self, index: int):
        self.stack.setCurrentIndex(index)
        # Refresh screens with data that can go stale
        current = self.stack.currentWidget()
        if current is self.dashboard_screen:
            self.dashboard_screen.refresh()
        elif current is self.invoices_screen:
            self.invoices_screen._refresh()
        elif current is self.customers_screen:
            self.customers_screen._refresh()
        elif current is self.products_screen:
            self.products_screen._refresh()
        elif current is self.stock_screen:
            self.stock_screen._refresh()
        elif current is self.payments_screen:
            self.payments_screen._refresh()
        elif current is self.billing_screen:
            self.billing_screen._refresh_next_invoice_number()
