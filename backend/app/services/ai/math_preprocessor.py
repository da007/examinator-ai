import re
from typing import List, Tuple

class MathPreprocessor:
    """
    Утилита для поиска и маскирования LaTeX формул в тексте.
    Поддерживает форматы: $$...$$ и \(...\)
    """
    # Паттерн для $$formula$$ и \(formula\)
    MATH_PATTERN = re.compile(r'(\$\$.*?\$\$|\\\(.*?\\\))', re.DOTALL)

    @classmethod
    def process(cls, text: str) -> Tuple[str, List[str]]:
        """
        Извлекает формулы и возвращает маскированный текст + список формул.
        Пример: "E=mc2" -> ("Энергия [MATH_0]", ["E=mc^2"])
        """
        if not text:
            return "", []

        extracted_formulas = []
        
        def replace_func(match):
            formula = match.group(0)
            # Очищаем от тегов
            clean_formula = formula
            if formula.startswith('$$') and formula.endswith('$$'):
                clean_formula = formula[2:-2]
            elif formula.startswith('\\(') and formula.endswith('\\)'):
                clean_formula = formula[2:-2]
            
            idx = len(extracted_formulas)
            extracted_formulas.append(clean_formula.strip())
            return f"[MATH_{idx}]"

        masked_text = cls.MATH_PATTERN.sub(replace_func, text)
        return masked_text, extracted_formulas

math_preprocessor = MathPreprocessor()