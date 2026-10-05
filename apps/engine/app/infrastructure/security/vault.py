"""OS credential storage; environment variables support headless deployments."""

import os
import hashlib
from app.core.config import settings


class SecretVault:
    def __init__(self):
        self.service = (
            "ScanSocial-"
            + hashlib.sha256(str(settings.DATA_DIR.resolve()).encode()).hexdigest()[:16]
        )

    def get_secret(self, key):
        value = os.getenv("SCANSOCIAL_" + key.upper())
        if value:
            return value
        try:
            import keyring

            return keyring.get_password(self.service, key)
        except Exception:
            return None

    def set_secret(self, key, value):
        try:
            import keyring

            keyring.set_password(self.service, key, value)
        except Exception as exc:
            raise RuntimeError(
                "OS keyring unavailable; configure a SCANSOCIAL_* environment variable instead"
            ) from exc

    def delete_secret(self, key):
        try:
            import keyring

            if keyring.get_password(self.service, key) is not None:
                keyring.delete_password(self.service, key)
        except Exception as exc:
            raise RuntimeError("Could not remove OS keyring secret") from exc


vault = SecretVault()
