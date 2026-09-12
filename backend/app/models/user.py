import enum
import uuid
from typing import Optional

from sqlalchemy import String, Enum, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class UserRole(str, enum.Enum):
    """
    Роли пользователей в системе.
    Используем str-mixin для удобной сериализации в JSON.
    """
    ADMIN = "admin"      # Глобальный администратор
    TEACHER = "teacher"  # Профессор (владелец дисциплины)
    TA = "ta"            # Ассистент (проверка апелляций, просмотр аналитики)
    STUDENT = "student"  # Студент


class User(Base):
    """
    Модель пользователя с поддержкой изоляции данных (org_id).
    """
    email: Mapped[str] = mapped_column(
        String(255), 
        unique=True, 
        index=True, 
        nullable=False,
        comment="Электронная почта (логин)"
    )
    
    hashed_password: Mapped[str] = mapped_column(
        String(255), 
        nullable=False,
        comment="Хеш пароля"
    )
    
    full_name: Mapped[Optional[str]] = mapped_column(
        String(255), 
        nullable=True,
        comment="ФИО пользователя"
    )
    
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole, 
            name="user_role", 
            create_type=True,
            values_callable=lambda x: [e.value for e in x]
        ),
        default=UserRole.STUDENT,
        nullable=False,
        index=True,
        comment="Роль пользователя в системе"
    )
    
    lectures: Mapped[list["Lecture"]] = relationship(
        "Lecture", 
        back_populates="teacher", 
        cascade="all, delete-orphan"
    )
    
    # Ключевое поле для Multi-tenancy
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        index=True,
        nullable=False,
        comment="ID организации или группы для изоляции данных"
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean, 
        default=True,
        comment="Флаг активности аккаунта"
    )

    is_superuser: Mapped[bool] = mapped_column(
        Boolean, 
        default=False,
        comment="Флаг суперпользователя (доступ ко всем org_id)"
    )
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="Телефон")
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="О себе / Регалии")

    def __repr__(self) -> str:
        return f"<User(email={self.email}, role={self.role}, org_id={self.org_id})>"