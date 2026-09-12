import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import Field

from app.schemas.base import APIModel


class ThesisSchema(APIModel):
    """Схема тезиса для API (используется внутри вопроса)."""
    text: str
    importance: int = Field(..., ge=1, le=3)


class QuestionBase(APIModel):
    question_text: str
    reference_answer: str
    key_theses: List[ThesisSchema]
    difficulty: str = "medium"
    question_type: str = "open_ended"


class QuestionCreate(QuestionBase):
    chunk_id: uuid.UUID


class QuestionUpdate(APIModel):
    """Схема для частичного обновления вопроса преподавателем."""
    question_text: Optional[str] = None
    reference_answer: Optional[str] = None
    key_theses: Optional[List[ThesisSchema]] = None
    difficulty: Optional[str] = None
    question_type: Optional[str] = None


class QuestionRead(QuestionBase):
    id: uuid.UUID
    chunk_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class QuestionGroupedByChunk(APIModel):
    """Схема для отображения вопросов, сгруппированных по контексту (чанку)."""
    chunk_id: uuid.UUID
    chunk_text: str
    questions: List[QuestionRead]