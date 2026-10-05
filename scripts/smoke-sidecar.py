"""Exercise a packaged engine against disposable data, never the real CRM."""

import argparse
import os
import secrets
import signal
import socket
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    candidates = list((root / "apps/desktop/src-tauri/bin").glob("scansocial-engine-*"))
    binary = args.binary or (candidates[0] if len(candidates) == 1 else None)
    if binary is None or not binary.is_file():
        raise SystemExit("Build a single platform sidecar or supply --binary")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix="scansocial-package-smoke-") as directory:
        token = secrets.token_urlsafe(32)
        environment = {
            **os.environ,
            "SCANSOCIAL_DATA_DIR": directory,
            "SCANSOCIAL_SESSION_TOKEN": token,
            "PYTHONIOENCODING": "utf-8",
        }
        kwargs = (
            {"creationflags": subprocess.CREATE_NO_WINDOW}
            if os.name == "nt"
            else {"start_new_session": True}
        )
        process = subprocess.Popen(
            [str(binary.resolve()), "--port", str(port)],
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            **kwargs,
        )
        try:
            with httpx.Client(
                base_url=f"http://127.0.0.1:{port}",
                headers={"X-App-Session-Token": token},
                timeout=5,
            ) as client:
                for _ in range(150):
                    if process.poll() is not None:
                        raise RuntimeError(
                            f"Packaged engine exited: {process.communicate()[0].decode(errors='replace')}"
                        )
                    try:
                        if client.get("/health").status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(0.2)
                else:
                    raise RuntimeError("Packaged engine did not become ready")
                assert (
                    httpx.get(f"http://127.0.0.1:{port}/api/v1/posts").status_code
                    == 401
                )
                result = client.post(
                    "/api/v1/scans/import",
                    json={
                        "platform": "FACEBOOK",
                        "posts": [
                            {
                                "platform": "FACEBOOK",
                                "external_id": "package-smoke",
                                "url": "https://www.facebook.com/example",
                                "author_name": "Package Smoke",
                                "content": "Cần lắp wifi và camera gấp hôm nay. 0989626638",
                                "posted_at": datetime.now(timezone.utc).isoformat(),
                            }
                        ],
                    },
                )
                assert result.status_code == 201, result.text
                post = client.get("/api/v1/posts").json()[0]
                person = client.post(f"/api/v1/posts/{post['id']}/promote")
                assert person.status_code == 200, person.text
                pid = person.json()["person_id"]
                customer = client.post(
                    f"/api/v1/persons/{pid}/convert-customer",
                    json={"need_type": "WIFI"},
                )
                assert customer.status_code == 200, customer.text
                assert client.get("/api/v1/search", params={"q": "0989626638"}).json()
                backup = client.post("/api/v1/backup/create")
                assert backup.status_code == 200, backup.text
                assert (
                    client.post(
                        "/api/v1/backup/restore",
                        json={"filename": backup.json()["backup"]["filename"]},
                    ).status_code
                    == 200
                )
                assert client.get("/api/v1/export/customers").status_code == 200
            print(
                "Packaged engine smoke: PASS (auth, import, CRM, FTS, backup/restore, CSV)"
            )
        finally:
            if process.poll() is None:
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        capture_output=True,
                    )
                else:
                    os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.communicate(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate()


if __name__ == "__main__":
    main()
