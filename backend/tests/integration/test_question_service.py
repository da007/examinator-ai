import pytest
from app.services.question_service import question_service
from app.schemas.question import QuestionUpdate
from app.models.lecture import LectureStatus

@pytest.mark.asyncio
class TestQuestionServiceGet:
    """
    Интеграционное тестирование сервиса вопросов (Чтение).
    Фокус на Multi-tenancy и Eager Loading связей.
    """

    async def test_get_questions_by_lecture_success(self, db, published_lecture):
        """Сервис успешно возвращает вопросы с подгруженными связями."""
        questions = await question_service.get_questions_by_lecture(
            db, 
            lecture_id=published_lecture.id, 
            org_id=published_lecture.org_id
        )
        
        assert len(questions) == 1
        q = questions[0]
        
        # ПРОВЕРКА EAGER LOADING:
        # Если joinedload не сработал, обращение к q.chunk вызовет 
        # sqlalchemy.exc.MissingGreenlet (в асинхронном режиме)
        assert q.chunk is not None
        assert q.chunk.lecture_id == published_lecture.id

    async def test_get_questions_filters_by_org(self, db, published_lecture, other_org_user):
        """Сервис должен вернуть пустой список, если org_id не совпадает."""
        questions = await question_service.get_questions_by_lecture(
            db, 
            lecture_id=published_lecture.id, 
            org_id=other_org_user.org_id
        )
        
        assert len(questions) == 0

    async def test_get_question_safe_wrong_org(self, db, published_lecture, other_org_user):
        """Безопасное получение одного вопроса возвращает None для чужой организации."""
        # Сначала получим реальный ID вопроса правильным запросом
        questions = await question_service.get_questions_by_lecture(
            db, 
            lecture_id=published_lecture.id, 
            org_id=published_lecture.org_id
        )
        q_id = questions[0].id

        # Теперь пытаемся получить его же, но с чужим org_id
        secure_q = await question_service.get_question_safe(
            db, 
            question_id=q_id, 
            org_id=other_org_user.org_id
        )
        
        assert secure_q is None

@pytest.mark.asyncio
class TestQuestionServiceMutations:
    """
    Интеграционное тестирование сервиса вопросов (Запись/Изменение).
    Фокус на Pydantic-маппинг, коммиты и изменение состояний.
    """

    async def test_update_question_success(self, db, published_lecture):
        """Сервис корректно применяет Pydantic схему и обновляет БД."""
        # 1. Получаем вопрос
        questions = await question_service.get_questions_by_lecture(
            db, lecture_id=published_lecture.id, org_id=published_lecture.org_id
        )
        target_q = questions[0]
        original_answer = target_q.reference_answer

        # 2. Формируем DTO для частичного обновления
        update_data = QuestionUpdate(question_text="Абсолютно новый текст?")

        # 3. Вызываем сервис
        updated_q = await question_service.update_question(
            db, db_obj=target_q, obj_in=update_data
        )

        assert updated_q.question_text == "Абсолютно новый текст?"
        # Убеждаемся, что остальные поля не затерлись (exclude_unset=True сработал)
        assert updated_q.reference_answer == original_answer

    async def test_delete_question_success(self, db, published_lecture):
        """Сервис удаляет вопрос и возвращает True."""
        questions = await question_service.get_questions_by_lecture(
            db, lecture_id=published_lecture.id, org_id=published_lecture.org_id
        )
        q_id = questions[0].id

        # Удаляем
        is_deleted = await question_service.delete_question(db, question_id=q_id)
        assert is_deleted is True

        # Проверяем, что вопрос реально исчез
        check_q = await question_service.get_question_safe(
            db, question_id=q_id, org_id=published_lecture.org_id
        )
        assert check_q is None

    async def test_delete_question_not_found(self, db):
        """Удаление несуществующего вопроса возвращает False (не падает)."""
        import uuid
        is_deleted = await question_service.delete_question(db, question_id=uuid.uuid4())
        assert is_deleted is False

    async def test_publish_lecture_success(self, db, draft_lecture):
        """Смена статуса лекции с UPLOADED на PUBLISHED."""
        assert draft_lecture.status == LectureStatus.UPLOADED

        published = await question_service.publish_lecture(
            db, lecture_id=draft_lecture.id, org_id=draft_lecture.org_id
        )

        assert published is not None
        assert published.status == LectureStatus.PUBLISHED