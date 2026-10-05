# Windows packages

Use Windows x64, Python >= 3.12, Node >= 22.12, Rust stable and Visual Studio C++ Build Tools with the Windows SDK. The app uses WebView2. See https://v2.tauri.app/start/prerequisites/.

From the repository root:

```powershell
python -m pip install -r apps/engine/requirements.txt pyinstaller
npm ci --prefix apps/desktop
python -m pytest apps/engine/tests -q
python scripts/build-sidecar.py
python scripts/smoke-sidecar.py
npm run tauri build --prefix apps/desktop
```

The packaging script creates the correctly named one-file sidecar from entrypoint.py. Tauri outputs NSIS setup EXE and MSI under apps/desktop/src-tauri/target/release/bundle/. The NSIS EXE is an installer, not a portable application.

Desktop Packages on GitHub Actions builds installers on each main push; download the scansocial-Windows artifact. Tagged v* releases use the release workflow. Packages are not code-signed; signing credentials are not included in this repository.

First launch starts the engine automatically and uses per-user app data. Configure permitted platform tokens in Settings. Test clean installation and native dialogs before distributing to customers.
