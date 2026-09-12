import uuid
from datetime import datetime
from typing import Optional
from pydantic import Field

from app.models.lecture import LectureStatus
from app.schemas.base import APIModel


class LectureBase(APIModel):
    title: str = Field(..., min_length=3, max_length=255)
    org_id: uuid.UUID
    subject_id: uuid.UUID  # <-- ДОБАВЛЕНО

class LectureCreate(LectureBase):
    teacher_id: Optional[uuid.UUID] = None
    open_from: Optional[datetime] = None        # FIX-6
    deadline_at: Optional[datetime] = None      # FIX-6
    exam_duration_minutes: Optional[int] = None # FIX-6

class LectureRead(LectureBase):
    id: uuid.UUID
    teacher_id: Optional[uuid.UUID] # Сделали Optional, так как SET NULL в БД
    status: LectureStatus
    version: int
    open_from: Optional[datetime] = None
    deadline_at: Optional[datetime] = None
    exam_duration_minutes: Optional[int] = None  # FIX-6
    created_at: datetime
    updated_at: datetime


class LectureUpdate(APIModel):
    title: Optional[str] = None
    status: Optional[LectureStatus] = None
    version: Optional[int] = None
    open_from: Optional[datetime] = None
    deadline_at: Optional[datetime] = None
    exam_duration_minutes: Optional[int] = None  # FIX-6


class LectureShort(APIModel):
    id: uuid.UUID
    title: str
    status: LectureStatus
    created_at: datetime