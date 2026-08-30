"""
Backup / restore (spec section 32).

SQLite backups are taken with the sqlite3 online backup API, which is
safe to run even while the app has the database open (unlike a raw
file copy, which can capture a torn/inconsistent write).
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import datetime as dt

from database.connection import get_db_path, get_app_dir


def get_backup_dir() -> str:
    backup_dir = os.path.join(get_app_dir(), "backups")
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir


def create_backup(label: str = None) -> str:
    """Returns the path of the newly created backup file. Raises on
    failure - caller (UI) is responsible for surfacing the error rather
    than silently losing the only copy of the data."""
    src_path = get_db_path()
    if not os.path.exists(src_path):
        raise FileNotFoundError("Live database not found - nothing to back up.")

    if label:
        filename = f"{label}.db" if not label.endswith(".db") else label
    else:
        date_str = dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        filename = f"backup_{date_str}.db"

    dest_path = os.path.join(get_backup_dir(), filename)

    src_conn = sqlite3.connect(src_path)
    dest_conn = sqlite3.connect(dest_path)
    try:
        with dest_conn:
            src_conn.backup(dest_conn)
    finally:
        src_conn.close()
        dest_conn.close()

    return dest_path


def check_and_trigger_daily_12pm_backup() -> str | None:
    """Checks if current time is post-12 PM and today's daily 12 PM backup is not yet taken.
    If so, creates daily_12pm_YYYY-MM-DD.db once per day."""
    now = dt.datetime.now()
    if now.hour >= 12:
        today_str = now.strftime("%Y-%m-%d")
        dest_filename = f"daily_12pm_{today_str}.db"
        dest_path = os.path.join(get_backup_dir(), dest_filename)

        if not os.path.exists(dest_path):
            try:
                created = create_backup(f"daily_12pm_{today_str}")
                print(f"✅ Auto Daily Backup: Created post-12 PM snapshot '{dest_filename}'")
                return created
            except Exception as e:
                print(f"Warning: Failed to create daily 12 PM backup: {e}")
    return None


_daily_12pm_thread_started = False


def start_daily_12pm_backup_service(check_interval_seconds: int = 60):
    """Background service that checks every 60s and triggers post-12 PM backup once per day."""
    global _daily_12pm_thread_started
    if _daily_12pm_thread_started:
        return
    _daily_12pm_thread_started = True

    import time
    import threading

    def _loop():
        while True:
            try:
                check_and_trigger_daily_12pm_backup()
            except Exception:
                pass
            time.sleep(check_interval_seconds)

    t = threading.Thread(target=_loop, daemon=True)
    t.start()


def list_backups() -> list[str]:
    backup_dir = get_backup_dir()
    files = [
        os.path.join(backup_dir, f) for f in os.listdir(backup_dir)
        if (f.startswith("backup_") or f.startswith("daily_12pm_")) and f.endswith(".db")
    ]
    files.sort(key=os.path.getmtime, reverse=True)
    return files


def last_backup_time() -> dt.datetime | None:
    backups = list_backups()
    if not backups:
        return None
    return dt.datetime.fromtimestamp(os.path.getmtime(backups[0]))


def restore_backup(backup_path: str) -> None:
    """Restores a backup over the live database. The CURRENT live
    database is first archived (never silently overwritten/deleted) so
    a mistaken restore can itself be undone."""
    if not os.path.exists(backup_path):
        raise FileNotFoundError("Backup file not found.")

    live_path = get_db_path()
    if os.path.exists(live_path):
        safety_copy = os.path.join(
            get_backup_dir(),
            f"pre_restore_{dt.datetime.now().strftime('%Y-%m-%d_%H%M%S')}.db",
        )
        shutil.copy2(live_path, safety_copy)

    shutil.copy2(backup_path, live_path)
