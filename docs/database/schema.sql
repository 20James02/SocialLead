-- ORM schema snapshot; runtime additive migrations and FTS triggers are in app/infrastructure.
-- Do not use this snapshot as a replacement for init_db()/FTSManager.install_sync().

CREATE TABLE app_settings (
	"key" VARCHAR(128) NOT NULL,
	value_json TEXT NOT NULL,
	updated_at DATETIME,
	PRIMARY KEY ("key")
);

CREATE TABLE audit_logs (
	id VARCHAR(36) NOT NULL,
	actor VARCHAR(128),
	action VARCHAR(128) NOT NULL,
	target_type VARCHAR(64) NOT NULL,
	target_id VARCHAR(64) NOT NULL,
	old_value_json TEXT,
	new_value_json TEXT,
	created_at DATETIME,
	PRIMARY KEY (id)
);

CREATE TABLE blacklist_entities (
	id VARCHAR(36) NOT NULL,
	entity_type VARCHAR(64) NOT NULL,
	value VARCHAR(255) NOT NULL,
	mode VARCHAR(32),
	reason VARCHAR(255),
	created_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT uq_blacklist_type_val UNIQUE (entity_type, value)
);

CREATE TABLE campaigns (
	id VARCHAR(36) NOT NULL,
	name VARCHAR(255) NOT NULL,
	channel VARCHAR(64) NOT NULL,
	status VARCHAR(32),
	message_template TEXT NOT NULL,
	frequency_cap_days INTEGER,
	created_at DATETIME,
	PRIMARY KEY (id)
);

CREATE TABLE labels (
	id VARCHAR(36) NOT NULL,
	name VARCHAR(64) NOT NULL,
	color_hex VARCHAR(16),
	label_type VARCHAR(32),
	created_at DATETIME,
	PRIMARY KEY (id),
	UNIQUE (name)
);

CREATE TABLE persons (
	id VARCHAR(36) NOT NULL,
	display_name VARCHAR(255) NOT NULL,
	avatar_url VARCHAR(1024),
	contact_quality_score INTEGER,
	source_type VARCHAR(64) NOT NULL,
	first_seen DATETIME,
	last_seen DATETIME,
	is_merged BOOLEAN,
	merged_into_id VARCHAR(36),
	created_at DATETIME,
	updated_at DATETIME,
	deleted_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(merged_into_id) REFERENCES persons (id) ON DELETE SET NULL
);

CREATE TABLE scan_jobs (
	id VARCHAR(36) NOT NULL,
	platform VARCHAR(32) NOT NULL,
	keywords_json TEXT NOT NULL,
	max_posts INTEGER,
	max_age_hours INTEGER,
	blacklist_mode VARCHAR(32),
	status VARCHAR(32),
	scanned_count INTEGER,
	matched_count INTEGER,
	qualified_count INTEGER,
	spam_count INTEGER,
	error_count INTEGER,
	error_message TEXT,
	started_at DATETIME,
	finished_at DATETIME,
	created_at DATETIME,
	PRIMARY KEY (id)
);

CREATE INDEX ix_scan_jobs_status ON scan_jobs (status);

CREATE TABLE social_posts (
	id VARCHAR(36) NOT NULL,
	platform VARCHAR(32) NOT NULL,
	external_id VARCHAR(128) NOT NULL,
	canonical_hash VARCHAR(64),
	url VARCHAR(1024) NOT NULL,
	author_id VARCHAR(128),
	author_name VARCHAR(255) NOT NULL,
	author_url VARCHAR(1024),
	content TEXT NOT NULL,
	group_name VARCHAR(255),
	group_url VARCHAR(1024),
	lead_score INTEGER,
	intent_score INTEGER,
	spam_score INTEGER,
	urgency VARCHAR(32),
	phone_extracted VARCHAR(64),
	posted_at DATETIME NOT NULL,
	detected_at DATETIME,
	is_raw BOOLEAN,
	created_at DATETIME,
	deleted_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT uq_post_platform_external_id UNIQUE (platform, external_id)
);

CREATE INDEX ix_social_posts_canonical_hash ON social_posts (canonical_hash);

CREATE INDEX ix_social_posts_is_raw ON social_posts (is_raw);

CREATE INDEX ix_social_posts_lead_score ON social_posts (lead_score);

CREATE INDEX ix_social_posts_posted_at ON social_posts (posted_at);

