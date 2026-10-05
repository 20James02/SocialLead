# Windows Build & Release Guide — ScanSocial

## Prerequisites
- Windows 10/11 (64-bit)
- Node.js 18+ & npm 9+
- Python 3.12+ (64-bit)
- Rust 1.75+ (`rustup default stable-x86_64-pc-windows-msvc`)
- Visual Studio C++ Build Tools & WiX Toolset v3 (for MSI installers)

## Build Instructions
1. **Compile Backend Sidecar Binary:**
   ```powershell
   cd apps/engine
   python -m pip install -r requirements.txt pyinstaller
   pyinstaller --clean --noconfirm --onedir --name scansocial-engine app/main.py
   # Copy binary output to Tauri sidecar directory
   New-Item -ItemType Directory -Force ../desktop/src-tauri/bin
   Copy-Item -Recurse dist/scansocial-engine ../desktop/src-tauri/bin/scansocial-engine-x86_64-pc-windows-msvc
   ```

2. **Package Desktop Shell via Tauri:**
   ```powershell
   cd ../desktop
   npm install
   npm run tauri build
   ```

3. **Output Artifacts:**
   - Standalone Portable Executable: `apps/desktop/src-tauri/target/release/bundle/nsis/*.exe`
   - Windows Installer: `apps/desktop/src-tauri/target/release/bundle/msi/*.msi`
