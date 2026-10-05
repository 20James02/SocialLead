# Quality Assurance & Test Plan — ScanSocial

## 1. Test Philosophy
Every core domain rule must be accompanied by automated unit tests with minimum **80% coverage** on critical domain logic.

## 2. Automated 10-Criteria Benchmark Matrix
The test suite features an integrated benchmark evaluator (`apps/engine/tests/test_benchmark_score.py`) scoring the application across 10 vital operational pillars (10 points each, maximum 100 points):

1. **Deduplication & Canonical Hashing:** Detection of identical post IDs and fuzzy content hash matches (`platform + author_id + normalized_text + timestamp`).
2. **Vietnamese Phone Normalization & Provenance:** Conversion of all variations (`0989...`, `+84989...`, `84989...`, `03...`, `07...`, `08...`, `05...`) to canonical E.164, stripping delimiters, rejecting invalid numbers.
3. **Identity Resolution & Duplicate Person Detection:** Name similarity, phone match, preventing wrongful auto-merge, full data migration on merge.
4. **Multi-mode Blacklist Engine:** Hard blacklist (instant discard) and Soft blacklist (-80 point penalty) across profiles, pages, groups, phones, and keywords.
5. **Multi-dimensional Lead Scoring & Explainability:** Computation of Intent, Urgency, Opportunity, Spam, Contact Quality, Overall Lead Score with transparent breakdown explanations.
6. **Need Profile & Next Best Action Extraction:** Accurate taxonomy extraction (WiFi, Camera, TV, Combo, Property type, Urgency, Next Best Action).
7. **CRM Lifecycle & Retention Engine:** Person to Customer transition, Opportunity stage movements, automated 24h retention cleanup for raw scans while permanently shielding Saved Posts and Customers.
8. **Care Calendar & Follow-up Rules:** Care task lifecycle, overdue calculation, automated rule generation for quoted leads without responses.
9. **Full-Text Search & Global Query (FTS5):** Sub-second unicode query resolution for phone numbers, URLs, post texts, notes, and labels.
10. **Security, Privacy & Consent Governance:** Loopback authentication verification, frequency capping, quiet hours enforcement, and opt-out compliance.
