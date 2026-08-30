"""
User account creation & password management utility script.
Use this file to create or reset confidential admin and sales passwords safely using bcrypt.

Run command:
    python create_user.py
"""
from __future__ import annotations

import getpass
import sys
from database.connection import init_engine, session_scope
from database.models import User, UserRole
from utils.security import hash_password


def create_or_update_user(username, password, full_name, role_str):
    with session_scope() as session:
        user = session.query(User).filter_by(username=username).first()
        salt, pw_hash = hash_password(password)
        
        role_enum = UserRole.ADMIN if role_str == "admin" else UserRole.SALES_EXECUTIVE

        if user:
            user.password_hash = pw_hash
            user.password_salt = salt
            user.full_name = full_name
            user.role = role_enum
            user.is_active = True
            print(f"[SUCCESS] Password updated for existing user '{username}' with bcrypt.")
        else:
            new_user = User(
                username=username,
                password_hash=pw_hash,
                password_salt=salt,
                full_name=full_name,
                role=role_enum,
                is_active=True
            )
            session.add(new_user)
            print(f"[SUCCESS] Created new user '{username}' ({role_str}) with bcrypt encryption.")


def main():
    init_engine()
    print("=" * 60)
    print(" BUILD PRO - CONFIDENTIAL USER ACCOUNT CREATION / PASSWORD RESET")
    print("=" * 60)

    username = input("Enter username (e.g. admin / manager): ").strip()
    if not username:
        print("Username cannot be empty.")
        return

    password = getpass.getpass("Enter confidential password: ").strip()
    if not password:
        print("Password cannot be empty.")
        return

    full_name = input("Enter Full Name (optional): ").strip() or username.title()
    role_str = input("Enter role (admin / sales) [default: admin]: ").strip().lower() or "admin"

    create_or_update_user(username, password, full_name, role_str)
    print("\nAccount setup complete! You can now log into the web system using these credentials.\n")


if __name__ == "__main__":
    main()
