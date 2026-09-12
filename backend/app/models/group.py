import uuid
from sqlalchemy import String, ForeignKey, Table, Column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

# 1. Таблица связи Группы и Студентов (Many-to-Many)
group_students = Table(
    "group_students",
    Base.metadata,
    Column("group_id", UUID(as_uuid=True), ForeignKey("group.id", ondelete="CASCADE"), primary_key=True),
    Column("student_id", UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), primary_key=True),
)

# 2. Таблица связи Группы и Дисциплины (Many-to-Many) - [NEW для Спринта 6]
group_subjects = Table(
    "group_subjects",
    Base.metadata,
    Column("group_id", UUID(as_uuid=True), ForeignKey("group.id", ondelete="CASCADE"), primary_key=True),
    Column("subject_id", UUID(as_uuid=True), ForeignKey("subject.id", ondelete="CASCADE"), primary_key=True),
)

class Group(Base):
    """
    Модель учебной группы.
    """
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Преподаватель, ответственный за группу
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("user.id"),
        nullable=False
    )
    
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)

    # Связи
    students = relationship("User", secondary=group_students, backref="student_groups")
    subjects = relationship("Subject", secondary=group_subjects, back_populates="groups")

    def __repr__(self) -> str:
        return f"<Group(name={self.name}, org_id={self.org_id})>"