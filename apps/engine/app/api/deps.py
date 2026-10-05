from typing import Generator
from fastapi import Depends
from sqlalchemy.orm import Session
from app.infrastructure.database.session import get_db
from app.core.security import verify_session_token


def get_current_db() -> Generator[Session, None, None]:
    yield from get_db()


# Common dependency requiring valid internal session token
SessionAuth = Depends(verify_session_token)
DbSession = Depends(get_current_db)