CREATE TABLE ai_analysis (
	id VARCHAR(36) NOT NULL,
	post_id VARCHAR(36) NOT NULL,
	intent_score INTEGER NOT NULL,
	urgency_score INTEGER NOT NULL,
	opportunity_score INTEGER NOT NULL,
	spam_score INTEGER NOT NULL,
	overall_score INTEGER NOT NULL,
	explanation_json TEXT NOT NULL,
	next_best_action VARCHAR(64) NOT NULL,
	created_at DATETIME,
	PRIMARY KEY (id),
	UNIQUE (post_id),
	FOREIGN KEY(post_id) REFERENCES social_posts (id) ON DELETE CASCADE
);

CREATE TABLE conversations (
	id VARCHAR(36) NOT NULL,
	platform VARCHAR(32) NOT NULL,
	external_conversation_id VARCHAR(128) NOT NULL,
	linked_person_id VARCHAR(36),
	title VARCHAR(255),
	last_message_at DATETIME,
	created_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT uq_conv_platform_ext_id UNIQUE (platform, external_conversation_id),
	FOREIGN KEY(linked_person_id) REFERENCES persons (id) ON DELETE SET NULL
);

CREATE TABLE customers (
	id VARCHAR(36) NOT NULL,
	person_id VARCHAR(36) NOT NULL,
	status VARCHAR(64),
	lead_score INTEGER,
	assigned_to VARCHAR(128),
	next_care_date DATETIME,
	last_interaction DATETIME,
	created_at DATETIME,
	updated_at DATETIME,
	deleted_at DATETIME,
	PRIMARY KEY (id),
	UNIQUE (person_id),
	FOREIGN KEY(person_id) REFERENCES persons (id) ON DELETE RESTRICT
);

CREATE INDEX ix_customers_next_care_date ON customers (next_care_date);

CREATE INDEX ix_customers_status ON customers (status);

CREATE TABLE notes (
	id VARCHAR(36) NOT NULL,
	person_id VARCHAR(36) NOT NULL,
	author VARCHAR(128),
	content TEXT NOT NULL,
	created_at DATETIME,
	updated_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(person_id) REFERENCES persons (id) ON DELETE CASCADE
);

CREATE TABLE permissions (
	id VARCHAR(36) NOT NULL,
	person_id VARCHAR(36) NOT NULL,
	marketing_allowed BOOLEAN,
	zalo_allowed BOOLEAN,
	opt_out BOOLEAN,
	do_not_contact BOOLEAN,
	source VARCHAR(64),
	updated_at DATETIME,
	PRIMARY KEY (id),
	UNIQUE (person_id),
	FOREIGN KEY(person_id) REFERENCES persons (id) ON DELETE CASCADE
);

CREATE TABLE person_labels (
	id VARCHAR(36) NOT NULL,
	person_id VARCHAR(36) NOT NULL,
	label_id VARCHAR(36) NOT NULL,
	created_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT uq_person_label UNIQUE (person_id, label_id),
	FOREIGN KEY(person_id) REFERENCES persons (id) ON DELETE CASCADE,
	FOREIGN KEY(label_id) REFERENCES labels (id) ON DELETE CASCADE
);

CREATE TABLE person_phones (
	id VARCHAR(36) NOT NULL,
	person_id VARCHAR(36) NOT NULL,
	raw_phone VARCHAR(32) NOT NULL,
	normalized_phone VARCHAR(32) NOT NULL,
	source_type VARCHAR(64) NOT NULL,
	source_url VARCHAR(1024),
	is_verified BOOLEAN,
	captured_at DATETIME,
	created_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(person_id) REFERENCES persons (id) ON DELETE CASCADE
);

CREATE INDEX ix_person_phones_normalized_phone ON person_phones (normalized_phone);

CREATE TABLE saved_posts (
	id VARCHAR(36) NOT NULL,
	post_id VARCHAR(36) NOT NULL,
	person_id VARCHAR(36),
	user_note TEXT,
	saved_at DATETIME,
	PRIMARY KEY (id),
	UNIQUE (post_id),
	FOREIGN KEY(post_id) REFERENCES social_posts (id) ON DELETE CASCADE,
	FOREIGN KEY(person_id) REFERENCES persons (id) ON DELETE SET NULL
);

CREATE TABLE scan_results (
	id VARCHAR(36) NOT NULL,
	job_id VARCHAR(36) NOT NULL,
	post_id VARCHAR(36) NOT NULL,
	created_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT uq_scan_result_job_post UNIQUE (job_id, post_id),
	FOREIGN KEY(job_id) REFERENCES scan_jobs (id) ON DELETE CASCADE,
	FOREIGN KEY(post_id) REFERENCES social_posts (id) ON DELETE CASCADE
);

