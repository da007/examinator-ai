import uuid
from typing import List, Optional, Sequence
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from fastapi import HTTPException, status
from sqlalchemy.orm.attributes import flag_modified

from app.models.exam import ExamSession, StudentAnswer, SessionStatus
from app.models.appeal import StudentAppeal, AppealStatus
from app.models.lecture import Lecture
from app.schemas.review import ManualAnswerCorrection, AppealResolve, AppealCreate

class ReviewService:
    """
    Сервис для ручной модерации результатов и обработки апелляций.
    Реализует механизмы контроля качества ИИ-оценок.
    """

    async def get_sessions_needing_review(
        self, db: AsyncSession, *, org_id: uuid.UUID
    ) -> Sequence[ExamSession]:
        """
        Получает список сессий, где есть ответы с низким Confidence Score 
        или флаг manual_review_required.
        """
        query = (
            select(ExamSession)
            .join(Lecture)
            .where(and_(
                Lecture.org_id == org_id,
                ExamSession.status == SessionStatus.COMPLETED
            ))
            .join(StudentAnswer)
            .where(StudentAnswer.manual_review_required == True)
            .options(
                joinedload(ExamSession.answers),
                joinedload(ExamSession.student),
                joinedload(ExamSession.lecture)
            )
            .distinct()
        )
        result = await db.execute(query)
        return result.unique().scalars().all()

    async def correct_answer(
        self, db: AsyncSession, *, correction: ManualAnswerCorrection, teacher_id: uuid.UUID
    ) -> StudentAnswer:
        
        query = select(StudentAnswer).where(StudentAnswer.id == correction.answer_id)
        result = await db.execute(query)
        answer = result.scalar_one_or_none()

        if not answer:
            raise HTTPException(status_code=404, detail="Ответ не найден")

        old_score = answer.final_score
        answer.final_score = correction.new_score
        answer.manual_review_required = False

        if not answer.ai_score:
            answer.ai_score = {}

        # Инициализируем аудит, если его нет
        if "audit" not in answer.ai_score:
            answer.ai_score["audit"] = []
            
        # Добавляем запись
        answer.ai_score["audit"].append({
            "teacher_id": str(teacher_id),
            "old_score": old_score,
            "new_score": correction.new_score,
            "comment": correction.teacher_comment
        })

        # ГЛАВНЫЙ ФИКС: Явно помечаем поле как измененное
        flag_modified(answer, "ai_score")

        await db.commit()
        await db.refresh(answer)
        return answer

    async def create_appeal(
        self, db: AsyncSession, *, student_id: uuid.UUID, obj_in: AppealCreate
    ) -> StudentAppeal:
        """Создание апелляции с детальной проверкой состояния."""
        
        # 1. Ищем сессию
        session_query = select(ExamSession).where(and_(
            ExamSession.id == obj_in.session_id,
            ExamSession.student_id == student_id
        ))
        res = await db.execute(session_query)
        session = res.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Экзаменационная сессия не найдена")

        # 2. Проверяем статус (Апелляция только после завершения всех расчетов ИИ)
        if session.status != SessionStatus.COMPLETED:
            raise HTTPException(
                status_code=400, 
                detail=f"Апелляция невозможна: текущий статус сессии '{session.status}'. Дождитесь завершения проверки."
            )

        # 3. Проверяем, нет ли уже открытой апелляции
        existing_query = select(StudentAppeal).where(and_(
            StudentAppeal.session_id == obj_in.session_id,
            StudentAppeal.status == AppealStatus.PENDING
        ))
        if (await db.execute(existing_query)).scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Апелляция по этому экзамену уже находится на рассмотрении")

        # 4. Создаем запись
        db_appeal = StudentAppeal(
            session_id=obj_in.session_id,
            student_id=student_id,
            reason=obj_in.reason,
            status=AppealStatus.PENDING
        )
        db.add(db_appeal)
        await db.commit()
        await db.refresh(db_appeal)
        return db_appeal

    async def resolve_appeal(
        self, db: AsyncSession, *, appeal_id: uuid.UUID, obj_in: AppealResolve, org_id: uuid.UUID
    ) -> StudentAppeal:
        """
        Рассмотрение апелляции преподавателем.
        """
        query = (
            select(StudentAppeal)
            .join(ExamSession)
            .join(Lecture)
            .where(and_(StudentAppeal.id == appeal_id, Lecture.org_id == org_id))
            .options(joinedload(StudentAppeal.session)) # Подгружаем сессию для логов
        )
        result = await db.execute(query)
        appeal = result.scalar_one_or_none()

        if not appeal:
            raise HTTPException(status_code=404, detail="Апелляция не найдена")

        if appeal.status != AppealStatus.PENDING:
            raise HTTPException(status_code=400, detail="Эта апелляция уже была рассмотрена ранее")

        appeal.status = obj_in.status
        appeal.teacher_comment = obj_in.teacher_comment
        
        # Если апелляция принята, это сигнал, что оценки были (или будут) исправлены вручную.
        # Мы можем добавить системный лог в метаданные сессии
        if obj_in.status == AppealStatus.ACCEPTED:
            if not appeal.session.integrity_details:
                appeal.session.integrity_details = {}
            appeal.session.integrity_details["appeal_resolved_at"] = datetime.now(timezone.utc).isoformat()

        await db.commit()
        await db.refresh(appeal)
        return appeal

review_service = ReviewService()