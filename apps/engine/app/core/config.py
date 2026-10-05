import os
import secrets
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SCANSOCIAL_")

    APP_NAME: str = "ScanSocial Engine"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Loopback Network Boundary
    HOST: str = "127.0.0.1"
    PORT: int = 8765

    # Ephemeral session token for loopback API protection
    SESSION_TOKEN: str = os.getenv(
        "SCANSOCIAL_SESSION_TOKEN", secrets.token_urlsafe(32)
    )

    # Storage Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    DB_NAME: str = "scansocial.db"

    @property
    def DATABASE_PATH(self) -> Path:
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        return self.DATA_DIR / self.DB_NAME

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"sqlite:///{self.DATABASE_PATH}"

    # Retention Defaults
    RAW_SCAN_RETENTION_HOURS: int = 24

    # AI Provider Defaults
    DEFAULT_AI_PROVIDER: str = "heuristic"
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "llama3:8b"

    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "tauri://localhost",
        "http://tauri.localhost",
        "https://tauri.localhost",
    ]
    FACEBOOK_GRAPH_VERSION: str = "v22.0"
    FACEBOOK_PAGE_IDS: list[str] = []

    @field_validator("HOST")
    @classmethod
    def loopback_only(cls, value: str) -> str:
        if value != "127.0.0.1":
            raise ValueError("Engine must bind exclusively to 127.0.0.1")
        return value


settings = Settings()
