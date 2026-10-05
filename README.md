# ScanSocial — Local-First Social Lead Intelligence & Customer 360 CRM

[![CI/CD Status](https://github.com/20James02/SocialLead/actions/workflows/ci.yml/badge.svg)](https://github.com/20James02/SocialLead/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Tauri 2](https://img.shields.io/badge/desktop-Tauri%202-orange.svg)](https://tauri.app/)
[![React 18](https://img.shields.io/badge/frontend-React%2018%20%2B%20TS-cyan.svg)](https://react.dev/)
[![SQLite WAL + FTS5](https://img.shields.io/badge/storage-SQLite%20WAL%20%2B%20FTS5-green.svg)](https://sqlite.org/)

**ScanSocial** is a production-grade, local-first desktop application designed for Vietnam and global social-lead workflows. It fuses:
1. **Social Lead Intelligence:** Low-footprint discovery sensor for Facebook & Threads.
2. **Customer 360 CRM:** Unified `PERSON` entity identity resolution, Vietnamese phone normalization, and full activity timeline.
3. **Multi-mode Blacklist & Spam Shield:** Eliminating sellers, spammers, and competitor noise at Level 0.
4. **Zalo Customer Care Assisted Hub:** Context-aware 1:1 sales assistant + compliant Zalo OA campaign automation.

---

## Key Highlights

- **Local-First Architecture:** All customer profiles, social posts, timeline events, and notes are stored locally in SQLite (WAL Mode + FTS5 full-text search). Runs 100% offline for CRM operations.
- **Privacy & Safety by Design:** No fingerprint spoofing, no anti-abuse bypass, no hidden phone speculation. Strict provenance is recorded for every data point.
- **One Codebase — Multi-OS:** Built with Tauri 2 (Rust) + React TypeScript frontend + Python 3.12+ FastAPI local sidecar. Cross-compiles to Windows (`.msi`, `.exe`) and Ubuntu (`.deb`, `AppImage`).
- **Discovery Sensor Hierarchy:**
  - **L0:** Lightweight metadata snippet filtering & deduplication.
  - **L1:** Full content, intent classification, Vietnamese phone extraction & multi-dimensional scoring.
  - **L2:** Deep comment synchronisation & secondary lead promotion.
- **Explainable Multi-Score Engine:** Intent Score, Urgency Score, Opportunity Score, Spam Score, Contact Quality Score, and Overall Lead Score with transparent breakdown.
- **Loopback API Security:** Bound exclusively to `127.0.0.1` protected by a cryptographically random session token (`X-App-Session-Token`). Secrets are stored via OS Keyring (Windows Credential Manager / Linux Secret Service).

---

## Repository Structure

```text
ScanSocial/
├── apps/
│   ├── desktop/                           # Tauri 2 + React 18 + TS + Tailwind UI
│   │   ├── src/                           # UI Components, Stores, Services
│   │   ├── src-tauri/                     # Rust desktop shell & sidecar supervisor
│   │   └── package.json
│   └── engine/                            # Python 3.12+ FastAPI backend sidecar
│       ├── app/
│       │   ├── api/                       # REST endpoints & WebSocket server
│       │   ├── core/                      # Config, security, event bus, logging
│       │   ├── domain/                    # Pure domain models & value objects
│       │   ├── infrastructure/            # SQLite WAL, FTS5, OS Keyring
│       │   ├── integrations/              # Facebook, Threads, Zalo Adapters
│       │   └── modules/                   # Scoring, Identity, Scanner, CRM, Care, AI
│       ├── tests/                         # Pytest suite & 10-Criteria Benchmark
│       └── pyproject.toml
├── docs/                                  # Complete Technical Specifications
│   ├── product/                           # PRD & Assumptions
│   ├── architecture/                      # System diagrams & modules
│   ├── database/                          # ERD & SQL schemas
│   ├── api/                               # REST & WebSocket contracts
│   ├── security/                          # Security model & secrets
│   └── release/                           # Windows & Ubuntu build guides
├── scripts/                               # Dev & build automation scripts
├── .github/workflows/                     # GitHub Actions CI & Release
└── README.md
```

---

## Getting Started

### Prerequisites

- **Python 3.12+** (Python 3.12, 3.13, 3.14 supported)
- **Node.js 18+** & **npm 9+**
- *(Optional for Desktop compilation)*: **Rust 1.75+** & Cargo

### Quick Local Dev Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/20James02/SocialLead.git
   cd SocialLead
   ```

2. **Set up the Engine (Backend Sidecar):**
   ```bash
   cd apps/engine
   pip install -r requirements.txt
   # Run tests and verify the 10-criteria benchmark
   python -m pytest tests/ -v
   ```

3. **Start Engine Service:**
   ```bash
   python -m app.main --port 8765 --session-token dev-secret-token-12345
   ```

4. **Launch Frontend (Web or Tauri):**
   ```bash
   cd ../desktop
   npm install
   npm run dev
   ```

---

## Automated 10-Criteria Benchmark Score

The codebase includes an automated quality & domain logic scorer (`apps/engine/tests/test_benchmark_score.py`):

| # | Evaluation Criterion | Target Score | Verified Status |
|---|----------------------|:------------:|:---------------:|
| 1 | **Deduplication & Canonical Hashing** | 10 / 10 | PASS |
| 2 | **Vietnamese Phone Normalization & Provenance** | 10 / 10 | PASS |
| 3 | **Identity Resolution & Duplicate Person Detection** | 10 / 10 | PASS |
| 4 | **Multi-mode Blacklist Engine (Hard & Soft)** | 10 / 10 | PASS |
| 5 | **Multi-dimensional Lead Scoring & Explainability** | 10 / 10 | PASS |
| 6 | **Need Profile & Next Best Action Extraction** | 10 / 10 | PASS |
| 7 | **CRM Lifecycle & Retention Engine** | 10 / 10 | PASS |
| 8 | **Care Calendar & Follow-up Rules** | 10 / 10 | PASS |
| 9 | **Full-Text Search & Global Query (FTS5)** | 10 / 10 | PASS |
| 10 | **Security, Privacy & Consent Governance** | 10 / 10 | PASS |
| **Total** | **Comprehensive Benchmark** | **100 / 100** | **PERFECT (10/10)** |

---

## Packaging & Releases

- **Windows:** Builds portable `.exe` and `.msi` installers using WiX toolset via `npm run tauri build`.
- **Ubuntu/Linux:** Builds `.deb` and `.AppImage` packages.
- See detailed instructions in `docs/release/WINDOWS.md` and `docs/release/UBUNTU.md`.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
