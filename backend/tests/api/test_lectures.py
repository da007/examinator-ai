import uuid
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.lecture import LectureStatus
from app.models.subject import Subject
from tests.conftest import make_auth_headers
from datetime import datetime, timezone

@pytest.mark.asyncio
class TestUploadLecture:
    """
    Тестирование загрузки лекций.
    Проверяем Multipart-парсинг, RBAC и запуск фоновой обработки.
    """

    async def test_upload_success(self, client: AsyncClient, teacher_user: User, test_subject: Subject):
        """
        Успешная загрузка преподавателем.
        """
        from app.worker.tasks import process_lecture_task
        from app.models.lecture import Lecture
        
        now = datetime.now(timezone.utc)
        file_content = b"Simple lecture content"
        files = {"file": ("lecture.txt", file_content, "text/plain")}
        data = {"title": "New Async Lecture", "subject_id": str(test_subject.id)}

        with patch("app.services.lecture_service.lecture_service.create_with_file", new_callable=AsyncMock) as mock_create:
            # Наполняем мок ВСЕМИ обязательными полями для LectureRead
            mock_lecture = Lecture(
                id=uuid.UUID("00000000-0000-0000-0000-000000000099"),
                title="New Async Lecture",
                org_id=teacher_user.org_id,
                subject_id=test_subject.id,
                teacher_id=teacher_user.id,
                status=LectureStatus.UPLOADED,
                version=1,              # Добавлено
                created_at=now,         # Добавлено
                updated_at=now          # Добавлено
            )
            mock_create.return_value = mock_lecture

            response = await client.post(
                "/api/v1/lectures/upload",
                headers=make_auth_headers(teacher_user),
                data=data,
                files=files
            )

            assert response.status_code == 202
            body = response.json()
            assert body["title"] == "New Async Lecture"
            assert body["version"] == 1
            assert "createdAt" in body
            
            # Проверка вызова Celery
            process_lecture_task.delay.assert_called_once()
            args, _ = process_lecture_task.delay.call_args
            assert args[0] == str(mock_lecture.id)

    async def test_upload_as_student_forbidden(self, client: AsyncClient, student_user: User):
        """
        RBAC: Студент не имеет прав загружать лекции.
        """
        files = {"file": ("test.txt", b"content", "text/plain")}
        data = {"title": "Student's attempt"}

        response = await client.post(
            "/api/v1/lectures/upload",
            headers=make_auth_headers(student_user),
            data=data,
            files=files
        )

        assert response.status_code == 403
        assert "enough privileges" in response.json()["detail"]

    async def test_upload_no_auth(self, client: AsyncClient):
        """
        Security: Анонимный пользователь получает 401.
        """
        response = await client.post("/api/v1/lectures/upload", data={"title": "No auth"})
        assert response.status_code == 401

