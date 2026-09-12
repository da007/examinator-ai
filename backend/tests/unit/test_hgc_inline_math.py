import pytest
from unittest.mock import MagicMock, AsyncMock
from app.services.ai.grading_service import GradingService
from app.models.question import Question
from app.schemas.llm_schemas import AIResultLabel

@pytest.mark.asyncio
async def test_grading_with_inline_math_success():
    # 1. Мокаем зависимости
    from tests.conftest import MockEmbedderService
    embedder = MockEmbedderService()
    llm = MagicMock()
    llm.evaluate_answer = AsyncMock(return_value=AIResultLabel(label="correct", confidence_delta=1.0))
    
    # 2. Инициализируем сервис
    service = GradingService(embedder=embedder, llm_generator=llm)
    
    question = Question(
        question_text="Чему равна энергия?",
        reference_answer="E=mc^2",
        question_type="formula",
        key_theses=[]
    )
    
    # Студент написал формулу внутри текста
    answer_text = r"Согласно Эйнштейну, энергия $$E=mc^2$$."
    
    result = await service.evaluate_answer(question, answer_text, {})
    
    # Итоговый балл должен быть высоким, так как формула совпала
    assert result["final_score"] > 0.8
    assert result["metrics"]["math_match"] == 1.0