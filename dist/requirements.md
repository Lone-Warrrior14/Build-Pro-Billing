# BuildPro Billing Software - System Requirements & Dependencies

This directory contains the standalone executable distributions for **BuildPro Billing System**. Below are the recommended and optional software prerequisites and installation links for running the application on target Windows machines.

---

## 📋 Recommended Runtime Dependencies

### 1. Microsoft Edge WebView2 Runtime *(Required for `BuildProGUI.exe`)*
`BuildProGUI.exe` uses Microsoft WebView2 to render the native desktop interface without opening external browser windows. WebView2 comes pre-installed on Windows 11 and recent Windows 10 updates. If missing on older machines:
- 🌐 **Official Page**: [Microsoft Edge WebView2 Developer Page](https://developer.microsoft.com/en-us/microsoft-edge/webview2/)
- ⬇️ **Direct Installer Download**: [Evergreen Standalone Bootstrapper (x64)](https://go.microsoft.com/fwlink/p/?LinkId=2124703)

---

### 2. Visual C++ Redistributable 2015–2022 *(Recommended)*
Standard Windows system runtime required by Python frozen executables:
- 🌐 **Official Page**: [Microsoft Visual C++ Supported Downloads](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist-downloads)
- ⬇️ **Direct Download (x64)**: [vc_redist.x64.exe](https://aka.ms/vs/17/release/vc_redist.x64.exe)

---

## 🌐 Remote Access & Public Tunneling Tools

BuildPro includes built-in background threads to expose your billing system securely over the internet for remote field access.

### 1. ngrok *(Primary Remote Access Tunnel)*
Allows generating secure temporary HTTPS links for remote order creation and mobile access.
- 🌐 **Official Website**: [https://ngrok.com/](https://ngrok.com/)
- ⬇️ **Download ngrok for Windows**: [https://ngrok.com/download](https://ngrok.com/download)
- 💡 *Note*: Place `ngrok.exe` in your system `PATH` or alongside `BuildPro.exe` to enable automated tunneling on launch.

---

### 2. Cloudflare Tunnel / `cloudflared` *(Backup Unlimited Remote Access)*
Provides **100% free, unlimited HTTPS remote access** without session bandwidth caps.
- 🌐 **Documentation**: [Cloudflare Tunnel Overview](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
- ⬇️ **Direct Download `cloudflared.exe` (x64)**: [cloudflared-windows-amd64.exe](https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe)

---

## 🚀 How to Launch BuildPro

| File | Type | Mode | Best Used For |
| :--- | :--- | :--- | :--- |
| **`BuildProGUI.exe`** | Standalone Native GUI App | Desktop Window | Main Shop Counter / Dedicated Billing Terminal |
| **`BuildPro.exe`** | Web Server + Browser Launcher | Browser Mode | Multi-tab workflows / Network sharing |

---

## 🔒 Data & Database Backups
All local transaction data, customer ledgers, and auto-backups are safely stored in:
- `data/buildpro.db` *(Live Database)*
- `backups/` *(Real-time mirrors and daily post-12 PM snapshots)*
