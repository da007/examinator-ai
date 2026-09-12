import uuid
import enum
from typing import Optional

from sqlalchemy import String, ForeignKey, Text, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

class AppealStatus(str, enum.Enum):
    PENDING = "pending"   # Подана студентом, ожидает рассмотрения
    ACCEPTED = "accepted" # Одобрена преподавателем, оценка изменена
    REJECTED = "rejected" # Отклонена преподавателем

class StudentAppeal(Base):
    """
    Модель апелляции студента на результаты экзаменационной сессии.
    Позволяет реализовать Human-in-the-loop контроль над ИИ.
    """
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("examsession.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("user.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )

    # Причина апелляции (заполняется студентом)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    
    status: Mapped[AppealStatus] = mapped_column(
        Enum(AppealStatus, name="appeal_status"),
        default=AppealStatus.PENDING,
        nullable=False,
        index=True
    )

    # Комментарий преподавателя при рассмотрении
    teacher_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Связи
    session: Mapped["ExamSession"] = relationship("ExamSession", backref="appeals")
    student: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return f"<StudentAppeal(session={self.session_id}, status={self.status})>"