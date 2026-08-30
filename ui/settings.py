from __future__ import annotations

import os
import shutil

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QPushButton,
    QLabel, QTextEdit, QDoubleSpinBox, QCheckBox, QSpinBox, QTabWidget,
    QFileDialog, QMessageBox, QGroupBox
)
from PySide6.QtGui import QPixmap

from database.connection import session_scope, get_app_dir
from database.models import CompanySettings
from services.backup_service import create_backup, list_backups, restore_backup, last_backup_time


ASSET_DIRS = {
    "logo": "assets/logo",
    "signature": "assets/signatures",
    "stamp": "assets/stamps",
}


def _copy_asset(src_path: str, kind: str) -> str:
    dest_dir = os.path.join(get_app_dir(), ASSET_DIRS[kind])
    os.makedirs(dest_dir, exist_ok=True)
    filename = os.path.basename(src_path)
    dest_path = os.path.join(dest_dir, filename)
    shutil.copy2(src_path, dest_path)
    return dest_path


class SettingsScreen(QWidget):
    def __init__(self, current_role: str):
        super().__init__()
        self.current_role = current_role
        self.is_admin = current_role == "admin"
        self._build_ui()
        self._load()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        if not self.is_admin:
            layout.addWidget(QLabel(
                "⚠ Only Administrators can change settings. Viewing read-only."))

        tabs = QTabWidget()
        layout.addWidget(tabs)

        # --- Company tab ---
        company_tab = QWidget()
        form = QFormLayout(company_tab)
        self.company_name = QLineEdit()
        self.address = QTextEdit(); self.address.setMaximumHeight(60)
        self.phone = QLineEdit()
        self.gstin = QLineEdit()
        self.logo_path_label = QLabel("No logo set")
        logo_btn = QPushButton("Upload Logo")
        logo_btn.clicked.connect(self._upload_logo)
        form.addRow("Company Name:", self.company_name)
        form.addRow("Address:", self.address)
        form.addRow("Phone:", self.phone)
        form.addRow("GSTIN:", self.gstin)
        form.addRow("Logo:", self.logo_path_label)
        form.addRow("", logo_btn)
        tabs.addTab(company_tab, "Company")

        # --- Invoice tab ---
        invoice_tab = QWidget()
        iform = QFormLayout(invoice_tab)
        self.invoice_prefix = QLineEdit()
        self.invoice_start = QSpinBox(); self.invoice_start.setMaximum(1_000_000)
        self.show_mrp = QCheckBox("Show MRP on invoice")
        self.show_customer_sig = QCheckBox("Show customer signature area")
        self.show_company_sig = QCheckBox("Show BuildPro signature")
        self.show_stamp = QCheckBox("Show company stamp")
        self.show_dealer = QCheckBox("Show Authorized Dealer section")
        iform.addRow("Invoice Prefix:", self.invoice_prefix)
        iform.addRow("Starting Number:", self.invoice_start)
        iform.addRow(self.show_mrp)
        iform.addRow(self.show_customer_sig)
        iform.addRow(self.show_company_sig)
        iform.addRow(self.show_stamp)
        iform.addRow(self.show_dealer)
        note = QLabel("Note: changing the prefix/start number only affects future invoices.")
        note.setStyleSheet("color: gray;")
        iform.addRow(note)
        tabs.addTab(invoice_tab, "Invoice")

        # --- GST tab ---
        gst_tab = QWidget()
        gform = QFormLayout(gst_tab)
        self.gst_rate = QDoubleSpinBox(); self.gst_rate.setMaximum(100); self.gst_rate.setSuffix(" %")
        self.cgst_rate = QDoubleSpinBox(); self.cgst_rate.setMaximum(100); self.cgst_rate.setSuffix(" %")
        self.sgst_rate = QDoubleSpinBox(); self.sgst_rate.setMaximum(100); self.sgst_rate.setSuffix(" %")
        gform.addRow("Default GST Rate:", self.gst_rate)
        gform.addRow("Default CGST:", self.cgst_rate)
        gform.addRow("Default SGST:", self.sgst_rate)
        gst_note = QLabel(
            "Changing these values only affects NEW products/invoices.\n"
            "Historical invoices always keep the GST rate that was used at the time.")
        gst_note.setStyleSheet("color: gray;")
        gform.addRow(gst_note)
        tabs.addTab(gst_tab, "GST")

        # --- Authorized Dealer tab ---
        dealer_tab = QWidget()
        dform = QFormLayout(dealer_tab)
        self.dealer_text = QTextEdit(); self.dealer_text.setMaximumHeight(80)
        dform.addRow("Authorized Dealer Text:", self.dealer_text)
        dform.addRow(QLabel("(e.g. 'Authorized Dealer of UltraTech Cement, ACC Cement')"))
        tabs.addTab(dealer_tab, "Authorized Dealer")

        # --- Signature tab ---
        sig_tab = QWidget()
        sform = QFormLayout(sig_tab)
        self.signatory_name = QLineEdit()
        self.signatory_designation = QLineEdit()
        self.signature_enabled = QCheckBox("Enable signature on invoices")
        self.signature_path_label = QLabel("No signature set")
        sig_upload_btn = QPushButton("Upload Signature (PNG/JPG)")
        sig_upload_btn.clicked.connect(self._upload_signature)
        sig_remove_btn = QPushButton("Remove Signature")
        sig_remove_btn.clicked.connect(self._remove_signature)
        sform.addRow("Signatory Name:", self.signatory_name)
        sform.addRow("Designation:", self.signatory_designation)
        sform.addRow(self.signature_enabled)
        sform.addRow("Signature Image:", self.signature_path_label)
        sig_btn_row = QHBoxLayout()
        sig_btn_row.addWidget(sig_upload_btn)
        sig_btn_row.addWidget(sig_remove_btn)
        sform.addRow(sig_btn_row)
        tabs.addTab(sig_tab, "Signature")

        # --- Stamp tab ---
        stamp_tab = QWidget()
        stform = QFormLayout(stamp_tab)
        self.stamp_enabled = QCheckBox("Enable company stamp on invoices")
        self.stamp_path_label = QLabel("No stamp set")
        stamp_upload_btn = QPushButton("Upload Stamp (PNG/JPG)")
        stamp_upload_btn.clicked.connect(self._upload_stamp)
        stamp_remove_btn = QPushButton("Remove Stamp")
        stamp_remove_btn.clicked.connect(self._remove_stamp)
        stform.addRow(self.stamp_enabled)
        stform.addRow("Stamp Image:", self.stamp_path_label)
        stamp_btn_row = QHBoxLayout()
        stamp_btn_row.addWidget(stamp_upload_btn)
        stamp_btn_row.addWidget(stamp_remove_btn)
        stform.addRow(stamp_btn_row)
        tabs.addTab(stamp_tab, "Company Stamp")

        # --- Stock tab ---
        stock_tab = QWidget()
        stkform = QFormLayout(stock_tab)
        self.allow_negative_stock = QCheckBox("Allow negative stock (not recommended)")
        self.low_stock_threshold = QSpinBox(); self.low_stock_threshold.setMaximum(1_000_000)
        stkform.addRow(self.allow_negative_stock)
        stkform.addRow("Low Stock Threshold (bags):", self.low_stock_threshold)
        tabs.addTab(stock_tab, "Stock")

        # --- Backup tab ---
        backup_tab = QWidget()
        bform = QVBoxLayout(backup_tab)
        self.backup_status_label = QLabel("")
        bform.addWidget(self.backup_status_label)
        backup_now_btn = QPushButton("Backup Now")
        backup_now_btn.clicked.connect(self._backup_now)
        bform.addWidget(backup_now_btn)
        restore_btn = QPushButton("Restore from Backup...")
        restore_btn.clicked.connect(self._restore_backup)
        bform.addWidget(restore_btn)
        bform.addStretch()
        tabs.addTab(backup_tab, "Backup")

        save_btn = QPushButton("💾 Save Settings")
        save_btn.setEnabled(self.is_admin)
        save_btn.clicked.connect(self._save)
        layout.addWidget(save_btn)

        if not self.is_admin:
            for w in [company_tab, invoice_tab, gst_tab, dealer_tab, sig_tab, stamp_tab, stock_tab]:
                w.setEnabled(False)

    def _load(self):
        with session_scope() as db:
            s = db.query(CompanySettings).first()
            self.company_name.setText(s.company_name or "")
            self.address.setPlainText(s.address or "")
            self.phone.setText(s.phone or "")
            self.gstin.setText(s.gstin or "")
            self.logo_path_label.setText(s.logo_path or "No logo set")
            self.invoice_prefix.setText(s.invoice_prefix or "INV-")
            self.invoice_start.setValue(s.invoice_start_number or 1)
            self.show_mrp.setChecked(bool(s.show_mrp))
            self.show_customer_sig.setChecked(bool(s.show_customer_signature))
            self.show_company_sig.setChecked(bool(s.show_company_signature))
            self.show_stamp.setChecked(bool(s.show_company_stamp))
            self.show_dealer.setChecked(bool(s.show_authorized_dealer))
            self.gst_rate.setValue(float(s.default_gst_rate))
            self.cgst_rate.setValue(float(s.default_cgst_rate))
            self.sgst_rate.setValue(float(s.default_sgst_rate))
            self.dealer_text.setPlainText(s.dealer_text or "")
            self.signatory_name.setText(s.signatory_name or "")
            self.signatory_designation.setText(s.signatory_designation or "")
            self.signature_enabled.setChecked(bool(s.signature_enabled))
            self.signature_path_label.setText(s.signature_path or "No signature set")
            self.stamp_enabled.setChecked(bool(s.stamp_enabled))
            self.stamp_path_label.setText(s.stamp_path or "No stamp set")
            self.allow_negative_stock.setChecked(bool(s.allow_negative_stock))
            self.low_stock_threshold.setValue(s.low_stock_threshold_bags or 100)

        last_bkp = last_backup_time()
        self.backup_status_label.setText(
            f"Last successful backup: {last_bkp.strftime('%d-%m-%Y %H:%M') if last_bkp else 'never'}"
        )

    def _upload_logo(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Logo", "", "Images (*.png *.jpg *.jpeg)")
        if path:
            dest = _copy_asset(path, "logo")
            self.logo_path_label.setText(dest)

    def _upload_signature(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Signature", "", "Images (*.png *.jpg *.jpeg)")
        if path:
            dest = _copy_asset(path, "signature")
            self.signature_path_label.setText(dest)

    def _remove_signature(self):
        self.signature_path_label.setText("No signature set")

    def _upload_stamp(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Stamp", "", "Images (*.png *.jpg *.jpeg)")
        if path:
            dest = _copy_asset(path, "stamp")
            self.stamp_path_label.setText(dest)

    def _remove_stamp(self):
        self.stamp_path_label.setText("No stamp set")

    def _save(self):
        with session_scope() as db:
            s = db.query(CompanySettings).first()
            s.company_name = self.company_name.text().strip()
            s.address = self.address.toPlainText().strip()
            s.phone = self.phone.text().strip()
            s.gstin = self.gstin.text().strip()
            logo = self.logo_path_label.text()
            s.logo_path = None if logo == "No logo set" else logo

            s.invoice_prefix = self.invoice_prefix.text().strip() or "INV-"
            s.invoice_start_number = self.invoice_start.value()
            s.show_mrp = self.show_mrp.isChecked()
            s.show_customer_signature = self.show_customer_sig.isChecked()
            s.show_company_signature = self.show_company_sig.isChecked()
            s.show_company_stamp = self.show_stamp.isChecked()
            s.show_authorized_dealer = self.show_dealer.isChecked()

            s.default_gst_rate = self.gst_rate.value()
            s.default_cgst_rate = self.cgst_rate.value()
            s.default_sgst_rate = self.sgst_rate.value()

            s.dealer_text = self.dealer_text.toPlainText().strip()

            s.signatory_name = self.signatory_name.text().strip()
            s.signatory_designation = self.signatory_designation.text().strip()
            s.signature_enabled = self.signature_enabled.isChecked()
            sig = self.signature_path_label.text()
            s.signature_path = None if sig == "No signature set" else sig

            s.stamp_enabled = self.stamp_enabled.isChecked()
            stamp = self.stamp_path_label.text()
            s.stamp_path = None if stamp == "No stamp set" else stamp

            s.allow_negative_stock = self.allow_negative_stock.isChecked()
            s.low_stock_threshold_bags = self.low_stock_threshold.value()

        QMessageBox.information(self, "Saved", "Settings saved. New invoices will use these values.")

    def _backup_now(self):
        try:
            path = create_backup()
        except Exception as e:
            QMessageBox.critical(self, "Backup failed", str(e))
            return
        QMessageBox.information(self, "Backup complete", f"Backup saved to:\n{path}")
        self._load()

    def _restore_backup(self):
        backups = list_backups()
        if not backups:
            QMessageBox.information(self, "No backups", "No backup files were found.")
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Backup File", os.path.dirname(backups[0]), "Database (*.db)")
        if not path:
            return
        reply = QMessageBox.warning(
            self, "Confirm Restore",
            "Restoring will replace the current database with the selected backup.\n"
            "The current database will first be safely archived. Continue?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            restore_backup(path)
        except Exception as e:
            QMessageBox.critical(self, "Restore failed", str(e))
            return
        QMessageBox.information(self, "Restored",
                                 "Backup restored. Please restart BuildPro for changes to take effect.")
