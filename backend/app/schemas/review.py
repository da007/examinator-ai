import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import Field
from app.models.appeal import AppealStatus
from app.schemas.base import APIModel

class AppealCreate(APIModel):
    """Схема создания апелляции. Принимает { sessionId, reason }"""
    session_id: uuid.UUID
    reason: str = Field(..., min_length=10, max_length=1000)

class AppealRead(APIModel):
    id: uuid.UUID
    session_id: uuid.UUID
    student_id: uuid.UUID
    reason: str
    status: AppealStatus
    student_name: Optional[str] = None   # Добавлено
    student_email: Optional[str] = None  # Добавлено
    teacher_comment: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class AppealResolve(APIModel):
    status: AppealStatus
    teacher_comment: str = Field(..., min_length=5)

class ManualAnswerCorrection(APIModel):
    answer_id: uuid.UUID
    new_score: float = Field(..., ge=0.0, le=1.0)
    teacher_comment: Optional[str] = None

class PendingReviewList(APIModel):
    session_id: uuid.UUID
    student_name: str
    lecture_title: str
    avg_confidence: float
    created_at: datetime