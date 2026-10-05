import re
from typing import Optional, List, Tuple
from app.domain.models import (
    LeadScoreResult, ScoreBreakdownItem, NextBestAction,
    NeedType, PropertyType, LeadUrgency, NeedProfileData
)

class LeadScorer:
    """
    Multi-dimensional Rule-Based & Heuristic Lead Scoring Engine.
    Provides complete explainability for Intent, Urgency, Opportunity, Spam,
    Contact Quality, and Overall Lead Score.
    """

    BUYER_PATTERNS = [
        (r'\b(cần|muốn|tìm|hỏi|nhờ)\s+(lắp|bắt|kéo|đăng ký|tư vấn|làm)\b', 40, "Direct buying intent detected"),
        (r'\b(báo giá|giá cả|gói cước|chi phí|bao nhiêu tiền)\b', 30, "Price & package inquiry"),
        (r'\b(mạng nào|nhà mạng nào|wifi nào|camera nào)\s+(ổn|tốt|mạnh|nhanh)\b', 35, "Vendor comparison inquiry"),
        (r'\b(khu vực|địa chỉ|ở đây)\s+(có mạng|kéo được)\b', 25, "Infrastructure availability query"),
        (r'\b(chuyển nhà|nhà mới|mới thuê|vừa dọn)\b', 20, "Relocation context"),
    ]

    URGENCY_PATTERNS = [
        (r'\b(gấp|ngay|hôm nay|luôn|càng sớm càng tốt)\b', 90, LeadUrgency.HIGH, "Immediate installation requested"),
        (r'\b(ngày mai|mai|cuối tuần|tuần này)\b', 65, LeadUrgency.MEDIUM, "Short-term installation timeline"),
        (r'\b(tuần sau|tháng tới|chuẩn bị|tham khảo)\b', 35, LeadUrgency.LOW, "Longer exploration timeline"),
    ]

    OPPORTUNITY_PATTERNS = [
        (r'\b(camera|cam)\b.*?\b(wifi|mạng|internet)\b|\b(wifi|mạng|internet)\b.*?\b(camera|cam)\b', 45, "Combo requirement (WiFi + Camera)"),
        (r'\b(\d+)\s*(mắt|chiếc|con|cái)\s*cam\b', 35, "Multi-camera bulk installation"),
        (r'\b(nhà\s*(mình\s*)?(\d+)\s*tầng|biệt thự|công ty|văn phòng|quán|shop|khách sạn)\b', 35, "Commercial or multi-story property"),
    ]

    SPAM_PATTERNS = [
        (r'\b(tuyển dụng|việc làm|ctv|hoa hồng|thu nhập|lương)\b', 80, "Recruitment / job posting"),
        (r'\b(thanh lý|xả kho|giá sỉ|bán lẻ|đại lý|nhập hàng)\b', 75, "E-commerce wholesale / liquidator"),
        (r'\b(cho vay|tài chính|tín dụng|nợ xấu|lãi suất)\b', 90, "Financial loan offer"),
        (r'\b(cờ bạc|tài xỉu|casino|cá cược)\b', 95, "Gambling content"),
        (r'\b(inbox em|ib em|liên hệ em|inbox shop)\b', 40, "Seller self-promotion"),
    ]

    @classmethod
    def extract_need_profile(cls, text: str) -> NeedProfileData:
        lower = text.lower()
        has_wifi = bool(re.search(r'\b(wifi|mạng|internet|cáp quang|fpt|viettel|vnpt)\b', lower))
        has_camera = bool(re.search(r'\b(camera|cam|đầu ghi|mắt cam)\b', lower))
        has_tv = bool(re.search(r'\b(truyền hình|tivi|tv box)\b', lower))

        if (has_wifi and has_camera) or (has_wifi and has_tv):
            need = NeedType.COMBO
        elif has_camera:
            need = NeedType.CAMERA
        elif has_tv:
            need = NeedType.TV
        elif has_wifi:
            need = NeedType.WIFI
        else:
            need = NeedType.OTHER

        # Property type
        prop = PropertyType.UNKNOWN
        if re.search(r'\b(chung cư|căn hộ|tập thể)\b', lower):
            prop = PropertyType.APARTMENT
        elif re.search(r'\b(phòng trọ|nhà trọ|sinh viên|thuê trọ)\b', lower):
            prop = PropertyType.RENTAL
        elif re.search(r'\b(quán|cửa hàng|shop|tiệm|spa)\b', lower):
            prop = PropertyType.STORE
        elif re.search(r'\b(văn phòng|công ty|doanh nghiệp)\b', lower):
            prop = PropertyType.OFFICE
        elif re.search(r'\b(nhà riêng|nhà dân|nhà\s*(mình\s*)?(\d+)\s*tầng|biệt thự)\b', lower):
            prop = PropertyType.HOUSE

        # Location heuristic
        province = None
        if re.search(r'\b(hà nội|hn|ba đình|cầu giấy|đống đa|hà đông)\b', lower):
            province = "Hà Nội"
        elif re.search(r'\b(hồ chí minh|tphcm|hcm|sài gòn|thủ đức)\b', lower):
            province = "TP. Hồ Chí Minh"
        elif re.search(r'\b(thái nguyên)\b', lower):
            province = "Thái Nguyên"
        elif re.search(r'\b(đà nẵng)\b', lower):
            province = "Đà Nẵng"

        # Urgency
        urgency = LeadUrgency.MEDIUM
        for pat, _, urg_level, _ in cls.URGENCY_PATTERNS:
            if re.search(pat, lower):
                urgency = urg_level
                break

        return NeedProfileData(
            need_type=need,
            property_type=prop,
            province=province,
            urgency=urgency
        )

    @classmethod
    def score_post(
        cls,
        content: str,
        phone_detected: Optional[str] = None,
        author_name: Optional[str] = None,
        is_soft_blacklisted: bool = False
    ) -> LeadScoreResult:
        breakdown: List[ScoreBreakdownItem] = []
        lower = content.lower()

        # 1. Intent Score
        intent_score = 0
        for pat, pts, reason in cls.BUYER_PATTERNS:
            if re.search(pat, lower):
                intent_score += pts
                breakdown.append(ScoreBreakdownItem(category="Intent", points=pts, reason=reason))
        intent_score = min(100, intent_score)

        # 2. Urgency Score
        urgency_score = 30 # Default baseline
        for pat, score, _, reason in cls.URGENCY_PATTERNS:
            if re.search(pat, lower):
                urgency_score = score
                breakdown.append(ScoreBreakdownItem(category="Urgency", points=score, reason=reason))
                break

        # 3. Opportunity Score
        opportunity_score = 30 # Baseline
        for pat, pts, reason in cls.OPPORTUNITY_PATTERNS:
            if re.search(pat, lower):
                opportunity_score += pts
                breakdown.append(ScoreBreakdownItem(category="Opportunity", points=pts, reason=reason))
        opportunity_score = min(100, opportunity_score)

        # 4. Spam Score
        spam_score = 0
        for pat, pts, reason in cls.SPAM_PATTERNS:
            if re.search(pat, lower):
                spam_score += pts
                breakdown.append(ScoreBreakdownItem(category="Spam", points=-pts, reason=reason))
        spam_score = min(100, spam_score)

        # 5. Contact Quality Score
        contact_quality = 10
        if phone_detected:
            contact_quality += 50
            breakdown.append(ScoreBreakdownItem(category="Contact Quality", points=50, reason="Valid verified phone present"))
        if author_name and len(author_name.strip()) > 2:
            contact_quality += 25
            breakdown.append(ScoreBreakdownItem(category="Contact Quality", points=25, reason="Legitimate author name identified"))
        contact_quality = min(100, contact_quality)

        # 6. Overall Composite Score
        composite = (
            (intent_score * 0.35) +
            (urgency_score * 0.20) +
            (opportunity_score * 0.25) +
            (contact_quality * 0.20) -
            (spam_score * 0.60)
        )
        
        if is_soft_blacklisted:
            composite -= 80
            breakdown.append(ScoreBreakdownItem(category="Blacklist", points=-80, reason="Soft Blacklist entity penalty applied"))

        overall = max(0, min(100, int(round(composite))))

        # 7. Next Best Action determination
        if spam_score >= 60:
            action = NextBestAction.IGNORE
            action_reason = "High probability spam or seller advertisement"
        elif phone_detected and (urgency_score >= 70 or overall >= 75):
            action = NextBestAction.CALL_NOW
            action_reason = "High intent & urgent timeline with verified phone ready for outreach"
        elif overall >= 55 and not phone_detected:
            action = NextBestAction.MESSAGE
            action_reason = "Strong purchasing interest detected; initiate outreach to obtain phone"
        elif urgency_score >= 50 and overall >= 40:
            action = NextBestAction.FOLLOW_UP
            action_reason = "Moderate interest with active timeframe; schedule check-in"
        elif overall >= 30:
            action = NextBestAction.NEED_MORE_INFO
            action_reason = "Inquiry requires location or requirement clarification"
        else:
            action = NextBestAction.WAIT
            action_reason = "Low purchase probability; observe for further activity"

        return LeadScoreResult(
            intent_score=intent_score,
            urgency_score=urgency_score,
            opportunity_score=opportunity_score,
            spam_score=spam_score,
            contact_quality_score=contact_quality,
            overall_lead_score=overall,
            breakdown=breakdown,
            next_best_action=action,
            action_reason=action_reason
        )

lead_scorer = LeadScorer()
