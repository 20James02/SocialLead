import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    Numeric,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from app.infrastructure.database.session import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PersonDB(Base):
    __tablename__ = "persons"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    display_name = Column(String(255), nullable=False)
    avatar_url = Column(String(1024), nullable=True)
    contact_quality_score = Column(Integer, default=0)
    source_type = Column(String(64), nullable=False)
    first_seen = Column(DateTime, default=utc_now)
    last_seen = Column(DateTime, default=utc_now)
    is_merged = Column(Boolean, default=False)
    merged_into_id = Column(
        String(36), ForeignKey("persons.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    phones = relationship(
        "PersonPhoneDB", back_populates="person", cascade="all, delete-orphan"
    )
    social_accounts = relationship(
        "SocialAccountDB", back_populates="person", cascade="all, delete-orphan"
    )
    customer = relationship("CustomerDB", back_populates="person", uselist=False)
    notes = relationship(
        "NoteDB", back_populates="person", cascade="all, delete-orphan"
    )
    timeline_events = relationship(
        "TimelineEventDB", back_populates="person", cascade="all, delete-orphan"
    )
    person_labels = relationship(
        "PersonLabelDB", back_populates="person", cascade="all, delete-orphan"
    )


class PersonPhoneDB(Base):
    __tablename__ = "person_phones"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    person_id = Column(
        String(36), ForeignKey("persons.id", ondelete="CASCADE"), nullable=False
    )
    raw_phone = Column(String(32), nullable=False)
    normalized_phone = Column(String(32), nullable=False, index=True)
    source_type = Column(String(64), nullable=False)
    source_url = Column(String(1024), nullable=True)
    is_verified = Column(Boolean, default=False)
    captured_at = Column(DateTime, default=utc_now)
    created_at = Column(DateTime, default=utc_now)

    person = relationship("PersonDB", back_populates="phones")


class SocialAccountDB(Base):
    __tablename__ = "social_accounts"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    person_id = Column(
        String(36), ForeignKey("persons.id", ondelete="CASCADE"), nullable=False
    )
    platform = Column(String(32), nullable=False)
    external_id = Column(String(128), nullable=False)
    username = Column(String(255), nullable=True)
    profile_url = Column(String(1024), nullable=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)

    person = relationship("PersonDB", back_populates="social_accounts")
    __table_args__ = (
        UniqueConstraint("platform", "external_id", name="uq_platform_external_id"),
    )


class CustomerDB(Base):
    __tablename__ = "customers"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    person_id = Column(
        String(36),
        ForeignKey("persons.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    status = Column(String(64), default="NEW", index=True)
    lead_score = Column(Integer, default=0)
    assigned_to = Column(String(128), nullable=True)
    next_care_date = Column(DateTime, nullable=True, index=True)
    last_interaction = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    deleted_at = Column(DateTime, nullable=True)

    person = relationship("PersonDB", back_populates="customer")
    need_profile = relationship(
        "CustomerNeedProfileDB",
        back_populates="customer",
        uselist=False,
        cascade="all, delete-orphan",
    )
    opportunities = relationship(
        "OpportunityDB", back_populates="customer", cascade="all, delete-orphan"
    )
    care_tasks = relationship(
        "CareTaskDB", back_populates="customer", cascade="all, delete-orphan"
    )


class CustomerNeedProfileDB(Base):
    __tablename__ = "customer_need_profiles"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    customer_id = Column(
        String(36),
        ForeignKey("customers.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    need_type = Column(String(64), nullable=False)
    province = Column(String(128), nullable=True)
    district = Column(String(128), nullable=True)
    ward = Column(String(128), nullable=True)
    property_type = Column(String(64), default="UNKNOWN")
    current_provider = Column(String(128), nullable=True)
    pain_points = Column(Text, nullable=True)
    urgency = Column(String(32), default="MEDIUM")
    budget_signal = Column(String(128), nullable=True)
    decision_timeline = Column(String(128), nullable=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    customer = relationship("CustomerDB", back_populates="need_profile")


class OpportunityDB(Base):
    __tablename__ = "opportunities"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    customer_id = Column(
        String(36), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    title = Column(String(255), nullable=False)
    stage = Column(String(64), default="NEW", index=True)
    expected_revenue = Column(Numeric(12, 2), default=0.0)
    notes = Column(Text, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    deleted_at = Column(DateTime, nullable=True)

    customer = relationship("CustomerDB", back_populates="opportunities")


class SocialPostDB(Base):
    __tablename__ = "social_posts"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    platform = Column(String(32), nullable=False)
    external_id = Column(String(128), nullable=False)
    canonical_hash = Column(String(64), nullable=True, index=True)
    url = Column(String(1024), nullable=False)
    author_id = Column(String(128), nullable=True)
    author_name = Column(String(255), nullable=False)
    author_url = Column(String(1024), nullable=True)
    content = Column(Text, nullable=False)
    group_name = Column(String(255), nullable=True)
    group_url = Column(String(1024), nullable=True)
    lead_score = Column(Integer, default=0, index=True)
    intent_score = Column(Integer, default=0)
    spam_score = Column(Integer, default=0)
    urgency = Column(String(32), default="LOW")
    phone_extracted = Column(String(64), nullable=True)
    posted_at = Column(DateTime, nullable=False, index=True)
    detected_at = Column(DateTime, default=utc_now)
    is_raw = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=utc_now)
    deleted_at = Column(DateTime, nullable=True)

    comments = relationship(
        "SocialCommentDB", back_populates="post", cascade="all, delete-orphan"
    )
    saved_entry = relationship(
        "SavedPostDB",
        back_populates="post",
        uselist=False,
        cascade="all, delete-orphan",
    )
    ai_analysis = relationship(
        "AIAnalysisDB",
        back_populates="post",
        uselist=False,
        cascade="all, delete-orphan",
    )
    __table_args__ = (
        UniqueConstraint(
            "platform", "external_id", name="uq_post_platform_external_id"
        ),
    )


class SocialCommentDB(Base):
    __tablename__ = "social_comments"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    post_id = Column(
        String(36), ForeignKey("social_posts.id", ondelete="CASCADE"), nullable=False
    )
    external_id = Column(String(128), nullable=False)
    author_name = Column(String(255), nullable=False)
    author_id = Column(String(128), nullable=True)
    author_url = Column(String(1024), nullable=True)
    content = Column(Text, nullable=False)
    detected_phone = Column(String(64), nullable=True)
    intent_score = Column(Integer, default=0)
    posted_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    post = relationship("SocialPostDB", back_populates="comments")
    __table_args__ = (
        UniqueConstraint("post_id", "external_id", name="uq_comment_post_external_id"),
    )


class SavedPostDB(Base):
    __tablename__ = "saved_posts"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    post_id = Column(
        String(36),
        ForeignKey("social_posts.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    person_id = Column(
        String(36), ForeignKey("persons.id", ondelete="SET NULL"), nullable=True
    )
    user_note = Column(Text, nullable=True)
    saved_at = Column(DateTime, default=utc_now)

    post = relationship("SocialPostDB", back_populates="saved_entry")


class ScanJobDB(Base):
    __tablename__ = "scan_jobs"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    platform = Column(String(32), nullable=False)
    keywords_json = Column(Text, nullable=False)
    max_posts = Column(Integer, default=500)
    max_age_hours = Column(Integer, default=24)
    blacklist_mode = Column(String(32), default="IGNORE_HARD")
    status = Column(String(32), default="PENDING", index=True)
    scanned_count = Column(Integer, default=0)
    matched_count = Column(Integer, default=0)
    qualified_count = Column(Integer, default=0)
    spam_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)


class ScanResultDB(Base):
    __tablename__ = "scan_results"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    job_id = Column(
        String(36), ForeignKey("scan_jobs.id", ondelete="CASCADE"), nullable=False
    )
    post_id = Column(
        String(36), ForeignKey("social_posts.id", ondelete="CASCADE"), nullable=False
    )
    created_at = Column(DateTime, default=utc_now)
    __table_args__ = (
        UniqueConstraint("job_id", "post_id", name="uq_scan_result_job_post"),
    )


class LabelDB(Base):
    __tablename__ = "labels"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(64), unique=True, nullable=False)
    color_hex = Column(String(16), default="#3B82F6")
    label_type = Column(String(32), default="MANUAL")
    created_at = Column(DateTime, default=utc_now)


class PersonLabelDB(Base):
    __tablename__ = "person_labels"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    person_id = Column(
        String(36), ForeignKey("persons.id", ondelete="CASCADE"), nullable=False
    )
    label_id = Column(
        String(36), ForeignKey("labels.id", ondelete="CASCADE"), nullable=False
    )
    created_at = Column(DateTime, default=utc_now)
    __table_args__ = (
        UniqueConstraint("person_id", "label_id", name="uq_person_label"),
    )

    person = relationship("PersonDB", back_populates="person_labels")
    label = relationship("LabelDB")


class NoteDB(Base):
    __tablename__ = "notes"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    person_id = Column(
        String(36), ForeignKey("persons.id", ondelete="CASCADE"), nullable=False
    )
    author = Column(String(128), default="User")
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    person = relationship("PersonDB", back_populates="notes")


class CareTaskDB(Base):
    __tablename__ = "care_tasks"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    customer_id = Column(
        String(36), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    opportunity_id = Column(
        String(36), ForeignKey("opportunities.id", ondelete="SET NULL"), nullable=True
    )
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    scheduled_at = Column(DateTime, nullable=False, index=True)
    priority = Column(String(32), default="MEDIUM")
    status = Column(String(32), default="PENDING", index=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    deleted_at = Column(DateTime, nullable=True)

    customer = relationship("CustomerDB", back_populates="care_tasks")


class TimelineEventDB(Base):
    __tablename__ = "timeline_events"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    person_id = Column(
        String(36), ForeignKey("persons.id", ondelete="CASCADE"), nullable=False
    )
    event_type = Column(String(64), nullable=False)
    title = Column(String(255), nullable=False)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, index=True)

    person = relationship("PersonDB", back_populates="timeline_events")


class BlacklistEntityDB(Base):
    __tablename__ = "blacklist_entities"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    entity_type = Column(String(64), nullable=False)
    value = Column(String(255), nullable=False)
    mode = Column(String(32), default="HARD_BLACKLIST")
    reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utc_now)
    __table_args__ = (
        UniqueConstraint("entity_type", "value", name="uq_blacklist_type_val"),
    )


class ConversationDB(Base):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    platform = Column(String(32), nullable=False)
    external_conversation_id = Column(String(128), nullable=False)
    linked_person_id = Column(
        String(36), ForeignKey("persons.id", ondelete="SET NULL"), nullable=True
    )
    title = Column(String(255), nullable=True)
    last_message_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    __table_args__ = (
        UniqueConstraint(
            "platform", "external_conversation_id", name="uq_conv_platform_ext_id"
        ),
    )


class MessageDB(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    conversation_id = Column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    sender_type = Column(String(32), nullable=False)  # "CUSTOMER" | "AGENT" | "BOT"
    content = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=utc_now)
    created_at = Column(DateTime, default=utc_now)


class CampaignDB(Base):
    __tablename__ = "campaigns"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=False)
    channel = Column(String(64), nullable=False)
    status = Column(String(32), default="DRAFT")
    message_template = Column(Text, nullable=False)
    frequency_cap_days = Column(Integer, default=7)
    created_at = Column(DateTime, default=utc_now)


class CampaignRecipientDB(Base):
    __tablename__ = "campaign_recipients"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    campaign_id = Column(
        String(36), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False
    )
    customer_id = Column(
        String(36), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    status = Column(String(32), default="QUEUED")
    sent_at = Column(DateTime, nullable=True)
    response_received = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)


class PermissionDB(Base):
    __tablename__ = "permissions"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    person_id = Column(
        String(36),
        ForeignKey("persons.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    marketing_allowed = Column(Boolean, default=False)
    zalo_allowed = Column(Boolean, default=False)
    opt_out = Column(Boolean, default=False)
    do_not_contact = Column(Boolean, default=False)
    source = Column(String(64), default="CUSTOMER_OPT_IN")
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class AIAnalysisDB(Base):
    __tablename__ = "ai_analysis"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    post_id = Column(
        String(36),
        ForeignKey("social_posts.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    intent_score = Column(Integer, nullable=False)
    urgency_score = Column(Integer, nullable=False)
    opportunity_score = Column(Integer, nullable=False)
    spam_score = Column(Integer, nullable=False)
    overall_score = Column(Integer, nullable=False)
    explanation_json = Column(Text, nullable=False)
    next_best_action = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=utc_now)

    post = relationship("SocialPostDB", back_populates="ai_analysis")


class AuditLogDB(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    actor = Column(String(128), default="system")
    action = Column(String(128), nullable=False)
    target_type = Column(String(64), nullable=False)
    target_id = Column(String(64), nullable=False)
    old_value_json = Column(Text, nullable=True)
    new_value_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)


class AppSettingDB(Base):
    __tablename__ = "app_settings"

    key = Column(String(128), primary_key=True)
    value_json = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
