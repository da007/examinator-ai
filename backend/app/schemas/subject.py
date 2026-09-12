import uuid
from datetime import datetime
from typing import Optional
from app.schemas.base import APIModel

class SubjectBase(APIModel):
    name: str
    description: Optional[str] = None

class SubjectCreate(SubjectBase):
    org_id: uuid.UUID
    teacher_id: uuid.UUID  # Ответственный за предмет

class SubjectTeacherInfo(APIModel):
    full_name: str
    email: str
    phone: Optional[str] = None
    bio: Optional[str] = None

class SubjectRead(SubjectBase):
    id: uuid.UUID
    org_id: uuid.UUID
    teacher_id: uuid.UUID
    teacher_info: Optional[SubjectTeacherInfo] = None # Добавлено
    created_at: datetime
    updated_at: datetime