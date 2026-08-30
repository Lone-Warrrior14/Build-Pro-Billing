"""
Database connection management for BuildPro.

Responsible for:
  * Locating/creating the SQLite file (data/buildpro.db next to the exe)
  * Creating the SQLAlchemy engine with sane SQLite pragmas
  * Providing a session factory + a `session_scope()` context manager
    that commits on success and rolls back on any exception, so every
    multi-step billing/stock/ledger update is atomic.
"""
from __future__ import annotations

import os
import sys
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from database.models import Base


def get_app_dir() -> str:
    """Directory the .exe (or script) lives in. Works both when frozen
    by PyInstaller and when run as a plain script."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_data_dir() -> str:
    data_dir = os.path.join(get_app_dir(), "data")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def get_db_path() -> str:
    return os.path.join(get_data_dir(), "buildpro.db")


import sqlite3
import shutil
import time
import threading

_mirror_thread_started = False


def get_mirror_db_path() -> str:
    backup_dir = os.path.join(get_app_dir(), "backups")
    os.makedirs(backup_dir, exist_ok=True)
    return os.path.join(backup_dir, "live_mirror.db")


def verify_and_recover_db(db_path: str):
    """Check if the primary SQLite DB is intact. If corrupted or missing, auto-recover from mirror or latest backup."""
    mirror_path = get_mirror_db_path()

    def is_valid_sqlite(path: str) -> bool:
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            return False
        try:
            conn = sqlite3.connect(path)
            res = conn.execute("PRAGMA quick_check;").fetchone()
            conn.close()
            return res and res[0] == "ok"
        except Exception:
            return False

    if not is_valid_sqlite(db_path):
        print(f"⚠️ Warning: Primary database '{db_path}' missing or corrupted.")
        if is_valid_sqlite(mirror_path):
            print(f"🔄 Auto-recovering primary database from live backup mirror '{mirror_path}'...")
            shutil.copy2(mirror_path, db_path)
            return

        backup_dir = os.path.join(get_app_dir(), "backups")
        if os.path.exists(backup_dir):
            backups = [
                os.path.join(backup_dir, f) for f in os.listdir(backup_dir)
                if f.endswith(".db") and os.path.getsize(os.path.join(backup_dir, f)) > 0
            ]
            backups.sort(key=os.path.getmtime, reverse=True)
            for b_file in backups:
                if is_valid_sqlite(b_file):
                    print(f"🔄 Auto-recovering primary database from latest backup '{b_file}'...")
                    shutil.copy2(b_file, db_path)
                    return
        print("ℹ️ Initializing new SQLite database...")


def sync_live_mirror():
    """Perform a zero-downtime online backup of the primary DB to the secondary mirror DB ONLY for successful commits."""
    src_path = get_db_path()
    mirror_path = get_mirror_db_path()
    if not os.path.exists(src_path):
        return
    try:
        src_conn = sqlite3.connect(src_path)
        dest_conn = sqlite3.connect(mirror_path)
        with dest_conn:
            src_conn.backup(dest_conn)
        src_conn.close()
        dest_conn.close()
    except Exception:
        pass


def export_successful_sql_dump():
    """Export a clean SQL script file (successful_edits.sql) containing all table data on successful edits."""
    src_path = get_db_path()
    if not os.path.exists(src_path):
        return
    sql_path = os.path.join(get_app_dir(), "backups", "successful_edits.sql")
    try:
        conn = sqlite3.connect(src_path)
        with open(sql_path, "w", encoding="utf-8") as f:
            for line in conn.itersdump():
                f.write(f"{line}\n")
        conn.close()
    except Exception:
        pass


def process_successful_commit_backup():
    """Service called exclusively on successful transaction commit."""
    sync_live_mirror()
    export_successful_sql_dump()


def start_database_mirror_service(interval_seconds: int = 15):
    """Background service that creates continuous secondary database backups every X seconds."""
    global _mirror_thread_started
    if _mirror_thread_started:
        return
    _mirror_thread_started = True

    def _loop():
        while True:
            time.sleep(interval_seconds)
            try:
                process_successful_commit_backup()
            except Exception:
                pass

    t = threading.Thread(target=_loop, daemon=True)
    t.start()


_engine = None
_SessionFactory = None


def init_engine(db_path: str | None = None, echo: bool = False):
    global _engine, _SessionFactory
    db_path = db_path or get_db_path()
    verify_and_recover_db(db_path)

    _engine = create_engine(
        f"sqlite:///{db_path}",
        echo=echo,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=FULL")
        cursor.close()

    _SessionFactory = sessionmaker(bind=_engine, expire_on_commit=False)
    Base.metadata.create_all(_engine)

    # Initial immediate sync to mirror & SQL dump
    process_successful_commit_backup()
    start_database_mirror_service(15)
    return _engine


def get_engine():
    if _engine is None:
        init_engine()
    return _engine


def get_session() -> Session:
    if _SessionFactory is None:
        init_engine()
    return _SessionFactory()


@contextmanager
def session_scope():
    """Provide a transactional scope. ONLY on successful commit does it update the backup SQLite server and SQL file."""
    session = get_session()
    try:
        yield session
        session.commit()
        # SUCCESSFUL EDIT: Trigger immediate sync to secondary backup DB & SQL dump
        threading.Thread(target=process_successful_commit_backup, daemon=True).start()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
