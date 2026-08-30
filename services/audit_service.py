"""Append-only audit log (spec section 34)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from database.models import AuditLog, User


def log_action(db: Session, user_id: int | None, action: str, entity_type: str = "",
                entity_id: int = None, old_value: str = None, new_value: str = None):
    username = ""
    if user_id:
        u = db.get(User, user_id)
        username = u.username if u else ""
    db.add(AuditLog(
        user_id=user_id, username_snapshot=username, action=action,
        entity_type=entity_type, entity_id=entity_id,
        old_value=old_value, new_value=new_value,
    ))