CREATE TABLE social_accounts (
	id VARCHAR(36) NOT NULL,
	person_id VARCHAR(36) NOT NULL,
	platform VARCHAR(32) NOT NULL,
	external_id VARCHAR(128) NOT NULL,
	username VARCHAR(255),
	profile_url VARCHAR(1024),
	is_verified BOOLEAN,
	created_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT uq_platform_external_id UNIQUE (platform, external_id),
	FOREIGN KEY(person_id) REFERENCES persons (id) ON DELETE CASCADE
);

CREATE TABLE social_comments (
	id VARCHAR(36) NOT NULL,
	post_id VARCHAR(36) NOT NULL,
	external_id VARCHAR(128) NOT NULL,
	author_name VARCHAR(255) NOT NULL,
	author_id VARCHAR(128),
	author_url VARCHAR(1024),
	content TEXT NOT NULL,
	detected_phone VARCHAR(64),
	intent_score INTEGER,
	posted_at DATETIME NOT NULL,
	created_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT uq_comment_post_external_id UNIQUE (post_id, external_id),
	FOREIGN KEY(post_id) REFERENCES social_posts (id) ON DELETE CASCADE
);

CREATE TABLE timeline_events (
	id VARCHAR(36) NOT NULL,
	person_id VARCHAR(36) NOT NULL,
	event_type VARCHAR(64) NOT NULL,
	title VARCHAR(255) NOT NULL,
	metadata_json TEXT,
	created_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(person_id) REFERENCES persons (id) ON DELETE CASCADE
);

CREATE INDEX ix_timeline_events_created_at ON timeline_events (created_at);

CREATE TABLE campaign_recipients (
	id VARCHAR(36) NOT NULL,
	campaign_id VARCHAR(36) NOT NULL,
	customer_id VARCHAR(36) NOT NULL,
	status VARCHAR(32),
	sent_at DATETIME,
	response_received TEXT,
	created_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(campaign_id) REFERENCES campaigns (id) ON DELETE CASCADE,
	FOREIGN KEY(customer_id) REFERENCES customers (id) ON DELETE CASCADE
);

CREATE TABLE customer_need_profiles (
	id VARCHAR(36) NOT NULL,
	customer_id VARCHAR(36) NOT NULL,
	need_type VARCHAR(64) NOT NULL,
	province VARCHAR(128),
	district VARCHAR(128),
	ward VARCHAR(128),
	property_type VARCHAR(64),
	current_provider VARCHAR(128),
	pain_points TEXT,
	urgency VARCHAR(32),
	budget_signal VARCHAR(128),
	decision_timeline VARCHAR(128),
	updated_at DATETIME,
	PRIMARY KEY (id),
	UNIQUE (customer_id),
	FOREIGN KEY(customer_id) REFERENCES customers (id) ON DELETE CASCADE
);

CREATE TABLE messages (
	id VARCHAR(36) NOT NULL,
	conversation_id VARCHAR(36) NOT NULL,
	sender_type VARCHAR(32) NOT NULL,
	content TEXT NOT NULL,
	sent_at DATETIME,
	created_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
);

CREATE TABLE opportunities (
	id VARCHAR(36) NOT NULL,
	customer_id VARCHAR(36) NOT NULL,
	title VARCHAR(255) NOT NULL,
	stage VARCHAR(64),
	expected_revenue NUMERIC(12, 2),
	notes TEXT,
	closed_at DATETIME,
	created_at DATETIME,
	updated_at DATETIME,
	deleted_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(customer_id) REFERENCES customers (id) ON DELETE CASCADE
);

CREATE INDEX ix_opportunities_stage ON opportunities (stage);

CREATE TABLE care_tasks (
	id VARCHAR(36) NOT NULL,
	customer_id VARCHAR(36) NOT NULL,
	opportunity_id VARCHAR(36),
	title VARCHAR(255) NOT NULL,
	description TEXT,
	scheduled_at DATETIME NOT NULL,
	priority VARCHAR(32),
	status VARCHAR(32),
	completed_at DATETIME,
	created_at DATETIME,
	deleted_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(customer_id) REFERENCES customers (id) ON DELETE CASCADE,
	FOREIGN KEY(opportunity_id) REFERENCES opportunities (id) ON DELETE SET NULL
);

CREATE INDEX ix_care_tasks_scheduled_at ON care_tasks (scheduled_at);

CREATE INDEX ix_care_tasks_status ON care_tasks (status);