@pytest.mark.asyncio
class TestListLectures:
    """
    Тестирование получения списка лекций.
    Проверяем Multi-tenancy и фильтрацию.
    """

    async def test_list_own_org_only(
        self, client: AsyncClient, teacher_user: User, published_lecture
    ):
        """
        Преподаватель видит лекции только своей организации.
        """
        response = await client.get(
            "/api/v1/lectures/",
            headers=make_auth_headers(teacher_user)
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == str(published_lecture.id)
        assert data[0]["orgId"] == str(teacher_user.org_id)

    async def test_other_org_invisible(
        self, client: AsyncClient, other_org_user: User, published_lecture
    ):
        """
        Пользователь из другой организации не видит чужие лекции.
        """
        # Лекция создана в Org 1, а мы запрашиваем от Org 2
        response = await client.get(
            "/api/v1/lectures/",
            headers=make_auth_headers(other_org_user)
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Ожидаем пустой список, так как в Org 2 лекций нет
        assert len(data) == 0

    async def test_list_unauthorized(self, client: AsyncClient):
        """Без токена список недоступен."""
        response = await client.get("/api/v1/lectures/")
        assert response.status_code == 401
        
@pytest.mark.asyncio
class TestGetLecture:
    """
    Тестирование получения детальной информации о лекции.
    Главный фокус на безопасности доступа по UUID.
    """

    async def test_get_own_lecture_success(
        self, client: AsyncClient, teacher_user: User, published_lecture
    ):
        """Преподаватель успешно получает свою лекцию."""
        response = await client.get(
            f"/api/v1/lectures/{published_lecture.id}",
            headers=make_auth_headers(teacher_user)
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(published_lecture.id)
        assert data["title"] == published_lecture.title
        # Проверяем наличие обязательных полей схемы Read
        assert "createdAt" in data
        assert "status" in data

    async def test_get_other_org_lecture_forbidden(
        self, client: AsyncClient, other_org_user: User, published_lecture
    ):
        """
        IDOR Check: Пользователь из другой организации 
        не может получить лекцию по UUID.
        """
        # Запрос от Org 2 к лекции из Org 1
        response = await client.get(
            f"/api/v1/lectures/{published_lecture.id}",
            headers=make_auth_headers(other_org_user)
        )

        # Согласно коду в app/api/v1/endpoints/lectures.py, 
        # при несовпадении org_id выбрасывается 403.
        assert response.status_code == 403
        assert "Доступ к этой лекции запрещен" in response.json()["detail"]

    async def test_get_lecture_not_found(
        self, client: AsyncClient, teacher_user: User
    ):
        """Запрос несуществующего UUID возвращает 404."""
        random_uuid = uuid.uuid4()
        response = await client.get(
            f"/api/v1/lectures/{random_uuid}",
            headers=make_auth_headers(teacher_user)
        )

        assert response.status_code == 404

@pytest.mark.asyncio
class TestPublishLecture:
    """
    Тестирование процесса публикации лекции.
    Проверяем смену статуса и безопасность.
    """

    async def test_publish_success(
        self, client: AsyncClient, db, teacher_user: User, draft_lecture
    ):
        """Преподаватель успешно публикует свою лекцию."""
        # Исходный статус лекции - UPLOADED (из фикстуры draft_lecture)
        assert draft_lecture.status == LectureStatus.UPLOADED

        response = await client.post(
            f"/api/v1/lectures/{draft_lecture.id}/publish",
            headers=make_auth_headers(teacher_user)
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "published"
        
        # Проверяем состояние в БД напрямую через сессию теста
        await db.refresh(draft_lecture)
        assert draft_lecture.status == LectureStatus.PUBLISHED

    async def test_publish_as_student_forbidden(
        self, client: AsyncClient, student_user: User, draft_lecture
    ):
        """RBAC: Студент не может публиковать лекции."""
        response = await client.post(
            f"/api/v1/lectures/{draft_lecture.id}/publish",
            headers=make_auth_headers(student_user)
        )

        assert response.status_code == 403
        assert "privileges" in response.json()["detail"]

    async def test_publish_other_org_forbidden(
        self, client: AsyncClient, other_org_user: User, draft_lecture
    ):
        """
        Security: Преподаватель другой организации не может 
        опубликовать чужую лекцию.
        """
        response = await client.post(
            f"/api/v1/lectures/{draft_lecture.id}/publish",
            headers=make_auth_headers(other_org_user)
        )

        # Согласно логике question_service.publish_lecture:
        # фильтрация идет по (id, org_id). Если не найдено — возвращается None,
        # а эндпоинт выбрасывает 404.
        assert response.status_code == 404
        assert "не найдена" in response.json()["detail"]

@pytest.mark.asyncio
class TestDeleteLecture:
    """
    Тестирование удаления лекций.
    Проверяем каскадное удаление и безопасность.
    """

    async def test_delete_own_lecture_success(
        self, client: AsyncClient, db: AsyncSession, teacher_user: User, published_lecture
    ):
        """Преподаватель может удалить лекцию своей организации."""
        # Убеждаемся, что лекция существует
        lecture_id = published_lecture.id
        
        response = await client.delete(
            f"/api/v1/lectures/{lecture_id}",
            headers=make_auth_headers(teacher_user)
        )

        assert response.status_code == 204
        
        # Проверяем в БД: лекция должна исчезнуть
        from app.models.lecture import Lecture
        from sqlalchemy import select
        
        # Используем свежий запрос в БД
        res = await db.execute(select(Lecture).where(Lecture.id == lecture_id))
        assert res.scalar_one_or_none() is None

    async def test_delete_other_org_lecture_forbidden(
        self, client: AsyncClient, other_org_user: User, published_lecture
    ):
        """
        Security: Нельзя удалить лекцию чужой организации.
        """
        response = await client.delete(
            f"/api/v1/lectures/{published_lecture.id}",
            headers=make_auth_headers(other_org_user)
        )

        assert response.status_code == 403
        assert "Доступ к удалению этой лекции запрещен" in response.json()["detail"]

    async def test_delete_as_student_forbidden(
        self, client: AsyncClient, student_user: User, published_lecture
    ):
        """RBAC: Студент не может удалять лекции."""
        response = await client.delete(
            f"/api/v1/lectures/{published_lecture.id}",
            headers=make_auth_headers(student_user)
        )

        assert response.status_code == 403