import hashlib
import re
from typing import Optional, Set
from collections import OrderedDict

class PostDeduplicator:
    """
    High-Performance Deduplication Engine.
    Employs exact external_id matching and canonical content hashing
    (platform + author_id + normalized_text + timestamp) with an in-memory LRU cache.
    """
    def __init__(self, cache_size: int = 50000):
        self.cache_size = cache_size
        self._id_cache: OrderedDict[str, bool] = OrderedDict()
        self._hash_cache: OrderedDict[str, bool] = OrderedDict()

    @staticmethod
    def normalize_text(text: str) -> str:
        """Strips markdown, emojis, excess whitespace, and converts to lowercase."""
        if not text:
            return ""
        # Remove URLs
        text = re.sub(r'https?://\S+', '', text)
        # Keep alphanumeric, basic Vietnamese characters, collapse whitespaces
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip().lower()
        return text

    @classmethod
    def compute_canonical_hash(
        cls,
        platform: str,
        author_id: Optional[str],
        content: str,
        timestamp_str: str
    ) -> str:
        norm_text = cls.normalize_text(content)
        author = (author_id or "unknown").strip().lower()
        raw_key = f"{platform.upper()}|{author}|{norm_text}|{timestamp_str.strip()}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def is_duplicate_id(self, platform: str, external_id: str) -> bool:
        composite_id = f"{platform.upper()}:{external_id}"
        if composite_id in self._id_cache:
            return True
        return False

    def is_duplicate_hash(self, canonical_hash: str) -> bool:
        if canonical_hash in self._hash_cache:
            return True
        return False

    def record_seen(self, platform: str, external_id: str, canonical_hash: str):
        composite_id = f"{platform.upper()}:{external_id}"
        self._id_cache[composite_id] = True
        self._hash_cache[canonical_hash] = True
        
        # Evict oldest if beyond cache size
        if len(self._id_cache) > self.cache_size:
            self._id_cache.popitem(last=False)
        if len(self._hash_cache) > self.cache_size:
            self._hash_cache.popitem(last=False)

    def is_duplicate(
        self,
        platform: str,
        external_id: str,
        author_id: Optional[str],
        content: str,
        timestamp_str: str
    ) -> bool:
        if self.is_duplicate_id(platform, external_id):
            return True
        chash = self.compute_canonical_hash(platform, author_id, content, timestamp_str)
        if self.is_duplicate_hash(chash):
            return True
        return False

deduplicator = PostDeduplicator()
