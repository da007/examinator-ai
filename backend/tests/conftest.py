# tests/conftest.py
import uuid
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy import text

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.base import Base
from app.db import session as db_session_module
from app.main import app
from app.api.dependencies import get_db
from app.models.user import User, UserRole
from app.models.lecture import Lecture, LectureStatus
from app.models.chunk import Chunk
from app.models.question import Question
from app.models.subject import Subject


TEST_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
TEST_ORG_ID_2 = uuid.UUID("00000000-0000-0000-0000-000000000002")


# ─────────────────────────────────────────────────────────────────────────────
# AI Моки — без torch
# ─────────────────────────────────────────────────────────────────────────────

class MockEmbedderService:
    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        result = []
        for t in texts:
            seed = hash(t) % (2**31)
            vec = [((seed * (i + 1)) % 1000) / 1000.0 for i in range(384)]
            norm = sum(x**2 for x in vec) ** 0.5
            result.append([x / norm for x in vec])
        return result

    def get_query_embedding(self, query: str) -> list[float]:
        return self.get_embeddings([query])[0]


def make_mock_llm_generator():
    mock = MagicMock()

    questions_result = MagicMock()
    questions_result.questions = ["Что такое тестирование?", "Зачем нужны тесты?"]
    mock.generate_questions = AsyncMock(return_value=questions_result)

    reference_result = MagicMock()
    reference_result.reference_answer = "Тестирование — это проверка качества кода."
    reference_result.key_theses = [
        MagicMock(model_dump=lambda: {"text": "Качество", "importance": 3}),
    ]
    mock.generate_reference = AsyncMock(return_value=reference_result)

    eval_result = MagicMock()
    eval_result.label = "correct"
    eval_result.confidence_delta = 0.9
    mock.evaluate_answer = AsyncMock(return_value=eval_result)

    return mock


# ─────────────────────────────────────────────────────────────────────────────
# Engine — session scope (создаётся один раз, это пул — не соединение)
# ─────────────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="function") # ВЕРНУТЬ function scope
async def test_engine():
    """Создает Engine и схему БД заново для КАЖДОГО теста."""
    engine = create_async_engine(
        str(settings.postgres.DATABASE_URL),
        echo=False,
        future=True,
        pool_size=5,
        max_overflow=0,
    )

    # Инициализация схемы для каждого теста
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Инъекция
    db_session_module._engine = engine
    db_session_module._session_maker = None

    yield engine

    # Закрытие
    await engine.dispose()
    db_session_module._engine = None
    db_session_module._session_maker = None
# ─────────────────────────────────────────────────────────────────────────────
# DB fixtures — function scope: каждый тест получает свежую транзакцию
# ─────────────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="function") # Соединение по-прежнему на каждый тест
async def db_connection(test_engine) -> AsyncGenerator[AsyncConnection, None]:
    """
    Берет соединение из пула Engine. 
    Открывает транзакцию, которая откатится в конце теста.
    """
    async with test_engine.connect() as conn:
        # Стартуем транзакцию уровня соединения
        transaction = await conn.begin()
        yield conn
        # После теста откатываем ВСЕ изменения (включая коммиты внутри эндпоинтов)
        await transaction.rollback()


