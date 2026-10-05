from datetime import datetime, timezone, timedelta, time
from typing import Tuple, Optional
from app.infrastructure.database.models import PermissionDB

class ConsentGovernance:
    """
    Enforces Platform Safety, Privacy & Messaging Safety Policies.
    Evaluates:
      - Permission flags (marketing_allowed, opt_out, do_not_contact)
      - Frequency cap (e.g. max 1 message every 7 days)
      - Quiet hours enforcement (e.g. 20:00 to 08:00 prohibited)
    """

    QUIET_HOURS_START = time(20, 0) # 8:00 PM
    QUIET_HOURS_END = time(8, 0)    # 8:00 AM

    @classmethod
    def is_in_quiet_hours(cls, check_time: Optional[datetime] = None) -> bool:
        t = (check_time or datetime.now()).time()
        if cls.QUIET_HOURS_START <= t or t <= cls.QUIET_HOURS_END:
            return True
        return False

    @classmethod
    def can_send_campaign(
        cls,
        permission: Optional[PermissionDB],
        last_contacted_at: Optional[datetime],
        frequency_cap_days: int = 7,
        current_time: Optional[datetime] = None
    ) -> Tuple[bool, str]:
        now = current_time or datetime.now(timezone.utc)

        # 1. Check Quiet Hours
        if cls.is_in_quiet_hours(now):
            return False, "Blocked: Current time falls within quiet hours (20:00 - 08:00)"

        # 2. Check Permission Records
        if not permission:
            return False, "Blocked: No explicit marketing consent record found"
        if permission.do_not_contact:
            return False, "Blocked: Contact explicitly marked as DO_NOT_CONTACT"
        if permission.opt_out:
            return False, "Blocked: Contact has opted out of marketing communications"
        if not permission.marketing_allowed:
            return False, "Blocked: Marketing permission flag is not enabled"

        # 3. Check Frequency Cap
        if last_contacted_at:
            if last_contacted_at.tzinfo is None:
                last_contacted_at = last_contacted_at.replace(tzinfo=timezone.utc)
            min_allowed_date = last_contacted_at + timedelta(days=frequency_cap_days)
            if now < min_allowed_date:
                days_left = (min_allowed_date - now).days + 1
                return False, f"Blocked: Frequency cap violation (Must wait {days_left} more days)"

        return True, "Eligible for messaging"

consent_governance = ConsentGovernance()
