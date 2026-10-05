# Verification plan

Run from the repository root:

```bash
python -m pip install -r apps/engine/requirements.txt
python -m pytest apps/engine/tests -q
npm ci --prefix apps/desktop
npm run build --prefix apps/desktop
cd apps/desktop
npx playwright install chromium
npm run test:e2e
```

Backend tests use disposable databases. They cover import/deduplication, scoring, phone provenance, blacklist and regex limits, CRM conversion/merge, partial opportunity updates, care tasks, retention, FTS, backup/restore, authentication, official API normalization, rate limits, OA eligibility/delivery ambiguity and Ollama fallback. Provider traffic is mocked; no real customer receives a message.

Three Chromium workflows exercise import-to-CRM-to-care, authentication/mobile layout, blacklist persistence and unavailable integration errors against a real temporary engine. Screenshots are emitted into ignored test-results/. Build runs TypeScript validation.

After packaging, run `python scripts/smoke-sidecar.py`. It starts the executable with temporary data and verifies auth, ingestion, CRM, FTS, CSV and backup/restore, then terminates its own process. Desktop Packages CI performs this check on Windows and Ubuntu before building native installers.

The benchmark tests cover selected algorithms, not a production quality score. No measured coverage or universal latency guarantee is claimed. Remaining manual acceptance: install/launch on a clean user machine, OS keyring interaction, native save/open dialogs and real Facebook/Threads/OA accounts with approved permissions. Live provider access cannot be certified by mocked tests.
