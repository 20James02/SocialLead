# Database Entity Relationship & Design — ScanSocial

## Core Principles
1. **Person-Centric:** All CRM relationships anchor to `persons`. A Person is discovered first; they may later be promoted to a `customers` record.
2. **Provenance Preservation:** Phone numbers, locations, and social identities permanently retain discovery metadata (`source_type`, `source_url`, `captured_at`).
3. **Soft-Delete Architecture:** Critical entities (`persons`, `customers`, `social_posts`, `opportunities`, `care_tasks`) include `deleted_at TIMESTAMP NULL` for non-destructive lifecycle management.
4. **Full-Text Search Indexing:** SQLite FTS5 index `fts_search` tracks titles, content, notes, and names for sub-second global queries.

## Table Inventory
1. `persons`: Master contact entity.
2. `person_phones`: Phone numbers with provenance and verification flags.
3. `social_accounts`: Platform identities (Facebook, Threads, Zalo).
4. `customers`: Promoted customer status, scores, assignment.
5. `customer_need_profiles`: Extracted service needs, property types, urgency.
6. `opportunities`: Deals/opportunities tied to a customer.
7. `social_posts`: Ingested posts from all platforms.
8. `social_comments`: Extracted comments and secondary lead candidates.
9. `saved_posts`: Bookmarked posts with user notes.
10. `scan_jobs`: Scanner configuration, targets, and live statistics.
11. `scan_results`: Linking table between scan jobs and discovered posts.
12. `labels`: Classification tags with color codes.
13. `person_labels`: Many-to-many link between persons and labels.
14. `notes`: Timestamped internal notes for persons and customers.
15. `care_tasks`: Calendar tasks, scheduled follow-ups, and reminders.
16. `timeline_events`: Unified chronological audit trail for Customer 360.
17. `blacklist_entities`: Profiles, Pages, Groups, Phones, and Keywords blacklisted.
18. `conversations`: Messaging threads from Zalo and social sources.
19. `messages`: Individual chat messages in a conversation.
20. `campaigns`: Marketing campaigns with frequency cap and permission criteria.
21. `campaign_recipients`: Deliveries, status, and responses for campaigns.
22. `permissions`: Consent, opt-out, and do-not-contact flags.
23. `ai_analysis`: Detailed scoring breakdown and AI rationale.
24. `audit_logs`: Security and mutation audit log for critical operations.
25. `app_settings`: Key-value configuration store.
