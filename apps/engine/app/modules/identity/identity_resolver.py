import difflib
from typing import Dict, Any, Tuple, Optional, List
from sqlalchemy.orm import Session
from app.infrastructure.database.models import (
    PersonDB, PersonPhoneDB, SocialAccountDB, TimelineEventDB, NoteDB, CustomerDB, OpportunityDB
)
from app.domain.models import PlatformType

class IdentityResolver:
    """
    Identity Resolution & Merge Engine.
    Rules:
      - Common verified phone: High confidence match (95%+).
      - Common social account (platform + external_id): 100% match.
      - Similar name alone: NEVER auto-merge (confidence capped at 40%).
    """

    @staticmethod
    def calculate_name_similarity(name1: str, name2: str) -> float:
        if not name1 or not name2:
            return 0.0
        n1 = name1.strip().lower()
        n2 = name2.strip().lower()
        return difflib.SequenceMatcher(None, n1, n2).ratio()

    @classmethod
    def evaluate_match(
        cls,
        person1: PersonDB,
        person2: PersonDB
    ) -> Tuple[float, str]:
        """
        Calculates similarity score (0.0 to 1.0) and match reason.
        """
        # 1. Check for shared social accounts
        p1_socials = {(sa.platform, sa.external_id) for sa in person1.social_accounts}
        p2_socials = {(sa.platform, sa.external_id) for sa in person2.social_accounts}
        if p1_socials and p2_socials and (p1_socials & p2_socials):
            return 1.0, "Identical verified social account ID"

        # 2. Check for shared normalized phone numbers
        p1_phones = {ph.normalized_phone for ph in person1.phones}
        p2_phones = {ph.normalized_phone for ph in person2.phones}
        if p1_phones and p2_phones and (p1_phones & p2_phones):
            shared = list(p1_phones & p2_phones)[0]
            return 0.95, f"Matching canonical phone number: {shared}"

        # 3. Similar name comparison (Strictly capped at 0.40 confidence)
        name_sim = cls.calculate_name_similarity(person1.display_name, person2.display_name)
        if name_sim >= 0.85:
            return min(0.40, name_sim * 0.4), "High name similarity only (Manual review required, auto-merge prohibited)"

        return 0.10, "No strong identity overlap"

    @classmethod
    def merge_persons(
        cls,
        db: Session,
        primary_id: str,
        duplicate_id: str,
        actor: str = "user",
        reason: str = "User confirmed identity merge"
    ) -> PersonDB:
        primary = db.query(PersonDB).filter(PersonDB.id == primary_id).first()
        duplicate = db.query(PersonDB).filter(PersonDB.id == duplicate_id).first()

        if not primary or not duplicate:
            raise ValueError("Both primary and duplicate persons must exist")
        if primary.id == duplicate.id:
            raise ValueError("Cannot merge a person into themselves")
        if duplicate.is_merged:
            raise ValueError("Duplicate person is already merged")

        # 1. Re-link phone numbers
        for phone in duplicate.phones:
            phone.person_id = primary.id

        # 2. Re-link social accounts (ignoring duplicates)
        existing_socials = {(sa.platform, sa.external_id) for sa in primary.social_accounts}
        for sa in list(duplicate.social_accounts):
            if (sa.platform, sa.external_id) not in existing_socials:
                sa.person_id = primary.id
                existing_socials.add((sa.platform, sa.external_id))
            else:
                db.delete(sa)

        # 3. Re-link Notes & Timeline Events
        for note in duplicate.notes:
            note.person_id = primary.id
        for event in duplicate.timeline_events:
            event.person_id = primary.id

        # 4. Handle Customer promotion & opportunities if duplicate has customer
        if duplicate.customer:
            if not primary.customer:
                duplicate.customer.person_id = primary.id
            else:
                # Merge opportunities into primary customer
                for opp in duplicate.customer.opportunities:
                    opp.customer_id = primary.customer.id
                db.delete(duplicate.customer)

        # 5. Mark duplicate as merged
        duplicate.is_merged = True
        duplicate.merged_into_id = primary.id

        # 6. Record Timeline event on primary
        merge_event = TimelineEventDB(
            person_id=primary.id,
            event_type="MERGE_COMPLETED",
            title=f"Hợp nhất hồ sơ từ '{duplicate.display_name}'",
            metadata_json=f'{{"duplicate_id": "{duplicate.id}", "reason": "{reason}", "actor": "{actor}"}}'
        )
        db.add(merge_event)
        db.commit()
        db.refresh(primary)
        return primary

identity_resolver = IdentityResolver()
