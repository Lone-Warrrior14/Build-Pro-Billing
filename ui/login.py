from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QLabel, QMessageBox
)
from PySide6.QtCore import Qt

from database.connection import session_scope
from database.models import User
from utils.security import verify_password


class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BuildPro - Login")
        self.setFixedSize(340, 200)
        self.authenticated_user_id = None
        self.authenticated_username = None
        self.authenticated_role = None

        layout = QVBoxLayout(self)
        title = QLabel("BuildPro Billing")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        form = QFormLayout()
        self.username_edit = QLineEdit()
        self.username_edit.setText("admin")
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        form.addRow("Username:", self.username_edit)
        form.addRow("Password:", self.password_edit)
        layout.addLayout(form)

        login_btn = QPushButton("Login")
        login_btn.clicked.connect(self.try_login)
        layout.addWidget(login_btn)

        hint = QLabel("Default admin password: admin123 (change it in Settings)")
        hint.setStyleSheet("color: gray; font-size: 10px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.password_edit.returnPressed.connect(self.try_login)

    def try_login(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        with session_scope() as db:
            user = db.query(User).filter_by(username=username, is_active=True).first()
            if user and verify_password(password, user.password_salt, user.password_hash):
                self.authenticated_user_id = user.id
                self.authenticated_username = user.username
                self.authenticated_role = user.role.value
                self.accept()
            else:
                QMessageBox.warning(self, "Login Failed", "Invalid username or password.")
