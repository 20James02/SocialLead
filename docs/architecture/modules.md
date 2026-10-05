# Module responsibilities

- `api/v1/scans.py` owns worker lifecycle and REST import/control. `scanner/pipeline.py` applies age, keywords, persistent indexed dedup, blacklist, scoring and comment ingestion. Deduplicator also exposes an in-memory cache for standalone algorithm use; ingestion persistence is authoritative.
- `identity/phone_normalizer.py` extracts/normalizes numbers with provenance. `identity_resolver.py` proposes confidence; explicit merge rewires CRM relationships, retains audit history and combines permissions conservatively.
- `scoring/lead_scorer.py` computes heuristic scores and needs. `ai/provider.py` implements heuristic and optional Ollama drafting. Cloud AI providers are not implemented.
- `api/v1/workspace.py`, persons/customers routers and `crm/care_service.py` implement contacts, profiles, opportunities, notes, labels, consent, conversations, tasks and export. Several original service filenames in the PRD are conceptual rather than separate files.
- `integrations/official.py` handles official Facebook Page and Threads HTTP discovery/comments with bounded paging. Zalo adapter handles official reviewed OA sends and explicitly refuses personal automatic sends. Provider webhooks are not implemented; message history is entered manually.
- `campaigns.py` applies consent, recent interaction, frequency and quiet-hour eligibility, tracks ambiguous delivery and provides operator reconciliation.
- `database/session.py` initializes/additively migrates SQLite and reconciles interrupted operations. `fts/fts_manager.py` owns FTS triggers/rebuild; backup manager snapshots SQLite online. Main lifespan coordinates maintenance and shutdown.
- `apps/desktop/src/App.tsx` owns workspace views; `api.ts` authenticates REST/live events and delegates native operations. Rust supervises the engine, source opening and CSV save.
