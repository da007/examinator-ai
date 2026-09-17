import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, declared_attr


class Base(DeclarativeBase):
    """
    Базовый класс для всех моделей системы.
    Использует возможности SQLAlchemy 2.0 для строгой типизации.
    """
    id: Any
    __name__: str

    # Автоматически генерируем имя таблицы на основе имени класса (в нижнем регистре)
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

    # Первичный ключ UUID для всех таблиц
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        index=True
    )
    
    # Таймстампы для аудита (когда создана и когда изменена запись)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        comment="Дата и время создания записи"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(),
        comment="Дата и время последнего обновления"
    )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id})>"