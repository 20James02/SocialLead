# Security and privacy

The engine binds only to 127.0.0.1. REST requires X-App-Session-Token; WebSocket requires the same session token. Tauri creates a random 256-bit token per launch and passes it through the child environment. Production access logs redact WebSocket tokens. CORS permits only configured local desktop/development origins.

Platform tokens are stored using OS keyring, scoped to the data directory. A missing/unavailable keyring fails explicitly; environment variables are supported. There is no local encrypted-vault fallback with a key stored beside the database.

SQLite contains customer information in plaintext. Backups and CSV exports contain the same personal data. Protect the user account, disk and exported files. Session authentication is a local boundary, not protection against another process running as the same user.

Extracted phones retain source, capture time and verification status. Extraction does not establish ownership. Unverified phones cannot authorize automatic identity merging. Merge is an explicit operation with audit history and conservative consent handling.

OA sends require consent, valid recipient identity, recent incoming interaction, frequency limits and Vietnam quiet hours. Ambiguous delivery is UNKNOWN and blocks automatic resend until manual reconciliation. Reconciliation records an operator note; it does not query provider delivery status. Personal Zalo messaging remains manual.

Restore validates SQLite integrity/schema/foreign keys, creates a safety backup, serializes database operations and rebuilds FTS. Interrupted scans become FAILED; uncertain in-flight sends become UNKNOWN after restart or restore. HTTP source links are validated before opening. CSV cells escape spreadsheet formula prefixes. Regex blacklist evaluation has a time limit.
