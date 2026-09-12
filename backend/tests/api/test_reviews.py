import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy import select

from app.models.user import User
from app.models.exam import ExamSession, StudentAnswer, SessionStatus
from app.models.appeal import StudentAppeal, AppealStatus
from tests.conftest import make_auth_headers



@pytest.mark.asyncio
class TestAppeals:
    """
    Тестирование апелляций и ручной проверки.
    """

    async def test_submit_appeal_success(
        self, client: AsyncClient, db, student_user: User, published_lecture
    ):
        """Студент успешно подает апелляцию на завершенный тест."""
        # 1. Подготовка: Завершенная сессия
        session = ExamSession(
            student_id=student_user.id,
            lecture_id=published_lecture.id,
            status=SessionStatus.COMPLETED,
            question_ids=[]
        )
        db.add(session)
        await db.commit()

        payload = {
            "session_id": str(session.id),
            "reason": "Я считаю, что ИИ не учел мой аргумент про интерпретатор."
        }

        response = await client.post(
            "/api/v1/reviews/appeals",
            headers=make_auth_headers(student_user),
            json=payload
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending"
        assert data["reason"] == payload["reason"]

    async def test_submit_appeal_on_active_session_fails(
        self, client: AsyncClient, db, student_user: User, published_lecture
    ):
        """Нельзя подать апелляцию, пока тест еще не завершен."""
        session = ExamSession(
            student_id=student_user.id,
            lecture_id=published_lecture.id,
            status=SessionStatus.ACTIVE,
            question_ids=[]
        )
        db.add(session)
        await db.commit()

        response = await client.post(
            "/api/v1/reviews/appeals",
            headers=make_auth_headers(student_user),
            # Длина строки должна быть >= 10 символов
            json={"session_id": str(session.id), "reason": "Сессия еще не завершена."} 
        )

        assert response.status_code == 400
        assert "Апелляция невозможна" in response.json()["detail"]

    async def test_get_pending_reviews_org_isolation(
        self, client: AsyncClient, db, teacher_user: User, other_org_user: User, student_user: User, published_lecture
    ):
        """Преподаватель видит на проверку только работы своей организации."""
        from app.models.question import Question
        from app.models.chunk import Chunk

        # 1. Создаем вопрос для FK
        res_q = await db.execute(select(Question).join(Chunk).where(Chunk.lecture_id == published_lecture.id))
        real_q = res_q.scalars().first()

        # 2. Создаем сессию, требующую проверки (manual_review_required=True)
        session = ExamSession(
            student_id=student_user.id,
            lecture_id=published_lecture.id,
            status=SessionStatus.COMPLETED,
            question_ids=[str(real_q.id)]
        )
        db.add(session)
        await db.flush()

        answer = StudentAnswer(
            session_id=session.id,
            question_id=real_q.id,
            answer_text="Низкий конфиденс",
            manual_review_required=True,
            confidence_score=0.3
        )
        db.add(answer)
        await db.commit()

        # 3. Преподаватель ТАКОЙ ЖЕ организации видит работу
        resp_own = await client.get(
            "/api/v1/reviews/pending",
            headers=make_auth_headers(teacher_user)
        )
        assert resp_own.status_code == 200
        assert len(resp_own.json()) == 1

        # 4. Преподаватель ДРУГОЙ организации не видит ничего
        resp_other = await client.get(
            "/api/v1/reviews/pending",
            headers=make_auth_headers(other_org_user)
        )
        assert resp_other.status_code == 200
        assert len(resp_other.json()) == 0

@pytest.mark.asyncio
class TestResolveReview:
    """
    Тестирование разрешения апелляций и корректировки оценок.
    Фокус на аудите и безопасности.
    """

    async def test_correct_answer_and_audit_success(
        self, client: AsyncClient, db, teacher_user: User, student_user: User, published_lecture
    ):
        """Преподаватель корректирует балл, аудит записывается в JSONB."""
        from app.models.question import Question
        from app.models.chunk import Chunk

        # 1. Подготовка: Сессия с ответом
        res_q = await db.execute(select(Question).join(Chunk).where(Chunk.lecture_id == published_lecture.id))
        question = res_q.scalars().first()

        session = ExamSession(
            student_id=student_user.id,
            lecture_id=published_lecture.id,
            status=SessionStatus.COMPLETED,
            question_ids=[str(question.id)]
        )
        db.add(session)
        await db.flush()

        answer = StudentAnswer(
            session_id=session.id,
            question_id=question.id,
            answer_text="Ответ для правки",
            final_score=0.2, # ИИ поставил мало
            ai_score={"explanation": "Low score by AI"}
        )
        db.add(answer)
        await db.commit()

        # 2. ДЕЙСТВИЕ: Преподаватель правит оценку
        payload = {
            "answer_id": str(answer.id),
            "new_score": 0.9,
            "teacher_comment": "ИИ ошибся, ответ верный."
        }

        response = await client.post(
            "/api/v1/reviews/correct-answer",
            headers=make_auth_headers(teacher_user),
            json=payload
        )

        assert response.status_code == 200
        
        # 3. ПРОВЕРКА АУДИТА В БД
        await db.refresh(answer)
        assert answer.final_score == 0.9
        
        audit = answer.ai_score.get("audit", [])
        assert len(audit) == 1
        assert audit[0]["new_score"] == 0.9
        assert audit[0]["teacher_id"] == str(teacher_user.id)
        assert audit[0]["comment"] == "ИИ ошибся, ответ верный."

    async def test_resolve_appeal_success(
        self, client: AsyncClient, db, teacher_user: User, student_user: User, published_lecture
    ):
        """Преподаватель успешно закрывает апелляцию."""
        # 1. Подготовка: Апелляция в статусе pending
        session = ExamSession(student_id=student_user.id, lecture_id=published_lecture.id, status=SessionStatus.COMPLETED, question_ids=[])
        db.add(session)
        await db.flush()

        appeal = StudentAppeal(
            session_id=session.id,
            student_id=student_user.id,
            reason="Хочу пересмотра",
            status=AppealStatus.PENDING
        )
        db.add(appeal)
        await db.commit()

        # 2. ДЕЙСТВИЕ: Разрешение
        payload = {
            "status": "accepted",
            "teacher_comment": "Принято, оценка будет исправлена."
        }

        response = await client.patch(
            f"/api/v1/reviews/appeals/{appeal.id}/resolve",
            headers=make_auth_headers(teacher_user),
            json=payload
        )

        assert response.status_code == 200
        assert response.json()["status"] == "accepted"
        
        await db.refresh(appeal)
        assert appeal.status == AppealStatus.ACCEPTED

    async def test_resolve_other_org_appeal_forbidden(
        self, client: AsyncClient, db, other_org_user: User, student_user: User, published_lecture
    ):
        """Security: Преподаватель не может закрыть чужую апелляцию."""
        session = ExamSession(student_id=student_user.id, lecture_id=published_lecture.id, status=SessionStatus.COMPLETED, question_ids=[])
        db.add(session)
        await db.flush()

        appeal = StudentAppeal(session_id=session.id, student_id=student_user.id, reason="Other org", status=AppealStatus.PENDING)
        db.add(appeal)
        await db.commit()

        response = await client.patch(
            f"/api/v1/reviews/appeals/{appeal.id}/resolve",
            headers=make_auth_headers(other_org_user),
            json={"status": "rejected", "teacher_comment": "I am a hacker"}
        )

        assert response.status_code == 404 # Скрываем через 404 согласно логике сервиса

@pytest.mark.asyncio
class TestTAAccess:
    """
    Проверка прав доступа Ассистента (TA).
    TA должен иметь возможность проверять апелляции и видеть список задач.
    """

    async def test_ta_can_view_pending_reviews(
        self, client: AsyncClient, db, ta_user: User, student_user: User, published_lecture
    ):
        """Проверка: TA видит список работ на модерацию."""
        # 1. Создаем сессию с manual_review_required=True
        # (Используем упрощенное создание сессии для теста прав)
        from app.models.exam import ExamSession, StudentAnswer, SessionStatus
        session = ExamSession(
            student_id=student_user.id,
            lecture_id=published_lecture.id,
            status=SessionStatus.COMPLETED,
            question_ids=[]
        )
        db.add(session)
        await db.flush()
        
        # Добавляем ответ с флагом проверки
        from app.models.question import Question
        from app.models.chunk import Chunk
        res_q = await db.execute(select(Question).join(Chunk).where(Chunk.lecture_id == published_lecture.id))
        q = res_q.scalars().first()
        
        answer = StudentAnswer(
            session_id=session.id,
            question_id=q.id,
            answer_text="TA test",
            manual_review_required=True
        )
        db.add(answer)
        await db.commit()

        # 2. Запрос от имени TA
        response = await client.get(
            "/api/v1/reviews/pending",
            headers=make_auth_headers(ta_user)
        )

        assert response.status_code == 200
        assert len(response.json()) > 0
        assert response.json()[0]["lectureTitle"] == published_lecture.title

    async def test_ta_cannot_delete_lecture(
        self, client: AsyncClient, ta_user: User, published_lecture
    ):
        """Проверка ограничений: TA не может удалять лекции (Task 1.2)."""
        response = await client.delete(
            f"/api/v1/lectures/{published_lecture.id}",
            headers=make_auth_headers(ta_user)
        )
        # Ожидаем 403, так как в lectures.py нет TA в RoleChecker
        assert response.status_code == 403