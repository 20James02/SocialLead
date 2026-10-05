import httpx
from app.integrations.base import MessagingAdapter
from app.infrastructure.security.vault import vault
from app.integrations.official import IntegrationUnavailable


class ZaloPersonalAssistAdapter(MessagingAdapter):
    async def send_message(self, conversation_id: str, content: str) -> bool:
        raise IntegrationUnavailable(
            "Personal Zalo messages require manual sending; use the draft assistant"
        )

    async def sync_recent_conversations(self):
        raise IntegrationUnavailable("Use manual conversation import for personal Zalo")


class ZaloOAAdapter(MessagingAdapter):
    async def send_message(self, conversation_id: str, content: str) -> bool:
        token = vault.get_secret("zalo_access_token")
        if not token:
            raise IntegrationUnavailable("Zalo OA access token is not configured")
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                "https://openapi.zalo.me/v3.0/oa/message/cs",
                headers={"access_token": token},
                json={
                    "recipient": {"user_id": conversation_id},
                    "message": {"text": content},
                },
            )
            response.raise_for_status()
            body = response.json()
            return body.get("error") == 0 and bool(
                body.get("data", {}).get("message_id")
            )

    async def sync_recent_conversations(self):
        raise IntegrationUnavailable(
            "Automatic conversation sync is not configured; log authorized messages locally"
        )


zalo_personal = ZaloPersonalAssistAdapter()
zalo_oa = ZaloOAAdapter()
