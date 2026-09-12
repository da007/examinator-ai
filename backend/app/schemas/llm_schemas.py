from typing import List, Optional
from pydantic import Field

from app.schemas.base import APIModel


class Thesis(APIModel):
    text: str = Field(..., description="Текст тезиса")
    importance: int = Field(..., ge=1, le=3)


class QuestionsData(APIModel):
    questions: List[str]


class ReferenceData(APIModel):
    reference_answer: str
    key_theses: List[Thesis]


class AIResultLabel(APIModel):
    """Схема для Layer 4 (Semantic Arbitrage) нашего HGC."""
    label: str = Field(..., pattern="^(correct|partially_correct|wrong)$")
    confidence_delta: float = Field(..., ge=0, le=1, description="Уверенность модели в этой метке")
    explanation: Optional[str] = None