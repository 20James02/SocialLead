from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.api.deps import SessionAuth
from app.infrastructure.security.vault import vault
from app.core.config import settings

router = APIRouter(
    prefix="/integrations", tags=["Integrations"], dependencies=[SessionAuth]
)
PROVIDERS = {"facebook", "threads", "zalo"}


@router.get("")
def integration_status():
    return {
        p: {
            "configured": bool(vault.get_secret(f"{p}_access_token")),
            "mode": "OFFICIAL_API" if p != "facebook" else "AUTHORIZED_PAGE_FEED",
        }
        for p in PROVIDERS
    } | {
        "facebook_page_ids": settings.FACEBOOK_PAGE_IDS,
        "ai_provider": settings.DEFAULT_AI_PROVIDER,
        "personal_zalo": "MANUAL_ASSIST",
    }


class TokenInput(BaseModel):
    access_token: str = Field(min_length=10, max_length=4096)


@router.put("/{provider}/token")
def set_token(provider: str, req: TokenInput):
    if provider not in PROVIDERS:
        raise HTTPException(404, "Unknown provider")
    try:
        vault.set_secret(f"{provider}_access_token", req.access_token)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc))
    return {"configured": True}


@router.delete("/{provider}/token")
def delete_token(provider: str):
    if provider not in PROVIDERS:
        raise HTTPException(404, "Unknown provider")
    try:
        vault.delete_secret(f"{provider}_access_token")
    except RuntimeError as exc:
        raise HTTPException(503, str(exc))
    return {"configured": bool(vault.get_secret(f"{provider}_access_token"))}
