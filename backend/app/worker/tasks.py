import asyncio
import logging
import uuid
import aioboto3

from app.core.celery_app import celery
from app.core.config import settings
from app.db.session import get_session_maker, get_engine
from app.models.lecture import Lecture, LectureStatus
from app.models.chunk import Chunk
from app.models.question import Question
from app.models.subject import Subject
from app.services.ingestion.parser import content_parser
from app.services.ingestion.chunker import semantic_chunker
from app.services.ai.embedder import embedder
from app.services.ai.generator import llm_generator

logger = logging.getLogger(__name__)


async def _process_lecture_logic(lecture_id: str, file_key: str):
    """
    Внутренняя асинхронная логика обработки лекции.
    Исправлено: улучшена обработка транзакций и типизация.
    """
    async with get_session_maker()() as db:
        # 1. Получаем объект лекции
        lecture = await db.get(Lecture, uuid.UUID(lecture_id))
        if not lecture:
            logger.error(f"Lecture {lecture_id} not found")
            return

        # Устанавливаем статус начала обработки
        lecture.status = LectureStatus.PROCESSING
        await db.commit()
        await db.refresh(lecture)

        try:
            # 2. Скачиваем файл из S3
            session = aioboto3.Session()
            async with session.client(
                "s3",
                endpoint_url=settings.s3.ENDPOINT,
                aws_access_key_id=settings.s3.ACCESS_KEY,
                aws_secret_access_key=settings.s3.SECRET_KEY,
            ) as s3:
                response = await s3.get_object(
                    Bucket=settings.s3.BUCKET_NAME, Key=file_key
                )
                file_content = await response["Body"].read()

            # 3. Парсинг текста (Модуль CIT)
            extension = file_key.split(".")[-1]
            # content_parser.get_text - асинхронный метод
            text = await content_parser.get_text(file_content, extension)

            # 4. Чанкинг (Модуль SKW)
            # semantic_chunker.split_text - асинхронный метод
            text_chunks = await semantic_chunker.split_text(text)

            lecture.status = LectureStatus.GENERATING
            await db.commit()
            await db.refresh(lecture)

            # 5. Обработка чанков и генерация вопросов (Модуль AGE)
            # FIX-2: считаем упавшие чанки; если все — откатываем в UPLOADED
            total_chunks = len(text_chunks)
            failed_chunks = 0

            for i, chunk_text in enumerate(text_chunks):
                # embedder.get_embeddings - синхронный (на CPU)
                vectors = embedder.get_embeddings([chunk_text])
                vector = vectors[0]

                db_chunk = Chunk(
                    lecture_id=lecture.id,
                    text_content=chunk_text,
                    embedding=vector,
                    order_index=i,
                )
                db.add(db_chunk)
                # Flush необходим, чтобы получить db_chunk.id для связи с вопросами
                await db.flush()

                # Генерация вопросов через LLM
                try:
                    q_data = await llm_generator.generate_questions(chunk_text)

                    for q_text in q_data.questions:
                        ref_data = await llm_generator.generate_reference(q_text, chunk_text)

                        db_question = Question(
                            chunk_id=db_chunk.id,
                            question_text=q_text,
                            reference_answer=ref_data.reference_answer,
                            # Превращаем Pydantic модели тезисов в dict для JSONB
                            key_theses=[t.model_dump() for t in ref_data.key_theses],
                        )
                        db.add(db_question)
                except Exception as llm_err:
                    logger.error(
                        f"LLM generation failed for chunk {i}/{total_chunks} "
                        f"in lecture {lecture_id}: {llm_err}"
                    )
                    failed_chunks += 1
                    continue  # Пропускаем проблемный чанк, продолжаем обработку

            # 6. Проверяем результат генерации
            if total_chunks > 0 and failed_chunks == total_chunks:
                # FIX-2: ВСЕ чанки упали — LLM недоступен (сетевая ошибка / Docker).
                # Откатываем в UPLOADED, чтобы преподаватель мог повторить позже.
                logger.error(
                    f"Lecture {lecture_id}: ALL {total_chunks} chunks failed LLM generation. "
                    f"Check LM_STUDIO_BASE_URL (Docker networking). Reverting to UPLOADED."
                )
                lecture.status = LectureStatus.UPLOADED
                await db.commit()
                return  # Не пробрасываем исключение — воркер не должен ретраиться (сеть, не код)

            # 7. Завершение
            lecture.status = LectureStatus.REVIEW_REQUIRED
            await db.commit()
            logger.info(
                f"Lecture {lecture_id} processed: {total_chunks - failed_chunks}/{total_chunks} "
                f"chunks OK. Status: REVIEW_REQUIRED"
            )

        except Exception as e:
            logger.error(f"Error processing lecture {lecture_id}: {str(e)}", exc_info=True)
            # Откатываем статус, чтобы преподаватель мог попробовать снова
            lecture.status = LectureStatus.UPLOADED
            await db.commit()
            raise e


async def _run_with_cleanup(lecture_id: str, file_key: str):
    """Обертка для гарантированного закрытия соединений."""
    try:
        await _process_lecture_logic(lecture_id, file_key)
    finally:
        # Важно для Celery воркеров, использующих asyncio.run
        await get_engine().dispose()


@celery.task(name="process_lecture_task", bind=True, max_retries=3)
def process_lecture_task(self, lecture_id: str, file_key: str):
    """Точка входа Celery."""
    try:
        return asyncio.run(_run_with_cleanup(lecture_id, file_key))
    except Exception as exc:
        # Экспоненциальный backoff
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))