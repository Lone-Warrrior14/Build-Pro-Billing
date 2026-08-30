"""
BuildPro Billing Software - Native Desktop GUI Entry Point

Launches the BuildPro application inside a dedicated, native Windows Desktop window.
"""
from __future__ import annotations

import os
import sys
import threading
import time
import webview

from app_web import app, init_app
from database.connection import get_app_dir
from services.backup_service import create_backup, last_backup_time
from main import start_ngrok_tunnel


def run_flask_server(port: int = 5000):
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


def main():
    # 1. Initialize database & default users/settings
    try:
        init_app()
    except Exception as e:
        print(f"Database Initialization Error: {e}")

    # 2. Daily post-12 PM auto-backup service
    try:
        from services.backup_service import start_daily_12pm_backup_service
        start_daily_12pm_backup_service()
    except Exception:
        pass

    port = 5000

    # 3. Start Flask backend server in background thread
    server_thread = threading.Thread(target=run_flask_server, args=(port,), daemon=True)
    server_thread.start()

    # 4. Start ngrok tunnel in background thread
    threading.Thread(target=start_ngrok_tunnel, args=(port,), daemon=True).start()

    # Allow Flask server 0.8 seconds to open socket
    time.sleep(0.8)

    # 5. Launch native Windows desktop GUI application window
    url = f"http://127.0.0.1:{port}"
    webview.create_window(
        title="BuildPro Billing System",
        url=url,
        width=1300,
        height=850,
        min_size=(1024, 680),
        resizable=True,
        confirm_close=True,
    )

    webview.start(private_mode=False)


if __name__ == "__main__":
    main()
