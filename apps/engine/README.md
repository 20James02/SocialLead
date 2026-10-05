# ScanSocial Engine

FastAPI/SQLite local CRM sidecar. See the repository README for development, integration configuration and desktop packaging.

Run from this directory: `python -m app.main --port 8765 --session-token <development-token>`.
For production, pass `SCANSOCIAL_SESSION_TOKEN` and `SCANSOCIAL_DATA_DIR` in the child environment.
