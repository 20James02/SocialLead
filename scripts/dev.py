"""Start the local engine and print the browser session token explicitly for development."""

import os
import secrets
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
token = secrets.token_urlsafe(32)
environment = {
    **os.environ,
    "SCANSOCIAL_SESSION_TOKEN": token,
    "SCANSOCIAL_DATA_DIR": str(root / "data"),
}
print("Engine: http://127.0.0.1:8765", flush=True)
print(f"Development session token (paste in the UI): {token}", flush=True)
print("Frontend: cd apps/desktop && npm run dev", flush=True)
try:
    subprocess.run(
        [sys.executable, "-m", "app.main"],
        cwd=root / "apps" / "engine",
        env=environment,
        check=True,
    )
except KeyboardInterrupt:
    pass
