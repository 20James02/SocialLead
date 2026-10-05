"""Ephemeral CRM backend for browser integration tests."""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "apps" / "engine"))
with tempfile.TemporaryDirectory(prefix="scansocial-e2e-") as directory:
    os.environ["SCANSOCIAL_DATA_DIR"] = directory
    os.environ["SCANSOCIAL_SESSION_TOKEN"] = "e2e-isolated-test-session-token"
    from app.main import run

    run()
