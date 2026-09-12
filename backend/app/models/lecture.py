import enum
import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Enum, ForeignKey, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from .subject import Subject
    from .user import User

class LectureStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    GENERATING = "generating"
    REVIEW_REQUIRED = "review_required"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class Lecture(Base):
    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    
    # Теперь лекция принадлежит дисциплине
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subject.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Кто создал/загрузил (может быть TA или Teacher)
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True
    )
    
    status: Mapped[LectureStatus] = mapped_column(
        Enum(LectureStatus, values_callable=lambda x: [e.value for e in x]), 
        default=LectureStatus.UPLOADED,
        nullable=False
    )
    
    version: Mapped[int] = mapped_column(Integer, default=1)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)

    # [NEW] Академические дедлайны и длительность
    open_from: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deadline_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # FIX-6: лимит времени на выполнение теста (в минутах), NULL = без ограничений
    exam_duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Связи
    subject = relationship("Subject", back_populates="lectures")
    teacher = relationship("User", back_populates="lectures")
    chunks = relationship("Chunk", back_populates="lecture", cascade="all, delete-orphan", passive_deletes=True)

    def __repr__(self) -> str:
        return f"<Lecture(title={self.title}, subject_id={self.subject_id})>"