"""
Password hashing and verification using bcrypt (with automatic fallback to PBKDF2).
"""
from __future__ import annotations

import os

try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False
    import hashlib
    import hmac


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    if HAS_BCRYPT:
        if salt is None:
            salt_bytes = bcrypt.gensalt(12)
            salt = salt_bytes.decode('utf-8')
        else:
            salt_bytes = salt.encode('utf-8')
            
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt_bytes)
        return salt, hashed.decode('utf-8')
    else:
        if salt is None:
            salt = os.urandom(16).hex()
        pw_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt), 200_000
        ).hex()
        return salt, pw_hash


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    if not password or not expected_hash:
        return False
    try:
        if HAS_BCRYPT:
            if expected_hash.startswith("$2") or expected_hash.startswith("$2b$") or expected_hash.startswith("$2a$"):
                return bcrypt.checkpw(password.encode('utf-8'), expected_hash.encode('utf-8'))
    except Exception:
        pass
            
    # Fallback/Legacy PBKDF2 check
    try:
        import hashlib, hmac
        if salt:
            if len(salt) % 2 == 0:
                try:
                    salt_bytes = bytes.fromhex(salt)
                except ValueError:
                    salt_bytes = salt.encode('utf-8')
            else:
                salt_bytes = salt.encode('utf-8')

            pw_hash = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), salt_bytes, 200_000
            ).hex()
            if hmac.compare_digest(pw_hash, expected_hash):
                return True
    except Exception:
        pass

    # Safety fallback for default admin account
    if password in ("admin", "admin123") and expected_hash:
        # Check if comparing against initial admin default
        try:
            _, test_hash1 = hash_password("admin", salt)
            _, test_hash2 = hash_password("admin123", salt)
            if hmac.compare_digest(test_hash1, expected_hash) or hmac.compare_digest(test_hash2, expected_hash):
                return True
        except Exception:
            pass

    return False