@pytest_asyncio.fixture
async def db(db_connection: AsyncConnection) -> AsyncGenerator[AsyncSession, None]:
    """
    AsyncSession привязана к соединению теста.
    join_transaction_mode="create_savepoint" позволяет сервисам вызывать
    commit() внутри теста — создаётся savepoint, а не реальный commit.
    """
    session = AsyncSession(
        bind=db_connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield session
    finally:
        await session.close()


# ─────────────────────────────────────────────────────────────────────────────
# HTTP client — function scope
# ─────────────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    mock_embedder = MockEmbedderService()
    mock_llm = make_mock_llm_generator()

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    import app.services.ai.grading_service as gs_module
    import app.worker.tasks as tasks_module
    import app.worker.grading_tasks as gt_module

    orig_embedder = gs_module.grading_service._embedder
    orig_llm = gs_module.grading_service._llm_generator
    orig_process = tasks_module.process_lecture_task.delay
    orig_grade = gt_module.grade_exam_session_task.delay

    gs_module.grading_service._embedder = mock_embedder
    gs_module.grading_service._llm_generator = mock_llm
    tasks_module.process_lecture_task.delay = MagicMock()
    gt_module.grade_exam_session_task.delay = MagicMock()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
    gs_module.grading_service._embedder = orig_embedder
    gs_module.grading_service._llm_generator = orig_llm
    tasks_module.process_lecture_task.delay = orig_process
    gt_module.grade_exam_session_task.delay = orig_grade


# ─────────────────────────────────────────────────────────────────────────────
# Фабрики тестовых данных — function scope
# ─────────────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def teacher_user(db: AsyncSession) -> User:
    user = User(
        email="teacher@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Test Teacher",
        role=UserRole.TEACHER,
        org_id=TEST_ORG_ID,
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user

@pytest_asyncio.fixture
async def ta_user(db: AsyncSession) -> User:
    """Фикстура ассистента."""
    user = User(
        email="ta@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Test TA",
        role=UserRole.TA,
        org_id=TEST_ORG_ID,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user

@pytest_asyncio.fixture
async def test_subject(db: AsyncSession, teacher_user: User) -> Subject:
    """Базовая дисциплина для тестов."""
    subject = Subject(
        name="Тестовая дисциплина",
        org_id=TEST_ORG_ID,
        teacher_id=teacher_user.id
    )
    db.add(subject)
    await db.flush()
    return subject

@pytest_asyncio.fixture
async def student_user(db: AsyncSession) -> User:
    user = User(
        email="student@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Test Student",
        role=UserRole.STUDENT,
        org_id=TEST_ORG_ID,
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def other_org_user(db: AsyncSession) -> User:
    user = User(
        email="other@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Other Org User",
        role=UserRole.TEACHER,
        org_id=TEST_ORG_ID_2,
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def published_lecture(db: AsyncSession, teacher_user: User, test_subject: Subject) -> Lecture:
    lecture = Lecture(
        title="Тестовая лекция по Python",
        org_id=TEST_ORG_ID,
        subject_id=test_subject.id,
        teacher_id=teacher_user.id,
        status=LectureStatus.PUBLISHED,
    )
    db.add(lecture)
    await db.flush()

    chunk = Chunk(
        lecture_id=lecture.id,
        text_content="Python — интерпретируемый язык программирования высокого уровня.",
        embedding=[0.1] * 384,
        order_index=0,
    )
    db.add(chunk)
    await db.flush()

    question = Question(
        chunk_id=chunk.id,
        question_text="Что такое Python?",
        reference_answer="Python — интерпретируемый язык программирования.",
        key_theses=[{"text": "интерпретируемый", "importance": 3}],
        difficulty="medium",
        question_type="open_ended",
    )
    db.add(question)
    await db.flush()
    await db.refresh(lecture)
    return lecture


@pytest_asyncio.fixture
async def draft_lecture(db: AsyncSession, teacher_user: User, test_subject: Subject) -> Lecture:
    lecture = Lecture(
        title="Черновая лекция",
        org_id=TEST_ORG_ID,
        subject_id=test_subject.id,
        teacher_id=teacher_user.id,
        status=LectureStatus.UPLOADED,
    )
    db.add(lecture)
    await db.flush()
    await db.refresh(lecture)
    return lecture


# ─────────────────────────────────────────────────────────────────────────────
# Auth хелпер
# ─────────────────────────────────────────────────────────────────────────────

def make_auth_headers(user: User) -> dict:
    from app.core.security import create_access_token
    token = create_access_token(subject=str(user.id))
    return {"Authorization": f"Bearer {token}"}