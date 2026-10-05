# Implementation choices

- Single-user local SQLite with WAL and SQLAlchemy is the supported runtime. A team/server edition is not implemented.
- Tauri selects a free loopback port and generates 32 random bytes for each session token, passed through the child environment. Developer mode uses scripts/dev.py.
- Raw unprotected posts expire after the configured retention period, default 24 hours. Saved or CRM-linked posts are retained.
- Vietnamese mobile phones normalize to E.164 and retain provenance. Extracted numbers begin unverified; extraction is not evidence of ownership.
- Offline heuristics provide scoring and need extraction. Optional Ollama drafts fall back if unavailable; quality and accuracy require evaluation against business data.
- Provider access uses official permitted APIs. Facebook Page feeds are not general social search. Personal Zalo sending is manual. OA sends require review and eligibility.
- The current core delivery includes desktop CRM, JSON discovery, official adapters, consent, care, backups and installers. Real account entitlement, signing and clean-machine acceptance are external requirements documented in IMPLEMENTATION_STATUS.
