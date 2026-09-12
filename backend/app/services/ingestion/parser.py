import io
import logging
from typing import Optional
import docx
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class ContentParser:
    """
    Сервис для извлечения текста из различных форматов файлов.
    Реализует модуль CIT (Content Ingestion Tool) из TDD.
    """

    @staticmethod
    async def parse_txt(file_content: bytes) -> str:
        """Парсинг текстовых файлов с автоматическим определением кодировки."""
        encodings = ['utf-8', 'cp1251', 'latin-1']
        for encoding in encodings:
            try:
                return file_content.decode(encoding)
            except UnicodeDecodeError:
                continue
        raise HTTPException(status_code=400, detail="Не удалось определить кодировку .txt файла")

    @staticmethod
    async def parse_docx(file_content: bytes) -> str:
        """Парсинг документов Microsoft Word."""
        try:
            doc = docx.Document(io.BytesIO(file_content))
            full_text = []
            for para in doc.paragraphs:
                if para.text.strip():
                    full_text.append(para.text.strip())
            return "\n".join(full_text)
        except Exception as e:
            logger.error(f"Ошибка при парсинге DOCX: {e}")
            raise HTTPException(status_code=400, detail="Ошибка при чтении .docx файла")

    async def get_text(self, file_content: bytes, extension: str) -> str:
        """Основной метод для извлечения текста на основе расширения."""
        ext = extension.lower().strip('.')
        
        if ext == 'txt':
            text = await self.parse_txt(file_content)
        elif ext in ['docx', 'doc']:
            text = await self.parse_docx(file_content)
        else:
            raise HTTPException(status_code=400, detail=f"Формат .{ext} не поддерживается")

        return self._clean_text(text)

    def _clean_text(self, text: str) -> str:
        """
        Очистка текста с сохранением структуры абзацев (\n\n).
        FIX-1: убираем только пробелы внутри строк, не трогая переносы,
        чтобы SemanticChunker мог делить по \n\n (абзацам).
        """
        import re as _re
        lines = text.splitlines()
        cleaned = []
        prev_blank = False
        for line in lines:
            stripped = line.strip()
            if not stripped:
                # Схлопываем несколько пустых строк в одну
                if not prev_blank:
                    cleaned.append("")
                prev_blank = True
            else:
                # Убираем множественные пробелы внутри строки
                cleaned.append(_re.sub(r"[^\S\n]+", " ", stripped))
                prev_blank = False
        return "\n".join(cleaned).strip()

# Синглтон для использования в сервисах и воркерах
content_parser = ContentParser()