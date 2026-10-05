#!/usr/bin/env python3
"""
ScanSocial Cross-Platform Sidecar Packaging Utility
Compiles apps/engine into a standalone binary and places it into apps/desktop/src-tauri/bin/
with the expected platform triple naming convention for Tauri.
"""

import sys
import os
import platform
import subprocess
import shutil
from pathlib import Path


def get_target_triple():
    arch = platform.machine().lower()
    if arch in ("amd64", "x86_64"):
        target_arch = "x86_64"
    elif arch in ("arm64", "aarch64"):
        target_arch = "aarch64"
    else:
        target_arch = arch

    system = platform.system().lower()
    if system == "windows":
        return f"{target_arch}-pc-windows-msvc"
    elif system == "linux":
        return f"{target_arch}-unknown-linux-gnu"
    elif system == "darwin":
        return f"{target_arch}-apple-darwin"
    else:
        raise RuntimeError(f"Unsupported OS: {system}")


def main():
    repo_root = Path(__file__).resolve().parent.parent
    engine_dir = repo_root / "apps" / "engine"
    tauri_bin_dir = repo_root / "apps" / "desktop" / "src-tauri" / "bin"
    tauri_bin_dir.mkdir(parents=True, exist_ok=True)

    triple = get_target_triple()
    ext = ".exe" if platform.system().lower() == "windows" else ""
    target_binary_name = f"scansocial-engine-{triple}{ext}"
    target_path = tauri_bin_dir / target_binary_name

    print(f"[*] Packaging ScanSocial Engine for target triple: {triple}")
    print(f"[*] Output destination: {target_path}")

    # Build using PyInstaller
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        "--onefile",
        "--name",
        f"scansocial-engine-{triple}",
        "--paths",
        str(engine_dir),
        "--collect-submodules",
        "app",
        "--collect-submodules",
        "uvicorn",
        "--collect-submodules",
        "sqlalchemy.dialects.sqlite",
        "--collect-submodules",
        "keyring.backends",
        "--hidden-import",
        "win32ctypes.pywin32.win32cred"
        if platform.system().lower() == "windows"
        else "keyring.backends.SecretService",
        str(engine_dir / "entrypoint.py"),
    ]

    subprocess.check_call(cmd, cwd=str(engine_dir))

    dist_binary = engine_dir / "dist" / f"scansocial-engine-{triple}{ext}"
    if dist_binary.exists():
        shutil.copy2(dist_binary, target_path)
        print(f"[+] Successfully packaged and deployed sidecar to {target_path}")
    else:
        print(f"[-] Dist binary not found at {dist_binary}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
