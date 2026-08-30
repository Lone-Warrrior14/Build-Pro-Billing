"""
BuildPro Billing Software - Main Application Entry Point (Web Mode)

Run with:  python main.py
Build exe with: pyinstaller buildpro.spec   (see README.md)
"""
from __future__ import annotations

import argparse
import sys
import threading
import time
import webbrowser

from app_web import app, init_app
from database.connection import init_engine
from database.migrations import ensure_defaults
from services.backup_service import create_backup, last_backup_time


def start_ngrok_tunnel(port: int):
    """Attempt to start an ngrok tunnel to expose local port over the internet."""
    import shutil
    import subprocess
    import urllib.request
    import json

    ngrok_path = shutil.which("ngrok")
    if not ngrok_path:
        print("Note: 'ngrok' command not found on PATH. Remote access tunnel skipped.")
        return

    try:
        subprocess.Popen(
            [ngrok_path, "http", str(port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(2.5)

        try:
            req = urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=5)
            tunnels_data = json.loads(req.read().decode('utf-8'))
            public_url = None
            for t in tunnels_data.get("tunnels", []):
                if t.get("proto") in ("https", "http"):
                    public_url = t.get("public_url")
                    if t.get("proto") == "https":
                        break
            if public_url:
                print("\n========================================================")
                print(f"  🌐 LIVE PUBLIC INTERNET TUNNEL (NGROK): {public_url}")
                print("========================================================\n")
        except Exception:
            print("\n[ngrok] Remote access tunnel active. Inspect at http://127.0.0.1:4040")
    except Exception as err:
        print(f"Warning: Could not start ngrok tunnel automatically: {err}")


def start_browser(port: int):
    """Wait briefly for Flask server startup then open default web browser."""
    time.sleep(1.2)
    url = f"http://127.0.0.1:{port}"
    print(f"\nOpening BuildPro Web App in browser: {url}")
    webbrowser.open(url)


def main():
    parser = argparse.ArgumentParser(description="BuildPro Billing Software (Web Server)")
    parser.add_argument("--port", type=int, default=5000, help="Port to run the web server on (default: 5000)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open web browser")
    parser.add_argument("--no-ngrok", action="store_true", help="Do not automatically start ngrok tunnel")
    args, _ = parser.parse_known_args()

    print("Initializing BuildPro Billing Engine...")

    # Initialize database (creates tables + defaults on first run)
    try:
        init_app()
    except Exception as e:
        print(f"Startup Error: Could not initialize database:\n{e}")
        input("Press Enter to exit...")
        sys.exit(1)

    # Automatic post-12 PM daily backup service
    try:
        from services.backup_service import start_daily_12pm_backup_service
        start_daily_12pm_backup_service()
    except Exception as e:
        print(f"Warning: Daily post-12 PM auto-backup service skipped: {e}")

    # Launch web browser thread
    if not args.no_browser:
        threading.Thread(target=start_browser, args=(args.port,), daemon=True).start()

    # Launch ngrok tunnel thread
    if not args.no_ngrok:
        threading.Thread(target=start_ngrok_tunnel, args=(args.port,), daemon=True).start()

    print("\n========================================================")
    print("      BUILDPRO BILLING WEB APPLICATION RUNNING")
    print("========================================================")
    print(f" Access locally via browser: http://127.0.0.1:{args.port}")
    print(f" Access on local network: http://localhost:{args.port}")
    print(" Press Ctrl+C in this terminal window to stop the app.")
    print("========================================================\n")

    app.run(host="0.0.0.0", port=args.port, debug=False)


if __name__ == "__main__":
    main()

