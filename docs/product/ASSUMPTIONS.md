# Engineering & Product Assumptions — ScanSocial

As specified in Rule LXXIX, any unprescribed implementation details are resolved with the simplest, most maintainable, cross-platform, testable, and modular approach, documented below:

1. **Storage Engine Choice:**
   - SQLite with WAL (Write-Ahead Logging) mode and memory-mapped I/O is selected for the local desktop engine.
   - Schema and queries use SQLAlchemy 2.0 ORM and Core patterns to ensure frictionless migration to PostgreSQL for team/server editions in V2.

2. **Loopback Port Negotiation:**
   - The Python sidecar defaults to port `8765` but supports dynamic port negotiation via the `--port` flag if the default port is occupied.
   - The session token (`X-App-Session-Token`) is generated via `secrets.token_urlsafe(32)` by the desktop shell and passed securely to the backend process upon launch.

3. **Retention Defaults:**
   - Unprocessed raw scan posts expire after **24 hours** by default (configurable to 3 days, 7 days, or never).
   - Any post that is marked as Saved, associated with a Person, or converted to a Customer is marked with `is_raw = False` and is permanently protected from automated retention cleanup.

4. **Vietnamese Phone Canonical Representation:**
   - All Vietnamese mobile phone numbers are normalized to the standard international E.164 format: `+84[3|5|7|8|9]xxxxxxxx`.
   - Domestic prefixes `03x`, `05x`, `07x`, `08x`, `09x` and plain country prefixes `84x` are mapped deterministically.
   - Invalid numbers (e.g. fewer than 10 digits or illegal telco network prefixes) are rejected from automatic phone entity creation.

5. **AI Provider Fallback:**
   - If no cloud API key is provided and local Ollama is not detected, the system smoothly falls back to a deterministic rule-based Heuristic NLP engine. This guarantees that scoring, intent classification, and need extraction function with 100% reliability offline without crashing.
