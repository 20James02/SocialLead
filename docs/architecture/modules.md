# Module Boundaries & Responsibilities — ScanSocial

## 1. Scanner Subsystem (`app.modules.scanner`)
- **`job_manager.py`:** Controls job state machine (`PENDING`, `RUNNING`, `PAUSED`, `STOPPED`, `COMPLETED`, `FAILED`). Dispatches discovery tasks to background workers.
- **`deduplicator.py`:** Computes canonical hashes (`platform + author_id + normalized_text + timestamp`) and maintains an in-memory Bloom filter/LRU cache for instant L0 drop.
- **`blacklist.py`:** Implements Hard Blacklist (immediate discard) and Soft Blacklist (score penalty of -80 points) across Profiles, Pages, Groups, Phones, and Keywords.
- **`retention.py`:** Runs periodically to delete raw scan records older than the configured threshold (default: 24h), while guaranteeing that `Saved Posts`, `Persons`, and `Customers` remain preserved indefinitely.

## 2. Identity & Normalization Subsystem (`app.modules.identity`)
- **`phone_normalizer.py`:** Extracts Vietnamese phone numbers from raw text using regex, strips formatting characters, and formats to E.164 (`+84...`). Retains provenance metadata.
- **`identity_resolver.py`:** Evaluates person similarity based on verified phone numbers and platform external IDs. Suggests merge candidates with confidence percentages without ever auto-merging solely on common names.

## 3. Lead Scoring & AI Subsystem (`app.modules.scoring`, `app.modules.ai`)
- **Multi-Score Calculator:**
  - Intent Score (0–100)
  - Urgency Score (0–100)
  - Opportunity Score (0–100)
  - Spam Score (0–100)
  - Contact Quality Score (0–100)
  - Overall Lead Score (0–100)
- **`explainability.py`:** Generates human-readable `score_breakdown` arrays explaining every positive and negative factor contributing to the score.
- **`AIProvider` Abstraction:** Dynamic dispatch to Cloud AI (Gemini, Claude, OpenAI), Local Ollama, or deterministic Rule-Based Heuristic engine.

## 4. CRM & Customer 360 Subsystem (`app.modules.crm`)
- **`person_service.py`:** Manages Person records, social account links, and phone provenance.
- **`customer_service.py`:** Promotes Person to Customer, maintains `Need Profile` and triggers timeline audit events.
- **`opportunity_service.py`:** Tracks multiple opportunities per customer across sales stages (`NEW` to `WON`/`LOST`).
- **`care_service.py`:** Manages Care Calendar tasks, due date alerts, and follow-up proposal rules.

## 5. Integrations (`app.integrations`)
- **`SocialSourceAdapter` Interface:** Common interface with `search()`, `fetch_post()`, `fetch_comments()`, and `normalize()`.
- **`FacebookAdapter`:** Handles Facebook discovery queries with rate-conscious throttling.
- **`ThreadsAdapter`:** Implements Threads query parsing into the common `SocialPost` model.
- **`ZaloAdapter`:** Bridges Zalo Personal manual assistance and Zalo Official Account automated webhooks.
