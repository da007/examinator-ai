import logging
import numpy as np
from typing import Dict, Any, List, Optional

from app.models.question import Question
from app.services.ai.math_preprocessor import math_preprocessor

logger = logging.getLogger(__name__)


class GradingService:
    """
    Hybrid Grading Core (HGC) Orchestrator.

    Зависимости (embedder, math_engine, llm_generator) принимаются через __init__,
    что позволяет подменять их в тестах без патчинга.
    Если не переданы — резолвятся лениво при первом evaluate_answer().
    Это гарантирует что torch не грузится при импорте этого модуля.
    """

    def __init__(
        self,
        embedder=None,
        math_engine=None,
        llm_generator=None,
    ):
        # None означает "использовать дефолтный синглтон лениво"
        self._embedder = embedder
        self._math_engine = math_engine
        self._llm_generator = llm_generator

    # --- Ленивые резолверы дефолтных зависимостей ---

    @property
    def embedder(self):
        if self._embedder is None:
            from app.services.ai.embedder import embedder as default
            self._embedder = default
        return self._embedder

    @property
    def math_engine(self):
        if self._math_engine is None:
            from app.services.ai.math_engine import math_engine as default
            self._math_engine = default
        return self._math_engine

    @property
    def llm_generator(self):
        if self._llm_generator is None:
            from app.services.ai.generator import llm_generator as default
            self._llm_generator = default
        return self._llm_generator

    # --- Вспомогательные методы ---

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        a, b = np.array(v1), np.array(v2)
        norm = np.linalg.norm(a) * np.linalg.norm(b)
        if norm == 0:
            return 0.0
        return float(np.dot(a, b) / norm)

    # --- Основной метод оценки ---

    async def evaluate_answer(
        self,
        question: Question,
        answer_text: str,
        formula_data: Dict[str, Any],
    ) -> Dict[str, Any]:

        masked_text, inline_formulas = math_preprocessor.process(answer_text)

        # Собираем кандидатов из ответа студента (из текста + спецполе фронтенда)
        candidate_formulas = list(inline_formulas)
        if formula_data.get("latex"):
            candidate_formulas.append(formula_data.get("latex"))

        # FIX-4: Layer 1 — Math (Task 2.2)
        # reference_answer хранит полный текст, а не «голый» LaTeX.
        # Извлекаем формулы из эталонного ответа через тот же MathPreprocessor,
        # чтобы сравнивать формулу-с-формулой через SymPy, а не формулу-с-текстом.
        _, ref_formulas = math_preprocessor.process(question.reference_answer)

        formula_score = 0.0
        has_math = question.question_type == "formula" or candidate_formulas or ref_formulas
        if has_math:
            if ref_formulas and candidate_formulas:
                # Для каждой эталонной формулы ищем лучшее совпадение среди кандидатов
                for ref_f in ref_formulas:
                    score = self.math_engine.find_best_match(candidate_formulas, ref_f)
                    if score > formula_score:
                        formula_score = score
                    if formula_score >= 1.0:
                        break
            elif candidate_formulas and not ref_formulas:
                # Эталон не содержит формул в маркерах — fallback на сравнение
                # с полным текстом (логика до фикса, оставляем как запасной вариант)
                formula_score = self.math_engine.find_best_match(
                    candidate_formulas,
                    question.reference_answer,
                )
            # Если у студента нет формул, но у эталона есть → formula_score = 0.0 (верно)

        # Layer 2: Embeddings
        embeddings = self.embedder.get_embeddings(
            [masked_text, question.reference_answer]
        )
        similarity_score = self._cosine_similarity(embeddings[0], embeddings[1])

        # Layer 3: Thesis Matcher
        matched_count = 0
        theses_details = []
        if question.key_theses:
            for thesis in question.key_theses:
                t_vec = self.embedder.get_embeddings([thesis["text"]])[0]
                t_sim = self._cosine_similarity(t_vec, embeddings[0])
                is_match = t_sim > 0.85
                if is_match:
                    matched_count += 1
                theses_details.append({"text": thesis["text"], "match": is_match})

        thesis_score = (
            matched_count / len(question.key_theses) if question.key_theses else 1.0
        )

        # Layer 4: LLM Arbitrage
        llm_result = await self.llm_generator.evaluate_answer(
            question=question.question_text,
            reference=question.reference_answer,
            student_answer=answer_text,
        )

        # Aggregation
        t5_map = {"correct": 1.0, "partially_correct": 0.5, "wrong": 0.0}
        t5_score = t5_map.get(llm_result.label, 0.0)

        thesis_score = (
            matched_count / len(question.key_theses) if question.key_theses else 0.0
        )

        preliminary_score = (
            0.3 * similarity_score + 0.4 * thesis_score + 0.3 * t5_score
        )
        length_penalty = min(
            len(answer_text) / max(len(question.reference_answer), 1), 1.0
        )
        final_score = preliminary_score * (0.8 + 0.2 * length_penalty)

        if llm_result.label == "wrong":
            # Режем балл в 5 раз (штраф за бред). 
            # Даже если векторы случайно совпали на 20%, студент получит 4%.
            final_score = final_score * 0.2 

        if question.question_type == "formula":
            final_score = final_score * 0.4 + formula_score * 0.6

        confidence = (
            0.4 * similarity_score
            + 0.4 * thesis_score
            + 0.2 * llm_result.confidence_delta
        )
        if formula_score == 0 and question.question_type == "formula":
            confidence *= 0.5

        final_score = max(0.0, min(final_score, 1.0))

        return {
            "final_score": round(final_score, 2),
            "confidence_score": round(confidence, 2),
            "metrics": {
                "similarity": round(similarity_score, 3),
                "thesis_match": thesis_score,
                "t5_label": llm_result.label,
                "math_match": formula_score,
                "explanation": None,
            },
            "theses_details": theses_details,
        }


# Синглтон для воркеров и продакшена.
# Создание дешёвое — torch не грузится до первого evaluate_answer().
grading_service = GradingService()