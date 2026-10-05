# Product Requirements Document (PRD) — ScanSocial

## 1. Product Summary
ScanSocial is a production-grade, local-first desktop application designed to discover, qualify, and manage sales leads from social networks (Facebook, Threads) and streamline 1:1 customer care via Zalo.

## 2. Core Value Proposition
- **High Signal-to-Noise:** Filters out spammers, sellers, and competitors at discovery time (L0/L1) to surface genuine buyer demand.
- **Unified Identity (Person-Centric CRM):** Consolidates multiple social accounts, verified phone numbers, and engagement history into a single cohesive profile.
- **Offline & Local First:** Complete CRM functionality operates with zero cloud dependency; data is stored securely on the local machine in SQLite WAL mode.
- **Responsible Automation:** Separates assisted 1:1 manual messaging from compliant official API campaigns with strict frequency caps and consent policies.

## 3. Detailed Functional Modules
1. **Facebook & Threads Discovery Scanner:**
   - Multi-keyword querying.
   - Age thresholds (e.g. `<= 6 hours`).
   - Source filtering (Groups, Pages, Public Posts).
   - Real-time progress updates via WebSocket.
2. **Multi-tier Pipeline (L0 / L1 / L2):**
   - **L0:** Lightweight snippet deduplication and blacklist rejection.
   - **L1:** Full content parsing, phone extraction, intent and urgency scoring.
   - **L2:** Deep comment synchronisation and secondary buyer-lead promotion.
3. **Blacklist Engine:**
   - Entities: Profiles, Pages, Groups, Phones, Domains, Content Regex.
   - Modes: Hard (instant drop) and Soft (score penalty).
   - Suggested spammer detection based on repetition thresholds.
4. **Customer 360 CRM & Opportunities:**
   - Person vs Customer lifecycle.
   - Need Profiles (WiFi, Camera, TV, Combo, Property type, Urgency, Budget).
   - Opportunity pipeline (`NEW`, `QUALIFIED`, `CONTACTED`, `INTERESTED`, `QUOTED`, `APPOINTMENT`, `WON`, `LOST`).
   - Comprehensive Activity Timeline (`TIMELINE_EVENTS`).
5. **Care Calendar & Follow-up Rules:**
   - Care tasks with due dates, priorities, and reminders.
   - Automated rule proposal (e.g. quote given with no reply after 48 hours -> schedule follow-up).
6. **Zalo Customer Care Integration:**
   - Conversation-to-Customer mapping.
   - CRM sidebar showing Need Profile, Notes, and Next Best Action.
   - In-chat status labeling with bidirectional synchronization.
7. **Global Full-Text Search (FTS5):**
   - Sub-second retrieval across phone numbers (all formats), names, URLs, post texts, notes, and labels.

## 4. Privacy, Safety & Ethical Boundaries
- Never bypass platform rate limits or CAPTCHAs.
- Never spoof browser fingerprints or rotate anti-abuse proxies.
- Only ingest public or legally accessible data.
- Strict phone provenance tracking (`source_type`, `source_url`, `captured_at`, `is_verified`).
- No bulk spamming on personal messaging accounts.
