import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.ai.grading_service import GradingService
from app.models.question import Question
from app.schemas.llm_schemas import AIResultLabel

@pytest.mark.asyncio
class TestGradingServiceLogic:
    """
    Юнит-тестирование логики Hybrid Grading Core.
    Проверяем формулы агрегации и работу слоев.
    """

    @pytest.fixture
    def mock_deps(self, client): # Используем client чтобы подтянуть моки из conftest
        # В conftest.py уже есть MockEmbedderService и make_mock_llm_generator
        from tests.conftest import MockEmbedderService, make_mock_llm_generator
        
        embedder = MockEmbedderService()
        llm = make_mock_llm_generator()
        math = MagicMock()
        
        return embedder, llm, math

    async def test_evaluate_perfect_match(self, mock_deps):
        """Идеальное совпадение ответа с эталоном должно давать ~1.0."""
        embedder, llm, math = mock_deps
        
        # 1. Настраиваем LLM
        llm.evaluate_answer.return_value = AIResultLabel(label="correct", confidence_delta=0.9)
        
        # 2. ХАК ДЛЯ МОКА: Заставляем эмбеддер возвращать одинаковые векторы 
        # для ответа и для тезиса, чтобы Layer 3 (Theses) выдал 1.0
        fixed_vector = [0.1] * 384
        embedder.get_embeddings = MagicMock(return_value=[fixed_vector, fixed_vector])
        
        service = GradingService(embedder=embedder, llm_generator=llm, math_engine=math)
        
        question = Question(
            question_text="Что такое Python?",
            reference_answer="Язык программирования",
            key_theses=[{"text": "язык", "importance": 3}],
            question_type="open_ended"
        )

        result = await service.evaluate_answer(
            question=question,
            answer_text="Язык программирования",
            formula_data={}
        )

        # Теперь score должен быть (0.3*1 + 0.4*1 + 0.3*1) = 1.0
        assert result["final_score"] >= 0.9
        assert result["metrics"]["thesis_match"] == 1.0

    async def test_length_penalty_application(self, mock_deps):
        """Слишком короткий ответ должен получать штраф (penalty)."""
        embedder, llm, math = mock_deps
        llm.evaluate_answer.return_value = AIResultLabel(label="partially_correct", confidence_delta=0.5)
        
        service = GradingService(embedder=embedder, llm_generator=llm, math_engine=math)
        
        question = Question(
            question_text="Опишите принцип работы ДВС",
            reference_answer="Длинное описание цикла Карно и работы поршней...",
            key_theses=[{"text": "поршень", "importance": 3}],
            question_type="open_ended"
        )

        # Очень короткий ответ
        result = await service.evaluate_answer(
            question=question,
            answer_text="Это мотор.",
            formula_data={}
        )

        # Оценка должна быть существенно ниже из-за length_penalty
        assert result["final_score"] < 0.5

    async def test_formula_weight_boost(self, mock_deps):
        """В вопросах типа 'formula' вес математического движка должен быть решающим."""
        embedder, llm, math = mock_deps
        service = GradingService(embedder=embedder, llm_generator=llm, math_engine=math)
        
        # Математический движок говорит: "Формулы идентичны"
        math.find_best_match.return_value = 1.0
        llm.evaluate_answer.return_value = AIResultLabel(label="correct", confidence_delta=0.9)

        question = Question(
            question_text="Решите уравнение",
            reference_answer="x^2",
            question_type="formula",
            key_theses=[]
        )

        result = await service.evaluate_answer(
            question=question,
            answer_text="Ответ x в квадрате",
            formula_data={"latex": "x^2"}
        )

        assert result["final_score"] > 0.8
        math.find_best_match.assert_called_once()