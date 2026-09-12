import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy import select 

from app.models.subject import Subject
from app.models.lecture import Lecture
from app.models.user import User
from app.models.exam import ExamSession, StudentAnswer, SessionStatus
from app.models.question import Question 
from app.models.chunk import Chunk   
from tests.conftest import make_auth_headers

@pytest.mark.asyncio
class TestStartExam:
    """
    Тестирование инициализации экзаменационной сессии.
    Проверяем логику выборки вопросов и защиту данных.
    """

    async def test_start_exam_success(
        self, client: AsyncClient, db, student_user: User, published_lecture
    ):
        """Студент успешно начинает тест по опубликованной лекции."""
        payload = {"lecture_id": str(published_lecture.id)}

        response = await client.post(
            "/api/v1/exams/start",
            headers=make_auth_headers(student_user),
            json=payload
        )

        assert response.status_code == 200
        data = response.json()
        
        # Проверка структуры сессии
        assert "id" in data
        assert data["status"] == SessionStatus.ACTIVE
        assert "questions" in data
        assert len(data["questions"]) > 0
        
        # КРИТИЧЕСКАЯ ПРОВЕРКА: Безопасность данных
        # В вопросе для студента НЕ должно быть эталонного ответа и тезисов
        first_q = data["questions"][0]
        assert "question_text" in first_q
        assert "reference_answer" not in first_q
        assert "key_theses" not in first_q

    async def test_start_exam_unpublished_forbidden(
        self, client: AsyncClient, student_user: User, draft_lecture
    ):
        """Нельзя начать тест по неопубликованной лекции."""
        payload = {"lecture_id": str(draft_lecture.id)}

        response = await client.post(
            "/api/v1/exams/start",
            headers=make_auth_headers(student_user),
            json=payload
        )

        assert response.status_code == 400
        assert "недоступна" in response.json()["detail"]

    async def test_start_exam_idempotency(
        self, client: AsyncClient, student_user: User, published_lecture
    ):
        """
        Повторный старт возвращает ту же самую активную сессию, 
        а не создает новую.
        """
        payload = {"lecture_id": str(published_lecture.id)}

        # Первый старт
        resp1 = await client.post(
            "/api/v1/exams/start",
            headers=make_auth_headers(student_user),
            json=payload
        )
        id1 = resp1.json()["id"]

        # Второй старт
        resp2 = await client.post(
            "/api/v1/exams/start",
            headers=make_auth_headers(student_user),
            json=payload
        )
        id2 = resp2.json()["id"]

        assert id1 == id2
        assert resp2.status_code == 200

    async def test_start_exam_no_questions(
        self, client: AsyncClient, db, student_user: User, teacher_user: User, test_subject: Subject
    ):
        """Если в лекции нет вопросов, старт невозможен."""
        # Создаем лекцию без вопросов через модель напрямую
        from app.models.lecture import Lecture, LectureStatus
        empty_lecture = Lecture(
            title="Пустая лекция",
            subject_id=test_subject.id,
            org_id=student_user.org_id,
            teacher_id=teacher_user.id,
            status=LectureStatus.PUBLISHED
        )
        db.add(empty_lecture)
        await db.flush()

        payload = {"lecture_id": str(empty_lecture.id)}
        response = await client.post(
            "/api/v1/exams/start",
            headers=make_auth_headers(student_user),
            json=payload
        )

        assert response.status_code == 404
        assert "вопросы" in response.json()["detail"]
        
    async def test_start_exam_after_deadline_forbidden(
        self, client: AsyncClient, db, student_user: User, published_lecture: Lecture
    ):
        """Проверка дедлайна: если время вышло, тест начать нельзя (Task 1.3)."""
        from datetime import datetime, timedelta, timezone
        
        # Устанавливаем дедлайн в прошлом
        published_lecture.deadline_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db.add(published_lecture)
        await db.commit()

        payload = {"lecture_id": str(published_lecture.id)}
        response = await client.post(
            "/api/v1/exams/start",
            headers=make_auth_headers(student_user),
            json=payload
        )

        assert response.status_code == 403
        assert "срок сдачи" in response.json()["detail"].lower()

