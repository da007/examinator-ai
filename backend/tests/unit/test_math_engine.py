import pytest
from app.services.ai.math_engine import math_engine

class TestMathEngineLogic:
    """
    Юнит-тестирование детерминированного математического движка.
    Проверяем символьную эквивалентность и устойчивость к ошибкам.
    """

    def test_identical_expressions(self):
        """Прямое совпадение строк."""
        student = "x + 1"
        reference = "x + 1"
        assert math_engine.compare_expressions(student, reference) == 1.0

    def test_equivalent_expressions(self):
        """Символьная эквивалентность (коммутативность и скобки)."""
        # x + 1 эквивалентно 1 + x
        assert math_engine.compare_expressions("x + 1", "1 + x") == 1.0
        # (a+b)^2 эквивалентно a^2 + 2ab + b^2
        assert math_engine.compare_expressions("(a + b)^2", "a^2 + 2*a*b + b^2") == 1.0

    def test_different_expressions(self):
        """Разные выражения должны давать 0.0."""
        assert math_engine.compare_expressions("x + 1", "x + 2") == 0.0
        assert math_engine.compare_expressions("x^2", "x^3") == 0.0

    def test_malformed_latex_handling(self):
        """
        Невалидный LaTeX не должен вызывать падение (Crash).
        Движок должен вернуть 0.0 и позволить другим слоям (LLM/Embeddings) оценить ответ.
        """
        # Незакрытая скобка или просто текст
        student = "\\frac{1}{0" 
        reference = "1/0"
        
        # Мы не ожидаем исключения (Exception), ожидаем корректный выход
        result = math_engine.compare_expressions(student, reference)
        assert result == 0.0

    def test_latex_normalization(self):
        """Проверка очистки специфичных для LaTeX команд пробелов."""
        # \; и \! — команды пробелов в LaTeX
        student = "x \; + \; 1"
        reference = "x+1"
        assert math_engine.compare_expressions(student, reference) == 1.0