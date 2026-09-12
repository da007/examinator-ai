import asyncio
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery
from app.db.session import get_session_maker, get_engine
from app.models.exam import ExamSession

logger = logging.getLogger(__name__)

async def _anonymize_old_data_logic(years: int = 5):
    """
    Логика анонимизации данных:
    1. Находит сессии старше X лет.
    2. Очищает черновики (current_draft), которые могут содержать личные заметки.
    3. Помечает сессию как архивированную.
    4. Оставляет StudentAnswer для обучения ИИ (без привязки к личности в будущем).
    """
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=years * 365)
    
    async with get_session_maker()() as db:
        # Ищем завершенные сессии, которые еще не анонимизированы
        query = (
            select(ExamSession)
            .where(and_(
                ExamSession.end_time < cutoff_date,
                ExamSession.is_archived == False
            ))
        )
        result = await db.execute(query)
        sessions = result.scalars().all()
        
        if not sessions:
            logger.info("No old sessions found for anonymization.")
            return

        for session in sessions:
            # Очищаем потенциально чувствительные данные
            session.current_draft = {"status": "anonymized_for_privacy"}
            session.is_archived = True
            session.anonymized_at = datetime.now(timezone.utc)
            
            logger.info(f"Session {session.id} has been anonymized.")

        await db.commit()
        logger.info(f"Successfully anonymized {len(sessions)} sessions.")

async def _run_maintenance_with_cleanup():
    try:
        await _anonymize_old_data_logic()
    finally:
        await get_engine().dispose()

@celery.task(name="anonymize_old_sessions_task")
def anonymize_old_sessions_task():
    """
    Периодическая задача (рекомендуется запускать раз в неделю).
    """
    return asyncio.run(_run_maintenance_with_cleanup())

@celery.task(name="cleanup_orphaned_s3_files_task")
def cleanup_orphaned_s3_files_task():
    """
    Заглушка для задачи очистки S3 от файлов удаленных лекций.
    Реализуется аналогично с использованием aioboto3.
    """
    logger.info("Starting S3 cleanup...")
    # Логика: сравнение ключей в S3 с записями в таблице Lecture
    pass