# System Architecture — ScanSocial

## Architectural Principles
ScanSocial follows **Clean Architecture** with a **Modular Monolith** pattern. Business domains remain strictly separated from delivery mechanisms (FastAPI, CLI, Tauri) and storage engines (SQLite, Alembic).

```text
┌─────────────────────────────────────────────────────────────┐
│                 DESKTOP SHELL (Tauri 2)                     │
│  - Native Windowing (Windows .msi / Ubuntu .deb)            │
│  - Python Sidecar Lifecycle Management & Supervision        │
│  - Native Secret Store Bridge (Keyring / Secret Service)    │
└──────────────────────────────┬──────────────────────────────┘
                               │
            Local Loopback HTTP / WebSocket (127.0.0.1)
            Headers: X-App-Session-Token
                               │
┌──────────────────────────────▼──────────────────────────────┐
│             REACT + TYPESCRIPT UI (Frontend)                │
│  - State Management: Zustand (Auth, Scanner, CRM, UI)       │
│  - Query Management: TanStack Query v5                      │
│  - Design System: Tailwind CSS + shadcn/ui                  │
│  - Virtualized Rendering: @tanstack/react-virtual           │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               │ JSON REST / WS
                               ▼
┌─────────────────────────────────────────────────────────────┐
│          PYTHON 3.12+ FASTAPI BACKEND (Local Sidecar)       │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ API Layer (REST Controllers & WebSocket Dispatcher)   │  │
│  └───────────────────────────┬───────────────────────────┘  │
│                              ▼                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Application Core & Event Bus                          │  │
│  │ - Scan Job Manager       - Identity Resolution        │  │
│  │ - Lead Scoring & AI      - Deduplication Engine       │  │
│  │ - Blacklist Engine       - CRM & Care Service         │  │
│  │ - Retention Worker       - Global Search (FTS5)       │  │
│  └───────┬───────────────────┬───────────────────┬───────┘  │
│          │                   │                   │          │
│          ▼                   ▼                   ▼          │
│  ┌───────────────┐   ┌───────────────┐   ┌───────────────┐  │
│  │ Facebook      │   │ Threads       │   │ Zalo          │  │
│  │ Adapter       │   │ Adapter       │   │ Connector     │  │
│  └───────┬───────┘   └───────┬───────┘   └───────┬───────┘  │
│          └───────────────────┼───────────────────┘          │
│                              ▼                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Infrastructure & Storage Layer                        │  │
│  │ - SQLAlchemy 2.0 ORM      - SQLite WAL Mode           │  │
│  │ - Alembic Migrations      - FTS5 Virtual Index        │  │
│  │ - OS Keyring Secret Vault - Online Backup Engine      │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Security & Network Isolation
1. **Loopback Binding:** The backend listens only on `127.0.0.1`. It never exposes endpoints to the local area network (LAN) by default.
2. **Session Authentication:** Every API request must include the header `X-App-Session-Token` matching the secret generated when the desktop shell starts.
3. **Secret Storage:** Sensitive tokens (cookies, Zalo tokens, AI keys) are encrypted via the host OS secure storage (`keyring` leveraging Windows Credential Manager or Linux `libsecret`).
