from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel


class NormalizedSocialPost(BaseModel):
    platform: str
    external_id: str
    url: str
    author_id: Optional[str] = None
    author_name: str
    author_url: Optional[str] = None
    content: str
    group_name: Optional[str] = None
    group_url: Optional[str] = None
    posted_at: datetime


class NormalizedSocialComment(BaseModel):
    external_id: str
    author_name: str
    author_id: Optional[str] = None
    author_url: Optional[str] = None
    content: str
    posted_at: datetime


class SocialSourceAdapter(ABC):
    """Common abstraction for social discovery platforms (Facebook, Threads)."""

    @abstractmethod
    async def search(
        self, keywords: List[str], max_results: int = 100
    ) -> List[NormalizedSocialPost]:
        pass

    @abstractmethod
    async def fetch_post(self, post_url_or_id: str) -> Optional[NormalizedSocialPost]:
        pass

    @abstractmethod
    async def fetch_comments(
        self, post_external_id: str
    ) -> List[NormalizedSocialComment]:
        pass


class MessagingAdapter(ABC):
    """Common abstraction for CRM messaging (Zalo Personal, Zalo OA)."""

    @abstractmethod
    async def send_message(self, conversation_id: str, content: str) -> bool:
        pass

    @abstractmethod
    async def sync_recent_conversations(self) -> List[Dict[str, Any]]:
        pass
