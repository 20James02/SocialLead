import difflib
import json
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional, List
from sqlalchemy.orm import Session
from app.infrastructure.database.models import (
    PersonDB,
    PersonPhoneDB,
    SocialAccountDB,
    TimelineEventDB,
    NoteDB,
    CustomerDB,
    OpportunityDB,
    PersonLabelDB,
    PermissionDB,
    SavedPostDB,
    ConversationDB,
    CampaignRecipientDB,
    AuditLogDB,
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
    def evaluate_match(cls, person1: PersonDB, person2: PersonDB) -> Tuple[float, str]:
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
            verified1 = {ph.normalized_phone for ph in person1.phones if ph.is_verified}
            verified2 = {ph.normalized_phone for ph in person2.phones if ph.is_verified}
            if verified1 & verified2:
                return 0.95, f"Matching verified canonical phone number: {shared}"
            return (
                0.65,
                f"Matching unverified canonical phone number: {shared} (Manual review required)",
            )

        # 3. Similar name comparison (Strictly capped at 0.40 confidence)
        name_sim = cls.calculate_name_similarity(
            person1.display_name, person2.display_name
        )
        if name_sim >= 0.85:
            return (
                min(0.40, name_sim * 0.4),
                "High name similarity only (Manual review required, auto-merge prohibited)",
            )

        return 0.10, "No strong identity overlap"

    @classmethod
    def merge_persons(
        cls,
        db: Session,
        primary_id: str,
        duplicate_id: str,
        actor: str = "user",
        reason: str = "User confirmed identity merge",
    ) -> PersonDB:
        primary = db.query(PersonDB).filter(PersonDB.id == primary_id).first()
        duplicate = db.query(PersonDB).filter(PersonDB.id == duplicate_id).first()

        if not primary or not duplicate:
            raise ValueError("Both primary and duplicate persons must exist")
        if primary.id == duplicate.id:
            raise ValueError("Cannot merge a person into themselves")
        if duplicate.is_merged:
            raise ValueError("Duplicate person is already merged")
        if primary.is_merged or primary.deleted_at or duplicate.deleted_at:
            raise ValueError("Cannot merge deleted or inactive profiles")

        # 1. Re-link phone numbers
        for phone in list(duplicate.phones):
            phone.person = primary

        # 2. Re-link social accounts (ignoring duplicates)
        existing_socials = {
            (sa.platform, sa.external_id) for sa in primary.social_accounts
        }
        for sa in list(duplicate.social_accounts):
            if (sa.platform, sa.external_id) not in existing_socials:
                sa.person = primary
                existing_socials.add((sa.platform, sa.external_id))
            else:
                db.delete(sa)

        # 3. Re-link Notes & Timeline Events
        for note in list(duplicate.notes):
            note.person = primary
        for event in list(duplicate.timeline_events):
            event.person = primary
        labels = {link.label_id for link in primary.person_labels}
        for link in list(duplicate.person_labels):
            if link.label_id in labels:
                db.delete(link)
            else:
                link.person = primary
                labels.add(link.label_id)
        for saved in db.query(SavedPostDB).filter_by(person_id=duplicate.id):
            saved.person_id = primary.id
        for conv in db.query(ConversationDB).filter_by(linked_person_id=duplicate.id):
            conv.linked_person_id = primary.id
        p_perm = db.query(PermissionDB).filter_by(person_id=primary.id).first()
        d_perm = db.query(PermissionDB).filter_by(person_id=duplicate.id).first()
        if d_perm and not p_perm:
            d_perm.person_id = primary.id
        elif p_perm and d_perm:
            p_perm.opt_out = p_perm.opt_out or d_perm.opt_out
            p_perm.do_not_contact = p_perm.do_not_contact or d_perm.do_not_contact
            p_perm.marketing_allowed = (
                p_perm.marketing_allowed and d_perm.marketing_allowed
            )
            p_perm.zalo_allowed = p_perm.zalo_allowed and d_perm.zalo_allowed
            db.delete(d_perm)

        # 4. Handle Customer promotion & opportunities if duplicate has customer
        if duplicate.customer:
            if not primary.customer:
                duplicate.customer.person = primary
            else:
                # Merge opportunities into primary customer
                old_customer = duplicate.customer
                for opp in list(old_customer.opportunities):
                    opp.customer = primary.customer
                for task in list(old_customer.care_tasks):
                    task.customer = primary.customer
                for recipient in db.query(CampaignRecipientDB).filter_by(
                    customer_id=old_customer.id
                ):
                    recipient.customer_id = primary.customer.id
                # Retain the original need profile and customer as an archived record.
                old_customer.deleted_at = datetime.now(timezone.utc)

        # 5. Mark duplicate as merged
        duplicate.is_merged = True
        duplicate.merged_into_id = primary.id

        # 6. Record Timeline event on primary
        merge_event = TimelineEventDB(
            person_id=primary.id,
            event_type="MERGE_COMPLETED",
            title=f"Hợp nhất hồ sơ từ '{duplicate.display_name}'",
            metadata_json=json.dumps(
                {"duplicate_id": duplicate.id, "reason": reason, "actor": actor},
                ensure_ascii=False,
            ),
        )
        db.add(merge_event)
        db.add(
            AuditLogDB(
                actor=actor,
                action="MERGE_PERSONS",
                target_type="PERSON",
                target_id=primary.id,
                new_value_json=merge_event.metadata_json,
            )
        )
        db.flush()
        if primary.customer:
            from app.infrastructure.database.models import CareTaskDB

            next_task = (
                db.query(CareTaskDB)
                .filter_by(customer_id=primary.customer.id, status="PENDING")
                .filter(CareTaskDB.deleted_at.is_(None))
                .order_by(CareTaskDB.scheduled_at)
                .first()
            )
            primary.customer.next_care_date = (
                next_task.scheduled_at if next_task else None
            )
        db.commit()
        db.refresh(primary)
        return primary


identity_resolver = IdentityResolver()
