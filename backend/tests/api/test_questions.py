import pytest
from httpx import AsyncClient
from sqlalchemy import select, and_  # Добавлено

from app.models.user import User
from app.models.question import Question  # Добавлено
from app.models.chunk import Chunk        # Добавлено
from tests.conftest import make_auth_headers

@pytest.mark.asyncio
class TestUpdateQuestion:
    """
    Тестирование обновления (модерации) вопроса.
    Проверяем частичные обновления и защиту данных.
    """

    async def test_update_question_text_success(
        self, client: AsyncClient, db, teacher_user: User, published_lecture
    ):
        """Успешное обновление только текста вопроса."""
        # JOIN необходим, чтобы найти вопрос, принадлежащий конкретной лекции
        res = await db.execute(
            select(Question)
            .join(Chunk, Question.chunk_id == Chunk.id)
            .where(Chunk.lecture_id == published_lecture.id)
        )
        question = res.scalars().first()
        
        new_text = "Обновленный вопрос: Как работает Python?"
        payload = {"question_text": new_text}

        response = await client.patch(
            f"/api/v1/questions/{question.id}",
            headers=make_auth_headers(teacher_user),
            json=payload
        )

        assert response.status_code == 200
        data = response.json()
        assert data["questionText"] == new_text
        assert data["referenceAnswer"] == question.reference_answer

    async def test_update_theses_success(
        self, client: AsyncClient, db, teacher_user: User, published_lecture
    ):
        """Успешное обновление ключевых тезисов (JSONB)."""
        res = await db.execute(
            select(Question)
            .join(Chunk, Question.chunk_id == Chunk.id)
            .where(Chunk.lecture_id == published_lecture.id)
        )
        question = res.scalars().first()

        new_theses = [
            {"text": "Интерпретатор", "importance": 3},
            {"text": "Динамическая типизация", "importance": 2}
        ]
        payload = {"key_theses": new_theses}

        response = await client.patch(
            f"/api/v1/questions/{question.id}",
            headers=make_auth_headers(teacher_user),
            json=payload
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["keyTheses"]) == 2

    async def test_update_other_org_forbidden(
        self, client: AsyncClient, db, other_org_user: User, published_lecture
    ):
        """Security: Нельзя редактировать вопрос чужой организации."""
        res = await db.execute(
            select(Question)
            .join(Chunk, Question.chunk_id == Chunk.id)
            .where(Chunk.lecture_id == published_lecture.id)
        )
        question = res.scalars().first()

        payload = {"question_text": "Хакерская атака"}

        response = await client.patch(
            f"/api/v1/questions/{question.id}",
            headers=make_auth_headers(other_org_user),
            json=payload
        )

        # 404, так как сервис ищет вопрос по связке (id, org_id)
        assert response.status_code == 404

@pytest.mark.asyncio
class TestDeleteQuestion:
    """
    Тестирование удаления вопроса.
    Проверяем права доступа и сохранение целостности родительских объектов.
    """

    async def test_delete_question_success(
        self, client: AsyncClient, db, teacher_user: User, published_lecture
    ):
        """Преподаватель успешно удаляет вопрос своей лекции."""
        # Находим вопрос через JOIN, как в предыдущих тестах
        res = await db.execute(
            select(Question)
            .join(Chunk, Question.chunk_id == Chunk.id)
            .where(Chunk.lecture_id == published_lecture.id)
        )
        question = res.scalars().first()
        question_id = question.id
        chunk_id = question.chunk_id

        response = await client.delete(
            f"/api/v1/questions/{question_id}",
            headers=make_auth_headers(teacher_user)
        )

        assert response.status_code == 204
        
        # Проверка 1: Вопрос исчез
        check_q = await db.execute(select(Question).where(Question.id == question_id))
        assert check_q.scalar_one_or_none() is None

        # Проверка 2: Чанк остался на месте (целостность структуры)
        check_c = await db.execute(select(Chunk).where(Chunk.id == chunk_id))
        assert check_c.scalar_one_or_none() is not None

    async def test_delete_other_org_question_forbidden(
        self, client: AsyncClient, db, other_org_user: User, published_lecture
    ):
        """Security: Нельзя удалить вопрос из чужой организации."""
        res = await db.execute(
            select(Question)
            .join(Chunk, Question.chunk_id == Chunk.id)
            .where(Chunk.lecture_id == published_lecture.id)
        )
        question = res.scalars().first()

        response = await client.delete(
            f"/api/v1/questions/{question.id}",
            headers=make_auth_headers(other_org_user)
        )

        # 404, так как эндпоинт ищет вопрос по связке (id, org_id)
        assert response.status_code == 404

    async def test_delete_question_as_student_forbidden(
        self, client: AsyncClient, db, student_user: User, published_lecture
    ):
        """RBAC: Студент не может удалять вопросы."""
        res = await db.execute(
            select(Question)
            .join(Chunk, Question.chunk_id == Chunk.id)
            .where(Chunk.lecture_id == published_lecture.id)
        )
        question = res.scalars().first()

        response = await client.delete(
            f"/api/v1/questions/{question.id}",
            headers=make_auth_headers(student_user)
        )

        assert response.status_code == 403