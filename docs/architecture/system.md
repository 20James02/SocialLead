# System architecture

React/TypeScript renders the Vietnamese workspace using component state, a small authenticated API client and application CSS. WebSocket events invalidate views; REST reloads authoritative data. The current UI does not depend on Zustand, TanStack Query, Tailwind or shadcn.

Tauri 2 owns the native window, obtains a free loopback port, generates a session token, starts the packaged Python engine and terminates it on exit. Native commands expose the connection, validated HTTP source opening and a CSV save dialog. Platform secrets are handled by the Python OS keyring adapter.

FastAPI exposes authenticated REST and WebSocket APIs. Scanner workers call official provider adapters, normalize records and ingest bounded chunks. An operation lock serializes API/database mutation and maintenance against restore. Domain modules implement deduplication, blacklist, scoring, identity, consent and care rules.

SQLAlchemy models define SQLite tables with WAL and foreign keys. init_db performs additive migrations for supported older databases; no Alembic revision workflow is currently configured. Transactional SQLite triggers maintain FTS5 documents. Startup rebuilds the index and reconciles interrupted operations. Maintenance removes eligible raw posts and emits due-care events.

JSON ingestion and CRM operate offline. Facebook, Threads and Zalo OA use explicit HTTP adapters with credential/permission failures. Personal Zalo uses manual messages. Ollama is optional for drafting; deterministic heuristic scoring remains local.

The engine is packaged with PyInstaller, then embedded as a Tauri sidecar. CI builds NSIS/MSI on Windows and DEB/AppImage on Ubuntu and smoke-tests the packaged engine first. See README, SECURITY and IMPLEMENTATION_STATUS for current limitations.
