-- ScanSocial Production SQLite Schema Definition
-- Supports SQLite 3.35+ with WAL mode and FTS5 enabled

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- 1. Master Persons
CREATE TABLE IF NOT EXISTS persons (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    avatar_url TEXT,
    contact_quality_score INTEGER DEFAULT 0,
    source_type TEXT NOT NULL,
    first_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_merged BOOLEAN DEFAULT 0,
    merged_into_id TEXT REFERENCES persons(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_persons_merged ON persons(is_merged, merged_into_id);
CREATE INDEX IF NOT EXISTS idx_persons_deleted ON persons(deleted_at);

-- 2. Phone Numbers with Provenance
CREATE TABLE IF NOT EXISTS person_phones (
    id TEXT PRIMARY KEY,
    person_id TEXT NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    raw_phone TEXT NOT NULL,
    normalized_phone TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_url TEXT,
    is_verified BOOLEAN DEFAULT 0,
    captured_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_phones_norm ON person_phones(normalized_phone);
CREATE INDEX IF NOT EXISTS idx_phones_person ON person_phones(person_id);

-- 3. Social Accounts
CREATE TABLE IF NOT EXISTS social_accounts (
    id TEXT PRIMARY KEY,
    person_id TEXT NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    external_id TEXT NOT NULL,
    username TEXT,
    profile_url TEXT,
    is_verified BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(platform, external_id)
);
CREATE INDEX IF NOT EXISTS idx_social_platform_id ON social_accounts(platform, external_id);
CREATE INDEX IF NOT EXISTS idx_social_person ON social_accounts(person_id);

-- 4. Promoted Customers
CREATE TABLE IF NOT EXISTS customers (
    id TEXT PRIMARY KEY,
    person_id TEXT NOT NULL UNIQUE REFERENCES persons(id) ON DELETE RESTRICT,
    status TEXT NOT NULL DEFAULT 'NEW',
    lead_score INTEGER DEFAULT 0,
    assigned_to TEXT,
    next_care_date TIMESTAMP,
    last_interaction TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_customers_status ON customers(status);
CREATE INDEX IF NOT EXISTS idx_customers_next_care ON customers(next_care_date);

-- 5. Need Profiles
CREATE TABLE IF NOT EXISTS customer_need_profiles (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL UNIQUE REFERENCES customers(id) ON DELETE CASCADE,
    need_type TEXT NOT NULL,
    province TEXT,
    district TEXT,
    ward TEXT,
    property_type TEXT,
    current_provider TEXT,
    pain_points TEXT,
    urgency TEXT DEFAULT 'MEDIUM',
    budget_signal TEXT,
    decision_timeline TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Opportunities
CREATE TABLE IF NOT EXISTS opportunities (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    stage TEXT NOT NULL DEFAULT 'NEW',
    expected_revenue DECIMAL(12, 2) DEFAULT 0.0,
    notes TEXT,
    closed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_opps_stage ON opportunities(stage);
CREATE INDEX IF NOT EXISTS idx_opps_customer ON opportunities(customer_id);

-- 7. Social Posts
CREATE TABLE IF NOT EXISTS social_posts (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    external_id TEXT NOT NULL,
    url TEXT NOT NULL,
    author_id TEXT,
    author_name TEXT NOT NULL,
    author_url TEXT,
    content TEXT NOT NULL,
    group_name TEXT,
    group_url TEXT,
    lead_score INTEGER DEFAULT 0,
    intent_score INTEGER DEFAULT 0,
    spam_score INTEGER DEFAULT 0,
    urgency TEXT DEFAULT 'LOW',
    phone_extracted TEXT,
    posted_at TIMESTAMP NOT NULL,
    detected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_raw BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,
    UNIQUE(platform, external_id)
);
CREATE INDEX IF NOT EXISTS idx_posts_scores ON social_posts(lead_score, intent_score, spam_score);
CREATE INDEX IF NOT EXISTS idx_posts_posted ON social_posts(posted_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_is_raw ON social_posts(is_raw);

-- 8. Social Comments
CREATE TABLE IF NOT EXISTS social_comments (
    id TEXT PRIMARY KEY,
    post_id TEXT NOT NULL REFERENCES social_posts(id) ON DELETE CASCADE,
    external_id TEXT NOT NULL,
    author_name TEXT NOT NULL,
    author_url TEXT,
    content TEXT NOT NULL,
    detected_phone TEXT,
    intent_score INTEGER DEFAULT 0,
    posted_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(post_id, external_id)
);
CREATE INDEX IF NOT EXISTS idx_comments_post ON social_comments(post_id);

-- 9. Saved Posts
CREATE TABLE IF NOT EXISTS saved_posts (
    id TEXT PRIMARY KEY,
    post_id TEXT NOT NULL UNIQUE REFERENCES social_posts(id) ON DELETE CASCADE,
    person_id TEXT REFERENCES persons(id) ON DELETE SET NULL,
    user_note TEXT,
    saved_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 10. Scan Jobs
CREATE TABLE IF NOT EXISTS scan_jobs (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    keywords_json TEXT NOT NULL,
    max_posts INTEGER DEFAULT 500,
    max_age_hours INTEGER DEFAULT 24,
    blacklist_mode TEXT DEFAULT 'IGNORE_HARD',
    status TEXT NOT NULL DEFAULT 'PENDING',
    scanned_count INTEGER DEFAULT 0,
    matched_count INTEGER DEFAULT 0,
    qualified_count INTEGER DEFAULT 0,
    spam_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON scan_jobs(status);

-- 11. Scan Results Linker
CREATE TABLE IF NOT EXISTS scan_results (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES scan_jobs(id) ON DELETE CASCADE,
    post_id TEXT NOT NULL REFERENCES social_posts(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(job_id, post_id)
);

-- 12. Labels
CREATE TABLE IF NOT EXISTS labels (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    color_hex TEXT NOT NULL DEFAULT '#3B82F6',
    label_type TEXT NOT NULL DEFAULT 'MANUAL',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 13. Person Labels
CREATE TABLE IF NOT EXISTS person_labels (
    id TEXT PRIMARY KEY,
    person_id TEXT NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    label_id TEXT NOT NULL REFERENCES labels(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(person_id, label_id)
);

-- 14. Notes
CREATE TABLE IF NOT EXISTS notes (
    id TEXT PRIMARY KEY,
    person_id TEXT NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    author TEXT NOT NULL DEFAULT 'User',
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 15. Care Tasks (Calendar & Follow-ups)
CREATE TABLE IF NOT EXISTS care_tasks (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    opportunity_id TEXT REFERENCES opportunities(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    description TEXT,
    scheduled_at TIMESTAMP NOT NULL,
    priority TEXT NOT NULL DEFAULT 'MEDIUM',
    status TEXT NOT NULL DEFAULT 'PENDING',
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_care_scheduled ON care_tasks(scheduled_at, status);

-- 16. Timeline Events
CREATE TABLE IF NOT EXISTS timeline_events (
    id TEXT PRIMARY KEY,
    person_id TEXT NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    title TEXT NOT NULL,
    metadata_json TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_timeline_person ON timeline_events(person_id, created_at DESC);

-- 17. Blacklist Entities
CREATE TABLE IF NOT EXISTS blacklist_entities (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    value TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'HARD_BLACKLIST',
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(entity_type, value)
);
CREATE INDEX IF NOT EXISTS idx_blacklist_val ON blacklist_entities(entity_type, value);

-- 18. Conversations
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    external_conversation_id TEXT NOT NULL,
    linked_person_id TEXT REFERENCES persons(id) ON DELETE SET NULL,
    title TEXT,
    last_message_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(platform, external_conversation_id)
);

-- 19. Messages
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_type TEXT NOT NULL,
    content TEXT NOT NULL,
    sent_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 20. Campaigns
CREATE TABLE IF NOT EXISTS campaigns (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    channel TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'DRAFT',
    message_template TEXT NOT NULL,
    frequency_cap_days INTEGER DEFAULT 7,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 21. Campaign Recipients
CREATE TABLE IF NOT EXISTS campaign_recipients (
    id TEXT PRIMARY KEY,
    campaign_id TEXT NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    customer_id TEXT NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'QUEUED',
    sent_at TIMESTAMP,
    response_received TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 22. Permissions & Consent
CREATE TABLE IF NOT EXISTS permissions (
    id TEXT PRIMARY KEY,
    person_id TEXT NOT NULL UNIQUE REFERENCES persons(id) ON DELETE CASCADE,
    marketing_allowed BOOLEAN DEFAULT 0,
    zalo_allowed BOOLEAN DEFAULT 0,
    opt_out BOOLEAN DEFAULT 0,
    do_not_contact BOOLEAN DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'CUSTOMER_OPT_IN',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 23. AI Analysis & Scoring Explainability
CREATE TABLE IF NOT EXISTS ai_analysis (
    id TEXT PRIMARY KEY,
    post_id TEXT NOT NULL UNIQUE REFERENCES social_posts(id) ON DELETE CASCADE,
    intent_score INTEGER NOT NULL,
    urgency_score INTEGER NOT NULL,
    opportunity_score INTEGER NOT NULL,
    spam_score INTEGER NOT NULL,
    overall_score INTEGER NOT NULL,
    explanation_json TEXT NOT NULL,
    next_best_action TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 24. Audit Logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id TEXT PRIMARY KEY,
    actor TEXT NOT NULL DEFAULT 'system',
    action TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    old_value_json TEXT,
    new_value_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 25. App Settings
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 26. Virtual Full-Text Search (FTS5) Table
CREATE VIRTUAL TABLE IF NOT EXISTS fts_search USING fts5(
    entity_id UNINDEXED,
    entity_type UNINDEXED,
    title,
    content,
    tokenize = 'unicode61 remove_diacritics 0'
);
