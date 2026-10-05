import re
import regex
from urllib.parse import urlparse
from typing import Dict, Optional, Set, Tuple
from app.domain.models import BlacklistMode, BlacklistEntityType


class BlacklistEvaluator:
    """
    Multi-mode Blacklist Engine supporting Profiles, Pages, Groups, Phones, and Keywords.
    Modes:
      - HARD_BLACKLIST: Immediate drop at Discovery L0.
      - SOFT_BLACKLIST: Retains record but applies a heavy Lead Score penalty (-80 points).
    """

    def __init__(self):
        # Maps (entity_type, value_lower) -> (mode, reason)
        self._rules: Dict[Tuple[str, str], Tuple[BlacklistMode, str]] = {}
        self._keyword_rules: Dict[str, Tuple[BlacklistMode, str]] = {}
        self._regex_rules = {}

    def add_rule(
        self,
        entity_type: BlacklistEntityType,
        value: str,
        mode: BlacklistMode,
        reason: str = "",
    ):
        clean_val = (
            value.strip()
            if entity_type == BlacklistEntityType.REGEX
            else value.strip().lower()
        )
        if entity_type == BlacklistEntityType.REGEX:
            self._regex_rules[clean_val] = (
                regex.compile(clean_val, regex.IGNORECASE),
                mode,
                reason,
            )
            return
        if entity_type == BlacklistEntityType.KEYWORD:
            self._keyword_rules[clean_val] = (mode, reason)
        else:
            self._rules[(entity_type.value, clean_val)] = (mode, reason)

    def remove_rule(self, entity_type: BlacklistEntityType, value: str):
        if entity_type == BlacklistEntityType.REGEX:
            self._regex_rules.pop(value.strip(), None)
            return
        clean_val = value.strip().lower()
        if entity_type == BlacklistEntityType.KEYWORD:
            self._keyword_rules.pop(clean_val, None)
        else:
            self._rules.pop((entity_type.value, clean_val), None)

    def clear(self):
        self._rules.clear()
        self._keyword_rules.clear()
        self._regex_rules.clear()

    def evaluate(
        self,
        author_id: Optional[str] = None,
        group_name: Optional[str] = None,
        phone: Optional[str] = None,
        content: Optional[str] = None,
        url: Optional[str] = None,
        author_url: Optional[str] = None,
        group_url: Optional[str] = None,
    ) -> Tuple[bool, Optional[BlacklistMode], Optional[str]]:
        """
        Evaluates an entity against all active blacklist rules.
        Hard blacklist has higher precedence than soft blacklist.
        Returns: (is_blacklisted, mode, reason)
        """
        soft_hit = None
        for pattern, mode, reason in self._regex_rules.values():
            try:
                matched = pattern.search(content or "", timeout=0.025)
            except TimeoutError:
                return (
                    True,
                    BlacklistMode.HARD_BLACKLIST,
                    "Content regex exceeded its evaluation budget",
                )
            if matched:
                if mode == BlacklistMode.HARD_BLACKLIST:
                    return True, mode, reason
                soft_hit = soft_hit or (mode, reason)

        # Pages, profile/group URLs and content domains share hard-rule precedence.
        domains = {
            urlparse(u).hostname.lower()
            for u in [
                url,
                author_url,
                group_url,
                *re.findall(r"https?://[^\s<>]+", content or ""),
            ]
            if u and urlparse(u).hostname
        }
        extra = [
            (BlacklistEntityType.PAGE.value, author_id),
            (BlacklistEntityType.PAGE.value, author_url),
            (BlacklistEntityType.PROFILE.value, author_url),
            (BlacklistEntityType.GROUP.value, group_url),
        ]
        for (kind, value), (mode, reason) in self._rules.items():
            domain_match = kind == BlacklistEntityType.DOMAIN.value and any(
                d == value or d.endswith("." + value) for d in domains
            )
            direct_match = any(
                kind == k and v and v.strip().lower() == value for k, v in extra
            )
            if domain_match or direct_match:
                if mode == BlacklistMode.HARD_BLACKLIST:
                    return True, mode, reason
                soft_hit = soft_hit or (mode, reason)

        # 1. Check Author Profile
        if author_id:
            key = (BlacklistEntityType.PROFILE.value, author_id.strip().lower())
            if key in self._rules:
                mode, reason = self._rules[key]
                if mode == BlacklistMode.HARD_BLACKLIST:
                    return True, mode, f"Author blacklisted: {reason}"
                soft_hit = (mode, f"Author soft-blacklisted: {reason}")

        # 2. Check Group
        if group_name:
            key = (BlacklistEntityType.GROUP.value, group_name.strip().lower())
            if key in self._rules:
                mode, reason = self._rules[key]
                if mode == BlacklistMode.HARD_BLACKLIST:
                    return True, mode, f"Group blacklisted: {reason}"
                soft_hit = soft_hit or (mode, f"Group soft-blacklisted: {reason}")

        # 3. Check Phone
        if phone:
            clean_phone = phone.strip().lower()
            key = (BlacklistEntityType.PHONE.value, clean_phone)
            if key in self._rules:
                mode, reason = self._rules[key]
                if mode == BlacklistMode.HARD_BLACKLIST:
                    return True, mode, f"Phone blacklisted: {reason}"
                soft_hit = soft_hit or (mode, f"Phone soft-blacklisted: {reason}")

        # 4. Check Content Keywords
        if content:
            lower_content = content.lower()
            for kw, (mode, reason) in self._keyword_rules.items():
                if kw in lower_content:
                    if mode == BlacklistMode.HARD_BLACKLIST:
                        return True, mode, f"Keyword '{kw}' hard-blacklisted: {reason}"
                    soft_hit = soft_hit or (
                        mode,
                        f"Keyword '{kw}' soft-blacklisted: {reason}",
                    )

        if soft_hit:
            return True, soft_hit[0], soft_hit[1]

        return False, None, None


blacklist_engine = BlacklistEvaluator()
