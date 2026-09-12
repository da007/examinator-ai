import uuid
import enum
from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, ForeignKey, Text, Integer, DateTime, func, Boolean, false
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

class SessionStatus(str, enum.Enum):
    ACTIVE = "active"         # Студент в процессе ответа
    PROCESSING = "processing" # Ответы сданы, ожидают оценки ИИ
    COMPLETED = "completed"   # Оценка завершена, результат доступен
    CANCELLED = "cancelled"   # Сессия прервана

class ExamSession(Base):
    """
    Сессия прохождения теста студентом.
    Хранит текущее состояние (черновик) и метаданные сессии.
    """
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lecture_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lecture.id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    status: Mapped[SessionStatus] = mapped_column(
        String(20), default=SessionStatus.ACTIVE, nullable=False, index=True
    )
    
    # Список ID вопросов, выбранных для этой сессии
    question_ids: Mapped[List[str]] = mapped_column(JSONB, nullable=False, server_default='[]')
    
    # Текущий черновик ответов (Auto-save)
    current_draft: Mapped[dict] = mapped_column(JSONB, server_default='{}', nullable=False)
    
    # Optimistic Locking
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    is_suspicious: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    integrity_details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # --- ПОЛЯ ДЛЯ КОМПЛАЕНСА И АРХИВАЦИИ (Sprint 5/6) ---
    is_archived: Mapped[bool] = mapped_column(
        Boolean, 
        default=False, 
        server_default=false() # Вот здесь магия SQLAlchemy
    )
    anonymized_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Связи
    student = relationship("User")
    lecture = relationship("Lecture")
    answers = relationship("StudentAnswer", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<ExamSession(student={self.student_id}, status={self.status}, archived={self.is_archived})>"

class StudentAnswer(Base):
    """
    Зафиксированный ответ студента на конкретный вопрос.
    """
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("examsession.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("question.id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Данные формул
    formula_data: Mapped[dict] = mapped_column(JSONB, server_default='{}', nullable=False)
    
    # Поля для HGC
    ai_score: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    final_score: Mapped[float] = mapped_column(default=0.0, nullable=False)
    confidence_score: Mapped[Optional[float]] = mapped_column(nullable=True)
    
    # Флаги
    is_plagiarism: Mapped[bool] = mapped_column(default=False)
    manual_review_required: Mapped[bool] = mapped_column(default=False)

    session = relationship("ExamSession", back_populates="answers")
    question = relationship("Question")

    def __repr__(self) -> str:
        return f"<StudentAnswer(session={self.session_id}, score={self.final_score})>"