@pytest.mark.asyncio
class TestSaveDraft:
    """
    Тестирование сохранения черновика (автосохранение).
    Проверяем инкремент версий и защиту от конфликтов.
    """

    async def test_save_draft_success(
        self, client: AsyncClient, db, student_user: User, published_lecture
    ):
        """Успешное сохранение черновика и инкремент версии."""
        # 1. Стартуем сессию
        start_resp = await client.post(
            "/api/v1/exams/start",
            headers=make_auth_headers(student_user),
            json={"lecture_id": str(published_lecture.id)}
        )
        session_id = start_resp.json()["id"]
        current_version = start_resp.json()["version"] # Обычно 1

        # 2. Сохраняем черновик
        q_id = start_resp.json()["questions"][0]["id"]
        draft_content = {
            str(q_id): {"text": "Мой первый ответ", "formula": {"latex": "E=mc^2"}}
        }
        
        payload = {
            "version": current_version,
            "current_draft": draft_content
        }

        response = await client.patch(
            f"/api/v1/exams/sessions/{session_id}/draft",
            headers=make_auth_headers(student_user),
            json=payload
        )

        assert response.status_code == 200
        data = response.json()
        assert data["version"] == current_version + 1
        assert data["current_draft"][str(q_id)]["text"] == "Мой первый ответ"

    async def test_save_draft_version_conflict(
        self, client: AsyncClient, student_user: User, published_lecture
    ):
        """Конфликт версий (Optimistic Locking) возвращает 409."""
        # 1. Стартуем
        start_resp = await client.post(
            "/api/v1/exams/start",
            headers=make_auth_headers(student_user),
            json={"lecture_id": str(published_lecture.id)}
        )
        session_id = start_resp.json()["id"]

        # 2. Делаем успешный сейв (версия станет 2)
        await client.patch(
            f"/api/v1/exams/sessions/{session_id}/draft",
            headers=make_auth_headers(student_user),
            json={"version": 1, "current_draft": {"some": "data"}}
        )

        # 3. Пытаемся сохранить ОПЯТЬ с версией 1 (конфликт)
        response = await client.patch(
            f"/api/v1/exams/sessions/{session_id}/draft",
            headers=make_auth_headers(student_user),
            json={"version": 1, "current_draft": {"wrong": "version"}}
        )

        assert response.status_code == 409
        assert "Конфликт версий" in response.json()["detail"]

    async def test_save_draft_other_student_forbidden(
        self, client: AsyncClient, student_user: User, other_org_user: User, published_lecture
    ):
        """Студент не может редактировать чужую сессию."""
        # 1. Студент 1 стартует
        start_resp = await client.post(
            "/api/v1/exams/start",
            headers=make_auth_headers(student_user),
            json={"lecture_id": str(published_lecture.id)}
        )
        session_id = start_resp.json()["id"]

        # 2. Студент 2 (из другой организации или просто другой) пытается сохранить
        response = await client.patch(
            f"/api/v1/exams/sessions/{session_id}/draft",
            headers=make_auth_headers(other_org_user),
            json={"version": 1, "current_draft": {"hack": "attempt"}}
        )

        # В вашем сервисе используется фильтр по student_id, поэтому вернется 409 или 404
        assert response.status_code in [404, 409]

