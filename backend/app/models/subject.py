import uuid
from typing import TYPE_CHECKING
from sqlalchemy import String, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from .user import User
    from .lecture import Lecture
    from .group import Group

class Subject(Base):
    """
    Дисциплина (Курс). Принадлежит организации и имеет ответственного профессора.
    """
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    
    # Профессор, ответственный за курс
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("user.id", ondelete="RESTRICT"),
        nullable=False
    )

    # Связи
    teacher = relationship("User", backref="managed_subjects")
    lectures = relationship("Lecture", back_populates="subject", cascade="all, delete-orphan")
    
    # Связь с группами через ассоциативную таблицу в group.py
    groups = relationship("Group", secondary="group_subjects", back_populates="subjects")

    def __repr__(self) -> str:
        return f"<Subject(name={self.name}, org_id={self.org_id})>"