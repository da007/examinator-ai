import logging
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

class SemanticChunker:
    """
    Сервис для разбиения текста на смысловые фрагменты.
    Реализует модуль SKW (Semantic Knowledge Warehouse) из TDD.
    """
    def __init__(
        self, 
        chunk_size: int = 1000,  # Оптимально для модели E5 и контекста LLM
        chunk_overlap: int = 200  # Перекрытие для сохранения связности контекста
    ):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            # Приоритет разделителей: абзацы -> предложения -> пробелы
            separators=["\n\n", "\n", ". ", " ", ""],
            is_separator_regex=False,
        )

    async def split_text(self, text: str) -> List[str]:
        """
        Разбивает текст на чанки. 
        Удаляет слишком короткие фрагменты (мусор), которые могли остаться после парсинга.
        """
        try:
            chunks = self.splitter.split_text(text)
            # Фильтруем пустые или слишком короткие чанки (менее 100 символов)
            # так как из них сложно извлечь качественный вопрос.
            valid_chunks = [c.strip() for c in chunks if len(c.strip()) > 100]
            
            logger.info(f"Текст разбит на {len(valid_chunks)} чанков.")
            return valid_chunks
        except Exception as e:
            logger.error(f"Ошибка при чанкинге текста: {e}")
            return []

# Синглтон с настройками по умолчанию
semantic_chunker = SemanticChunker()