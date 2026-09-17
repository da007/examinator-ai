import uuid
import random
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from sqlalchemy import select, and_, update, func # <-- ДОБАВЛЕНО func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from fastapi import HTTPException, status

from app.models.exam import ExamSession, StudentAnswer, SessionStatus
from app.models.question import Question
from app.models.chunk import Chunk
from app.models.lecture import Lecture, LectureStatus
from app.schemas.exam import ExamSessionCreate, ExamSessionUpdateDraft

from app.worker.grading_tasks import grade_exam_session_task


class ExamService:
    async def get_active_session(
        self, db: AsyncSession, *, student_id: uuid.UUID, lecture_id: uuid.UUID
    ) -> Optional[ExamSession]:
        """Проверка наличия активной сессии."""
        query = select(ExamSession).where(
            and_(
                ExamSession.student_id == student_id,
                ExamSession.lecture_id == lecture_id,
                ExamSession.status == SessionStatus.ACTIVE
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def start_session(
        self, db: AsyncSession, *, student_id: uuid.UUID, obj_in: ExamSessionCreate
    ) -> ExamSession:
        lecture_query = select(Lecture).where(Lecture.id == obj_in.lecture_id)
        lecture_res = await db.execute(lecture_query)
        lecture = lecture_res.scalar_one_or_none()
        
        if not lecture:
            raise HTTPException(status_code=404, detail="Лекция не найдена")

        if lecture.status != LectureStatus.PUBLISHED:
            raise HTTPException(status_code=400, detail="Лекция еще не опубликована преподавателем")

        # --- УЛУЧШЕННАЯ ПРОВЕРКА ВРЕМЕНИ ---
        import logging
        logger = logging.getLogger(__name__)
        now = datetime.now(timezone.utc)

        if lecture.open_from:
            # Убеждаемся, что время из БД имеет таймзону UTC для корректного сравнения
            open_from = lecture.open_from if lecture.open_from.tzinfo else lecture.open_from.replace(tzinfo=timezone.utc)
            if now < open_from:
                logger.warning(f"Student {student_id} tried to start exam too early. Now: {now}, Open: {open_from}")
                raise HTTPException(
                    status_code=403, 
                    detail=f"Доступ к тесту откроется только {open_from.strftime('%d.%m.%Y %H:%M')}"
                )
            
        if lecture.deadline_at:
            deadline = lecture.deadline_at if lecture.deadline_at.tzinfo else lecture.deadline_at.replace(tzinfo=timezone.utc)
            if now > deadline:
                logger.warning(f"Student {student_id} tried to start exam after deadline. Now: {now}, Deadline: {deadline}")
                raise HTTPException(
                    status_code=403, 
                    detail="Срок сдачи этой лекции истек"
                )
        # ----------------------------------

        # Проверяем, нет ли уже активной сессии
        existing_session = await self.get_active_session(
            db, student_id=student_id, lecture_id=obj_in.lecture_id
        )
        if existing_session:
            return existing_session

        chunks_query = (
            select(Chunk)
            .where(Chunk.lecture_id == obj_in.lecture_id)
            .options(joinedload(Chunk.questions))
            .order_by(Chunk.order_index)
        )
        chunks_res = await db.execute(chunks_query)
        chunks = chunks_res.scalars().unique().all()

        selected_question_ids = []
        for chunk in chunks:
            if chunk.questions:
                q = random.choice(chunk.questions)
                selected_question_ids.append(str(q.id)) # Преобразуем в str

        if not selected_question_ids:
            raise HTTPException(status_code=404, detail="Для этой лекции еще не сгенерированы вопросы")

        initial_draft = {} # Начинаем с абсолютно чистого листа
        
        db_session = ExamSession(
            student_id=student_id,
            lecture_id=obj_in.lecture_id,
            question_ids=selected_question_ids, # Теперь это List[str]
            status=SessionStatus.ACTIVE,
            current_draft=initial_draft
        )
        db.add(db_session)
        await db.commit()
        await db.refresh(db_session)
        return db_session

    async def update_draft(
        self, db: AsyncSession, *, session_id: uuid.UUID, student_id: uuid.UUID, obj_in: ExamSessionUpdateDraft
    ) -> ExamSession:
        """Обновление черновика с защитой от потери данных (Deep Merge)."""
        
        # 1. Получаем текущую сессию, чтобы иметь доступ к старому черновику
        query = select(ExamSession).where(
            and_(
                ExamSession.id == session_id,
                ExamSession.student_id == student_id,
                ExamSession.version == obj_in.version, # Проверка версии для Optimistic Locking
                ExamSession.status == SessionStatus.ACTIVE
            )
        )
        result = await db.execute(query)
        db_session = result.scalar_one_or_none()

        if not db_session:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Конфликт версий или сессия уже сдана. Пожалуйста, обновите страницу."
            )

        # 2. МЕРДЖ ДАННЫХ: берем старый черновик и накладываем на него новые изменения
        # Это гарантирует, что если мы обновили вопрос №5, ответы на 1-4 не исчезнут.
        updated_draft = dict(db_session.current_draft) # Копируем старый
        updated_draft.update(obj_in.current_draft)     # Накладываем новый

        # 3. Применяем изменения
        db_session.current_draft = updated_draft
        db_session.version += 1
        db_session.updated_at = func.now()

        # 4. Подгружаем вопросы для корректного ответа фронтенду (чтобы ничего не исчезало из UI)
        from app.models.question import Question
        questions_query = select(Question).where(Question.id.in_(db_session.question_ids))
        q_res = await db.execute(questions_query)
        questions = q_res.scalars().all()
        
        q_map = {str(q.id): q for q in questions}
        db_session.questions = [q_map[str(qid)] for qid in db_session.question_ids if str(qid) in q_map]

        await db.commit()
        await db.refresh(db_session)
        return db_session

    async def submit_session(
        self, db: AsyncSession, *, session_id: uuid.UUID, student_id: uuid.UUID
    ) -> ExamSession:
        query = select(ExamSession).where(
            and_(ExamSession.id == session_id, ExamSession.student_id == student_id)
        )
        res = await db.execute(query)
        session = res.scalar_one_or_none()

        if not session or session.status != SessionStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="Сессия не активна")

        from app.models.exam import StudentAnswer
        from sqlalchemy import delete
        await db.execute(delete(StudentAnswer).where(StudentAnswer.session_id == session.id))
        # -------------------------------------------------------------------------

        # 1. Фиксируем ответы из черновика
        for q_id_str, answer_data in session.current_draft.items():
            # Сохраняем ответ только если в нем есть хоть какой-то текст
            if answer_data.get("text", "").strip():
                answer = StudentAnswer(
                    session_id=session.id,
                    question_id=uuid.UUID(q_id_str),
                    answer_text=answer_data.get("text", ""),
                    formula_data=answer_data.get("formula", {})
                )
                db.add(answer)

        session.status = SessionStatus.PROCESSING
        session.end_time = datetime.now(timezone.utc)
        
        await db.commit()
        await db.refresh(session)
        grade_exam_session_task.delay(str(session.id))

        return session

exam_service = ExamService()