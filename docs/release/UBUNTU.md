# Ubuntu / Linux Build & Release Guide — ScanSocial

## Prerequisites
- Ubuntu 22.04 LTS / 24.04 LTS
- Node.js 18+ & npm 9+
- Python 3.12+
- System packages:
  ```bash
  sudo apt update
  sudo apt install -y build-essential libwebkit2gtk-4.1-dev libappindicator3-dev librsvg2-dev patchelf libsecret-1-dev
  ```
- Rust 1.75+ (`curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`)

## Build Instructions
1. **Compile Backend Sidecar:**
   ```bash
   cd apps/engine
   pip install -r requirements.txt pyinstaller
   pyinstaller --clean --noconfirm --onedir --name scansocial-engine app/main.py
   mkdir -p ../desktop/src-tauri/bin
   cp -r dist/scansocial-engine ../desktop/src-tauri/bin/scansocial-engine-x86_64-unknown-linux-gnu
   ```

2. **Package Desktop Shell via Tauri:**
   ```bash
   cd ../desktop
   npm install
   npm run tauri build
   ```

3. **Output Artifacts:**
   - Debian Package: `apps/desktop/src-tauri/target/release/bundle/deb/*.deb`
   - Linux AppImage: `apps/desktop/src-tauri/target/release/bundle/appimage/*.AppImage`
