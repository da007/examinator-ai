import uuid
from datetime import datetime
from typing import Optional
from pydantic import EmailStr, Field

from app.models.user import UserRole
from app.schemas.base import APIModel


class UserBase(APIModel):
    email: EmailStr
    full_name: Optional[str] = Field(None, max_length=255)
    role: UserRole = UserRole.STUDENT
    org_id: uuid.UUID
    is_active: bool = True
    phone: Optional[str] = None
    bio: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="Пароль должен быть не менее 8 символов")


class UserUpdate(APIModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserOut(UserBase):
    id: uuid.UUID
    created_at: datetime
    phone: Optional[str] = None
    bio: Optional[str] = None