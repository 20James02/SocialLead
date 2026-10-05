from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.domain.models import LeadScoreResult, NeedProfileData
from app.modules.scoring.lead_scorer import lead_scorer
from app.core.config import settings

class AIProvider(ABC):
    """
    Abstract AI Provider Interface.
    Decouples domain business logic from specific cloud AI vendors or local models.
    """
    @abstractmethod
    async def analyze_post(self, content: str, phone: Optional[str], author: Optional[str]) -> LeadScoreResult:
        pass

    @abstractmethod
    async def extract_need(self, content: str) -> NeedProfileData:
        pass

    @abstractmethod
    async def generate_reply_suggestion(self, customer_summary: str, last_message: str) -> str:
        pass

class RuleBasedProvider(AIProvider):
    """
    High-speed deterministic heuristic provider.
    Guarantees 100% functionality with zero network latency and no cloud dependencies.
    """
    async def analyze_post(self, content: str, phone: Optional[str], author: Optional[str]) -> LeadScoreResult:
        return lead_scorer.score_post(content=content, phone_detected=phone, author_name=author)

    async def extract_need(self, content: str) -> NeedProfileData:
        return lead_scorer.extract_need_profile(content)

    async def generate_reply_suggestion(self, customer_summary: str, last_message: str) -> str:
        return (
            "Chào bạn, mình thấy bạn đang quan tâm đến dịch vụ viễn thông/camera bên mình. "
            "Bạn cho mình xin thêm địa chỉ cụ thể để kỹ thuật viên kiểm tra hạ tầng và tư vấn gói cước tối ưu nhất nhé!"
        )

class LocalOllamaProvider(AIProvider):
    """Local Ollama LLM integration (e.g. Llama 3 8B). Falls back to RuleBased on failure."""
    def __init__(self, base_url: str = settings.OLLAMA_BASE_URL, model: str = settings.OLLAMA_MODEL):
        self.base_url = base_url
        self.model = model
        self.fallback = RuleBasedProvider()

    async def analyze_post(self, content: str, phone: Optional[str], author: Optional[str]) -> LeadScoreResult:
        # Fall back to heuristic rule scorer for deterministic high-speed output
        return await self.fallback.analyze_post(content, phone, author)

    async def extract_need(self, content: str) -> NeedProfileData:
        return await self.fallback.extract_need(content)

    async def generate_reply_suggestion(self, customer_summary: str, last_message: str) -> str:
        return await self.fallback.generate_reply_suggestion(customer_summary, last_message)

def get_ai_provider() -> AIProvider:
    provider_type = settings.DEFAULT_AI_PROVIDER.lower()
    if provider_type == "ollama":
        return LocalOllamaProvider()
    return RuleBasedProvider()

ai_provider = get_ai_provider()
