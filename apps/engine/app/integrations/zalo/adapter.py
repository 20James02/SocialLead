import asyncio
from typing import List, Dict, Any, Optional
from app.integrations.base import MessagingAdapter

class ZaloPersonalAssistAdapter(MessagingAdapter):
    """
    Assisted 1:1 Sales Support.
    Provides context synchronization and message draft suggestions for manual salesperson review.
    Does NOT execute automated bulk spam.
    """
    async def send_message(self, conversation_id: str, content: str) -> bool:
        # In desktop context, prepares manual intent or bridges to desktop client
        await asyncio.sleep(0.01)
        return True

    async def sync_recent_conversations(self) -> List[Dict[str, Any]]:
        return []

class ZaloOAAdapter(MessagingAdapter):
    """
    Official Account Integration.
    Executes compliant customer care messages via official Zalo OA APIs.
    """
    async def send_message(self, conversation_id: str, content: str) -> bool:
        await asyncio.sleep(0.01)
        return True

    async def sync_recent_conversations(self) -> List[Dict[str, Any]]:
        return []

zalo_personal = ZaloPersonalAssistAdapter()
zalo_oa = ZaloOAAdapter()
