import hmac
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from app.core.config import settings

API_KEY_HEADER = APIKeyHeader(name="X-App-Session-Token", auto_error=False)


def verify_session_token(token: str | None = Security(API_KEY_HEADER)) -> bool:
    """
    Validates that the incoming request has the matching internal session token.
    Uses constant-time comparison to prevent timing attacks.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required X-App-Session-Token header",
        )

    # Constant-time comparison
    is_valid = hmac.compare_digest(token.encode(), settings.SESSION_TOKEN.encode())
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid internal session token",
        )
    return True
