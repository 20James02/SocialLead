import os
import json
import base64
from typing import Optional
from cryptography.fernet import Fernet
from app.core.config import settings

class SecretVault:
    """
    Cross-platform Secret Management.
    Attempts to use native OS Keyring (Windows Credential Manager / Linux Secret Service).
    Falls back to AES-256 encrypted local vault file if keyring is unavailable in headless environments.
    """
    SERVICE_NAME = "ScanSocialSecureVault"

    def __init__(self):
        self._keyring_available = False
        try:
            import keyring
            self._keyring = keyring
            # Test if a backend is available
            backend = keyring.get_keyring()
            if "fail" not in backend.__class__.__name__.lower():
                self._keyring_available = True
        except Exception:
            self._keyring_available = False
            
        self._fallback_file = settings.DATA_DIR / ".vault.enc"
        self._master_key_file = settings.DATA_DIR / ".vault.key"
        self._fernet: Optional[Fernet] = None
        self._init_fallback_fernet()

    def _init_fallback_fernet(self):
        settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not self._master_key_file.exists():
            key = Fernet.generate_key()
            self._master_key_file.write_bytes(key)
        else:
            key = self._master_key_file.read_bytes()
        self._fernet = Fernet(key)

    def set_secret(self, key: str, value: str):
        if self._keyring_available:
            try:
                self._keyring.set_password(self.SERVICE_NAME, key, value)
                return
            except Exception:
                pass
        
        # Fallback to local encrypted file
        vault = self._load_fallback_vault()
        vault[key] = value
        encrypted = self._fernet.encrypt(json.dumps(vault).encode("utf-8"))
        self._fallback_file.write_bytes(encrypted)

    def get_secret(self, key: str) -> Optional[str]:
        if self._keyring_available:
            try:
                val = self._keyring.get_password(self.SERVICE_NAME, key)
                if val is not None:
                    return val
            except Exception:
                pass
        
        vault = self._load_fallback_vault()
        return vault.get(key)

    def delete_secret(self, key: str):
        if self._keyring_available:
            try:
                self._keyring.delete_password(self.SERVICE_NAME, key)
            except Exception:
                pass
        vault = self._load_fallback_vault()
        if key in vault:
            del vault[key]
            encrypted = self._fernet.encrypt(json.dumps(vault).encode("utf-8"))
            self._fallback_file.write_bytes(encrypted)

    def _load_fallback_vault(self) -> dict:
        if not self._fallback_file.exists():
            return {}
        try:
            raw = self._fallback_file.read_bytes()
            decrypted = self._fernet.decrypt(raw)
            return json.loads(decrypted.decode("utf-8"))
        except Exception:
            return {}

vault = SecretVault()
