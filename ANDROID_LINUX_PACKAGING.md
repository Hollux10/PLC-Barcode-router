# Android APK Packaging Guide for PLC Barcode Router
# Using Kivy Buildozer or BeeWare Briefcase

This document explains how to package the PLC Barcode Router application into a native **Android APK file (`.apk`)**.

---

## Method 1: Using Kivy / Buildozer (Recommended for Python APKs)

Buildozer packages the Python runtime, FastAPI app, dependencies, and a WebView foreground service into an Android APK.

> **Note:** Buildozer requires a Linux environment (or Ubuntu inside WSL on Windows).

### Step 1: Install Buildozer dependencies (Linux/WSL)
```bash
sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libssl-dev libffi-dev libsqlite3-dev
pip install --upgrade buildozer
```

### Step 2: Initialize & Configure Buildozer
In your project directory:
```bash
buildozer init
```

Update the generated `buildozer.spec` file:
```ini
[app]
title = PLC Barcode Router
package.name = plcrouter
package.domain = com.company.plcrouter
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,html,js,css,db,txt,spec,json
requirements = python3,fastapi,uvicorn,jinja2,pydantic,python-multipart,sqlite3

# Target Android API
android.api = 33
android.minapi = 21

# Permissions needed for TCP listener and local storage
android.permissions = INTERNET, ACCESS_NETWORK_STATE, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, FOREGROUND_SERVICE

# Keep app running in background service
# android.services = plcservice:service.py
```

### Step 3: Build the APK
Run:
```bash
buildozer -v android debug
```
The resulting `.apk` will be saved in `bin/plcrouter-0.1-debug.apk`.

---

## Method 2: Termux Shortcut (Run natively on Android device)

If you don't need a formal APK installation and want to run it on an Android scanner/device directly:

1. Install **Termux** app on Android from F-Droid.
2. Open Termux and run:
   ```bash
   pkg update && pkg install -y python sqlite
   pip install fastapi uvicorn jinja2 pydantic python-multipart
   ```
3. Copy the project folder to the device and run:
   ```bash
   python main.py
   ```
4. Access the web UI in Chrome or any browser at `http://localhost:5000`.
