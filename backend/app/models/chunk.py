import uuid
from sqlalchemy import String, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector # Специальный тип для векторов

from app.db.base_class import Base

class Chunk(Base):
    """
    Таблица для хранения фрагментов лекций и их векторных представлений.
    """
    lecture_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("lecture.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Сам текст фрагмента
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Векторное представление (эмбеддинг). 
    # Для модели multilingual-e5-small размерность составляет 384.
    embedding: Mapped[Vector] = mapped_column(Vector(384), nullable=True)
    
    # Порядковый номер чанка в лекции (для восстановления контекста)
    order_index: Mapped[int] = mapped_column(nullable=False, default=0)

    # Связь с лекцией
    lecture = relationship("Lecture", back_populates="chunks")

    def __repr__(self) -> str:
        return f"<Chunk(lecture_id={self.lecture_id}, order={self.order_index})>"