# Implementation status

The original PRD and architecture documents describe product intent. README and the running OpenAPI schema describe implemented behavior. This audit replaced missing desktop code and placeholder integrations with working local workflows.

| Area | Current implementation | External acceptance |
| --- | --- | --- |
| Desktop CRM | Vietnamese React UI, Tauri sidecar, contacts, customer profiles, opportunities, care, notes and labels | Clean-machine install/native dialogs |
| Discovery | JSON import, official Threads keyword search, authorized Facebook Page feeds, comments sync | Approved tokens and account permissions |
| Lead processing | Persistent canonical dedup, phone provenance, offline explainable score/needs, blacklist | Tune heuristics against representative business data |
| Zalo personal | Draft, clipboard and manual history | User performs sending |
| Zalo OA | Preview, reviewed official sends, consent/quiet hours/cap, uncertain delivery reconciliation | Real permitted OA account and recipient |
| Data | SQLite WAL, transactional FTS triggers, protected retention, CSV, safe restore | Secure storage/export handling |
| AI | Offline heuristic; optional local Ollama drafting with fallback | Install/configure Ollama if desired |
| Packaging | Windows NSIS/MSI and Ubuntu DEB/AppImage in CI, executable engine smoke test | Signing and distribution policy |

Automated tests do not prove external API entitlement, message delivery on a real account, code signing or unrestricted social-network search. Those requirements are not silently simulated.
