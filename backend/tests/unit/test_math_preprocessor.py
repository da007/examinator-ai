import pytest
from app.services.ai.math_preprocessor import math_preprocessor

def test_extract_inline_math():
    # Используем r"..." для корректной обработки обратных слешей в LaTeX
    text = r"Сила равна \(F=ma\), а энергия $$\text{E}=mc^2$$."
    masked, formulas = math_preprocessor.process(text)
    
    assert "F=ma" in formulas
    # Теперь \t не превратится в табуляцию
    assert r"\text{E}=mc^2" in formulas
    assert "[MATH_0]" in masked
    assert "[MATH_1]" in masked
    assert "F=ma" not in masked

def test_no_math():
    text = "Просто текст без формул."
    masked, formulas = math_preprocessor.process(text)
    assert masked == text
    assert formulas == []