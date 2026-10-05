# Ubuntu packages

The CI target is Ubuntu 22.04 x64. Install Python >= 3.12, Node >= 22.12, Rust stable and system libraries: libwebkit2gtk-4.1-dev, build-essential, libssl-dev, libayatana-appindicator3-dev, librsvg2-dev, patchelf and libsecret-1-dev.

```bash
python -m pip install -r apps/engine/requirements.txt pyinstaller
npm ci --prefix apps/desktop
python scripts/build-sidecar.py
python scripts/smoke-sidecar.py
npm run tauri build --prefix apps/desktop
```

DEB and AppImage output lives under apps/desktop/src-tauri/target/release/bundle/. Download scansocial-Linux from Desktop Packages Actions artifacts. A working Secret Service session is required for keyring storage; environment tokens can be used if unavailable. Clean-machine installation remains a manual acceptance check.
