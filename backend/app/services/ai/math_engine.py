import logging
from typing import Optional, List
from sympy import simplify, expand, count_ops
from sympy.parsing.latex import parse_latex
from sympy.core.sympify import SympifyError

logger = logging.getLogger(__name__)

class MathEngine:
    """
    Движок для детерминированной проверки математических выражений.
    Использует SymPy для символьного сравнения формул.
    """

    def find_best_match(self, student_formulas: List[str], reference_latex: str) -> float:
        """
        Task 2.2: Ищет среди списка формул студента ту, которая 
        максимально близка к эталону.
        """
        if not student_formulas or not reference_latex:
            return 0.0

        best_score = 0.0
        
        for f in student_formulas:
            current_score = self.compare_expressions(f, reference_latex)
            if current_score > best_score:
                best_score = current_score
            
            # Если нашли идеальное совпадение, дальше можно не искать
            if best_score >= 1.0:
                return 1.0
                
        return best_score

    def normalize_latex(self, latex_str: str) -> str:
        """Базовая очистка LaTeX строки перед парсингом."""
        if not latex_str:
            return ""
        # Убираем лишние пробелы, специфичные для некоторых редакторов команды
        clean_latex = latex_str.replace(r'\;', '').replace(r'\:', '').replace(r'\!', '')
        return clean_latex.strip()

    def compare_expressions(self, student_latex: str, reference_latex: str) -> float:
        """
        Сравнивает две LaTeX формулы.
        Возвращает 1.0 если они эквивалентны, иначе 0.0.
        """
        s_latex = self.normalize_latex(student_latex)
        r_latex = self.normalize_latex(reference_latex)

        if not s_latex or not r_latex:
            return 0.0

        if s_latex == r_latex:
            return 1.0

        try:
            # Парсим LaTeX в объекты SymPy
            # Примечание: требует установленного antlr4-python3-runtime
            expr_student = parse_latex(s_latex)
            expr_ref = parse_latex(r_latex)

            # Проверка на эквивалентность через упрощение разности
            # simplify(A - B) == 0 — самый надежный способ
            diff = simplify(expr_student - expr_ref)
            
            if diff == 0:
                return 1.0
            
            # Дополнительная проверка через раскрытие скобок (на случай сложных полиномов)
            if expand(expr_student) == expand(expr_ref):
                return 1.0

        except Exception as e:
            logger.error(f"SymPy parsing error: {e} | Student: {s_latex} | Ref: {r_latex}")
            # Если не удалось распарсить (например, не математика, а текст в блоке формул),
            # возвращаем 0.0, чтобы Layer 2 (Семантика) взял на себя оценку.
            return 0.0

        return 0.0

    def get_complexity_penalty(self, student_latex: str, reference_latex: str) -> float:
        """
        [Advanced] Проверка на 'читерство' или избыточность.
        Если формула студента в 5 раз сложнее эталона, возможно он 'льет воду' в математике.
        """
        try:
            expr_s = parse_latex(student_latex)
            expr_r = parse_latex(reference_latex)
            
            ops_s = count_ops(expr_s)
            ops_r = count_ops(expr_r)
            
            if ops_s > ops_r * 5:
                return 0.8 # Штраф 20% за избыточность
        except:
            pass
        return 1.0

math_engine = MathEngine()