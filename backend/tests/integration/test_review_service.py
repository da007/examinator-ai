import pytest
import uuid
from sqlalchemy import select
from app.services.review_service import review_service
from app.schemas.review import ManualAnswerCorrection, AppealCreate, AppealResolve
from app.models.exam import ExamSession, StudentAnswer, SessionStatus
from app.models.appeal import StudentAppeal, AppealStatus

@pytest.mark.asyncio
class TestReviewServiceModeration:
    """
    Интеграционное тестирование модерации оценок ИИ.
    Фокус на фильтрации (Distinct) и мутации JSONB (Audit).
    """

    async def test_get_sessions_needing_review_distinct(
        self, db, student_user, published_lecture
    ):
        """Сервис возвращает уникальные сессии, требующие проверки."""
        from app.models.question import Question
        from app.models.chunk import Chunk

        res_q = await db.execute(select(Question).join(Chunk).where(Chunk.lecture_id == published_lecture.id))
        q = res_q.scalars().first()

        # Создаем сессию
        session = ExamSession(student_id=student_user.id, lecture_id=published_lecture.id, status=SessionStatus.COMPLETED, question_ids=[str(q.id)])
        db.add(session)
        await db.flush()

        # Создаем ДВА ответа в одной сессии, требующие проверки
        # Если сервис не использует .distinct(), он вернет сессию дважды
        ans1 = StudentAnswer(session_id=session.id, question_id=q.id, answer_text="1", manual_review_required=True)
        ans2 = StudentAnswer(session_id=session.id, question_id=q.id, answer_text="2", manual_review_required=True)
        db.add_all([ans1, ans2])
        await db.commit()

        sessions = await review_service.get_sessions_needing_review(db, org_id=published_lecture.org_id)
        
        # Ожидаем ровно 1 уникальную сессию
        assert len(sessions) == 1
        assert sessions[0].id == session.id

    async def test_correct_answer_saves_audit_and_clears_flag(
        self, db, teacher_user, student_user, published_lecture
    ):
        """
        Ручная корректировка сохраняет старый балл в аудит 
        и снимает флаг необходимости проверки.
        """
        from app.models.question import Question
        res_q = await db.execute(select(Question))
        q = res_q.scalars().first()

        session = ExamSession(student_id=student_user.id, lecture_id=published_lecture.id, status=SessionStatus.COMPLETED, question_ids=[str(q.id)])
        db.add(session)
        await db.flush()

        answer = StudentAnswer(
            session_id=session.id, 
            question_id=q.id, 
            answer_text="Плохой ответ", 
            final_score=0.1, 
            manual_review_required=True,
            ai_score={"explanation": "Bad"}
        )
        db.add(answer)
        await db.commit()

        # Выполняем коррекцию
        correction = ManualAnswerCorrection(
            answer_id=answer.id,
            new_score=0.9,
            teacher_comment="Ответ верный"
        )
        updated_answer = await review_service.correct_answer(
            db, correction=correction, teacher_id=teacher_user.id
        )

        # Проверка 1: Балл изменен, флаг снят
        assert updated_answer.final_score == 0.9
        assert updated_answer.manual_review_required is False

        # Проверка 2: Аудит успешно зафиксирован в JSONB (спасибо flag_modified)
        audit = updated_answer.ai_score.get("audit")
        assert audit is not None
        assert len(audit) == 1
        assert audit[0]["old_score"] == 0.1
        assert audit[0]["new_score"] == 0.9
        assert audit[0]["teacher_id"] == str(teacher_user.id)
@pytest.mark.asyncio
class TestReviewServiceAppeals:
    """
    Интеграционное тестирование жизненного цикла апелляций.
    Проверяем бизнес-ограничения и смену состояний.
    """

    async def test_create_appeal_success(self, db, student_user, published_lecture):
        """Успешное создание апелляции на завершенную сессию."""
        # 1. Создаем завершенную сессию
        session = ExamSession(
            student_id=student_user.id,
            lecture_id=published_lecture.id,
            status=SessionStatus.COMPLETED,
            question_ids=[]
        )
        db.add(session)
        await db.commit()

        # 2. Создаем апелляцию через сервис
        obj_in = AppealCreate(
            session_id=session.id,
            reason="Я не согласен с оценкой за второй вопрос."
        )
        appeal = await review_service.create_appeal(
            db, student_id=student_user.id, obj_in=obj_in
        )

        assert appeal.status == AppealStatus.PENDING
        assert appeal.session_id == session.id
        assert appeal.reason == obj_in.reason

    async def test_create_appeal_duplicate_fails(self, db, student_user, published_lecture):
        """Нельзя создать вторую апелляцию, если первая еще на рассмотрении."""
        session = ExamSession(student_id=student_user.id, lecture_id=published_lecture.id, status=SessionStatus.COMPLETED, question_ids=[])
        db.add(session)
        await db.flush()

        # Первая апелляция (создаем через модель, чтобы не зависеть от схем здесь)
        appeal1 = StudentAppeal(
            session_id=session.id, 
            student_id=student_user.id, 
            reason="Первоначальная причина апелляции.", # > 10 символов
            status=AppealStatus.PENDING
        )
        db.add(appeal1)
        await db.commit()

        # Попытка второй через сервис (валидное DTO)
        obj_in = AppealCreate(
            session_id=session.id, 
            reason="Повторная причина апелляции." # > 10 символов
        )
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as excinfo:
            await review_service.create_appeal(db, student_id=student_user.id, obj_in=obj_in)
        
        assert excinfo.value.status_code == 400
        assert "уже находится на рассмотрении" in excinfo.value.detail

    async def test_resolve_appeal_success(self, db, teacher_user, student_user, published_lecture):
        """Преподаватель успешно одобряет апелляцию."""
        session = ExamSession(student_id=student_user.id, lecture_id=published_lecture.id, status=SessionStatus.COMPLETED, question_ids=[])
        db.add(session)
        await db.flush()

        # Удлиняем причину
        appeal = StudentAppeal(
            session_id=session.id, 
            student_id=student_user.id, 
            reason="Проверьте, пожалуйста, мой ответ еще раз.", 
            status=AppealStatus.PENDING
        )
        db.add(appeal)
        await db.commit()

        obj_in = AppealResolve(
            status=AppealStatus.ACCEPTED,
            teacher_comment="Оценка пересмотрена, вы правы."
        )
        
        resolved = await review_service.resolve_appeal(
            db, appeal_id=appeal.id, obj_in=obj_in, org_id=teacher_user.org_id
        )

        assert resolved.status == AppealStatus.ACCEPTED