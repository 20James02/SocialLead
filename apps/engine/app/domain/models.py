from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class PlatformType(str, Enum):
    FACEBOOK = "FACEBOOK"
    THREADS = "THREADS"
    ZALO = "ZALO"
    MANUAL = "MANUAL"


class ScanJobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class BlacklistMode(str, Enum):
    HARD_BLACKLIST = "HARD_BLACKLIST"
    SOFT_BLACKLIST = "SOFT_BLACKLIST"


class BlacklistEntityType(str, Enum):
    PROFILE = "PROFILE"
    PAGE = "PAGE"
    GROUP = "GROUP"
    PHONE = "PHONE"
    KEYWORD = "KEYWORD"
    DOMAIN = "DOMAIN"
    REGEX = "REGEX"


class NeedType(str, Enum):
    WIFI = "WIFI"
    CAMERA = "CAMERA"
    TV = "TV"
    COMBO = "COMBO"
    OTHER = "OTHER"


class PropertyType(str, Enum):
    HOUSE = "HOUSE"
    APARTMENT = "APARTMENT"
    RENTAL = "RENTAL"
    STORE = "STORE"
    OFFICE = "OFFICE"
    BUSINESS = "BUSINESS"
    UNKNOWN = "UNKNOWN"


class LeadUrgency(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class NextBestAction(str, Enum):
    CALL_NOW = "CALL_NOW"
    MESSAGE = "MESSAGE"
    FOLLOW_UP = "FOLLOW_UP"
    WAIT = "WAIT"
    NEED_MORE_INFO = "NEED_MORE_INFO"
    IGNORE = "IGNORE"


class OpportunityStage(str, Enum):
    NEW = "NEW"
    QUALIFIED = "QUALIFIED"
    CONTACTED = "CONTACTED"
    INTERESTED = "INTERESTED"
    QUOTED = "QUOTED"
    APPOINTMENT = "APPOINTMENT"
    WON = "WON"
    LOST = "LOST"
    PAUSED = "PAUSED"


class CarePriority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class CareTaskStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


# Data Transfer / Value Objects


class PhoneProvenance(BaseModel):
    raw_phone: str
    normalized_phone: str
    source_type: str
    source_url: Optional[str] = None
    captured_at: datetime
    is_verified: bool = False


class ScoreBreakdownItem(BaseModel):
    category: str
    points: int
    reason: str


class LeadScoreResult(BaseModel):
    intent_score: int = Field(ge=0, le=100)
    urgency_score: int = Field(ge=0, le=100)
    opportunity_score: int = Field(ge=0, le=100)
    spam_score: int = Field(ge=0, le=100)
    contact_quality_score: int = Field(ge=0, le=100)
    overall_lead_score: int = Field(ge=0, le=100)
    breakdown: List[ScoreBreakdownItem] = []
    next_best_action: NextBestAction
    action_reason: str


class NeedProfileData(BaseModel):
    need_type: NeedType
    province: Optional[str] = None
    district: Optional[str] = None
    ward: Optional[str] = None
    property_type: PropertyType = PropertyType.UNKNOWN
    current_provider: Optional[str] = None
    pain_points: Optional[str] = None
    urgency: LeadUrgency = LeadUrgency.MEDIUM
    budget_signal: Optional[str] = None
    decision_timeline: Optional[str] = None
