import re
from typing import List, Optional
from datetime import datetime, timezone
from app.domain.models import PhoneProvenance

# Vietnamese telecom prefixes for 10-digit mobile numbers:
# Viettel: 086, 096, 097, 098, 032, 033, 034, 035, 036, 037, 038, 039
# Mobifone: 089, 090, 093, 070, 079, 077, 076, 078
# Vinaphone: 088, 091, 094, 083, 084, 085, 081, 082
# Vietnamobile: 092, 056, 058
# Gmobile: 099, 059
# Itelecom: 087
# Wintel: 055
VN_MOBILE_PREFIXES = {
    "86", "96", "97", "98", "32", "33", "34", "35", "36", "37", "38", "39",
    "89", "90", "93", "70", "79", "77", "76", "78",
    "88", "91", "94", "83", "84", "85", "81", "82",
    "92", "56", "58",
    "99", "59",
    "87", "55"
}

class PhoneNormalizer:
    """
    Production-grade Vietnamese Phone Extractor, Normalizer & Provenance Tracker.
    Converts 09x, 03x, 07x, 08x, 05x, 84x, +84x into canonical E.164 (+84xxxxxxxxx).
    """
    # Regex to find candidate phone patterns in raw text (handling dots, spaces, dashes)
    PHONE_REGEX = re.compile(
        r'(?:\+?84|0)(?:[\s.-]*\d){9}\b'
    )

    @classmethod
    def normalize_single(cls, raw: str) -> Optional[str]:
        """
        Normalizes a single candidate phone string into canonical E.164 (+84...).
        Returns None if the phone is invalid or does not match official VN mobile prefixes.
        """
        if not raw:
            return None
        
        # Strip all delimiters (spaces, dots, dashes, parentheses)
        digits = re.sub(r'[\s.\-()]+', '', raw.strip())
        
        # Handle +84 prefix
        if digits.startswith('+84'):
            core = digits[3:]
        elif digits.startswith('84'):
            core = digits[2:]
        elif digits.startswith('0'):
            core = digits[1:]
        else:
            return None
        
        # Must be exactly 9 digits after country code / leading zero
        if len(core) != 9 or not core.isdigit():
            return None
        
        prefix = core[:2]
        if prefix not in VN_MOBILE_PREFIXES:
            return None
        
        return f"+84{core}"

    @classmethod
    def extract_and_normalize_all(
        cls,
        text: str,
        source_type: str = "SOCIAL_POST",
        source_url: Optional[str] = None,
        captured_at: Optional[datetime] = None
    ) -> List[PhoneProvenance]:
        """
        Finds all valid Vietnamese phone numbers in unstructured text and wraps them
        with immutable provenance metadata.
        """
        if not text:
            return []
        
        captured_time = captured_at or datetime.now(timezone.utc)
        matches = cls.PHONE_REGEX.findall(text)
        results: List[PhoneProvenance] = []
        seen = set()

        for m in matches:
            norm = cls.normalize_single(m)
            if norm and norm not in seen:
                seen.add(norm)
                results.append(
                    PhoneProvenance(
                        raw_phone=m.strip(),
                        normalized_phone=norm,
                        source_type=source_type,
                        source_url=source_url,
                        captured_at=captured_time,
                        is_verified=False
                    )
                )
        return results
