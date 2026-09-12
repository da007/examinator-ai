import uuid
from sqlalchemy import String, ForeignKey, Text, Float, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

class Question(Base):
    """
    Модель для хранения сгенерированных вопросов, эталонов и тезисов.
    Реализует модули AGE (QGen, AGen, TGen) из TDD.
    """
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("chunk.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Эталонный ответ (Reference Answer)
    reference_answer: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Ключевые тезисы (Key Theses) храним в JSONB для гибкости и быстрого поиска.
    # Структура: [{"text": "...", "importance": 3, "embedding": [...]}]
    key_theses: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    
    # Сложность вопроса (может пригодиться для Topic-based Sampling)
    difficulty: Mapped[str] = mapped_column(String(20), default="medium")
    
    # Тип вопроса (по умолчанию open_ended, согласно TDD)
    question_type: Mapped[str] = mapped_column(String(50), default="open_ended")

    # Связь с чанком
    chunk = relationship("Chunk", backref="questions")

    def __repr__(self) -> str:
        return f"<Question(id={self.id}, type={self.question_type})>"