@pytest.mark.asyncio
class TestSubmitExam:
    """
    Тестирование финальной сдачи экзамена.
    Проверяем фиксацию ответов и запуск ИИ-воркера.
    """

    async def test_submit_success(
        self, client: AsyncClient, db, student_user: User, published_lecture
    ):
        """Успешная сдача: статус меняется, ответы создаются, Celery вызван."""
        from app.models.exam import StudentAnswer
        from app.worker.grading_tasks import grade_exam_session_task

        # 1. Подготовка: стартуем и наполняем черновик
        start_resp = await client.post(
            "/api/v1/exams/start",
            headers=make_auth_headers(student_user),
            json={"lecture_id": str(published_lecture.id)}
        )
        session_id = start_resp.json()["id"]
        q_id = start_resp.json()["questions"][0]["id"]
        
        draft_content = {
            str(q_id): {"text": "Финальный ответ", "formula": {}}
        }
        await client.patch(
            f"/api/v1/exams/sessions/{session_id}/draft",
            headers=make_auth_headers(student_user),
            json={"version": 1, "current_draft": draft_content}
        )

        # 2. ДЕЙСТВИЕ: Сдача теста
        response = await client.post(
            f"/api/v1/exams/sessions/{session_id}/submit",
            headers=make_auth_headers(student_user)
        )

        assert response.status_code == 200
        assert response.json()["status"] == SessionStatus.PROCESSING
        
        # 3. ПРОВЕРКА БД: Ответы перенесены из JSON в таблицу StudentAnswer
        ans_query = select(StudentAnswer).where(StudentAnswer.session_id == uuid.UUID(session_id))
        res = await db.execute(ans_query)
        answers = res.scalars().all()
        
        assert len(answers) == 1
        assert answers[0].answer_text == "Финальный ответ"
        assert answers[0].question_id == uuid.UUID(q_id)

        # 4. ПРОВЕРКА CELERY: Задача на оценку поставлена в очередь
        grade_exam_session_task.delay.assert_called_once_with(session_id)

    async def test_submit_already_submitted_forbidden(
        self, client: AsyncClient, student_user: User, published_lecture
    ):
        """Нельзя сдать тест дважды (400)."""
        # 1. Стартуем
        start_resp = await client.post(
            "/api/v1/exams/start",
            headers=make_auth_headers(student_user),
            json={"lecture_id": str(published_lecture.id)}
        )
        session_id = start_resp.json()["id"]

        # 2. Сдаем первый раз
        await client.post(
            f"/api/v1/exams/sessions/{session_id}/submit",
            headers=make_auth_headers(student_user)
        )

        # 3. Пытаемся сдать второй раз
        response = await client.post(
            f"/api/v1/exams/sessions/{session_id}/submit",
            headers=make_auth_headers(student_user)
        )

        assert response.status_code == 400
        assert "не активна" in response.json()["detail"]

    async def test_submit_other_student_forbidden(
        self, client: AsyncClient, student_user: User, other_org_user: User, published_lecture
    ):
        """Студент не может сдать чужую сессию."""
        start_resp = await client.post(
            "/api/v1/exams/start",
            headers=make_auth_headers(student_user),
            json={"lecture_id": str(published_lecture.id)}
        )
        session_id = start_resp.json()["id"]

        response = await client.post(
            f"/api/v1/exams/sessions/{session_id}/submit",
            headers=make_auth_headers(other_org_user)
        )

        assert response.status_code == 400 # Тот же код "не найдена"

@pytest.mark.asyncio
class TestGetExamResults:
    """
    Тестирование получения результатов экзамена.
    """

    async def test_get_results_success(
        self, client: AsyncClient, db, student_user: User, published_lecture
    ):
        """Успешное получение результатов после завершения проверки."""
        
        # 1. Сначала найдем реальный вопрос, который создала фикстура published_lecture
        res_q = await db.execute(
            select(Question)
            .join(Chunk)
            .where(Chunk.lecture_id == published_lecture.id)
        )
        real_question = res_q.scalars().first()
        real_q_id = real_question.id

        # 2. Создаем сессию с РЕАЛЬНЫМ ID вопроса
        session = ExamSession(
            student_id=student_user.id,
            lecture_id=published_lecture.id,
            status=SessionStatus.COMPLETED,
            question_ids=[str(real_q_id)] # Используем реальный ID
        )
        db.add(session)
        await db.flush()

        # 3. Создаем ответ, привязанный к существующему вопросу
        answer = StudentAnswer(
            session_id=session.id,
            question_id=real_q_id, # Теперь FK не ругается
            answer_text="Тестовый ответ",
            final_score=0.85,
            ai_score={"explanation": "Хороший ответ, но не полный"}
        )
        db.add(answer)
        await db.commit()

        # 4. Запрос результатов
        response = await client.get(
            f"/api/v1/exams/sessions/{session.id}/result",
            headers=make_auth_headers(student_user)
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_score"] == 0.85
        assert data["answers"][0]["ai_explanation"] == "Хороший ответ, но не полный"

    async def test_get_results_still_processing(
        self, client: AsyncClient, db, student_user: User, published_lecture
    ):
        """Если проверка еще идет, возвращается статус 202."""
        session = ExamSession(
            student_id=student_user.id,
            lecture_id=published_lecture.id,
            status=SessionStatus.PROCESSING,
            question_ids=[]
        )
        db.add(session)
        await db.commit()

        response = await client.get(
            f"/api/v1/exams/sessions/{session.id}/result",
            headers=make_auth_headers(student_user)
        )

        assert response.status_code == 202

    async def test_get_results_other_student_forbidden(
        self, client: AsyncClient, db, other_org_user: User, student_user: User, published_lecture
    ):
        """IDOR Check: Нельзя смотреть чужие результаты."""
        session = ExamSession(
            student_id=student_user.id,
            lecture_id=published_lecture.id,
            status=SessionStatus.COMPLETED,
            question_ids=[]
        )
        db.add(session)
        await db.commit()

        response = await client.get(
            f"/api/v1/exams/sessions/{session.id}/result",
            headers=make_auth_headers(other_org_user)
        )

        assert response.status_code == 404