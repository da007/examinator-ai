import uuid
from typing import List, Optional, Sequence
from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.question import Question
from app.models.chunk import Chunk
from app.models.lecture import Lecture, LectureStatus
from app.schemas.question import QuestionUpdate, QuestionCreate


class QuestionService:
    async def get_questions_by_lecture(
        self, db: AsyncSession, lecture_id: uuid.UUID, org_id: uuid.UUID | None = None
    ) -> Sequence[Question]:
        """Получает все вопросы для лекции с полной подгрузкой связей."""
        query = (
            select(Question)
            .join(Chunk, Question.chunk_id == Chunk.id)
            .join(Lecture, Chunk.lecture_id == Lecture.id)
            .where(Chunk.lecture_id == lecture_id)
        )

        if org_id is not None:
            query = query.where(Lecture.org_id == org_id)

        query = (
            query
            .options(
                joinedload(Question.chunk).joinedload(Chunk.lecture)
            )
            .order_by(Chunk.order_index, Question.created_at)
        )
        result = await db.execute(query)
        return result.scalars().all()

    async def create_question(self, db: AsyncSession, *, obj_in: QuestionCreate) -> Question:
        db_obj = Question(**obj_in.model_dump())
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_question_safe(
        self, db: AsyncSession, question_id: uuid.UUID, org_id: uuid.UUID
    ) -> Optional[Question]:
        """Получает вопрос с проверкой прав организации."""
        query = (
            select(Question)
            .join(Chunk)
            .join(Lecture)
            .where(
                and_(
                    Question.id == question_id,
                    Lecture.org_id == org_id
                )
            )
            .options(joinedload(Question.chunk))
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def update_question(
        self, db: AsyncSession, *, db_obj: Question, obj_in: QuestionUpdate
    ) -> Question:
        """
        Обновление вопроса.
        """
        # Pydantic v2 model_dump() автоматически превращает вложенные списки схем в списки словарей.
        # Поэтому update_data["key_theses"] — это уже готовый list[dict], пригодный для JSONB.
        update_data = obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        await db.commit()
        
        # Обязательно делаем refresh, чтобы асинхронно подтянуть новое значение updated_at из БД
        # Это предотвратит ошибку MissingGreenlet при формировании ответа сервером.
        await db.refresh(db_obj)
        
        return db_obj

    async def delete_question(self, db: AsyncSession, question_id: uuid.UUID) -> bool:
        """Удаление вопроса."""
        query = delete(Question).where(Question.id == question_id)
        result = await db.execute(query)
        await db.commit()
        return result.rowcount > 0

    async def publish_lecture(
        self, db: AsyncSession, lecture_id: uuid.UUID, org_id: uuid.UUID
    ) -> Optional[Lecture]:
        """Перевод лекции в статус PUBLISHED с автоматизацией дат."""
        from datetime import datetime, timezone, timedelta
        
        query = select(Lecture).where(
            and_(Lecture.id == lecture_id, Lecture.org_id == org_id)
        )
        result = await db.execute(query)
        lecture = result.scalar_one_or_none()
        
        if lecture:
            now = datetime.now(timezone.utc)
            
            # Логика: если время начала не задано — открываем прямо сейчас
            if not lecture.open_from:
                lecture.open_from = now
                
            # Логика: если дедлайн не задан — ставим +24 часа от момента публикации
            if not lecture.deadline_at:
                lecture.deadline_at = lecture.open_from + timedelta(hours=24)
            
            lecture.status = LectureStatus.PUBLISHED
            db.add(lecture)
            await db.commit()
            await db.refresh(lecture)
            return lecture
        return None


question_service = QuestionService()