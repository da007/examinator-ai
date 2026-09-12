import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import ConfigDict, Field, field_validator

from app.models.exam import SessionStatus
from app.schemas.base import APIModel # Используем наш базовый класс с поддержкой camelCase

# --- Вспомогательные схемы ---

class FormulaData(APIModel):
    """Схема для хранения LaTeX формул в ответе."""
    raw: str = ""
    latex: str = ""
    normalized: Optional[str] = None

class QuestionShort(APIModel):
    """
    Упрощенная схема вопроса для студента.
    """
    id: uuid.UUID
    question_text: str
    question_type: str
    difficulty: str

# --- Схемы Сессии ---

class ExamSessionCreate(APIModel):
    """Запрос на начало нового теста. Принимает { lectureId: "..." }"""
    lecture_id: uuid.UUID

class ExamSessionRead(APIModel):
    """Полная информация о сессии для фронтенда."""
    id: uuid.UUID
    lecture_id: uuid.UUID
    status: SessionStatus
    version: int
    start_time: datetime
    end_time: Optional[datetime] = None
    
    # Список вопросов, которые попали в этот тест
    questions: List[QuestionShort] = []
    # Текущее состояние черновика
    current_draft: Dict[str, Any] = {}

class ExamSessionUpdateDraft(APIModel):
    """
    Схема для автосохранения (PATCH).
    Реализует Optimistic Locking.
    """
    version: int
    current_draft: Dict[str, Any]

class ExamSessionSubmit(APIModel):
    """Запрос на финальную сдачу теста."""
    final_draft: Optional[Dict[str, Any]] = None

# --- Схемы Ответов (для результатов) ---

class StudentAnswerRead(APIModel):
    id: uuid.UUID
    question_id: uuid.UUID
    answer_text: str
    formula_data: FormulaData
    
    final_score: Optional[float] = None
    confidence_score: Optional[float] = None
    reference_answer: Optional[str] = None
    
    # Позволяет читать из ai_score в БД и отдавать как ai_explanation
    ai_explanation: Optional[str] = Field(None, validation_alias="ai_score")
    
    @field_validator("ai_explanation", mode="before")
    @classmethod
    def extract_explanation(cls, v: Any) -> Optional[str]:
        if isinstance(v, dict):
            return v.get("explanation")
        return None

class ExamResultRead(APIModel):
    """Схема итогового результата всего экзамена."""
    session_id: uuid.UUID
    status: SessionStatus
    total_score: Optional[float] = None
    answers: List[StudentAnswerRead]