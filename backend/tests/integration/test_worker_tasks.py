import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select

from app.worker.tasks import _process_lecture_logic
from app.models.lecture import Lecture, LectureStatus
from app.models.chunk import Chunk
# Импортируем мок из контеста для единообразия векторов
from tests.conftest import MockEmbedderService 

@pytest.mark.asyncio
class TestLectureWorkerIntegration:
    async def test_process_lecture_logic_full_cycle(
        self, db, db_connection, teacher_user, draft_lecture
    ):
        db.add(draft_lecture)
        await db.flush()

        lecture_id = str(draft_lecture.id)
        file_key = f"{teacher_user.org_id}/{lecture_id}.txt"

        worker_session_factory = async_sessionmaker(
            bind=db_connection,
            expire_on_commit=False,
            class_=AsyncSession,
            join_transaction_mode="create_savepoint"
        )

        # 1. Моки S3
        mock_s3_client = AsyncMock()
        long_text = "This is a very long lecture content that needs to be at least one hundred characters long to pass the semantic chunker filter. It must be informative."
        mock_s3_client.get_object.return_value = {
            "Body": AsyncMock(read=AsyncMock(return_value=long_text.encode("utf-8")))
        }
        mock_s3_client.__aenter__.return_value = mock_s3_client

        # 2. Моки LLM
        from app.schemas.llm_schemas import QuestionsData, ReferenceData, Thesis
        mock_q_data = QuestionsData(questions=["What is Python?"])
        mock_ref_data = ReferenceData(
            reference_answer="Language", 
            key_theses=[Thesis(text="test", importance=3)]
        )

        # 3. Наш мок эмбеддера (чтобы не грузить torch)
        mock_embedder = MockEmbedderService()

        # 4. ПАТЧИМ ВСЁ
        with patch("aioboto3.Session.client", return_value=mock_s3_client), \
             patch("app.services.ai.generator.llm_generator.generate_questions", new_callable=AsyncMock, return_value=mock_q_data), \
             patch("app.services.ai.generator.llm_generator.generate_reference", new_callable=AsyncMock, return_value=mock_ref_data), \
             patch("app.worker.tasks.get_session_maker", return_value=worker_session_factory), \
             patch("app.worker.tasks.embedder", new=mock_embedder): # <--- ГЛАВНЫЙ ФИКС ДЛЯ ML

            # ДЕЙСТВИЕ
            await _process_lecture_logic(lecture_id, file_key)

        # 5. ПРОВЕРКА
        await db.refresh(draft_lecture)
        assert draft_lecture.status == LectureStatus.REVIEW_REQUIRED
        
        res_chunks = await db.execute(select(Chunk).where(Chunk.lecture_id == draft_lecture.id))
        chunks = res_chunks.scalars().all()
        assert len(chunks) > 0
        # Проверяем, что эмбеддинг создался (нашим моком)
        assert chunks[0].embedding is not None
        assert len(chunks[0].embedding) == 384